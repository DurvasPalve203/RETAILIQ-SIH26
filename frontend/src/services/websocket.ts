import { LiveStatePayload } from '../types';

export class LiveFeedSocket {
  private socket: WebSocket | null = null;
  private onStateCallback: ((state: LiveStatePayload) => void) | null = null;
  private reconnectTimeout: any = null;
  private isExplicitlyClosed = false;

  constructor(onState: (state: LiveStatePayload) => void) {
    this.onStateCallback = onState;
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
        console.log('[RetailIQ WebSocket] Connected to edge inference stream.');
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
        if (!this.isExplicitlyClosed) {
          this.reconnectTimeout = setTimeout(() => this.connect(), 2000);
        }
      };

      this.socket.onerror = (err) => {
        console.warn('[RetailIQ WebSocket] Connection error:', err);
        this.socket?.close();
      };
    } catch (e) {
      if (!this.isExplicitlyClosed) {
        this.reconnectTimeout = setTimeout(() => this.connect(), 3000);
      }
    }
  }

  public close() {
    this.isExplicitlyClosed = true;
    if (this.reconnectTimeout) clearTimeout(this.reconnectTimeout);
    if (this.socket) this.socket.close();
  }
}
