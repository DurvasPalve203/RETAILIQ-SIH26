import { LiveStatePayload } from '../types';

export class LiveFeedSocket {
  private socket: WebSocket | null = null;
  private onStateCallback: ((state: LiveStatePayload) => void) | null = null;
  private onStatusChange?: (isConnected: boolean) => void;
  private reconnectTimeout: any = null;
  private isExplicitlyClosed = false;
  private backoffDelay = 1500;
  private maxBackoff = 10000;

  constructor(
    onState: (state: LiveStatePayload) => void,
    onStatusChange?: (isConnected: boolean) => void
  ) {
    this.onStateCallback = onState;
    this.onStatusChange = onStatusChange;
    this.connect();
  }

  private connect() {
    if (this.isExplicitlyClosed) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/events/live`;

    try {
      this.socket = new WebSocket(wsUrl);

      this.socket.onopen = () => {
        console.log('[RetailIQ WebSocket] Connected to edge stream.');
        this.backoffDelay = 1500;
        if (this.onStatusChange) this.onStatusChange(true);
      };

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data && this.onStateCallback) {
            this.onStateCallback(data);
          }
        } catch (err) {
          console.error('[RetailIQ WebSocket] Parse error:', err);
        }
      };

      this.socket.onclose = () => {
        if (this.onStatusChange) this.onStatusChange(false);
        if (!this.isExplicitlyClosed) {
          this.reconnectTimeout = setTimeout(() => {
            this.backoffDelay = Math.min(this.backoffDelay * 1.5, this.maxBackoff);
            this.connect();
          }, this.backoffDelay);
        }
      };

      this.socket.onerror = (err) => {
        console.warn('[RetailIQ WebSocket] Stream reconnecting...');
        if (this.onStatusChange) this.onStatusChange(false);
        this.socket?.close();
      };
    } catch (e) {
      if (this.onStatusChange) this.onStatusChange(false);
      if (!this.isExplicitlyClosed) {
        this.reconnectTimeout = setTimeout(() => this.connect(), this.backoffDelay);
      }
    }
  }

  public close() {
    this.isExplicitlyClosed = true;
    if (this.reconnectTimeout) clearTimeout(this.reconnectTimeout);
    if (this.socket) this.socket.close();
  }
}
