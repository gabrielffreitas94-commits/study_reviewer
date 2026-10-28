/**
 * study_canvas.js — Motor Interativo do Canvas RPG: Forja Ancestral & Grafo de Maestria
 * Suporta pan, zoom, arrastar medalhões, traçar vínculos de pré-requisito, criação rápida de nó filho (1-click) e Side Drawer interativo.
 */

(function () {
    'use strict';

    // Estado Global da Aplicação no Canvas
    const state = {
        mapId: window.CURRENT_MAP_ID || null,
        isOwner: window.CURRENT_MAP_IS_OWNER || false,
        graph: { map: null, nodes: [], edges: [] },
        view: { x: 80, y: 80, scale: 1.0 },
        isPanning: false,
        panStart: { x: 0, y: 0 },
        activeDragNode: null,
        dragOffset: { x: 0, y: 0 },
        hasDragged: false,
        interactionMode: 'study', // 'study' (Modo Jornada) ou 'edit' (Modo Forja)
        connectModeActive: false,
        connectSourceNodeId: null,
        selectedNode: null,
        quickAddParentNode: null,
        currentDrawerTab: 'content',
        batchSaveTimer: null,
        pendingPositions: new Map(),
        contextMenuNode: null,
        contextMenuWorldPos: null,
        pendingSpawnCoords: null,
    };

    // Mapeamento Rúnico de Todos os Ícones RPG
    const ICON_MAP = {
        calculator: '📐',
        'trending-up': '📈',
        dice: '🎲',
        activity: '⚡',
        brain: '🧠',
        book: '📖',
        code: '💻',
        cpu: '⚙️',
        database: '🗄️',
        globe: '🌐',
        layers: '📚',
        shield: '🛡️',
        terminal: '🖥️',
        zap: '⚡',
        award: '🏆',
        compass: '🧭',
        feather: '🪶',
        flame: '🔥',
        key: '🗝️',
        scroll: '📜',
        sword: '⚔️',
        fire: '🔥',
        flask: '🧪',
        gem: '💎',
        rune: '🔮',
    };

    // Elementos do DOM
    const viewport = document.getElementById('canvas-viewport');
    const container = document.getElementById('canvas-container');
    const edgesGroup = document.getElementById('edges-group');
    const nodesLayer = document.getElementById('nodes-layer');
    const nodeModal = document.getElementById('node-modal');

    // Inicialização ao carregar a página
    document.addEventListener('DOMContentLoaded', () => {
        setupPanAndZoom();
        loadGraph();
    });

    // --- Carregamento e Renderização do Grafo ---

    async function loadGraph() {
        if (!state.mapId) return;

        try {
            const res = await fetch(`/api/v1/study-maps/${state.mapId}`);
            if (!res.ok) {
                const err = await res.json();
                alert('Erro ao carregar mapa: ' + (err.detail || 'Falha de rede'));
                return;
            }
            state.graph = await res.json();
            if (state.selectedNode) {
                state.selectedNode = state.graph.nodes.find(n => n.id === state.selectedNode.id) || state.selectedNode;
                renderPrerequisites(state.selectedNode);
                renderDrawerPrerequisites(state.selectedNode);
            }
            renderAll();
        } catch (err) {
            console.error('Falha ao buscar grafo da forja:', err);
        }
    }

    function renderAll() {
        renderEdges();
        renderNodes();
    }

    // Renderiza os vínculos de pré-requisito (arestas SVG de energia)
    function renderEdges() {
        if (!edgesGroup) return;
        edgesGroup.innerHTML = '';
        const nodeMap = new Map(state.graph.nodes.map(n => [n.id, n]));

        state.graph.edges.forEach(edge => {
            const source = nodeMap.get(edge.source_node_id);
            const target = nodeMap.get(edge.target_node_id);
            if (!source || !target) return;

            // Centro do medalhão (raio ~40px, centro em 40,40)
            const sx = source.pos_x + 40;
            const sy = source.pos_y + 40;
            const tx = target.pos_x + 40;
            const ty = target.pos_y + 40;
            const dx = tx - sx;
            const dy = ty - sy;
            const dist = Math.hypot(dx, dy);
            const R = 42; // Medallion outer radius

            let startX = sx, startY = sy, endX = tx, endY = ty;
            if (dist > R * 2) {
                const ux = dx / dist;
                const uy = dy / dist;
                startX = sx + R * ux;
                startY = sy + R * uy;
                endX = tx - R * ux;
                endY = ty - R * uy;
            }

            const reqLevel = edge.required_level || 1;
            const isUnlocked = (source.effective_level || 0) >= reqLevel;

            // Curva Bezier cúbica suave conectando os perímetros externos
            const spanX = endX - startX;
            const cx1 = startX + spanX * 0.45;
            const cy1 = startY;
            const cx2 = startX + spanX * 0.55;
            const cy2 = endY;

            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('d', `M ${startX} ${startY} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${endX} ${endY}`);
            path.setAttribute('fill', 'none');
            path.setAttribute('stroke', isUnlocked ? 'url(#edge-unlocked-grad)' : '#3b322c');
            path.setAttribute('stroke-width', isUnlocked ? '3.5' : '2');
            if (!isUnlocked) {
                path.setAttribute('stroke-dasharray', '6,6');
            } else {
                path.style.filter = 'drop-shadow(0 0 6px rgba(240, 200, 105, 0.7))';
            }
            path.setAttribute('marker-end', isUnlocked ? 'url(#arrow-unlocked)' : 'url(#arrow-locked)');

            if (isUnlocked) {
                path.classList.add('transition-all');
            }

            // No Modo Forja, clicar na linha permite remover o vínculo
            if (state.interactionMode === 'edit') {
                path.style.cursor = 'pointer';
                path.style.pointerEvents = 'stroke';
                path.setAttribute('stroke-width', '10');
                path.setAttribute('stroke-opacity', isUnlocked ? '0.85' : '0.5');
                path.addEventListener('click', (e) => {
                    e.stopPropagation();
                    if (confirm('Deseja remover esta conexão de pré-requisito?')) {
                        deleteEdge(edge.id);
                    }
                });
            }

            edgesGroup.appendChild(path);
        });
    }

    // Renderiza os medalhões circulares de habilidade
    function renderNodes() {
        if (!nodesLayer) return;
        nodesLayer.innerHTML = '';

        state.graph.nodes.forEach(node => {
            const el = document.createElement('div');
            el.className = 'absolute flex flex-col items-center cursor-pointer group select-none transition-transform duration-75';
            el.style.left = `${node.pos_x}px`;
            el.style.top = `${node.pos_y}px`;
            el.dataset.nodeId = node.id;

            const isLocked = !node.is_unlocked;
            const isOverdue = node.overdue_questions_count > 0;
            const svgIconMarkup = (typeof window.getRpgIconSvg === 'function')
                ? window.getRpgIconSvg(node.icon, 'w-8 h-8 text-[#f0c869] drop-shadow')
                : `<span class="text-3xl filter drop-shadow">${ICON_MAP[node.icon] || '📜'}</span>`;

            // Aura e estilização conforme patente SRS
            let ringClass = 'border-[#574737] bg-[#1c1612] text-[#a39276]';
            let glowEffect = 'shadow-[0_4px_16px_rgba(0,0,0,0.7)]';
            let rankLabel = `Nv. ${node.effective_level || 0}`;

            if (isLocked) {
                ringClass = 'border-[#3b322c] bg-[#14100d] opacity-50 grayscale';
                rankLabel = '🔒 SELADO';
            } else if (node.effective_level >= 5) {
                // Ouro Lendário (Rank V - VI)
                ringClass = 'border-[#f0c869] bg-[#251c14] ring-2 ring-[#f0c869]/50';
                glowEffect = 'shadow-[0_0_25px_rgba(240,200,105,0.7)]';
            } else if (node.effective_level >= 3) {
                // Prata Rúnica / Ouro Intermediário (Rank III - IV)
                ringClass = 'border-[#c89b3c] bg-[#1f1813] ring-1 ring-[#c89b3c]/40';
                glowEffect = 'shadow-[0_0_18px_rgba(200,155,60,0.5)]';
            } else if (node.effective_level >= 1) {
                // Bronze Forjado (Rank I - II)
                ringClass = 'border-[#785a28] bg-[#1a1410] ring-1 ring-[#785a28]/40';
                glowEffect = 'shadow-[0_0_14px_rgba(120,90,40,0.4)]';
            }

            // Pulsação Carmesim de Decaimento se houver revisões atrasadas
            let overduePulse = '';
            if (isOverdue && !isLocked) {
                overduePulse = 'ring-4 ring-[#e11d48]/70 shadow-[0_0_22px_rgba(225,29,72,0.85)] animate-pulse';
            }

            el.innerHTML = `
                <div class="relative w-20 h-20 rounded-full border-2 ${ringClass} ${glowEffect} ${overduePulse} flex items-center justify-center transition-all duration-200 group-hover:scale-110">
                    <div class="w-9 h-9 flex items-center justify-center">${svgIconMarkup}</div>

                    ${isLocked ? `
                        <div class="absolute -top-1.5 -right-1.5 w-6 h-6 rounded-full bg-[#14100d] border border-[#3b322c] flex items-center justify-center text-xs shadow-md">
                            🔒
                        </div>
                    ` : ''}

                    ${isOverdue && !isLocked ? `
                        <div class="absolute -top-1.5 -right-1.5 px-1.5 py-0.5 rounded-full bg-[#e11d48] border border-[#f5ebd6] text-[10px] font-black text-white shadow-lg animate-bounce">
                            ! ${node.overdue_questions_count}
                        </div>
                    ` : ''}

                    <div class="absolute -bottom-2.5 px-2 py-0.5 rounded-md bg-[#0c0908] border border-[#785a28] text-[9px] font-cinzel font-bold tracking-wider ${node.effective_level >= 1 ? 'text-[#f0c869]' : 'text-[#a39276]'}">
                        ${rankLabel}
                    </div>

                    <button
                        type="button"
                        data-quick-add-parent="${node.id}"
                        title="Criar nó filho conectado a ${escapeHtml(node.title)}"
                        class="quick-add-child-btn absolute -right-3 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-[#c89b3c] hover:bg-[#f0c869] text-[#0c0908] border-2 border-[#0c0908] font-bold text-sm flex items-center justify-center shadow-lg hover:scale-125 transition-all z-20"
                    >
                        +
                    </button>
                </div>
                <div class="mt-3 px-3 py-1 rounded-xl bg-[#14100d]/90 backdrop-blur border border-[#785a28]/60 text-center max-w-[150px] shadow-lg">
                    <span class="text-xs font-bold font-cinzel text-[#f5ebd6] truncate block">${escapeHtml(node.title)}</span>
                </div>
            `;

            // Botão de criação rápida de nó filho (1-click)
            const quickAddBtn = el.querySelector('.quick-add-child-btn');
            if (quickAddBtn) {
                quickAddBtn.addEventListener('mousedown', (e) => e.stopPropagation());
                quickAddBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    e.preventDefault();
                    quickAddChildNode(node);
                });
            }

            // Eventos do mouse e clique no medalhão
            el.addEventListener('mousedown', (e) => onNodeMouseDown(e, node));
            el.addEventListener('click', (e) => onNodeClick(e, node));
            el.addEventListener('contextmenu', (e) => onNodeContextMenu(e, node));

            nodesLayer.appendChild(el);
        });
    }

    // --- Pan e Zoom da Câmera Ancestral ---

    function setupPanAndZoom() {
        if (!viewport) return;

        viewport.addEventListener('mousedown', (e) => {
            closeContextMenus();
            if (e.target === viewport || e.target.id === 'canvas-container' || e.target.tagName === 'svg') {
                state.isPanning = true;
                state.panStart.x = e.clientX - state.view.x;
                state.panStart.y = e.clientY - state.view.y;
            }
        });

        viewport.addEventListener('contextmenu', (e) => {
            if (e.target === viewport || e.target.id === 'canvas-container' || e.target.tagName === 'svg') {
                onCanvasContextMenu(e);
            }
        });

        window.addEventListener('mousemove', (e) => {
            if (state.isPanning) {
                state.view.x = e.clientX - state.panStart.x;
                state.view.y = e.clientY - state.panStart.y;
                applyTransform();
            } else if (state.activeDragNode) {
                onNodeMouseMove(e);
            }
        });

        window.addEventListener('mouseup', () => {
            state.isPanning = false;
            if (state.activeDragNode) {
                onNodeMouseUp();
            }
        });

        viewport.addEventListener('wheel', (e) => {
            e.preventDefault();
            closeContextMenus();
            const zoomFactor = e.deltaY < 0 ? 1.1 : 0.9;
            const newScale = Math.min(Math.max(state.view.scale * zoomFactor, 0.4), 2.5);

            const rect = viewport.getBoundingClientRect();
            const mouseX = e.clientX - rect.left;
            const mouseY = e.clientY - rect.top;

            state.view.x = mouseX - (mouseX - state.view.x) * (newScale / state.view.scale);
            state.view.y = mouseY - (mouseY - state.view.y) * (newScale / state.view.scale);
            state.view.scale = newScale;

            applyTransform();
            updateZoomLabel();
        }, { passive: false });

        window.addEventListener('click', (e) => {
            if (!e.target.closest('#node-context-menu') && !e.target.closest('#canvas-context-menu')) {
                closeContextMenus();
            }
        });

        window.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                closeContextMenus();
            }
        });
    }

    function applyTransform() {
        if (container) {
            container.style.transform = `translate(${state.view.x}px, ${state.view.y}px) scale(${state.view.scale})`;
        }
    }

    function updateZoomLabel() {
        const label = document.getElementById('zoom-label');
        if (label) label.textContent = `${Math.round(state.view.scale * 100)}%`;
    }

    window.zoomIn = () => {
        state.view.scale = Math.min(state.view.scale * 1.2, 2.5);
        applyTransform();
        updateZoomLabel();
    };

    window.zoomOut = () => {
        state.view.scale = Math.max(state.view.scale * 0.8, 0.4);
        applyTransform();
        updateZoomLabel();
    };

    window.resetView = () => {
        state.view.x = 80;
        state.view.y = 80;
        state.view.scale = 1.0;
        applyTransform();
        updateZoomLabel();
    };

    // --- Arrastar Medalhões na Forja (Drag & Drop) ---

    function onNodeMouseDown(e, node) {
        if (state.interactionMode !== 'edit' || state.connectModeActive) return;
        if (e.button !== 0) return;

        e.stopPropagation();
        state.activeDragNode = node;
        state.hasDragged = false;
        state.dragOffset.x = (e.clientX - state.view.x) / state.view.scale - node.pos_x;
        state.dragOffset.y = (e.clientY - state.view.y) / state.view.scale - node.pos_y;
    }

    function onNodeMouseMove(e) {
        if (!state.activeDragNode) return;
        state.hasDragged = true;

        const newX = (e.clientX - state.view.x) / state.view.scale - state.dragOffset.x;
        const newY = (e.clientY - state.view.y) / state.view.scale - state.dragOffset.y;

        state.activeDragNode.pos_x = Math.round(newX);
        state.activeDragNode.pos_y = Math.round(newY);

        const el = nodesLayer.querySelector(`[data-node-id="${state.activeDragNode.id}"]`);
        if (el) {
            el.style.left = `${state.activeDragNode.pos_x}px`;
            el.style.top = `${state.activeDragNode.pos_y}px`;
        }

        renderEdges();

        state.pendingPositions.set(state.activeDragNode.id, {
            node_id: state.activeDragNode.id,
            pos_x: state.activeDragNode.pos_x,
            pos_y: state.activeDragNode.pos_y,
        });
    }

    function onNodeMouseUp() {
        if (!state.activeDragNode) return;
        state.activeDragNode = null;

        clearTimeout(state.batchSaveTimer);
        state.batchSaveTimer = setTimeout(flushPendingPositions, 500);
    }

    async function flushPendingPositions() {
        if (state.pendingPositions.size === 0) return;

        const positions = Array.from(state.pendingPositions.values());
        state.pendingPositions.clear();

        try {
            await fetch(`/api/v1/study-maps/${state.mapId}/nodes/positions-batch`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ positions }),
            });
        } catch (err) {
            console.error('Falha ao salvar coordenadas do medalhão:', err);
        }
    }

    // --- Clique em Nós: Abertura do Side Drawer Interativo ---

    function onNodeClick(e, node) {
        e.stopPropagation();

        if (state.hasDragged) {
            state.hasDragged = false;
            return;
        }

        // Se estiver traçando vínculo de dependência no Modo Forja
        if (state.connectModeActive) {
            if (!state.connectSourceNodeId) {
                state.connectSourceNodeId = node.id;
                const banner = document.getElementById('connect-banner');
                if (banner) {
                    banner.innerHTML = `<span>⚡ PRÉ-REQUISITO SELECIONADO: "${escapeHtml(node.title)}". Agora clique no nó DEPENDENTE.</span>
                    <button type="button" onclick="toggleConnectMode()" class="ml-2 text-xs bg-[#0c0908]/20 px-2 py-0.5 rounded font-sans">Cancelar</button>`;
                }
            } else {
                if (state.connectSourceNodeId === node.id) {
                    alert('Um nó não pode depender de si mesmo!');
                    return;
                }
                createEdge(state.connectSourceNodeId, node.id);
                toggleConnectMode();
            }
            return;
        }

        // Abre o Slide-Over Side Drawer para estudo dual-screen / anotações / IA
        openNodeSideDrawer(node);
    }

    window.toggleConnectMode = () => {
        state.connectModeActive = !state.connectModeActive;
        state.connectSourceNodeId = null;
        const banner = document.getElementById('connect-banner');
        const btn = document.getElementById('btn-connect-mode');

        if (state.connectModeActive) {
            if (banner) {
                banner.classList.remove('hidden');
                banner.innerHTML = `<span>⚡ CONECTAR NÓS: Clique no nó de pré-requisito e depois no nó dependente</span>
                <button type="button" onclick="toggleConnectMode()" class="ml-2 text-xs bg-[#0c0908]/20 px-2 py-0.5 rounded font-sans">Cancelar</button>`;
            }
            if (btn) btn.className = 'rpg-btn-gold text-xs py-1.5 px-3 flex items-center space-x-1';
        } else {
            if (banner) banner.classList.add('hidden');
            if (btn) btn.className = 'rpg-btn-bronze text-xs py-1.5 px-3 flex items-center space-x-1';
        }
    };

    async function createEdge(sourceId, targetId, requiredLevel = 1) {
        try {
            const res = await fetch(`/api/v1/study-maps/${state.mapId}/edges`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    source_node_id: sourceId,
                    target_node_id: targetId,
                    required_level: requiredLevel,
                }),
            });
            if (res.ok) {
                await loadGraph();
            } else {
                const err = await res.json();
                alert('Erro ao conectar nós: ' + (err.detail || 'Falha de validação'));
            }
        } catch (err) {
            alert('Erro de conexão: ' + err.message);
        }
    }

    async function updateEdgeRequiredLevel(edgeId, newLevel) {
        try {
            const res = await fetch(`/api/v1/study-maps/${state.mapId}/edges/${edgeId}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ required_level: parseInt(newLevel, 10) }),
            });
            if (res.ok) {
                await loadGraph();
            } else {
                const err = await res.json();
                alert('Erro ao calibrar nível do pré-requisito: ' + (err.detail || 'Falha ao salvar'));
            }
        } catch (err) {
            alert('Erro de conexão: ' + err.message);
        }
    }

    async function deleteEdge(edgeId) {
        try {
            const res = await fetch(`/api/v1/study-maps/${state.mapId}/edges/${edgeId}`, {
                method: 'DELETE',
            });
            if (res.ok) {
                await loadGraph();
            } else {
                const err = await res.json();
                alert('Falha ao remover pré-requisito: ' + (err.detail || 'Erro no servidor'));
            }
        } catch (err) {
            alert('Falha ao remover pré-requisito: ' + err.message);
        }
    }

    async function addPrerequisiteEdge(event) {
        if (event) event.preventDefault();
        if (!state.selectedNode) return;

        const selectEl = document.getElementById('new-prereq-node-select') || document.getElementById('add-prerequisite-select');
        const levelEl = document.getElementById('new-prereq-level-select') || document.getElementById('add-prerequisite-level');

        if (!selectEl || !selectEl.value) {
            alert('Selecione um nó de pré-requisito.');
            return;
        }

        const sourceId = selectEl.value;
        const requiredLevel = levelEl ? parseInt(levelEl.value, 10) : 1;

        await createEdge(sourceId, state.selectedNode.id, requiredLevel);
    }

    function renderPrerequisites(node) {
        const listEl = document.getElementById('node-prerequisites-list');
        const selectEl = document.getElementById('new-prereq-node-select') || document.getElementById('add-prerequisite-select');
        if (!listEl) return;

        const incomingEdges = (state.graph.edges || []).filter(e => e.target_node_id === node.id);
        const nodeMap = new Map((state.graph.nodes || []).map(n => [n.id, n]));

        if (incomingEdges.length === 0) {
            listEl.innerHTML = `<div class="p-2.5 rounded-lg bg-[#0c0908] border border-[#785a28]/40 text-xs text-[#a39276] italic text-center">Nenhum pré-requisito vinculado a este nó.</div>`;
        } else {
            listEl.innerHTML = incomingEdges.map(edge => {
                const srcNode = nodeMap.get(edge.source_node_id);
                const title = srcNode ? escapeHtml(srcNode.title) : 'Nó Ancestral';
                const iconName = srcNode ? srcNode.icon : 'scroll';
                const iconSvg = (typeof window.getRpgIconSvg === 'function')
                    ? window.getRpgIconSvg(iconName, 'w-4 h-4 text-[#f0c869]')
                    : '📜';
                const reqLvl = edge.required_level || 1;

                return `
                    <div class="flex items-center justify-between gap-2 p-2 rounded-lg bg-[#0c0908] border border-[#785a28]/50 shadow-inner">
                        <div class="flex items-center space-x-2 min-w-0">
                            <span class="w-5 h-5 flex items-center justify-center shrink-0">${iconSvg}</span>
                            <span class="text-xs font-cinzel font-bold text-[#f5ebd6] truncate">${title}</span>
                        </div>
                        <div class="flex items-center space-x-2 shrink-0">
                            <label class="text-[10px] uppercase font-cinzel text-[#a39276]">Exigir:</label>
                            <select
                                onchange="updateEdgeRequiredLevel('${edge.id}', this.value)"
                                class="bg-[#14100d] border border-[#785a28] rounded px-1.5 py-0.5 text-xs text-[#f0c869] font-cinzel font-bold focus:border-[#f0c869] focus:outline-none"
                            >
                                <option value="1" ${reqLvl === 1 ? 'selected' : ''}>Nv. 1</option>
                                <option value="2" ${reqLvl === 2 ? 'selected' : ''}>Nv. 2</option>
                                <option value="3" ${reqLvl === 3 ? 'selected' : ''}>Nv. 3</option>
                                <option value="4" ${reqLvl === 4 ? 'selected' : ''}>Nv. 4</option>
                            </select>
                            <button
                                type="button"
                                onclick="deleteEdge('${edge.id}')"
                                class="text-[#e11d48] hover:text-red-400 text-xs px-1.5 py-0.5 rounded transition-colors"
                                title="Remover Pré-requisito"
                            >
                                🗑️
                            </button>
                        </div>
                    </div>
                `;
            }).join('');
        }

        // Atualiza as opções do select de novos pré-requisitos
        if (selectEl) {
            const existingSourceIds = new Set(incomingEdges.map(e => e.source_node_id));
            const availableCandidates = (state.graph.nodes || []).filter(
                n => n.id !== node.id && !existingSourceIds.has(n.id)
            );

            if (availableCandidates.length === 0) {
                selectEl.innerHTML = `<option value="">Nenhum outro nó disponível</option>`;
                selectEl.disabled = true;
            } else {
                selectEl.disabled = false;
                selectEl.innerHTML = `
                    <option value="">Selecione um nó de pré-requisito...</option>
                    ${availableCandidates.map(c => `
                        <option value="${c.id}">${escapeHtml(c.title)} (Nv. ${c.effective_level || 0})</option>
                    `).join('')}
                `;
            }
        }
    }

    // --- Alternar Modos: Modo Jornada vs Modo Forja ---

    window.setInteractionMode = (mode) => {
        state.interactionMode = mode;
        const btnStudy = document.getElementById('btn-mode-study');
        const btnEdit = document.getElementById('btn-mode-edit');
        const editorActions = document.getElementById('editor-actions');

        if (mode === 'edit') {
            if (btnEdit) {
                btnEdit.className = 'px-3.5 py-1.5 font-bold font-cinzel rounded-lg transition-all bg-[#c89b3c] text-[#0c0908] shadow-sm flex items-center space-x-1.5';
            }
            if (btnStudy) {
                btnStudy.className = 'px-3.5 py-1.5 font-medium font-cinzel rounded-lg text-[#a39276] hover:text-[#f0c869] transition-all flex items-center space-x-1.5';
            }
            if (editorActions) editorActions.classList.remove('hidden');
        } else {
            if (btnStudy) {
                btnStudy.className = 'px-3.5 py-1.5 font-bold font-cinzel rounded-lg transition-all bg-[#c89b3c] text-[#0c0908] shadow-sm flex items-center space-x-1.5';
            }
            if (btnEdit) {
                btnEdit.className = 'px-3.5 py-1.5 font-medium font-cinzel rounded-lg text-[#a39276] hover:text-[#f0c869] transition-all flex items-center space-x-1.5';
            }
            if (editorActions) editorActions.classList.add('hidden');
            if (state.connectModeActive) toggleConnectMode();
        }
        renderEdges();
    };

    // --- Inspector da Forja (Criação & Edição de Nós Raiz / Metadados) ---

    window.openCreateNodeModal = () => {
        state.selectedNode = null;
        const titleEl = document.getElementById('node-modal-title');
        if (titleEl) titleEl.textContent = 'Criar Novo Nó';

        const idInput = document.getElementById('modal-node-id');
        if (idInput) idInput.value = '';

        const titleInput = document.getElementById('modal-node-title-input');
        if (titleInput) titleInput.value = '';

        const descInput = document.getElementById('modal-node-desc-input');
        if (descInput) descInput.value = '';

        const iconSelect = document.getElementById('modal-node-icon-select');
        if (iconSelect) iconSelect.value = 'brain';

        const deleteBtn = document.getElementById('btn-delete-node');
        if (deleteBtn) deleteBtn.classList.add('hidden');

        const grimoireBtn = document.getElementById('btn-open-grimoire');
        if (grimoireBtn) grimoireBtn.classList.add('hidden');

        const prereqSection = document.getElementById('node-prerequisites-section');
        if (prereqSection) prereqSection.classList.add('hidden');

        if (nodeModal) nodeModal.classList.remove('hidden');
    };

    window.openEditNodeModal = (node) => {
        const targetNode = node || state.selectedNode;
        if (!targetNode) return;
        state.selectedNode = targetNode;

        const titleEl = document.getElementById('node-modal-title');
        if (titleEl) titleEl.textContent = `Editar Nó: ${targetNode.title}`;

        const idInput = document.getElementById('modal-node-id');
        if (idInput) idInput.value = targetNode.id;

        const titleInput = document.getElementById('modal-node-title-input');
        if (titleInput) titleInput.value = targetNode.title;

        const descInput = document.getElementById('modal-node-desc-input');
        if (descInput) descInput.value = targetNode.description || '';

        const iconSelect = document.getElementById('modal-node-icon-select');
        if (iconSelect) iconSelect.value = targetNode.icon || 'brain';

        const deleteBtn = document.getElementById('btn-delete-node');
        if (deleteBtn) deleteBtn.classList.remove('hidden');

        const grimoireBtn = document.getElementById('btn-open-grimoire');
        if (grimoireBtn) grimoireBtn.classList.remove('hidden');

        const prereqSection = document.getElementById('node-prerequisites-section');
        if (prereqSection) {
            prereqSection.classList.remove('hidden');
            renderPrerequisites(targetNode);
        }

        if (nodeModal) nodeModal.classList.remove('hidden');
    };

    window.closeNodeModal = () => {
        state.pendingSpawnCoords = null;
        if (nodeModal) nodeModal.classList.add('hidden');
    };

    window.openSelectedNodeGrimoire = () => {
        if (!state.selectedNode) return;
        const node = state.selectedNode;
        // Navegação direta à página completa do Grimório do nó
        window.location.href = `/study-maps/${state.mapId}/nodes/${node.id}`;
    };

    window.handleSaveNode = async (e) => {
        e.preventDefault();
        const nodeId = document.getElementById('modal-node-id').value;
        const title = document.getElementById('modal-node-title-input').value.trim();
        const description = document.getElementById('modal-node-desc-input').value.trim();
        const icon = document.getElementById('modal-node-icon-select').value;

        try {
            if (!nodeId) {
                // Criação do nó posicionado no cursor (se invocado via menu de contexto) ou no centro visível
                let posX, posY;
                if (state.pendingSpawnCoords) {
                    posX = state.pendingSpawnCoords.x;
                    posY = state.pendingSpawnCoords.y;
                    state.pendingSpawnCoords = null;
                } else {
                    posX = Math.round((-state.view.x + viewport.clientWidth / 2) / state.view.scale - 40);
                    posY = Math.round((-state.view.y + viewport.clientHeight / 2) / state.view.scale - 40);
                }

                const res = await fetch(`/api/v1/study-maps/${state.mapId}/nodes`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        title,
                        description,
                        icon,
                        pos_x: posX,
                        pos_y: posY,
                    }),
                });
                if (res.ok) {
                    closeNodeModal();
                    await loadGraph();
                } else {
                    const err = await res.json();
                    alert('Erro ao criar nó: ' + (err.detail || 'Falha de validação'));
                }
            } else {
                // Atualização dos metadados do nó
                const res = await fetch(`/api/v1/study-maps/${state.mapId}/nodes/${nodeId}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title, description, icon }),
                });
                if (res.ok) {
                    closeNodeModal();
                    await loadGraph();
                } else {
                    const err = await res.json();
                    alert('Erro ao atualizar nó: ' + (err.detail || 'Falha ao salvar'));
                }
            }
        } catch (err) {
            alert('Erro de conexão: ' + err.message);
        }
    };

    window.deleteCurrentNode = async () => {
        if (!state.selectedNode) return;
        if (!confirm(`Deseja excluir o nó "${state.selectedNode.title}" e todas as suas perguntas?`)) return;

        try {
            const res = await fetch(`/api/v1/study-maps/${state.mapId}/nodes/${state.selectedNode.id}`, {
                method: 'DELETE',
            });
            if (res.ok) {
                closeNodeModal();
                closeNodeSideDrawer();
                await loadGraph();
            } else {
                alert('Falha ao excluir nó.');
            }
        } catch (err) {
            alert('Erro de rede: ' + err.message);
        }
    };

    // --- 1-Click Quick Add Connected Child Node (+) ---

    window.quickAddChildNode = async function (parentNode, optionalTitle) {
        if (!parentNode) return;

        if (optionalTitle && optionalTitle.trim()) {
            await executeCreateConnectedChild(parentNode, optionalTitle.trim());
            return;
        }

        const modal = document.getElementById('quick-child-modal');
        if (modal) {
            state.quickAddParentNode = parentNode;
            const parentNameEl = document.getElementById('quick-child-parent-name');
            if (parentNameEl) parentNameEl.textContent = parentNode.title;
            const titleInput = document.getElementById('quick-child-title-input');
            if (titleInput) {
                titleInput.value = '';
                modal.classList.remove('hidden');
                setTimeout(() => titleInput.focus(), 50);
            } else {
                modal.classList.remove('hidden');
            }
        } else {
            const promptTitle = window.prompt(`Criar nó filho conectado a "${parentNode.title}":`);
            if (promptTitle && promptTitle.trim()) {
                await executeCreateConnectedChild(parentNode, promptTitle.trim());
            }
        }
    };

    window.closeQuickChildModal = function () {
        const modal = document.getElementById('quick-child-modal');
        if (modal) modal.classList.add('hidden');
        state.quickAddParentNode = null;
    };

    window.handleQuickChildSubmit = async function (event) {
        if (event) event.preventDefault();
        const input = document.getElementById('quick-child-title-input');
        const title = input ? input.value.trim() : '';
        const parentNode = state.quickAddParentNode;
        if (!title || !parentNode) return;

        closeQuickChildModal();
        await executeCreateConnectedChild(parentNode, title);
    };

    async function executeCreateConnectedChild(parentNode, title) {
        try {
            const childEdges = (state.graph.edges || []).filter(e => e.source_node_id === parentNode.id);
            const childCount = childEdges.length;
            const posX = Math.round(parentNode.pos_x + 200);
            const posY = Math.round(parentNode.pos_y + (childCount * 110) - (childCount > 0 ? 55 : 0));

            // 1. Criação do nó filho
            const nodeRes = await fetch(`/api/v1/study-maps/${state.mapId}/nodes`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    title: title.trim(),
                    description: '',
                    icon: parentNode.icon || 'brain',
                    pos_x: posX,
                    pos_y: posY,
                }),
            });

            if (!nodeRes.ok) {
                const err = await nodeRes.json();
                alert('Erro ao criar nó filho: ' + (err.detail || 'Falha na validação'));
                return;
            }

            const newNode = await nodeRes.json();

            // 2. Conectar nó pai ao nó filho via POST /edges
            const edgeRes = await fetch(`/api/v1/study-maps/${state.mapId}/edges`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    source_node_id: parentNode.id,
                    target_node_id: newNode.id,
                    required_level: 1,
                }),
            });

            if (!edgeRes.ok) {
                console.warn('Nó criado, mas falhou ao conectar aresta:', await edgeRes.text());
            }

            // 3. Recarregar grafo e abrir Side Drawer para o nó recém-criado
            await loadGraph();
            const created = (state.graph.nodes || []).find(n => n.id === newNode.id) || newNode;
            openNodeSideDrawer(created);
        } catch (err) {
            console.error('Erro na criação de nó filho:', err);
            alert('Erro ao criar nó conectado: ' + err.message);
        }
    }

    // --- Side Drawer Interativo do Nó (Dual-Screen com IA) ---

    window.openNodeSideDrawer = async function (node) {
        if (!node) return;
        state.selectedNode = node;

        const drawer = document.getElementById('node-side-drawer');
        if (!drawer) return;

        // Revela o drawer
        drawer.classList.remove('translate-x-full');
        drawer.classList.remove('hidden');

        // Atualiza cabeçalho do drawer
        const titleEl = document.getElementById('drawer-node-title');
        if (titleEl) titleEl.textContent = node.title;

        const rankEl = document.getElementById('drawer-node-rank');
        if (rankEl) {
            if (!node.is_unlocked) {
                rankEl.textContent = '🔒 SELADO';
                rankEl.className = 'px-2 py-0.5 rounded text-[10px] font-cinzel font-bold bg-[#14100d] border border-[#3b322c] text-[#a39276]';
            } else {
                rankEl.textContent = `Nv. ${node.effective_level || 0}`;
                rankEl.className = 'px-2 py-0.5 rounded text-[10px] font-cinzel font-bold bg-[#0c0908] border border-[#785a28] text-[#f0c869]';
            }
        }

        const iconEl = document.getElementById('drawer-node-icon');
        if (iconEl) {
            const iconSvg = (typeof window.getRpgIconSvg === 'function')
                ? window.getRpgIconSvg(node.icon, 'w-6 h-6 text-[#f0c869]')
                : `<span>${ICON_MAP[node.icon] || '📜'}</span>`;
            iconEl.innerHTML = iconSvg;
        }

        // Sub-aba ativa padrão
        switchDrawerTab(state.currentDrawerTab || 'content');

        // Renderiza lista de bloqueios com dados atuais do grafo
        renderDrawerPrerequisites(node);

        // Busca dados detalhados do hub do nó (/hub) para teoria e questões
        try {
            const res = await fetch(`/api/v1/study-maps/${state.mapId}/nodes/${node.id}/hub`);
            if (res.ok) {
                const data = await res.json();
                const hubNode = data.node || node;
                const theoryInput = document.getElementById('drawer-theory-input');
                if (theoryInput) {
                    theoryInput.value = hubNode.theory_content || '';
                }
                const questions = data.all_questions || [];
                renderDrawerQuestionsList(questions);
            }
        } catch (err) {
            console.error('Falha ao carregar hub do nó no side drawer:', err);
        }
    };

    window.closeNodeSideDrawer = function () {
        const drawer = document.getElementById('node-side-drawer');
        if (drawer) {
            drawer.classList.add('translate-x-full');
        }
    };

    window.openNodeDrawer = window.openNodeSideDrawer;
    window.closeNodeDrawer = window.closeNodeSideDrawer;

    window.switchDrawerTab = function (tabName) {
        state.currentDrawerTab = tabName;

        const tabs = ['content', 'questions', 'prereqs'];
        tabs.forEach(t => {
            const panel = document.getElementById(`drawer-tab-${t}`);
            const btn = document.getElementById(`drawer-tab-btn-${t}`);
            if (panel) {
                if (t === tabName) {
                    panel.classList.remove('hidden');
                } else {
                    panel.classList.add('hidden');
                }
            }
            if (btn) {
                if (t === tabName) {
                    btn.className = 'flex-1 py-2.5 text-xs font-cinzel font-bold border-b-2 border-[#f0c869] text-[#f0c869] bg-[#1a1410] transition-colors';
                } else {
                    btn.className = 'flex-1 py-2.5 text-xs font-cinzel font-medium border-b-2 border-transparent text-[#a39276] hover:text-[#f5ebd6] hover:bg-[#14100d] transition-colors';
                }
            }
        });

        if (tabName === 'prereqs' && state.selectedNode) {
            renderDrawerPrerequisites(state.selectedNode);
        }
    };

    window.saveDrawerTheory = async function () {
        if (!state.selectedNode) return;
        const nodeId = state.selectedNode.id;
        const textarea = document.getElementById('drawer-theory-input');
        const statusEl = document.getElementById('drawer-theory-status');
        const theory_content = textarea ? textarea.value : '';

        try {
            // PUT / PATCH /theory — Atualiza o resumo teórico do nó
            const res = await fetch(`/api/v1/study-maps/${state.mapId}/nodes/${nodeId}/theory`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ theory_content }),
            });

            if (res.ok) {
                state.selectedNode.theory_content = theory_content;
                if (statusEl) {
                    statusEl.classList.remove('hidden');
                    setTimeout(() => statusEl.classList.add('hidden'), 3000);
                }
            } else {
                const err = await res.json();
                alert('Erro ao salvar resumo: ' + (err.detail || 'Falha no servidor'));
            }
        } catch (err) {
            console.error('Erro ao salvar teoria:', err);
            alert('Erro ao salvar resumo: ' + err.message);
        }
    };

    window.copyAiJsonPrompt = async function () {
        const nodeTitle = state.selectedNode ? state.selectedNode.title : 'este tópico';
        const promptText = `Gere questões de estudo aprofundadas sobre "${nodeTitle}" para revisão espaçada ativa.\nRetorne EXCLUSIVAMENTE um array JSON válido no formato abaixo, usando formatação Markdown rica (**negrito** para conceitos-chave, listas com "-", blocos de código com \`\`\`linguagem, tabelas ou citações ">") tanto no "prompt" quanto no "expected_answer":\n\n[\n  {\n    "prompt": "Enunciado contextualizado ou problema prático em Markdown...",\n    "expected_answer": "### Pontos Essenciais:\\n- **Conceito 1:** Explicação objetiva.\\n- **Conceito 2:** Critério técnico ou exemplo de código."\n  }\n]`;

        const statusEl = document.getElementById('copy-ai-prompt-status');
        try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(promptText);
            } else {
                const ta = document.createElement('textarea');
                ta.value = promptText;
                document.body.appendChild(ta);
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
            }
            if (statusEl) {
                statusEl.classList.remove('hidden');
                setTimeout(() => statusEl.classList.add('hidden'), 3000);
            }
        } catch (err) {
            console.error('Erro ao copiar prompt:', err);
            prompt('Copie o prompt abaixo:', promptText);
        }
    };

    window.submitDrawerBulkQuestions = async function () {
        if (!state.selectedNode) return;
        const nodeId = state.selectedNode.id;
        const textarea = document.getElementById('drawer-bulk-questions-input');
        const statusEl = document.getElementById('drawer-bulk-status');
        const rawText = textarea ? textarea.value.trim() : '';

        if (!rawText) {
            alert('Cole pelo menos uma pergunta com resposta no campo de texto.');
            return;
        }

        let parsedQuestions;
        try {
            parsedQuestions = parseBulkQuestions(rawText);
        } catch (parseErr) {
            alert(parseErr.message);
            return;
        }

        if (!parsedQuestions || parsedQuestions.length === 0) {
            alert('Não foi possível identificar perguntas e respostas no formato inserido. Use JSON ou "P: Pergunta\\nR: Resposta" ou "Pergunta | Resposta".');
            return;
        }

        try {
            // POST /questions/batch — Importação em lote de perguntas SRS
            const res = await fetch(`/api/v1/study-maps/${state.mapId}/nodes/${nodeId}/questions/batch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ questions: parsedQuestions }),
            });

            if (res.ok) {
                const createdList = await res.json();
                if (textarea) textarea.value = '';
                if (statusEl) {
                    statusEl.textContent = `✓ ${createdList.length} questões importadas!`;
                    statusEl.className = 'text-xs font-cinzel font-bold text-emerald-400 ml-2';
                    statusEl.classList.remove('hidden');
                    setTimeout(() => statusEl.classList.add('hidden'), 3500);
                }
                await reloadDrawerQuestions(nodeId);
                await loadGraph();
            } else {
                const err = await res.json();
                alert('Erro ao importar questões em lote: ' + (err.detail || 'Falha de validação'));
            }
        } catch (err) {
            console.error('Erro na importação em lote:', err);
            alert('Erro ao importar questões: ' + err.message);
        }
    };
    window.submitDrawerBatchQuestions = window.submitDrawerBulkQuestions;

    window.submitDrawerSingleQuestion = async function (event) {
        if (event) event.preventDefault();
        if (!state.selectedNode) return;
        const nodeId = state.selectedNode.id;
        const promptInput = document.getElementById('drawer-single-prompt');
        const answerInput = document.getElementById('drawer-single-answer');
        const prompt = promptInput ? promptInput.value.trim() : '';
        const expected_answer = answerInput ? answerInput.value.trim() : '';

        if (!prompt) {
            alert('O enunciado da pergunta é obrigatório.');
            return;
        }

        try {
            const res = await fetch(`/api/v1/study-maps/${state.mapId}/nodes/${nodeId}/questions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt, expected_answer }),
            });

            if (res.ok) {
                if (promptInput) promptInput.value = '';
                if (answerInput) answerInput.value = '';
                await reloadDrawerQuestions(nodeId);
                await loadGraph();
            } else {
                const err = await res.json();
                alert('Erro ao adicionar questão: ' + (err.detail || 'Falha de validação'));
            }
        } catch (err) {
            console.error('Erro ao adicionar questão:', err);
            alert('Erro ao adicionar questão: ' + err.message);
        }
    };

    window.deleteDrawerQuestion = async function (questionId) {
        if (!state.selectedNode) return;
        if (!confirm('Deseja realmente excluir esta questão do nó?')) return;

        try {
            const res = await fetch(`/api/v1/study-maps/${state.mapId}/nodes/${state.selectedNode.id}/questions/${questionId}`, {
                method: 'DELETE',
            });

            if (res.ok) {
                await reloadDrawerQuestions(state.selectedNode.id);
                await loadGraph();
            } else {
                alert('Falha ao excluir questão.');
            }
        } catch (err) {
            console.error('Erro ao excluir questão:', err);
            alert('Erro ao excluir questão: ' + err.message);
        }
    };

    async function reloadDrawerQuestions(nodeId) {
        try {
            const res = await fetch(`/api/v1/study-maps/${state.mapId}/nodes/${nodeId}/hub`);
            if (res.ok) {
                const data = await res.json();
                renderDrawerQuestionsList(data.all_questions || []);
            }
        } catch (err) {
            console.error('Erro ao recarregar questões do drawer:', err);
        }
    }

    function renderDrawerQuestionsList(questions) {
        const listEl = document.getElementById('drawer-questions-list');
        const countEl = document.getElementById('drawer-questions-count');
        if (countEl) countEl.textContent = `${questions ? questions.length : 0}`;

        if (!listEl) return;

        if (!questions || questions.length === 0) {
            listEl.innerHTML = `<div class="p-4 rounded-xl bg-[#0c0908] border border-[#785a28]/40 text-xs text-[#a39276] italic text-center">Nenhuma provação SRS cadastrada neste nó. Use o campo acima para importar em lote!</div>`;
            return;
        }

        listEl.innerHTML = questions.map((q, idx) => {
            const rawPrompt = q.prompt || q.statement || '';
            const rawAnswer = q.expected_answer || '';
            const promptHtml = (typeof window.renderRpgMarkdown === 'function')
                ? window.renderRpgMarkdown(rawPrompt)
                : escapeHtml(rawPrompt);
            const ansHtml = (typeof window.renderRpgMarkdown === 'function')
                ? window.renderRpgMarkdown(rawAnswer)
                : escapeHtml(rawAnswer);
            const lvl = q.current_level || 0;
            return `
                <div class="p-3 rounded-xl bg-[#0c0908] border border-[#785a28]/50 shadow-inner flex flex-col space-y-1.5 group">
                    <div class="flex items-start justify-between gap-2">
                        <div class="flex items-center space-x-2">
                            <span class="text-[10px] font-mono px-1.5 py-0.5 rounded bg-[#1c1612] text-[#a39276]">#${idx + 1}</span>
                            <span class="text-[10px] font-cinzel font-bold px-1.5 py-0.5 rounded bg-[#c89b3c]/20 text-[#f0c869] border border-[#c89b3c]/30">Nv. ${lvl}</span>
                        </div>
                        <button
                            type="button"
                            onclick="deleteDrawerQuestion('${q.id}')"
                            class="text-[#e11d48] hover:text-red-400 text-xs p-1 rounded transition-colors"
                            title="Excluir Questão"
                        >
                            🗑️
                        </button>
                    </div>
                    <div class="text-xs font-bold font-tome text-[#f5ebd6] leading-snug rpg-markdown" data-rpg-markdown="true">${promptHtml}</div>
                    ${rawAnswer ? `<div class="text-[11px] font-tome text-[#a39276] italic border-l-2 border-[#785a28]/50 pl-2 mt-1 leading-snug rpg-markdown" data-rpg-markdown="true">${ansHtml}</div>` : ''}
                </div>
            `;
        }).join('');
    }

    function renderDrawerPrerequisites(node) {
        const listEl = document.getElementById('drawer-prerequisites-list');
        const selectEl = document.getElementById('drawer-prereq-node-select');
        if (!listEl) return;

        const incomingEdges = (state.graph.edges || []).filter(e => e.target_node_id === node.id);
        const nodeMap = new Map((state.graph.nodes || []).map(n => [n.id, n]));

        if (incomingEdges.length === 0) {
            listEl.innerHTML = `<div class="p-3 rounded-xl bg-[#0c0908] border border-[#785a28]/40 text-xs text-[#a39276] italic text-center">Nenhum pré-requisito bloqueando este nó.</div>`;
        } else {
            listEl.innerHTML = incomingEdges.map(edge => {
                const srcNode = nodeMap.get(edge.source_node_id);
                const title = srcNode ? escapeHtml(srcNode.title) : 'Nó Ancestral';
                const iconName = srcNode ? srcNode.icon : 'scroll';
                const iconSvg = (typeof window.getRpgIconSvg === 'function')
                    ? window.getRpgIconSvg(iconName, 'w-4 h-4 text-[#f0c869]')
                    : '📜';
                const reqLvl = edge.required_level || 1;

                return `
                    <div class="flex items-center justify-between gap-2 p-2.5 rounded-xl bg-[#0c0908] border border-[#785a28]/50 shadow-inner">
                        <div class="flex items-center space-x-2 min-w-0">
                            <span class="w-5 h-5 flex items-center justify-center shrink-0">${iconSvg}</span>
                            <span class="text-xs font-cinzel font-bold text-[#f5ebd6] truncate">${title}</span>
                        </div>
                        <div class="flex items-center space-x-2 shrink-0">
                            <label class="text-[10px] uppercase font-cinzel text-[#a39276]">Exigir:</label>
                            <select
                                onchange="updateEdgeRequiredLevel('${edge.id}', this.value)"
                                class="bg-[#14100d] border border-[#785a28] rounded px-1.5 py-0.5 text-xs text-[#f0c869] font-cinzel font-bold focus:border-[#f0c869] focus:outline-none"
                            >
                                <option value="1" ${reqLvl === 1 ? 'selected' : ''}>Nv. 1</option>
                                <option value="2" ${reqLvl === 2 ? 'selected' : ''}>Nv. 2</option>
                                <option value="3" ${reqLvl === 3 ? 'selected' : ''}>Nv. 3</option>
                                <option value="4" ${reqLvl === 4 ? 'selected' : ''}>Nv. 4</option>
                            </select>
                            <button
                                type="button"
                                onclick="deleteEdge('${edge.id}')"
                                class="text-[#e11d48] hover:text-red-400 text-xs px-1.5 py-0.5 rounded transition-colors"
                                title="Remover Bloqueio"
                            >
                                🗑️
                            </button>
                        </div>
                    </div>
                `;
            }).join('');
        }

        if (selectEl) {
            const existingSourceIds = new Set(incomingEdges.map(e => e.source_node_id));
            const availableCandidates = (state.graph.nodes || []).filter(
                n => n.id !== node.id && !existingSourceIds.has(n.id)
            );

            if (availableCandidates.length === 0) {
                selectEl.innerHTML = `<option value="">Nenhum outro nó disponível</option>`;
                selectEl.disabled = true;
            } else {
                selectEl.disabled = false;
                selectEl.innerHTML = `
                    <option value="">Selecione um nó de pré-requisito...</option>
                    ${availableCandidates.map(c => `
                        <option value="${c.id}">${escapeHtml(c.title)} (Nv. ${c.effective_level || 0})</option>
                    `).join('')}
                `;
            }
        }
    }

    window.addDrawerPrerequisiteEdge = async function (event) {
        if (event) event.preventDefault();
        if (!state.selectedNode) return;

        const selectEl = document.getElementById('drawer-prereq-node-select');
        const levelEl = document.getElementById('drawer-prereq-level-select');

        if (!selectEl || !selectEl.value) {
            alert('Selecione um nó de pré-requisito.');
            return;
        }

        const sourceId = selectEl.value;
        const requiredLevel = levelEl ? parseInt(levelEl.value, 10) : 1;

        await createEdge(sourceId, state.selectedNode.id, requiredLevel);
        renderDrawerPrerequisites(state.selectedNode);
    };

    function parseBulkQuestions(rawText) {
        if (!rawText || !rawText.trim()) return [];
        const trimmed = rawText.trim();
        const fenceMatch = trimmed.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i);
        const candidateJson = fenceMatch ? fenceMatch[1].trim() : trimmed;

        if (candidateJson.startsWith('[') || candidateJson.startsWith('{')) {
            let parsedJson;
            try {
                parsedJson = JSON.parse(candidateJson);
            } catch (err) {
                throw new Error('Formato JSON inválido: ' + err.message);
            }

            const arr = Array.isArray(parsedJson)
                ? parsedJson
                : (parsedJson.questions || parsedJson.items || [parsedJson]);

            if (Array.isArray(arr)) {
                const questions = [];
                for (const item of arr) {
                    if (!item || typeof item !== 'object') continue;
                    const prompt = String(item.prompt || item.question || item.pergunta || item.enunciado || '').trim();
                    const expected_answer = String(item.expected_answer || item.answer || item.resposta || item.gabarito || '').trim();
                    if (prompt && expected_answer) {
                        questions.push({ prompt, expected_answer });
                    }
                }
                if (questions.length > 0) {
                    return questions;
                }
            }
        }

        const questions = [];
        const normalized = rawText.replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim();

        // Regex para blocos P: ... R: ... / Pergunta: ... Resposta: ... / Q: ... A: ...
        const prRegex = /(?:^|\n)\s*(?:P|Pergunta|Q|Question)\s*[:\-]\s*([\s\S]*?)\n\s*(?:R|Resposta|A|Answer)\s*[:\-]\s*([\s\S]*?)(?=(?:\n\s*(?:P|Pergunta|Q|Question)\s*[:\-])|\n\s*---\s*\n|$)/gi;
        let match;
        while ((match = prRegex.exec(normalized)) !== null) {
            const prompt = match[1].trim();
            const answer = match[2].trim();
            if (prompt && answer) {
                questions.push({ prompt, expected_answer: answer });
            }
        }
        if (questions.length > 0) {
            return questions;
        }

        // Divide por blocos separados por '---' ou por linhas em branco duplas
        const blocks = normalized.split(/\n\s*---\s*\n|\n\s*\n+/);
        for (const block of blocks) {
            const blockTrimmed = block.trim();
            if (!blockTrimmed) continue;

            // Formato separado por barra vertical |
            if (blockTrimmed.includes('|')) {
                const parts = blockTrimmed.split('|');
                const prompt = parts[0].trim();
                const answer = parts.slice(1).join('|').trim();
                if (prompt && answer) {
                    questions.push({ prompt, expected_answer: answer });
                    continue;
                }
            }

            // Formato linha 1: pergunta, linha 2+: resposta
            const lines = blockTrimmed.split('\n').map(l => l.trim()).filter(Boolean);
            if (lines.length >= 2) {
                const prompt = lines[0].replace(/^(?:P|Pergunta|Q|\d+[\.\)])\s*[:\-]\s*/i, '').trim();
                const answer = lines.slice(1).join('\n').replace(/^(?:R|Resposta|A)\s*[:\-]\s*/i, '').trim();
                if (prompt && answer) {
                    questions.push({ prompt, expected_answer: answer });
                }
            }
        }

        return questions;
    }

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    // --- Menus de Contexto do Canvas & Nós (RPG Right-Click) ---

    function closeContextMenus() {
        const nodeMenu = document.getElementById('node-context-menu');
        const canvasMenu = document.getElementById('canvas-context-menu');
        if (nodeMenu) nodeMenu.classList.add('hidden');
        if (canvasMenu) canvasMenu.classList.add('hidden');
    }

    function onNodeContextMenu(e, node) {
        e.preventDefault();
        e.stopPropagation();
        closeContextMenus();
        state.contextMenuNode = node;

        const menu = document.getElementById('node-context-menu');
        if (!menu) return;

        const titleEl = document.getElementById('ctx-node-title');
        if (titleEl) titleEl.textContent = node.title;

        const iconEl = document.getElementById('ctx-node-icon');
        if (iconEl) {
            const svgIcon = (typeof window.getRpgIconSvg === 'function')
                ? window.getRpgIconSvg(node.icon, 'w-4 h-4 text-[#f0c869]')
                : `<span>${ICON_MAP[node.icon] || '📜'}</span>`;
            iconEl.innerHTML = svgIcon;
        }

        const maxLeft = Math.max(10, window.innerWidth - 270);
        const maxTop = Math.max(10, window.innerHeight - 320);
        const posX = Math.min(e.clientX, maxLeft);
        const posY = Math.min(e.clientY, maxTop);

        menu.style.left = `${posX}px`;
        menu.style.top = `${posY}px`;
        menu.classList.remove('hidden');
    }

    function onCanvasContextMenu(e) {
        e.preventDefault();
        e.stopPropagation();
        closeContextMenus();

        const rect = viewport.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;
        const worldX = Math.round((mouseX - state.view.x) / state.view.scale - 40);
        const worldY = Math.round((mouseY - state.view.y) / state.view.scale - 40);
        state.contextMenuWorldPos = { x: worldX, y: worldY };

        const menu = document.getElementById('canvas-context-menu');
        if (!menu) return;

        const maxLeft = Math.max(10, window.innerWidth - 240);
        const maxTop = Math.max(10, window.innerHeight - 150);
        const posX = Math.min(e.clientX, maxLeft);
        const posY = Math.min(e.clientY, maxTop);

        menu.style.left = `${posX}px`;
        menu.style.top = `${posY}px`;
        menu.classList.remove('hidden');
    }

    function ctxCreateChildNode() {
        const node = state.contextMenuNode;
        closeContextMenus();
        if (!node) return;
        if (typeof window.quickAddChildNode === 'function') {
            window.quickAddChildNode(node);
        }
    }

    function ctxStartConnection() {
        const node = state.contextMenuNode;
        closeContextMenus();
        if (!node) return;
        state.connectModeActive = true;
        state.connectSourceNodeId = node.id;
        const banner = document.getElementById('connect-banner');
        if (banner) {
            banner.classList.remove('hidden');
            banner.innerHTML = `<span>⚡ PRÉ-REQUISITO SELECIONADO: "${escapeHtml(node.title)}". Agora clique no nó DEPENDENTE.</span>
            <button type="button" onclick="toggleConnectMode()" class="ml-2 text-xs bg-[#0c0908]/20 px-2 py-0.5 rounded font-sans">Cancelar</button>`;
        }
        const btn = document.getElementById('btn-connect-mode');
        if (btn) btn.className = 'rpg-btn-gold text-xs py-1.5 px-3 flex items-center space-x-1';
    }

    async function ctxOpenTheory() {
        const node = state.contextMenuNode;
        closeContextMenus();
        if (!node) return;
        if (typeof window.openNodeSideDrawer === 'function') {
            await window.openNodeSideDrawer(node);
        }
        if (typeof window.switchDrawerTab === 'function') {
            window.switchDrawerTab('content');
        }
        const input = document.getElementById('drawer-theory-input');
        if (input) {
            input.focus();
        }
    }

    async function ctxOpenBulkQuestions() {
        const node = state.contextMenuNode;
        closeContextMenus();
        if (!node) return;
        if (typeof window.openNodeSideDrawer === 'function') {
            await window.openNodeSideDrawer(node);
        }
        if (typeof window.switchDrawerTab === 'function') {
            window.switchDrawerTab('questions');
        }
        const input = document.getElementById('drawer-bulk-questions-input');
        if (input) {
            input.focus();
        }
    }

    function ctxStudyNode() {
        const node = state.contextMenuNode;
        closeContextMenus();
        if (!node) return;
        window.location.href = `/study-maps/${state.mapId}/nodes/${node.id}`;
    }

    function ctxEditNodeMeta() {
        const node = state.contextMenuNode;
        closeContextMenus();
        if (!node) return;
        if (typeof window.openEditNodeModal === 'function') {
            window.openEditNodeModal(node);
        }
    }

    async function ctxDeleteNode() {
        const node = state.contextMenuNode;
        closeContextMenus();
        if (!node) return;
        state.selectedNode = node;
        if (typeof window.deleteCurrentNode === 'function') {
            await window.deleteCurrentNode();
        }
    }

    function ctxCreateNodeAtCursor() {
        closeContextMenus();
        state.pendingSpawnCoords = state.contextMenuWorldPos;
        if (typeof window.openCreateNodeModal === 'function') {
            window.openCreateNodeModal();
        }
    }

    // Exposição Global de Comandos da Forja e Side Drawer
    window.updateEdgeRequiredLevel = updateEdgeRequiredLevel;
    window.deleteEdge = deleteEdge;
    window.addPrerequisiteEdge = addPrerequisiteEdge;
    window.selectNode = window.openEditNodeModal;
    window.fetchGraph = loadGraph;
    window.parseBulkQuestions = parseBulkQuestions;

    // Métodos exportados para o Side Drawer & Quick Add
    window.quickAddChildNode = quickAddChildNode;
    window.closeQuickChildModal = closeQuickChildModal;
    window.handleQuickChildSubmit = handleQuickChildSubmit;
    window.openNodeSideDrawer = openNodeSideDrawer;
    window.openNodeDrawer = openNodeSideDrawer;
    window.closeNodeSideDrawer = closeNodeSideDrawer;
    window.closeNodeDrawer = closeNodeSideDrawer;
    window.switchDrawerTab = switchDrawerTab;
    window.saveDrawerTheory = saveDrawerTheory;
    window.submitDrawerBulkQuestions = submitDrawerBulkQuestions;
    window.submitDrawerBatchQuestions = submitDrawerBulkQuestions;
    window.submitDrawerSingleQuestion = submitDrawerSingleQuestion;
    window.deleteDrawerQuestion = deleteDrawerQuestion;
    window.addDrawerPrerequisiteEdge = addDrawerPrerequisiteEdge;
    window.renderDrawerPrerequisites = renderDrawerPrerequisites;
    window.renderDrawerQuestions = renderDrawerQuestionsList;
    window.renderDrawerQuestionsList = renderDrawerQuestionsList;
    window.copyAiJsonPrompt = copyAiJsonPrompt;

    // Menus de Contexto do Canvas & Nós
    window.closeContextMenus = closeContextMenus;
    window.onNodeContextMenu = onNodeContextMenu;
    window.onCanvasContextMenu = onCanvasContextMenu;
    window.ctxCreateChildNode = ctxCreateChildNode;
    window.ctxStartConnection = ctxStartConnection;
    window.ctxOpenTheory = ctxOpenTheory;
    window.ctxOpenBulkQuestions = ctxOpenBulkQuestions;
    window.ctxStudyNode = ctxStudyNode;
    window.ctxEditNodeMeta = ctxEditNodeMeta;
    window.ctxDeleteNode = ctxDeleteNode;
    window.ctxCreateNodeAtCursor = ctxCreateNodeAtCursor;

})();
