import { describe, expect, it, vi } from 'vitest'
import { CodingStream, type WebSocketLike } from './codingStream'
import type { CodingServerEvent } from '../types/api'

class FakeSocket implements WebSocketLike {
  readyState = 1
  onmessage: ((event: { data: string }) => void) | null = null
  onerror: (() => void) | null = null
  onclose: (() => void) | null = null
  sent: string[] = []
  closed = false

  send(data: string): void {
    this.sent.push(data)
  }

  close(): void {
    this.closed = true
    this.readyState = 3
    this.onclose?.()
  }

  emit(event: CodingServerEvent): void {
    this.onmessage?.({ data: JSON.stringify(event) })
  }
}

describe('CodingStream', () => {
  it('connects and sends user messages', () => {
    const sockets: FakeSocket[] = []
    const onEvent = vi.fn()
    const stream = new CodingStream({
      createSocket: () => {
        const socket = new FakeSocket()
        sockets.push(socket)
        return socket
      },
      onEvent,
      onError: vi.fn(),
    })

    stream.connect('coding_1', 'ws://local/stream')
    const sent = stream.send('hello')
    sockets[0].emit({ type: 'final', content: 'done' })

    expect(sent).toBe(true)
    expect(sockets[0].sent).toEqual([JSON.stringify({ content: 'hello' })])
    expect(onEvent).toHaveBeenCalledWith({ type: 'final', content: 'done' })
  })

  it('disconnect closes the active socket and prevents sending', () => {
    const sockets: FakeSocket[] = []
    const stream = new CodingStream({
      createSocket: () => {
        const socket = new FakeSocket()
        sockets.push(socket)
        return socket
      },
      onEvent: vi.fn(),
      onError: vi.fn(),
    })

    stream.connect('coding_1', 'ws://local/stream')
    stream.disconnect()

    expect(sockets[0].closed).toBe(true)
    expect(stream.send('hello')).toBe(false)
  })

  it('ignores events from an old socket after session switch', () => {
    const sockets: FakeSocket[] = []
    const onEvent = vi.fn()
    const stream = new CodingStream({
      createSocket: () => {
        const socket = new FakeSocket()
        sockets.push(socket)
        return socket
      },
      onEvent,
      onError: vi.fn(),
    })

    stream.connect('coding_1', 'ws://local/one')
    const oldSocket = sockets[0]
    stream.connect('coding_2', 'ws://local/two')
    oldSocket.emit({ type: 'final', content: 'old' })
    sockets[1].emit({ type: 'final', content: 'new' })

    expect(onEvent).toHaveBeenCalledTimes(1)
    expect(onEvent).toHaveBeenCalledWith({ type: 'final', content: 'new' })
  })
})
