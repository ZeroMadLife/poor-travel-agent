import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, expect, it } from 'vitest'
import { useChatStore } from './chat'

type SocketHandler = ((event?: MessageEvent) => void) | null

class FakeWebSocket {
  static instances: FakeWebSocket[] = []

  readonly url: string
  onopen: SocketHandler = null
  onmessage: SocketHandler = null
  onerror: SocketHandler = null
  onclose: SocketHandler = null
  closed = false

  constructor(url: string) {
    this.url = url
    FakeWebSocket.instances.push(this)
  }

  close() {
    this.closed = true
    this.onclose?.()
  }

  open() {
    this.onopen?.()
  }

  receive(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent)
  }
}

beforeEach(() => {
  setActivePinia(createPinia())
  FakeWebSocket.instances = []
})

it('connects to the chat websocket and stores progress events', () => {
  const store = useChatStore()

  store.connectStream('session-001', (url) => new FakeWebSocket(url) as unknown as WebSocket)
  const socket = FakeWebSocket.instances[0]
  socket.open()
  socket.receive({ type: 'progress', agent: 'planning', message: '正在生成行程' })

  expect(socket.url).toContain('/api/v1/chat/session-001/stream')
  expect(store.connectionStatus).toBe('connected')
  expect(store.events).toEqual([
    { type: 'progress', agent: 'planning', message: '正在生成行程' },
  ])
})

it('stores result events and closes the active socket', () => {
  const store = useChatStore()

  store.connectStream('session-001', (url) => new FakeWebSocket(url) as unknown as WebSocket)
  const socket = FakeWebSocket.instances[0]
  socket.receive({
    type: 'result',
    itinerary: { destination: '杭州', days: [], total_cost: 0 },
    validation: { passed: false, issues: [] },
    metrics: { latency_ms: 1200 },
  })
  store.closeStream()

  expect(store.result?.itinerary.destination).toBe('杭州')
  expect(socket.closed).toBe(true)
})
