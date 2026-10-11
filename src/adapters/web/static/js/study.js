/**
 * Study Reviewer — Motor de Sessão de Estudo em Alta Escala (study.js)
 * Conforme especificação docs/specs/study-sessions-high-scale-spec.md (Sprint 02)
 *
 * Funcionalidades:
 * - Flip 100% CSS 3D em 0ms (aposentando a rota HTTP /study/flip)
 * - Integração com Dedicated Web Worker (study-sync.worker.js) para outbox IndexedDB
 * - Optimistic UI com micro-transições aceleradas por GPU (120-150ms)
 * - Prefetch preditivo com Low-Water Mark (10 cards) via /api/v1/study/batch
 * - Degradação graciosa em Modo Privado / Quota Excedida
 * - Acessibilidade WCAG 2.1 AA (retenção de foco, live regions, atalhos WCAG 2.1.4)
 * - Widget discreto de status de sincronização no cabeçalho
 */

(function () {
  "use strict";

  // Estado interno da sessão de estudo
  const state = {
    cardQueue: [],
    currentCard: null,
    nextRoundFirstCard: null,
    sessionId: null,
    subjectId: null,
    topicId: null,
    totalCards: 0,
    roundNumber: 1,
    hasMore: true,
    isLoadingBatch: false,
    isPrivateMode: false,
    worker: null,
    deviceId: null,
    lowWaterMark: 10,
    cacheTtlMs: 2 * 60 * 60 * 1000, // 2 horas
    batchLoadedAt: null,
    isAdvancing: false,
  };

  // Elementos do DOM
  let els = {};

  function queryElements() {
    els = {
      container: document.getElementById("flashcard-container"),
      surface: document.getElementById("card-surface"),
      frontText: document.getElementById("card-front-text"),
      backText: document.getElementById("card-back-text"),
      frontTopics: document.getElementById("front-topics-container"),
      backTopics: document.getElementById("back-topics-container"),
      frontPos: document.getElementById("front-card-position"),
      backPos: document.getElementById("back-card-position"),
      btnFlip: document.getElementById("btn-flip"),
      btnFlipLabel: document.getElementById("btn-flip-label"),
      btnNext: document.getElementById("btn-next"),
      announcer: document.getElementById("card-announcer"),
      progress: document.getElementById("progress-indicator"),
      privateBanner: document.getElementById("private-mode-banner"),
      errorBanner: document.getElementById("sync-error-banner"),
      btnRetry: document.getElementById("btn-sync-retry"),
      victoryState: document.getElementById("victory-state"),
      btnRestart: document.getElementById("btn-restart-round"),
      filterSubject: document.getElementById("filter-subject"),
      filterTopic: document.getElementById("filter-topic"),
      syncDot: document.getElementById("sync-status-dot"),
      syncText: document.getElementById("sync-status-text"),
      syncWidget: document.getElementById("sync-status-widget"),
      statCards: document.getElementById("stat-cards-count"),
      statRound: document.getElementById("stat-round-number"),
    };
  }

  // Gera ou recupera identificador do dispositivo
  function getDeviceId() {
    try {
      let id = localStorage.getItem("study_reviewer_device_id");
      if (!id) {
        id = "dev-" + (crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 15));
        localStorage.setItem("study_reviewer_device_id", id);
      }
      return id;
    } catch (e) {
      return "volatile-device-" + Math.random().toString(36).substring(2, 10);
    }
  }

  // Atualiza o Widget de Status de Sincronização no cabeçalho
  function updateSyncWidget(status, pendingCount = 0) {
    if (!els.syncWidget || !els.syncDot || !els.syncText) return;

    if (status === "synced") {
      els.syncDot.className = "inline-block w-2 h-2 rounded-full bg-emerald-500";
      els.syncDot.innerHTML = "";
      els.syncText.textContent = "Progresso salvo na nuvem";
      if (els.errorBanner) els.errorBanner.classList.add("hidden");
    } else if (status === "syncing") {
      els.syncDot.className = "inline-flex items-center justify-center";
      els.syncDot.innerHTML =
        '<svg class="w-3.5 h-3.5 text-indigo-600 animate-spin" viewBox="0 0 24 24" fill="none"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>';
      els.syncText.textContent = "Sincronizando respostas...";
    } else if (status === "offline") {
      els.syncDot.className = "inline-block w-2 h-2 rounded-full bg-amber-500";
      els.syncDot.innerHTML = "";
      els.syncText.textContent =
        pendingCount > 0
          ? `Modo offline (${pendingCount} respostas salvas no dispositivo)`
          : "Modo offline (respostas salvas no dispositivo)";
    } else if (status === "error") {
      els.syncDot.className = "inline-block w-2 h-2 rounded-full bg-rose-500";
      els.syncDot.innerHTML = "";
      els.syncText.textContent = "Aguardando conexão para envio";
      if (els.errorBanner) els.errorBanner.classList.remove("hidden");
    }
  }

  // Fallback de sincronização para Modo Privado / Quota Excedida
  async function syncVolatileDirect(eventItem) {
    try {
      updateSyncWidget("syncing");
      const resp = await fetch("/api/v1/study/sync-answers", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: state.sessionId,
          events: [eventItem],
          batch_index: eventItem.current_index,
        }),
      });
      if (resp.ok) {
        updateSyncWidget("synced");
      } else {
        updateSyncWidget("error", 1);
      }
    } catch (e) {
      updateSyncWidget("offline", 1);
    }
  }

  // Inicializa o Web Worker ou aciona o fallback gracioso
  function initWorker() {
    try {
      // Teste de disponibilidade do IndexedDB
      if (!window.indexedDB) {
        throw new Error("IndexedDB não disponível");
      }

      state.worker = new Worker("/static/js/study-sync.worker.js");
      state.worker.onmessage = function (e) {
        const data = e.data || {};
        if (data.type === "SYNC_STATUS") {
          updateSyncWidget(data.status, data.pendingCount);
        }
      };
      state.worker.onerror = function () {
        enablePrivateModeFallback();
      };
    } catch (e) {
      enablePrivateModeFallback();
    }
  }

  function enablePrivateModeFallback() {
    state.isPrivateMode = true;
    state.worker = null;
    if (els.privateBanner) {
      els.privateBanner.classList.remove("hidden");
    }
  }

  // Normaliza o objeto de card garantindo consistência entre camelCase e snake_case
  function normalizeCard(rawCard) {
    if (!rawCard) return null;
    const currentIndex =
      rawCard.currentIndex !== undefined
        ? rawCard.currentIndex
        : rawCard.current_index;
    const totalCards =
      rawCard.totalCards !== undefined
        ? rawCard.totalCards
        : rawCard.total_cards;
    const roundNumber =
      rawCard.roundNumber !== undefined
        ? rawCard.roundNumber
        : rawCard.round_number;
    const sessionId =
      rawCard.sessionId !== undefined
        ? rawCard.sessionId
        : rawCard.session_id;

    return {
      ...rawCard,
      id: rawCard.id,
      front: rawCard.front || "",
      back: rawCard.back || "",
      position: rawCard.position || 100,
      currentIndex: parseInt(currentIndex || "1", 10),
      current_index: parseInt(currentIndex || "1", 10),
      totalCards: parseInt(totalCards || state.totalCards || "1", 10),
      total_cards: parseInt(totalCards || state.totalCards || "1", 10),
      roundNumber: parseInt(roundNumber || state.roundNumber || "1", 10),
      round_number: parseInt(roundNumber || state.roundNumber || "1", 10),
      sessionId: sessionId || state.sessionId || null,
      session_id: sessionId || state.sessionId || null,
      topic_names: rawCard.topic_names || [],
    };
  }

  // Enfileira evento de estudo no Worker ou via fallback volátil
  function dispatchStudyEvent(card) {
    if (!card || !state.sessionId) return;
    const normalized = normalizeCard(card);

    const eventPayload = {
      id: crypto.randomUUID ? crypto.randomUUID() : null,
      card_id: normalized.id,
      session_id: state.sessionId,
      reviewed_at: new Date().toISOString(),
      current_index: normalized.currentIndex,
      status: "viewed",
      device_id: state.deviceId,
    };

    if (state.worker && !state.isPrivateMode) {
      state.worker.postMessage({
        type: "ENQUEUE_EVENT",
        payload: eventPayload,
      });
    } else {
      syncVolatileDirect(eventPayload);
    }
  }

  // Virar o card em 0ms (Client-Side CSS 3D)
  function flipCard() {
    if (!els.surface) return;

    // Remove qualquer transform inline para que as regras CSS 3D funcionem perfeitamente
    els.surface.style.removeProperty("transform");

    const isCurrentlyFlipped = els.surface.classList.contains("is-flipped");
    if (isCurrentlyFlipped) {
      els.surface.classList.remove("is-flipped");
      els.surface.setAttribute(
        "aria-label",
        "Pergunta do card. Pressione espaço ou clique para revelar a resposta."
      );
      if (els.btnFlipLabel) els.btnFlipLabel.textContent = "Virar Card (Espaço)";
      if (els.announcer && state.currentCard) {
        els.announcer.textContent = `Pergunta: ${state.currentCard.front}`;
      }
    } else {
      els.surface.classList.add("is-flipped");
      els.surface.setAttribute(
        "aria-label",
        "Resposta do card. Pressione espaço ou clique para ver a pergunta."
      );
      if (els.btnFlipLabel) els.btnFlipLabel.textContent = "Ver Pergunta (Espaço)";
      if (els.announcer && state.currentCard) {
        els.announcer.textContent = `Resposta revelada: ${state.currentCard.back}`;
      }
    }
  }

  // Atualiza os dados visuais do card na tela com micro-transição GPU
  function renderCard(card, isNewRound = false) {
    if (!els.surface) return;

    const normalized = normalizeCard(card);
    state.currentCard = normalized;

    // Reseta estado de flip visual e classes/estilos residuais
    els.surface.classList.remove("is-flipped");
    els.surface.style.removeProperty("transform");
    if (els.btnFlipLabel) {
      els.btnFlipLabel.textContent = "Virar Card (Espaço)";
    }

    // Micro-transição suave com fade de opacidade (sem poluir o transform 3D)
    els.surface.style.opacity = "0.6";

    setTimeout(() => {
      // Atualiza textos
      if (els.frontText) els.frontText.textContent = normalized.front;
      if (els.backText) els.backText.textContent = normalized.back;
      if (els.frontPos) els.frontPos.textContent = `#${normalized.position}`;
      if (els.backPos) els.backPos.textContent = `#${normalized.position}`;

      // Atualiza tópicos
      const topicsHtml = (normalized.topic_names || [])
        .map(
          (t) =>
            `<span class="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-medium bg-slate-100 dark:bg-slate-700/70 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-600 max-w-full break-words-anywhere" title="${t}"><span class="mr-1 shrink-0" aria-hidden="true">🏷️</span><span>${t}</span></span>`
        )
        .join("");

      if (els.frontTopics) els.frontTopics.innerHTML = topicsHtml;
      if (els.backTopics) els.backTopics.innerHTML = topicsHtml;

      // Atualiza atributos do dataset e acessibilidade
      els.surface.setAttribute("data-card-id", normalized.id);
      els.surface.setAttribute("data-current-index", normalized.currentIndex);
      els.surface.setAttribute("data-total-cards", normalized.totalCards);
      els.surface.setAttribute("data-round-number", normalized.roundNumber);
      els.surface.setAttribute("data-position", normalized.position);
      if (normalized.sessionId) {
        els.surface.setAttribute("data-session-id", normalized.sessionId);
      }
      els.surface.setAttribute(
        "aria-label",
        "Pergunta do card. Pressione espaço ou clique para revelar a resposta."
      );

      // Atualiza indicador de progresso
      if (els.progress) {
        els.progress.innerHTML = `
          <span class="inline-block w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></span>
          <span>Card <strong class="text-slate-900 dark:text-white">${normalized.currentIndex}</strong> de <strong class="text-slate-900 dark:text-white">${normalized.totalCards}</strong></span>
          <span>•</span>
          <span>Rodada <strong class="text-slate-900 dark:text-white">${normalized.roundNumber}</strong></span>
        `;
      }

      // Região viva do leitor de tela
      if (els.announcer) {
        const prefix = isNewRound ? "Nova rodada iniciada. " : "";
        els.announcer.textContent = `${prefix}Card número ${normalized.currentIndex} de ${normalized.totalCards}, Rodada ${normalized.roundNumber}. Pergunta: ${normalized.front}`;
      }

      // Conclui transição restaurando opacidade e garantindo zero transform inline
      els.surface.style.removeProperty("opacity");
      els.surface.style.removeProperty("transform");
      els.surface.classList.remove("card-transition-gpu");

      // Retenção programática de foco (WCAG 2.1 AA)
      els.surface.focus();
    }, 130);
  }

  // Exibe a tela de vitória / conclusão de rodada (Victory State)
  function showVictoryState(completedRound) {
    if (els.surface) {
      els.surface.classList.remove("is-flipped");
      els.surface.style.removeProperty("transform");
      els.surface.style.removeProperty("opacity");
      if (els.surface.parentElement) {
        els.surface.parentElement.classList.add("hidden");
      }
    }
    const actionBtns = els.btnFlip ? els.btnFlip.parentElement : null;
    if (actionBtns) actionBtns.classList.add("hidden");

    const roundToShow =
      completedRound ||
      (state.currentCard ? (state.currentCard.roundNumber || state.currentCard.round_number) : state.roundNumber);
    if (els.statCards) els.statCards.textContent = state.totalCards;
    if (els.statRound) els.statRound.textContent = roundToShow;
    if (els.victoryState) els.victoryState.classList.remove("hidden");

    if (els.announcer) {
      els.announcer.textContent =
        "Parabéns! Rodada concluída com sucesso. Todos os cards deste bloco foram revisados.";
    }

    if (els.btnRestart) els.btnRestart.focus();
  }

  // Oculta victory state e exibe a superfície do card
  function hideVictoryState() {
    if (els.victoryState) els.victoryState.classList.add("hidden");
    if (els.surface) {
      els.surface.classList.remove("is-flipped");
      els.surface.style.removeProperty("transform");
      els.surface.style.removeProperty("opacity");
      if (els.surface.parentElement) {
        els.surface.parentElement.classList.remove("hidden");
      }
    }
    if (els.btnFlipLabel) {
      els.btnFlipLabel.textContent = "Virar Card (Espaço)";
    }
    const actionBtns = els.btnFlip ? els.btnFlip.parentElement : null;
    if (actionBtns) actionBtns.classList.remove("hidden");
  }

  // Prefetch preditivo de lote via API /api/v1/study/batch
  async function prefetchBatchIfNeeded() {
    if (state.isLoadingBatch || !state.hasMore) return;

    // Verifica TTL de segurança em lotes offline (2 horas - Seção 6.3)
    const now = Date.now();
    if (state.batchLoadedAt && now - state.batchLoadedAt > state.cacheTtlMs) {
      state.cardQueue = []; // Invalida lote expirado
    }

    if (state.cardQueue.length > state.lowWaterMark) return;

    state.isLoadingBatch = true;
    try {
      const params = new URLSearchParams();
      if (state.subjectId) params.set("subject_id", state.subjectId);
      if (state.topicId) params.set("topic_id", state.topicId);
      params.set("limit", "25");

      const resp = await fetch(`/api/v1/study/batch?${params.toString()}`);
      if (resp.status === 403) {
        // Matéria revogada ou convertida para privada (Seção 6.3)
        state.cardQueue = [];
        window.location.reload();
        return;
      }

      if (resp.ok) {
        const batch = await resp.json();
        const incomingCards = batch.cards || [];
        state.hasMore = batch.has_more;
        state.totalCards = batch.total_cards;
        state.roundNumber = batch.round_number;
        state.batchLoadedAt = Date.now();

        // Adiciona à fila apenas cards ainda não presentes
        const existingIds = new Set(state.cardQueue.map((c) => c.id));
        if (state.currentCard) existingIds.add(state.currentCard.id);

        for (const card of incomingCards) {
          if (!existingIds.has(card.id)) {
            state.cardQueue.push(card);
            existingIds.add(card.id);
          }
        }
      }
    } catch (e) {
      // Em caso de erro de rede, mantém a fila local sem quebrar o fluxo
    } finally {
      state.isLoadingBatch = false;
    }
  }

  // Avança para o próximo card (Optimistic UI em 0ms com proteção contra duplo clique)
  async function advanceCard() {
    if (!state.currentCard || state.isAdvancing) return;
    state.isAdvancing = true;
    setTimeout(() => {
      state.isAdvancing = false;
    }, 130);

    const finishedCard = normalizeCard(state.currentCard);

    // 1. Enfileira o evento do card que acaba de ser estudado
    dispatchStudyEvent(finishedCard);

    // 2. Se a fila em memória tiver o próximo card, avança imediatamente
    if (state.cardQueue.length > 0) {
      const nextCard = normalizeCard(state.cardQueue.shift());
      state.currentCard = nextCard;
      renderCard(nextCard);
      prefetchBatchIfNeeded();
      return;
    }

    // 3. Fila esgotada: busca da API se tem próximo card ou conclui rodada
    try {
      const params = new URLSearchParams();
      if (state.subjectId) params.set("subject_id", state.subjectId);
      if (state.topicId) params.set("topic_id", state.topicId);
      if (finishedCard && (finishedCard.currentIndex || finishedCard.current_index)) {
        params.set("current_index", (finishedCard.currentIndex || finishedCard.current_index).toString());
      }

      const resp = await fetch(`/api/v1/study/next?${params.toString()}`);
      if (resp.ok) {
        const nextCard = normalizeCard(await resp.json());
        const wasLastCard =
          finishedCard && finishedCard.currentIndex >= state.totalCards;
        if (nextCard.round_shuffled || nextCard.currentIndex === 1 || wasLastCard) {
          // Rodada concluiu! Salva o primeiro card da próxima rodada para quando o usuário clicar
          state.nextRoundFirstCard = nextCard;
          showVictoryState(finishedCard ? finishedCard.roundNumber : state.roundNumber);
        } else {
          state.currentCard = nextCard;
          renderCard(nextCard);
          prefetchBatchIfNeeded();
        }
      } else {
        showVictoryState(finishedCard ? finishedCard.roundNumber : state.roundNumber);
      }
    } catch (e) {
      showVictoryState(finishedCard ? finishedCard.roundNumber : state.roundNumber);
    }
  }

  // Reinicia a rodada após a tela de vitória (ou avança para a próxima lista)
  async function restartRound() {
    hideVictoryState();
    state.hasMore = true;
    state.cardQueue = [];
    bindCardEvents();

    if (state.nextRoundFirstCard) {
      const nextCard = normalizeCard(state.nextRoundFirstCard);
      state.nextRoundFirstCard = null;
      state.currentCard = nextCard;
      state.roundNumber = nextCard.roundNumber;
      state.totalCards = nextCard.totalCards;
      renderCard(nextCard, true);
      prefetchBatchIfNeeded();
      return;
    }

    try {
      const params = new URLSearchParams();
      if (state.subjectId) params.set("subject_id", state.subjectId);
      if (state.topicId) params.set("topic_id", state.topicId);

      const resp = await fetch(`/api/v1/study/next?${params.toString()}`);
      if (resp.ok) {
        const nextCard = normalizeCard(await resp.json());
        state.currentCard = nextCard;
        state.roundNumber = nextCard.roundNumber;
        state.totalCards = nextCard.totalCards;
        renderCard(nextCard, true);
        prefetchBatchIfNeeded();
      } else {
        window.location.reload();
      }
    } catch (e) {
      window.location.reload();
    }
  }

  // Inicializa atalhos de teclado (WCAG 2.1.4 compliant)
  function initKeyboardShortcuts() {
    document.addEventListener("keydown", function (e) {
      // Ignora atalhos se o foco estiver dentro de input, textarea ou select
      const activeTag = (document.activeElement && document.activeElement.tagName) || "";
      if (["INPUT", "TEXTAREA", "SELECT"].includes(activeTag)) {
        return;
      }

      // Espaço: Virar card (ou reiniciar rodada se na tela de vitória)
      if (e.code === "Space") {
        e.preventDefault();
        if (els.victoryState && !els.victoryState.classList.contains("hidden")) {
          restartRound();
        } else {
          flipCard();
        }
        return;
      }

      // Enter ou Seta Direita: Próximo card (ou reiniciar rodada se na tela de vitória)
      if (e.code === "Enter" || e.code === "ArrowRight") {
        e.preventDefault();
        if (els.victoryState && !els.victoryState.classList.contains("hidden")) {
          restartRound();
        } else {
          advanceCard();
        }
        return;
      }

      // 'M' ou 'm': Focar seletor de Matéria
      if (e.key === "m" || e.key === "M") {
        if (els.filterSubject) {
          e.preventDefault();
          els.filterSubject.focus();
        }
        return;
      }

      // 'T' ou 't': Focar seletor de Tema
      if (e.key === "t" || e.key === "T") {
        if (els.filterTopic && !els.filterTopic.disabled) {
          e.preventDefault();
          els.filterTopic.focus();
        }
        return;
      }
    });
  }

  // Gestos touch mobile (Swipe para a esquerda avança o card)
  function initTouchGestures() {
    let touchStartX = 0;
    let touchEndX = 0;

    document.addEventListener(
      "touchstart",
      function (e) {
        touchStartX = e.changedTouches[0].screenX;
      },
      { passive: true }
    );

    document.addEventListener(
      "touchend",
      function (e) {
        touchEndX = e.changedTouches[0].screenX;
        const threshold = 60;
        if (touchStartX - touchEndX > threshold) {
          advanceCard();
        }
      },
      { passive: true }
    );
  }

  function onVictoryClick() {
    restartRound();
  }

  function onRetryClick() {
    if (state.worker) state.worker.postMessage({ type: "FLUSH" });
  }

  // Vincula ouvintes aos elementos do card atual (seguro contra swaps HTMX)
  function bindCardEvents() {
    if (els.surface) {
      els.surface.removeEventListener("click", flipCard);
      els.surface.addEventListener("click", flipCard);
    }
    if (els.btnFlip) {
      els.btnFlip.removeEventListener("click", flipCard);
      els.btnFlip.addEventListener("click", flipCard);
    }
    if (els.btnNext) {
      els.btnNext.removeEventListener("click", advanceCard);
      els.btnNext.addEventListener("click", advanceCard);
    }
    if (els.btnRestart) {
      els.btnRestart.removeEventListener("click", restartRound);
      els.btnRestart.addEventListener("click", function (e) {
        e.stopPropagation();
        restartRound();
      });
    }
    if (els.victoryState) {
      els.victoryState.removeEventListener("click", onVictoryClick);
      els.victoryState.addEventListener("click", onVictoryClick);
    }
    if (els.btnRetry) {
      els.btnRetry.removeEventListener("click", onRetryClick);
      els.btnRetry.addEventListener("click", onRetryClick);
    }
  }

  // Tratamento de swaps do HTMX (mudança de filtros de matéria / tema)
  function onHtmxSwap() {
    queryElements();

    const urlParams = new URLSearchParams(window.location.search);
    state.subjectId =
      (els.filterSubject && els.filterSubject.value) ||
      urlParams.get("subject_id") ||
      null;
    state.topicId =
      (els.filterTopic && els.filterTopic.value) ||
      urlParams.get("topic_id") ||
      null;

    state.cardQueue = [];
    state.hasMore = true;
    state.nextRoundFirstCard = null;
    state.isAdvancing = false;

    if (els.surface) {
      state.currentCard = normalizeCard({
        id: els.surface.getAttribute("data-card-id"),
        sessionId: els.surface.getAttribute("data-session-id") || null,
        front: els.frontText ? els.frontText.textContent.trim() : "",
        back: els.backText ? els.backText.textContent.trim() : "",
        currentIndex: parseInt(els.surface.getAttribute("data-current-index") || "1", 10),
        totalCards: parseInt(els.surface.getAttribute("data-total-cards") || "1", 10),
        roundNumber: parseInt(els.surface.getAttribute("data-round-number") || "1", 10),
        position: parseInt(els.surface.getAttribute("data-position") || "100", 10),
      });
      state.sessionId = state.currentCard.sessionId;
      state.totalCards = state.currentCard.totalCards;
      state.roundNumber = state.currentCard.roundNumber;

      bindCardEvents();
      prefetchBatchIfNeeded();
    } else {
      state.currentCard = null;
    }
  }

  // Inicialização principal da aplicação de estudo
  function init() {
    queryElements();
    state.deviceId = getDeviceId();

    // Lê parâmetros da URL para subject e topic
    const urlParams = new URLSearchParams(window.location.search);
    state.subjectId =
      (els.filterSubject && els.filterSubject.value) ||
      urlParams.get("subject_id") ||
      null;
    state.topicId =
      (els.filterTopic && els.filterTopic.value) ||
      urlParams.get("topic_id") ||
      null;

    // Inicializa dados do card ativo se presente no DOM
    if (els.surface) {
      state.currentCard = normalizeCard({
        id: els.surface.getAttribute("data-card-id"),
        sessionId: els.surface.getAttribute("data-session-id") || null,
        front: els.frontText ? els.frontText.textContent.trim() : "",
        back: els.backText ? els.backText.textContent.trim() : "",
        currentIndex: parseInt(els.surface.getAttribute("data-current-index") || "1", 10),
        totalCards: parseInt(els.surface.getAttribute("data-total-cards") || "1", 10),
        roundNumber: parseInt(els.surface.getAttribute("data-round-number") || "1", 10),
        position: parseInt(els.surface.getAttribute("data-position") || "100", 10),
      });
      state.sessionId = state.currentCard.sessionId;
      state.totalCards = state.currentCard.totalCards;
      state.roundNumber = state.currentCard.roundNumber;

      bindCardEvents();

      // Inicializa Web Worker e prefetch
      initWorker();
      prefetchBatchIfNeeded();
    }

    initKeyboardShortcuts();
    initTouchGestures();

    // Ouvintes de ciclo de vida HTMX e histórico para troca ágil de matérias/temas
    document.body.addEventListener("htmx:afterSwap", onHtmxSwap);
    document.body.addEventListener("htmx:historyRestore", onHtmxSwap);
    window.addEventListener("popstate", onHtmxSwap);
  }

  // Executa ao carregar o DOM
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
