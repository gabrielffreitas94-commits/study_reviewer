/**
 * study_canvas.js — Motor Interativo do Canvas RPG: Forja Ancestral & Grafo de Maestria
 * Suporta pan, zoom, arrastar medalhões, traçar vínculos de pré-requisito e navegação direta ao Grimório.
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
        batchSaveTimer: null,
        pendingPositions: new Map(),
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

            const isUnlocked = source.effective_level >= 1;

            // Curva Bezier cúbica suave e elegante
            const dx = tx - sx;
            const dy = ty - sy;
            const cx1 = sx + dx * 0.45;
            const cy1 = sy;
            const cx2 = sx + dx * 0.55;
            const cy2 = ty;

            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('d', `M ${sx} ${sy} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${tx} ${ty}`);
            path.setAttribute('fill', 'none');
            path.setAttribute('stroke', isUnlocked ? 'url(#edge-unlocked-grad)' : '#3b322c');
            path.setAttribute('stroke-width', isUnlocked ? '3.5' : '2');
            if (!isUnlocked) {
                path.setAttribute('stroke-dasharray', '6,6');
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
                    if (confirm('Deseja dissipar este vínculo de pré-requisito?')) {
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
            const iconGlyph = ICON_MAP[node.icon] || '🧠';

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
                    <span class="text-3xl filter drop-shadow">${iconGlyph}</span>

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
                </div>
                <div class="mt-3 px-3 py-1 rounded-xl bg-[#14100d]/90 backdrop-blur border border-[#785a28]/60 text-center max-w-[150px] shadow-lg">
                    <span class="text-xs font-bold font-cinzel text-[#f5ebd6] truncate block">${escapeHtml(node.title)}</span>
                </div>
            `;

            // Eventos do mouse e clique
            el.addEventListener('mousedown', (e) => onNodeMouseDown(e, node));
            el.addEventListener('click', (e) => onNodeClick(e, node));

            nodesLayer.appendChild(el);
        });
    }

    // --- Pan e Zoom da Câmera Ancestral ---

    function setupPanAndZoom() {
        if (!viewport) return;

        viewport.addEventListener('mousedown', (e) => {
            if (e.target === viewport || e.target.id === 'canvas-container' || e.target.tagName === 'svg') {
                state.isPanning = true;
                state.panStart.x = e.clientX - state.view.x;
                state.panStart.y = e.clientY - state.view.y;
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

    // --- Clique em Nós: Modo Jornada vs Modo Forja ---

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
                    banner.innerHTML = `<span>⚡ PRÉ-REQUISITO SELECIONADO: "${escapeHtml(node.title)}". Agora clique no medalhão DEPENDENTE.</span>
                    <button type="button" onclick="toggleConnectMode()" class="ml-2 text-xs bg-[#0c0908]/20 px-2 py-0.5 rounded font-sans">Cancelar</button>`;
                }
            } else {
                if (state.connectSourceNodeId === node.id) {
                    alert('Um medalhão não pode depender de si mesmo!');
                    return;
                }
                createEdge(state.connectSourceNodeId, node.id);
                toggleConnectMode();
            }
            return;
        }

        // NO MODO JORNADA (ESTUDO): Navegação direta à Página Dedicada do Nó (Grimório)!
        if (state.interactionMode === 'study') {
            window.location.href = `/study-maps/${state.mapId}/nodes/${node.id}`;
            return;
        }

        // NO MODO FORJA (CONSTRUÇÃO): Abre o Inspector Rápido de Edição do Nó
        openEditNodeModal(node);
    }

    window.toggleConnectMode = () => {
        state.connectModeActive = !state.connectModeActive;
        state.connectSourceNodeId = null;
        const banner = document.getElementById('connect-banner');
        const btn = document.getElementById('btn-connect-mode');

        if (state.connectModeActive) {
            if (banner) {
                banner.classList.remove('hidden');
                banner.innerHTML = `<span>⚡ TRAÇAR VÍNCULO: Clique no nó de pré-requisito e depois no medalhão dependente</span>
                <button type="button" onclick="toggleConnectMode()" class="ml-2 text-xs bg-[#0c0908]/20 px-2 py-0.5 rounded font-sans">Cancelar</button>`;
            }
            if (btn) btn.className = 'rpg-btn-gold text-xs py-1.5 px-3 flex items-center space-x-1';
        } else {
            if (banner) banner.classList.add('hidden');
            if (btn) btn.className = 'rpg-btn-bronze text-xs py-1.5 px-3 flex items-center space-x-1';
        }
    };

    async function createEdge(sourceId, targetId) {
        try {
            const res = await fetch(`/api/v1/study-maps/${state.mapId}/edges`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ source_node_id: sourceId, target_node_id: targetId }),
            });
            if (res.ok) {
                loadGraph();
            } else {
                const err = await res.json();
                alert('Erro ao traçar vínculo: ' + (err.detail || 'Falha de validação'));
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
                loadGraph();
            }
        } catch (err) {
            alert('Falha ao dissipar dependência: ' + err.message);
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

    // --- Inspector da Forja (Criação & Edição de Nós) ---

    window.openCreateNodeModal = () => {
        state.selectedNode = null;
        const titleEl = document.getElementById('node-modal-title');
        if (titleEl) titleEl.textContent = 'Forjar Novo Medalhão';

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

        if (nodeModal) nodeModal.classList.remove('hidden');
    };

    window.openEditNodeModal = (node) => {
        state.selectedNode = node;
        const titleEl = document.getElementById('node-modal-title');
        if (titleEl) titleEl.textContent = `Editar Medalhão: ${node.title}`;

        const idInput = document.getElementById('modal-node-id');
        if (idInput) idInput.value = node.id;

        const titleInput = document.getElementById('modal-node-title-input');
        if (titleInput) titleInput.value = node.title;

        const descInput = document.getElementById('modal-node-desc-input');
        if (descInput) descInput.value = node.description || '';

        const iconSelect = document.getElementById('modal-node-icon-select');
        if (iconSelect) iconSelect.value = node.icon || 'brain';

        const deleteBtn = document.getElementById('btn-delete-node');
        if (deleteBtn) deleteBtn.classList.remove('hidden');

        const grimoireBtn = document.getElementById('btn-open-grimoire');
        if (grimoireBtn) grimoireBtn.classList.remove('hidden');

        if (nodeModal) nodeModal.classList.remove('hidden');
    };

    window.closeNodeModal = () => {
        if (nodeModal) nodeModal.classList.add('hidden');
        state.selectedNode = null;
    };

    window.openSelectedNodeGrimoire = () => {
        if (!state.selectedNode) return;
        window.location.href = `/study-maps/${state.mapId}/nodes/${state.selectedNode.id}`;
    };

    window.handleSaveNode = async (e) => {
        e.preventDefault();
        const nodeId = document.getElementById('modal-node-id').value;
        const title = document.getElementById('modal-node-title-input').value.trim();
        const description = document.getElementById('modal-node-desc-input').value.trim();
        const icon = document.getElementById('modal-node-icon-select').value;

        try {
            if (!nodeId) {
                // Criação do nó posicionado no centro visível
                const centerX = (-state.view.x + viewport.clientWidth / 2) / state.view.scale - 40;
                const centerY = (-state.view.y + viewport.clientHeight / 2) / state.view.scale - 40;

                const res = await fetch(`/api/v1/study-maps/${state.mapId}/nodes`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        title,
                        description,
                        icon,
                        pos_x: Math.round(centerX),
                        pos_y: Math.round(centerY),
                    }),
                });
                if (res.ok) {
                    closeNodeModal();
                    loadGraph();
                } else {
                    const err = await res.json();
                    alert('Erro ao forjar nó: ' + (err.detail || 'Falha de validação'));
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
                    loadGraph();
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
        if (!confirm(`Deseja dissipar o medalhão "${state.selectedNode.title}" e suas provações?`)) return;

        try {
            const res = await fetch(`/api/v1/study-maps/${state.mapId}/nodes/${state.selectedNode.id}`, {
                method: 'DELETE',
            });
            if (res.ok) {
                closeNodeModal();
                loadGraph();
            } else {
                alert('Falha ao dissipar nó.');
            }
        } catch (err) {
            alert('Erro de rede: ' + err.message);
        }
    };

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

})();
