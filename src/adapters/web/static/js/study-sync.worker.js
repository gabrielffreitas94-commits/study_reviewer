/**
 * Dedicated Web Worker: study-sync.worker.js
 * Isolamento total de I/O em IndexedDB e despacho de rede em segundo plano (INP <= 50ms).
 * Despacho com fetch(keepalive: true) e propagação de W3C TraceContext.
 */

const DB_NAME = "study_reviewer_outbox";
const DB_VERSION = 1;
const STORE_NAME = "events";
const BATCH_SIZE = 25;
let syncEndpoint = "/api/v1/study/sync-answers";
let isSyncing = false;

// Inicializa ou abre o banco de dados IndexedDB
function openDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = (event) => {
      const db = event.target.result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME, { keyPath: "local_id", autoIncrement: true });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// Salva um ou mais eventos no outbox local
async function saveToOutbox(events) {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    events.forEach((ev) => store.add(ev));
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

// Obtém lote pendente do outbox
async function getPendingEvents(limit = BATCH_SIZE) {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readonly");
    const store = tx.objectStore(STORE_NAME);
    const request = store.openCursor();
    const batch = [];
    request.onsuccess = (event) => {
      const cursor = event.target.result;
      if (cursor && batch.length < limit) {
        batch.push(cursor.value);
        cursor.continue();
      } else {
        resolve(batch);
      }
    };
    request.onerror = () => reject(request.error);
  });
}

// Remove eventos concluídos do outbox
async function removeFromOutbox(localIds) {
  const db = await openDatabase();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    localIds.forEach((id) => store.delete(id));
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

// Gera cabeçalho W3C TraceContext (traceparent)
function generateTraceParent() {
  const randHex = (len) => {
    let s = "";
    for (let i = 0; i < len; i++) {
      s += Math.floor(Math.random() * 16).toString(16);
    }
    return s;
  };
  const traceId = randHex(32);
  const spanId = randHex(16);
  return `00-${traceId}-${spanId}-01`;
}

// Despacha eventos em lote com keepalive
async function flushOutbox(authToken, csrfToken) {
  if (isSyncing) return;
  isSyncing = true;

  try {
    const batch = await getPendingEvents(BATCH_SIZE);
    if (!batch || batch.length === 0) {
      isSyncing = false;
      self.postMessage({ type: "SYNC_STATUS", status: "idle", pendingCount: 0 });
      return;
    }

    self.postMessage({ type: "SYNC_STATUS", status: "syncing", pendingCount: batch.length });

    // Agrupa por session_id
    const sessionId = batch[0].session_id;
    const cleanEvents = batch.map((ev) => ({
      id: ev.id,
      card_id: ev.card_id,
      reviewed_at: ev.reviewed_at,
      status: ev.status || "viewed",
      device_id: ev.device_id || "web-client",
    }));

    const maxBatchIndex = Math.max(...batch.map((ev) => ev.current_index || 0));

    const headers = {
      "Content-Type": "application/json",
      "traceparent": generateTraceParent(),
    };
    if (authToken) headers["Authorization"] = `Bearer ${authToken}`;
    if (csrfToken) headers["X-CSRF-Token"] = csrfToken;

    const response = await fetch(syncEndpoint, {
      method: "POST",
      headers,
      body: JSON.stringify({
        session_id: sessionId,
        events: cleanEvents,
        batch_index: maxBatchIndex,
      }),
      keepalive: true,
    });

    if (response.ok) {
      const data = await response.json();
      const removedIds = batch.map((b) => b.local_id);
      await removeFromOutbox(removedIds);
      const remaining = await getPendingEvents(1);
      self.postMessage({
        type: "SYNC_STATUS",
        status: remaining.length === 0 ? "synced" : "syncing",
        pendingCount: remaining.length,
        syncedCount: cleanEvents.length,
        serverIndex: data.current_index,
      });

      // Se restarem itens no outbox, despacha recursivamente
      if (remaining.length > 0) {
        setTimeout(() => flushOutbox(authToken, csrfToken), 100);
      }
    } else {
      self.postMessage({
        type: "SYNC_STATUS",
        status: "error",
        pendingCount: batch.length,
        statusCode: response.status,
      });
    }
  } catch (err) {
    self.postMessage({
      type: "SYNC_STATUS",
      status: "offline",
      error: err.message,
    });
  } finally {
    isSyncing = false;
  }
}

// Limpa banco de dados local por completo (Privacy by Default no Logout)
async function purgeDatabase() {
  try {
    indexedDB.deleteDatabase(DB_NAME);
    self.postMessage({ type: "PURGE_COMPLETE" });
  } catch (err) {
    self.postMessage({ type: "PURGE_ERROR", error: err.message });
  }
}

// Receptor de comandos da thread principal
self.onmessage = async (event) => {
  const { type, payload, authToken, csrfToken, endpoint } = event.data;

  if (endpoint) {
    syncEndpoint = endpoint;
  }

  if (type === "ENQUEUE_EVENT") {
    try {
      await saveToOutbox([payload]);
      await flushOutbox(authToken, csrfToken);
    } catch (err) {
      self.postMessage({ type: "SYNC_STATUS", status: "offline", error: err.message });
    }
  } else if (type === "FLUSH") {
    await flushOutbox(authToken, csrfToken);
  } else if (type === "PURGE") {
    await purgeDatabase();
  }
};
