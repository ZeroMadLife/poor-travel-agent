import type { CodingServerEvent } from '../types/api'

export type WebSocketLike = {
  readyState: number
  onmessage: ((event: { data: string }) => void) | null
  onerror: (() => void) | null
  onclose: (() => void) | null
  send(data: string): void
  close(): void
}

export type WebSocketFactory = (url: string) => WebSocketLike

export type CodingStreamOptions = {
  createSocket?: WebSocketFactory
  onEvent: (event: CodingServerEvent) => void
  onError: (message: string) => void
}

const OPEN = 1

export class CodingStream {
  private socket: WebSocketLike | null = null
  private generation = 0
  private readonly createSocket: WebSocketFactory
  private readonly onEvent: (event: CodingServerEvent) => void
  private readonly onError: (message: string) => void

  constructor(options: CodingStreamOptions) {
    this.createSocket =
      options.createSocket ||
      ((url: string) => new WebSocket(url) as unknown as WebSocketLike)
    this.onEvent = options.onEvent
    this.onError = options.onError
  }

  connect(_sessionId: string, url: string): void {
    this.disconnect()
    const generation = ++this.generation
    const socket = this.createSocket(url)
    this.socket = socket
    socket.onmessage = (event) => {
      if (generation !== this.generation) return
      this.onEvent(JSON.parse(event.data) as CodingServerEvent)
    }
    socket.onerror = () => {
      if (generation !== this.generation) return
      this.onError('连接中断')
    }
    socket.onclose = () => {
      if (generation !== this.generation) return
      if (this.socket === socket) this.socket = null
    }
  }

  send(content: string): boolean {
    if (!this.socket || this.socket.readyState !== OPEN) return false
    this.socket.send(JSON.stringify({ content }))
    return true
  }

  stop(): void {
    this.disconnect()
  }

  disconnect(): void {
    this.generation += 1
    const socket = this.socket
    this.socket = null
    socket?.close()
  }
}
