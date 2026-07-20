<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ArrowRight, Send, Sparkles, X } from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import {
  answerPublicProfileQuestion,
  type PublicAgentSource,
} from '../../harness/publicAgent'

type AgentMessage = {
  role: 'visitor' | 'sage'
  text: string
  sources?: PublicAgentSource[]
}

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ close: [] }>()
const router = useRouter()

const question = ref('')
const isAnswering = ref(false)
const agentMessages = ref<AgentMessage[]>([
  { role: 'sage', text: '这是公开资料预览。我只回答已经公开的项目、方法和成长记录。' },
])
const bodyRef = ref<HTMLElement | null>(null)

async function answerQuestion(preset = '') {
  const value = (preset || question.value).trim()
  if (!value || isAnswering.value) return
  question.value = ''
  agentMessages.value.push({ role: 'visitor', text: value })
  isAnswering.value = true
  try {
    const response = await answerPublicProfileQuestion(value)
    agentMessages.value.push({ role: 'sage', text: response.answer, sources: response.sources })
  } finally {
    isAnswering.value = false
    await nextTick()
    if (bodyRef.value) bodyRef.value.scrollTop = bodyRef.value.scrollHeight
  }
}

async function openSource(source: PublicAgentSource) {
  emit('close')
  const target = source.target.startsWith('#') ? source.target : `#${source.target}`
  if (router.currentRoute.value.path !== '/') {
    await router.push({ path: '/', hash: target })
  } else {
    await router.replace({ hash: target })
  }
  document.querySelector(target)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function onExternalAsk(event: Event) {
  const detail = (event as CustomEvent<{ prompt?: string }>).detail
  if (detail?.prompt) void answerQuestion(detail.prompt)
}

onMounted(() => {
  window.addEventListener('sage-public-ask', onExternalAsk as EventListener)
})
onBeforeUnmount(() => {
  window.removeEventListener('sage-public-ask', onExternalAsk as EventListener)
})

watch(
  () => props.open,
  async (open) => {
    if (!open) return
    await nextTick()
    bodyRef.value?.scrollTo?.({ top: bodyRef.value.scrollHeight })
  },
)
</script>

<template>
  <aside
    v-if="open"
    class="public-agent"
    role="dialog"
    aria-modal="true"
    aria-label="公开 Sage 助手"
    @keydown.esc="emit('close')"
  >
    <header>
      <div class="agent-title">
        <span class="agent-mark"><Sparkles :size="16" /></span>
        <span>
          <strong>Ask Sage</strong>
          <small>公开资料预览</small>
        </span>
      </div>
      <button class="icon-button" type="button" aria-label="关闭公开助手" @click="emit('close')">
        <X :size="17" />
      </button>
    </header>

    <section ref="bodyRef" class="agent-body" aria-live="polite">
      <div
        v-for="(message, index) in agentMessages"
        :key="index"
        class="agent-message"
        :class="message.role"
      >
        <span>{{ message.role === 'sage' ? 'Sage' : '你' }}</span>
        <p>{{ message.text }}</p>
        <div v-if="message.sources?.length" class="agent-sources">
          <strong>回答依据</strong>
          <button
            v-for="source in message.sources"
            :key="source.id + source.label"
            type="button"
            class="agent-source"
            @click="openSource(source)"
          >
            <span>{{ source.label }}</span>
            <small>{{ source.detail }}</small>
            <ArrowRight :size="13" />
          </button>
        </div>
      </div>
    </section>

    <div class="agent-prompts">
      <span>试试问：</span>
      <button type="button" @click="answerQuestion('Sage 是做什么的？')">Sage 是做什么的？</button>
      <button type="button" @click="answerQuestion('Harness 2.0 解决什么问题？')">Harness 2.0 解决什么问题？</button>
      <button type="button" @click="answerQuestion('知识图谱在这里做什么？')">知识图谱在这里做什么？</button>
    </div>

    <form class="agent-form" :aria-busy="isAnswering" @submit.prevent="answerQuestion()">
      <textarea
        v-model="question"
        rows="3"
        placeholder="询问公开的项目与方法…"
        :disabled="isAnswering"
      />
      <button type="submit" aria-label="发送问题" :disabled="isAnswering || !question.trim()">
        <Send :size="16" />
      </button>
    </form>
    <p class="agent-disclaimer">当前是静态资料问答，后续可替换为受限公网 Harness。</p>
  </aside>
</template>

<style scoped>
.public-agent {
  position: fixed;
  z-index: 50;
  inset: 0 0 0 auto;
  display: flex;
  flex-direction: column;
  width: min(408px, 100%);
  border-left: 1px solid var(--pub-border);
  background: var(--pub-bg);
  box-shadow: -18px 0 48px rgb(28 55 36 / 14%);
}
.public-agent > header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 70px;
  padding: 0 18px;
  border-bottom: 1px solid var(--pub-border);
  background: var(--pub-surface);
}
.agent-title {
  display: flex;
  align-items: center;
  gap: 10px;
}
.agent-title > span:last-child { display: grid; gap: 1px; }
.agent-title strong { font-size: 13px; }
.agent-title small { color: var(--pub-muted); font-size: 10px; }
.agent-mark {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  color: #fff;
  background: var(--pub-brand);
}
.icon-button {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: 0;
  color: var(--pub-muted);
  background: transparent;
}
.agent-body {
  display: grid;
  align-content: start;
  gap: 16px;
  flex: 1;
  min-height: 0;
  padding: 20px 18px;
  overflow: auto;
}
.agent-message {
  display: grid;
  gap: 5px;
  max-width: 90%;
}
.agent-message > span {
  color: var(--pub-muted);
  font-family: var(--sage-font-mono, ui-monospace, monospace);
  font-size: 10px;
}
.agent-message p {
  margin: 0;
  padding: 11px 12px;
  color: var(--pub-text);
  background: var(--pub-surface);
  border: 1px solid var(--pub-border);
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.7;
}
.agent-message.visitor { justify-self: end; max-width: 86%; }
.agent-message.visitor > span { text-align: right; }
.agent-message.visitor p {
  color: #fff;
  background: var(--pub-brand);
  border-color: var(--pub-brand);
}
.agent-sources {
  display: grid;
  margin-top: 1px;
  border: 1px solid var(--pub-border);
  border-radius: 12px;
  overflow: hidden;
  background: var(--pub-surface);
}
.agent-sources > strong {
  padding: 10px 12px 6px;
  color: var(--pub-muted);
  font-size: 9px;
}
.agent-source {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 2px 8px;
  padding: 8px 12px;
  border: 0;
  border-top: 1px solid var(--pub-border);
  color: var(--pub-brand-strong);
  background: transparent;
  text-align: left;
}
.agent-source > span { font-size: 11px; font-weight: 650; }
.agent-source small {
  grid-column: 1;
  color: var(--pub-muted);
  font-size: 9px;
  line-height: 1.45;
}
.agent-source svg {
  grid-row: 1 / span 2;
  grid-column: 2;
  align-self: center;
}
.agent-prompts {
  display: grid;
  gap: 6px;
  padding: 16px 18px;
  border-top: 1px solid var(--pub-border);
}
.agent-prompts > span { color: var(--pub-muted); font-size: 10px; }
.agent-prompts button {
  padding: 6px 0;
  border: 0;
  color: var(--pub-brand-strong);
  background: transparent;
  text-align: left;
  font-size: 11px;
}
.agent-form {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 34px;
  gap: 8px;
  align-items: end;
  margin: 0 12px;
  padding: 10px;
  border: 1px solid var(--pub-border);
  border-radius: 14px;
  background: var(--pub-surface);
}
.agent-form textarea {
  min-height: 58px;
  resize: none;
  border: 0;
  outline: 0;
  color: var(--pub-text);
  background: transparent;
  font-size: 13px;
  line-height: 1.55;
}
.agent-form button {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 10px;
  color: #fff;
  background: var(--pub-brand);
}
.agent-form button:disabled {
  color: var(--pub-muted);
  background: color-mix(in srgb, var(--pub-border) 70%, var(--pub-surface));
}
.agent-disclaimer {
  margin: 8px 18px 14px;
  color: var(--pub-muted);
  font-size: 10px;
}
@media (max-width: 560px) {
  .public-agent { width: 100%; }
}
</style>
