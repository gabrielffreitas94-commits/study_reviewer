/**
 * study_canvas.js — Motor Interativo do Canvas RPG da Árvore de Estudos
 * Suporta pan, zoom, arrastar nós livres, conexões direcionadas, níveis SRS e gaveta de conteúdos.
 */

(function () {
    'use strict';

    // Estado Global da Aplicação no Canvas
    const state = {
        mapId: window.CURRENT_MAP_ID || null,
        isOwner: window.CURRENT_MAP_IS_OWNER || false,
        graph: { map: null, nodes: [], edges: [] },
        view: { x: 50, y: 50, scale: 1.0 },
        isPanning: false,
        panStart: { x: 0, y: 0 },
        activeDragNode: null,
        dragOffset: { x: 0, y: 0 },
        hasDragged: false,
        interactionMode: 'study', // 'study' ou 'edit'
        connectModeActive: false,
        connectSourceNodeId: null,
        selectedNode: null,
        batchSaveTimer: null,
        pendingPositions: new Map(),
    };

    const ICON_MAP = {
        brain: '🧠',
        sword: '⚔️',
        shield: '🛡️',
        book: '📖',
        code: '💻',
        fire: '🔥',
        scroll: '📜',
        flask: '🧪',
        gem: '💎',
    };

    // Elementos do DOM
    const viewport = document.getElementById('canvas-viewport');
    const container = document.getElementById('canvas-container');
    const edgesGroup = document.getElementById('edges-group');
    const nodesLayer = document.getElementById('nodes-layer');
    const drawer = document.getElementById('node-drawer');

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
            console.error('Falha ao buscar grafo:', err);
        }
    }

    function renderAll() {
        renderEdges();
        renderNodes();
    }

    // Renderiza as arestas no SVG
    function renderEdges() {
        edgesGroup.innerHTML = '';
        const nodeMap = new Map(state.graph.nodes.map(n => [n.id, n]));

        state.graph.edges.forEach(edge => {
            const source = nodeMap.get(edge.source_node_id);
            const target = nodeMap.get(edge.target_node_id);
            if (!source || !target) return;

            // Centro dos nós (nó tem ~64px de raio total)
            const sx = source.pos_x + 36;
            const sy = source.pos_y + 36;
            const tx = target.pos_x + 36;
            const ty = target.pos_y + 36;

            const isUnlocked = source.effective_level >= 1;

            // Curva Bezier cúbica elegante
            const dx = tx - sx;
            const dy = ty - sy;
            const cx1 = sx + dx * 0.4;
            const cy1 = sy;
            const cx2 = sx + dx * 0.6;
            const cy2 = ty;

            const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
            path.setAttribute('d', `M ${sx} ${sy} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${tx} ${ty}`);
            path.setAttribute('fill', 'none');
            path.setAttribute('stroke', isUnlocked ? 'url(#edge-unlocked-grad)' : '#334155');
            path.setAttribute('stroke-width', isUnlocked ? '3' : '2');
            if (!isUnlocked) {
                path.setAttribute('stroke-dasharray', '5,5');
            }
            path.setAttribute('marker-end', isUnlocked ? 'url(#arrow-unlocked)' : 'url(#arrow-locked)');

            if (isUnlocked) {
                path.classList.add('transition-all');
            }

            // Exclusão de aresta no modo editor ao clicar na linha
            if (state.interactionMode === 'edit') {
                path.style.cursor = 'pointer';
                path.style.pointerEvents = 'stroke';
                path.setAttribute('stroke-width', '8');
                path.setAttribute('stroke-opacity', isUnlocked ? '0.8' : '0.4');
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

    // Renderiza os nós no container HTML
    function renderNodes() {
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

            // Cores do anel conforme Nível SRS (0 a 6)
            let ringColorClass = 'border-slate-600 bg-slate-900';
            let glowEffect = '';
            if (node.effective_level >= 5) {
                ringColorClass = 'border-amber-400 bg-slate-900 ring-4 ring-amber-400/30';
                glowEffect = 'shadow-[0_0_20px_rgba(251,191,36,0.5)]';
            } else if (node.effective_level >= 1) {
                ringColorClass = 'border-emerald-500 bg-slate-900 ring-4 ring-emerald-500/20';
                glowEffect = 'shadow-[0_0_15px_rgba(16,185,129,0.4)]';
            }

            if (isLocked) {
                ringColorClass = 'border-slate-700 bg-slate-950 opacity-40 grayscale';
            }

            // Pulsação de Alerta se houver revisões atrasadas no SRS
            let overduePulse = '';
            if (isOverdue && !isLocked) {
                overduePulse = 'animate-pulse ring-4 ring-rose-500/60 shadow-[0_0_20px_rgba(244,63,94,0.7)]';
            }

            el.innerHTML = `
                <div class="relative w-18 h-18 rounded-2xl border-2 ${ringColorClass} ${glowEffect} ${overduePulse} flex items-center justify-center transition-all duration-200 group-hover:scale-110">
                    <span class="text-3xl">${iconGlyph}</span>
                    
                    ${isLocked ? `
                        <div class="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-slate-800 border border-slate-600 flex items-center justify-center text-xs">
                            🔒
                        </div>
                    ` : ''}

                    ${isOverdue && !isLocked ? `
                        <div class="absolute -top-2 -right-2 px-1.5 py-0.5 rounded-full bg-rose-600 border border-white text-[10px] font-black text-white shadow-md">
                            ! ${node.overdue_questions_count}
                        </div>
                    ` : ''}

                    <div class="absolute -bottom-2.5 px-2 py-0.5 rounded-md bg-slate-950 border border-slate-700 text-[9px] font-mono font-bold tracking-wider ${node.effective_level >= 1 ? 'text-emerald-400' : 'text-slate-500'}">
                        LVL ${node.effective_level}
                    </div>
                </div>
                <div class="mt-3 px-2 py-1 rounded-lg bg-slate-950/80 backdrop-blur border border-slate-800 text-center max-w-[140px]">
                    <span class="text-xs font-bold text-slate-200 truncate block">${escapeHtml(node.title)}</span>
                </div>
            `;

            // Eventos de clique e arrastar
            el.addEventListener('mousedown', (e) => onNodeMouseDown(e, node));
            el.addEventListener('click', (e) => onNodeClick(e, node));

            nodesLayer.appendChild(el);
        });
    }

    // --- Pan e Zoom da Câmera Cósmica ---

    function setupPanAndZoom() {
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

            // Zoom centrado na posição do cursor
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
        container.style.transform = `translate(${state.view.x}px, ${state.view.y}px) scale(${state.view.scale})`;
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

    // --- Arrastar Nós no Canvas (Drag & Drop) ---

    function onNodeMouseDown(e, node) {
        if (state.interactionMode !== 'edit' || state.connectModeActive) return;
        if (e.button !== 0) return; // Apenas botão esquerdo

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

        // Atualiza posição do elemento no DOM imediatamente (60 FPS)
        const el = nodesLayer.querySelector(`[data-node-id="${state.activeDragNode.id}"]`);
        if (el) {
            el.style.left = `${state.activeDragNode.pos_x}px`;
            el.style.top = `${state.activeDragNode.pos_y}px`;
        }

        // Re-renderiza arestas dinamicamente durante o movimento
        renderEdges();

        // Enfileira posição para salvamento em lote via debounce
        state.pendingPositions.set(state.activeDragNode.id, {
            node_id: state.activeDragNode.id,
            pos_x: state.activeDragNode.pos_x,
            pos_y: state.activeDragNode.pos_y,
        });
    }

    function onNodeMouseUp() {
        if (!state.activeDragNode) return;
        state.activeDragNode = null;

        // Dispara salvamento das coordenadas com debounce
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
            console.error('Falha ao salvar coordenadas do nó:', err);
        }
    }

    // --- Clique em Nós & Modo Conexão ---

    function onNodeClick(e, node) {
        e.stopPropagation();

        if (state.hasDragged) {
            state.hasDragged = false;
            return;
        }

        // Se estiver em modo conexão de arestas
        if (state.connectModeActive) {
            if (!state.connectSourceNodeId) {
                state.connectSourceNodeId = node.id;
                document.getElementById('connect-banner').textContent =
                    `⚡ ORIGEM SELECIONADA: "${node.title}". Agora clique no nó DEPENDENTE.`;
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

        // Caso normal: abre a gaveta lateral de inspeção do nó
        openNodeDrawer(node);
    }

    window.toggleConnectMode = () => {
        state.connectModeActive = !state.connectModeActive;
        state.connectSourceNodeId = null;
        const banner = document.getElementById('connect-banner');
        const btn = document.getElementById('btn-connect-mode');

        if (state.connectModeActive) {
            banner.classList.remove('hidden');
            banner.textContent = '⚡ MODO CONEXÃO: Clique no nó de pré-requisito e depois no dependente';
            btn.classList.add('bg-amber-600', 'text-white');
        } else {
            banner.classList.add('hidden');
            btn.classList.remove('bg-amber-600', 'text-white');
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
                alert('Erro ao conectar nós: ' + (err.detail || 'Falha de validação'));
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
            alert('Falha ao remover dependência: ' + err.message);
        }
    }

    // --- Alternar Modos: Estudo vs Edição ---

    window.setInteractionMode = (mode) => {
        state.interactionMode = mode;
        const btnStudy = document.getElementById('btn-mode-study');
        const btnEdit = document.getElementById('btn-mode-edit');
        const editorActions = document.getElementById('editor-actions');

        if (mode === 'edit') {
            btnEdit.className = 'px-3 py-1 font-bold rounded-lg transition-all bg-indigo-600 text-white shadow-sm';
            btnStudy.className = 'px-3 py-1 font-medium rounded-lg text-slate-400 hover:text-white transition-all';
            editorActions.classList.remove('hidden');
        } else {
            btnStudy.className = 'px-3 py-1 font-bold rounded-lg transition-all bg-indigo-600 text-white shadow-sm';
            btnEdit.className = 'px-3 py-1 font-medium rounded-lg text-slate-400 hover:text-white transition-all';
            editorActions.classList.add('hidden');
            if (state.connectModeActive) toggleConnectMode();
        }
        renderEdges();
    };

    // --- Drawer de Inspeção do Nó ---

    window.openNodeDrawer = async (node) => {
        state.selectedNode = node;
        drawer.classList.remove('hidden');

        document.getElementById('drawer-node-icon').textContent = ICON_MAP[node.icon] || '🧠';
        document.getElementById('drawer-node-title').textContent = node.title;
        document.getElementById('drawer-node-desc').textContent = node.description || 'Sem descrição cadastrada.';

        const levelBadge = document.getElementById('drawer-level-badge');
        levelBadge.textContent = `NÍVEL ${node.effective_level}`;

        const statusLabel = document.getElementById('drawer-unlock-status');
        statusLabel.textContent = node.is_unlocked ? 'Desbloqueado' : 'Bloqueado (Pré-requisitos pendentes)';
        statusLabel.className = node.is_unlocked ? 'text-xs text-emerald-400 font-semibold' : 'text-xs text-rose-400 font-semibold';

        const dueBadge = document.getElementById('drawer-due-badge');
        dueBadge.textContent = `${node.overdue_questions_count} pendentes hoje`;

        // Sub-mapa fractal
        const submapAction = document.getElementById('drawer-submap-action');
        submapAction.innerHTML = `
            <button
                type="button"
                onclick="handleSubmapClick('${node.id}', '${escapeHtml(node.title)}')"
                class="w-full py-2 px-3 rounded-xl text-xs font-bold bg-slate-800 hover:bg-slate-700 text-indigo-400 border border-indigo-500/30 flex items-center justify-center space-x-1.5 transition-colors"
            >
                <span>🔮 Abrir / Criar Sub-mapa Fractal ➔</span>
            </button>
        `;

        // Carrega hub completo de conteúdos do nó
        loadNodeHub(node.id);
    };

    window.closeNodeDrawer = () => {
        drawer.classList.add('hidden');
        state.selectedNode = null;
    };

    async function loadNodeHub(nodeId) {
        try {
            const res = await fetch(`/api/v1/study-maps/${state.mapId}/nodes/${nodeId}/hub`);
            if (!res.ok) return;
            const hub = await res.json();

            // Atualiza contadores das abas
            document.getElementById('count-tab-questions').textContent = hub.all_questions.length;
            document.getElementById('count-tab-materials').textContent = hub.materials.length;
            document.getElementById('count-tab-flashcards').textContent = hub.flashcards.length;

            renderDrawerQuestions(hub.all_questions);
            renderDrawerMaterials(hub.materials);
            renderDrawerFlashcards(hub.flashcards);
        } catch (err) {
            console.error('Erro ao carregar hub do nó:', err);
        }
    }

    function renderDrawerQuestions(questions) {
        const list = document.getElementById('drawer-questions-list');
        if (questions.length === 0) {
            list.innerHTML = `<p class="text-xs text-slate-500 italic py-2">Nenhuma pergunta aberta vinculada a este nó.</p>`;
            return;
        }

        list.innerHTML = questions.map(q => `
            <div class="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex items-start justify-between space-x-2">
                <div class="flex-1">
                    <div class="flex items-center space-x-2 mb-1">
                        <span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-indigo-950 text-indigo-400 border border-indigo-800">
                            SRS LVL ${q.current_level}
                        </span>
                        <span class="text-[10px] text-slate-500">Próx: ${q.next_review_date}</span>
                    </div>
                    <p class="text-xs text-slate-200 font-medium">${escapeHtml(q.prompt)}</p>
                </div>
                <button
                    type="button"
                    onclick="detachContent('question', '${q.id}')"
                    class="text-xs text-slate-500 hover:text-rose-400 p-1"
                    title="Desvincular"
                >✕</button>
            </div>
        `).join('');
    }

    function renderDrawerMaterials(materials) {
        const list = document.getElementById('drawer-materials-list');
        if (materials.length === 0) {
            list.innerHTML = `<p class="text-xs text-slate-500 italic py-2">Nenhum material didático vinculado.</p>`;
            return;
        }

        list.innerHTML = materials.map(m => `
            <div class="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex items-center justify-between">
                <div class="flex items-center space-x-2">
                    <span class="text-base">📄</span>
                    <div>
                        <p class="text-xs text-slate-200 font-bold">${escapeHtml(m.title)}</p>
                        <span class="text-[10px] text-slate-500 uppercase">${escapeHtml(m.content_type)}</span>
                    </div>
                </div>
                <button
                    type="button"
                    onclick="detachContent('material', '${m.id}')"
                    class="text-xs text-slate-500 hover:text-rose-400 p-1"
                    title="Desvincular"
                >✕</button>
            </div>
        `).join('');
    }

    function renderDrawerFlashcards(flashcards) {
        const list = document.getElementById('drawer-flashcards-list');
        if (flashcards.length === 0) {
            list.innerHTML = `<p class="text-xs text-slate-500 italic py-2">Nenhum flashcard vinculado.</p>`;
            return;
        }

        list.innerHTML = flashcards.map(fc => `
            <div class="p-3 rounded-xl bg-slate-950/60 border border-slate-800 flex items-start justify-between space-x-2">
                <div>
                    <p class="text-xs text-slate-200 font-semibold">${escapeHtml(fc.front)}</p>
                    <p class="text-[11px] text-slate-400 mt-1 line-clamp-2">${escapeHtml(fc.back)}</p>
                </div>
                <button
                    type="button"
                    onclick="detachContent('flashcard', '${fc.id}')"
                    class="text-xs text-slate-500 hover:text-rose-400 p-1"
                    title="Desvincular"
                >✕</button>
            </div>
        `).join('');
    }

    window.switchDrawerTab = (tabName) => {
        ['questions', 'materials', 'flashcards'].forEach(t => {
            const btn = document.getElementById(`tab-btn-${t}`);
            const content = document.getElementById(`tab-content-${t}`);
            if (t === tabName) {
                btn.className = 'pb-3 border-b-2 border-indigo-500 text-indigo-400 px-3 transition-colors';
                content.classList.remove('hidden');
            } else {
                btn.className = 'pb-3 border-b-2 border-transparent hover:text-slate-200 px-3 transition-colors';
                content.classList.add('hidden');
            }
        });
    };

    window.startNodeStudySession = () => {
        if (!state.selectedNode) return;
        // Redireciona para o estudo de perguntas SRS
        window.location.href = `/questions/study`;
    };

    window.handleSubmapClick = async (nodeId, nodeTitle) => {
        // Tenta encontrar se já existe um sub-mapa apontando para este parent_node_id
        try {
            const res = await fetch('/api/v1/study-maps');
            const maps = await res.json();
            const existingSubmap = maps.find(m => m.parent_node_id === nodeId);

            if (existingSubmap) {
                window.location.href = `/study-maps/${existingSubmap.id}/canvas`;
            } else {
                if (confirm(`Deseja criar um novo sub-mapa para aprofundar o nó "${nodeTitle}"?`)) {
                    const createRes = await fetch('/api/v1/study-maps', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            title: `Sub-mapa: ${nodeTitle}`,
                            description: `Detalhamento do conceito ${nodeTitle}`,
                            parent_node_id: nodeId,
                        }),
                    });
                    if (createRes.ok) {
                        const newSubmap = await createRes.json();
                        window.location.href = `/study-maps/${newSubmap.id}/canvas`;
                    }
                }
            }
        } catch (err) {
            alert('Falha ao acessar sub-mapa: ' + err.message);
        }
    };

    // --- Vinculação e Desvinculação de Conteúdos ---

    window.openAttachModal = async (contentType) => {
        const modal = document.getElementById('attach-modal');
        const titleEl = document.getElementById('attach-modal-title');
        const container = document.getElementById('attach-modal-items');
        modal.classList.remove('hidden');
        container.innerHTML = '<p class="text-xs text-slate-400">Carregando itens da sua biblioteca...</p>';

        let label = 'Perguntas';
        if (contentType === 'material') label = 'Materiais Didáticos';
        if (contentType === 'flashcard') label = 'Flashcards';
        titleEl.textContent = `Vincular ${label}`;

        try {
            let items = [];
            if (contentType === 'question') {
                const res = await fetch('/api/v1/questions/manage');
                if (res.ok) items = await res.json();
            } else if (contentType === 'material') {
                const res = await fetch('/api/v1/knowledge/sources');
                if (res.ok) items = await res.json();
            } else if (contentType === 'flashcard') {
                const res = await fetch('/api/v1/flashcards');
                if (res.ok) items = await res.json();
            }

            if (!items || items.length === 0) {
                container.innerHTML = `<p class="text-xs text-slate-400 py-3 italic">Nenhum item encontrado na biblioteca para vincular.</p>`;
                return;
            }

            container.innerHTML = items.map(item => {
                const itemTitle = item.prompt || item.title || item.front || 'Sem título';
                return `
                    <div class="p-3 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-between">
                        <span class="text-xs text-slate-200 font-medium truncate max-w-[300px]">${escapeHtml(itemTitle)}</span>
                        <button
                            type="button"
                            onclick="attachContent('${contentType}', '${item.id}')"
                            class="px-3 py-1 rounded-lg text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white shadow-sm"
                        >Vincular</button>
                    </div>
                `;
            }).join('');
        } catch (err) {
            container.innerHTML = `<p class="text-xs text-rose-400">Erro ao carregar itens da biblioteca.</p>`;
        }
    };

    window.closeAttachModal = () => {
        document.getElementById('attach-modal').classList.add('hidden');
    };

    window.attachContent = async (contentType, contentId) => {
        if (!state.selectedNode) return;
        try {
            const res = await fetch(`/api/v1/study-maps/${state.mapId}/nodes/${state.selectedNode.id}/contents`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content_type: contentType, content_id: contentId }),
            });
            if (res.ok) {
                closeAttachModal();
                loadNodeHub(state.selectedNode.id);
                loadGraph(); // Atualiza contadores no nó
            } else {
                alert('Falha ao vincular item ao nó.');
            }
        } catch (err) {
            alert('Erro de conexão: ' + err.message);
        }
    };

    window.detachContent = async (contentType, contentId) => {
        if (!state.selectedNode) return;
        if (!confirm('Deseja desvincular este item do nó?')) return;

        try {
            const res = await fetch(`/api/v1/study-maps/${state.mapId}/nodes/${state.selectedNode.id}/contents/${contentType}/${contentId}`, {
                method: 'DELETE',
            });
            if (res.ok) {
                loadNodeHub(state.selectedNode.id);
                loadGraph();
            }
        } catch (err) {
            alert('Erro ao desvincular: ' + err.message);
        }
    };

    // --- Criação e Edição de Nós ---

    window.openCreateNodeModal = () => {
        document.getElementById('node-modal-title').textContent = 'Adicionar Nó';
        document.getElementById('modal-node-id').value = '';
        document.getElementById('modal-node-title-input').value = '';
        document.getElementById('modal-node-desc-input').value = '';
        document.getElementById('modal-node-icon-select').value = 'brain';
        document.getElementById('node-modal').classList.remove('hidden');
    };

    window.openEditNodeModal = () => {
        if (!state.selectedNode) return;
        document.getElementById('node-modal-title').textContent = 'Editar Nó';
        document.getElementById('modal-node-id').value = state.selectedNode.id;
        document.getElementById('modal-node-title-input').value = state.selectedNode.title;
        document.getElementById('modal-node-desc-input').value = state.selectedNode.description || '';
        document.getElementById('modal-node-icon-select').value = state.selectedNode.icon || 'brain';
        document.getElementById('node-modal').classList.remove('hidden');
    };

    window.closeNodeModal = () => {
        document.getElementById('node-modal').classList.add('hidden');
    };

    window.handleSaveNode = async (e) => {
        e.preventDefault();
        const nodeId = document.getElementById('modal-node-id').value;
        const title = document.getElementById('modal-node-title-input').value.trim();
        const description = document.getElementById('modal-node-desc-input').value.trim();
        const icon = document.getElementById('modal-node-icon-select').value;

        try {
            if (!nodeId) {
                // Criação: posiciona no centro do viewport visível
                const centerX = (-state.view.x + viewport.clientWidth / 2) / state.view.scale - 36;
                const centerY = (-state.view.y + viewport.clientHeight / 2) / state.view.scale - 36;

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
                    alert('Erro ao criar nó: ' + (err.detail || 'Falha de validação'));
                }
            } else {
                // Atualização
                const res = await fetch(`/api/v1/study-maps/${state.mapId}/nodes/${nodeId}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title, description, icon }),
                });
                if (res.ok) {
                    closeNodeModal();
                    if (state.selectedNode) {
                        state.selectedNode.title = title;
                        state.selectedNode.description = description;
                        state.selectedNode.icon = icon;
                        openNodeDrawer(state.selectedNode);
                    }
                    loadGraph();
                }
            }
        } catch (err) {
            alert('Erro ao salvar nó: ' + err.message);
        }
    };

    window.deleteCurrentNode = async () => {
        if (!state.selectedNode) return;
        if (!confirm(`Deseja excluir o nó "${state.selectedNode.title}"?`)) return;

        try {
            const res = await fetch(`/api/v1/study-maps/${state.mapId}/nodes/${state.selectedNode.id}`, {
                method: 'DELETE',
            });
            if (res.ok) {
                closeNodeDrawer();
                loadGraph();
            }
        } catch (err) {
            alert('Falha ao excluir nó: ' + err.message);
        }
    };

    function escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

})();
