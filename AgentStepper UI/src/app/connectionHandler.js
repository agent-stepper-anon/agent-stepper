/**
 * Manages WebSocket connection and reconnection logic.
 */
import { ref, onUnmounted } from 'vue';

const WS_URL = 'ws://localhost:4567';
const RECONNECT_DELAY_MS = 3000;
let socket = null;
let reconnectTimeoutId = null;
let wasConnected = false;

/**
 * Reactive flag indicating whether to show a disconnection notification.
 * @type {import('vue').Ref<boolean>}
 */
export const showNotification = ref(true);

/**
 * Establishes a WebSocket connection and sets up event handlers.
 * @param {function(WebSocket): void} onConnect - Callback invoked when the connection is established, receiving the socket.
 * @param {function(): void} onDisconnect - Callback invoked when the connection is lost.
 * @param {function(Event): void} onMessage - Callback invoked when a message is received from the server.
 */
export function connect(onConnect, onDisconnect, onMessage) {
  socket = new WebSocket(WS_URL);

  socket.addEventListener('open', () => {
    wasConnected = true;
    onConnect(socket);
    showNotification.value = false;
    clearReconnectTimeout();
  });

  socket.addEventListener('message', onMessage);

  socket.addEventListener('close', () => {
    if (wasConnected) {
      onDisconnect();
      showNotification.value = true;
    }
    scheduleReconnect(onConnect, onDisconnect, onMessage);
  });

  socket.addEventListener('error', () => {
    if (socket.readyState !== WebSocket.CLOSED) {
      socket.close();
    }
  });
}

/**
 * Schedules a reconnection attempt after a delay.
 * @param {function(WebSocket): void} onConnect - Callback for connection establishment.
 * @param {function(): void} onDisconnect - Callback for connection loss.
 * @param {function(Event): void} onMessage - Callback for received messages.
 */
function scheduleReconnect(onConnect, onDisconnect, onMessage) {
  clearReconnectTimeout();
  reconnectTimeoutId = setTimeout(() => {
    reconnectTimeoutId = null;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      connect(onConnect, onDisconnect, onMessage);
    }
  }, RECONNECT_DELAY_MS);
}

/**
 * Clears the reconnection timeout if it exists.
 */
function clearReconnectTimeout() {
  if (reconnectTimeoutId) {
    clearTimeout(reconnectTimeoutId);
    reconnectTimeoutId = null;
  }
}

/**
 * Closes the connection and clears the timeout when unmounted.
 */
onUnmounted(() => {
  if (socket) socket.close();
  if (reconnectTimeoutId) clearTimeout(reconnectTimeoutId);
});