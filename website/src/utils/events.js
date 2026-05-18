/**
 * EventSource helper for `/api/events?...` (token in query — EventSource cannot set headers).
 *
 * @param {string} baseUrl - e.g. import.meta.env.VITE_API_BASE or ''
 * @param {string} serverToken - same as X-Server-Token
 * @param {(msg: MessageEvent) => void} onMessage
 * @param {object} [options]
 * @param {string[]} [options.topics] - server-side topic filter (comma list)
 * @param {number} [options.maxDelayMs] - reconnect cap (default 30s)
 * @returns {{ close: () => void, get url(): string }}
 */
export function openEventsStream(baseUrl, serverToken, onMessage, options = {}) {
  const { topics = [], maxDelayMs = 30000 } = options;
  let closed = false;
  let attempt = 0;
  let es = null;
  let reconnectTimer = null;

  const buildUrl = () => {
    const u = new URL("/api/events", baseUrl || window.location.origin);
    u.searchParams.set("token", serverToken);
    if (topics.length) {
      u.searchParams.set("topics", topics.join(","));
    }
    return u;
  };

  const scheduleReconnect = () => {
    if (closed || reconnectTimer) {
      return;
    }
    const delay = Math.min(maxDelayMs, 1000 * 2 ** attempt);
    attempt += 1;
    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null;
      connect();
    }, delay);
  };

  const connect = () => {
    if (closed) {
      return;
    }
    if (es) {
      es.close();
    }
    es = new EventSource(buildUrl().toString());
    es.onmessage = onMessage;
    es.onopen = () => {
      attempt = 0;
    };
    es.onerror = () => {
      if (es) {
        es.close();
      }
      scheduleReconnect();
    };
  };

  connect();

  return {
    get url() {
      return buildUrl().toString();
    },
    close: () => {
      closed = true;
      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      if (es) {
        es.close();
        es = null;
      }
    },
  };
}
