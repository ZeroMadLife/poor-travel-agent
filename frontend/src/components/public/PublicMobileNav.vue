<script setup lang="ts">
import { Github, MessageCircle, X } from 'lucide-vue-next'
import { useRouter } from 'vue-router'

defineProps<{
  open: boolean
  brand: string
  githubUrl: string
  githubText: string
}>()

const emit = defineEmits<{
  close: []
  openAsk: []
}>()

const router = useRouter()

async function go(path: string, hash = '') {
  emit('close')
  if (path === '/' && hash) {
    await router.push({ path: '/', hash })
    document.querySelector(hash)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    return
  }
  await router.push(path)
}
</script>

<template>
  <div v-if="open" class="mobile-nav" role="dialog" aria-modal="true" aria-label="移动导航">
    <div class="panel">
      <header>
        <strong>{{ brand }}</strong>
        <button type="button" aria-label="关闭导航菜单" @click="emit('close')"><X :size="18" /></button>
      </header>
      <nav>
        <button type="button" @click="go('/')">首页</button>
        <button type="button" @click="go('/', '#harness')">体系</button>
        <button type="button" @click="go('/', '#evidence')">证据</button>
        <button type="button" @click="go('/notes')">笔记</button>
        <button type="button" @click="go('/', '#about')">关于</button>
      </nav>
      <div class="actions">
        <a :href="githubUrl" target="_blank" rel="noreferrer"><Github :size="15" />{{ githubText }}</a>
        <button type="button" @click="emit('openAsk')"><MessageCircle :size="15" />问 Sage</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mobile-nav {
  position: fixed;
  inset: 0;
  z-index: 40;
  background: rgb(10 16 12 / 42%);
  padding: 14px;
}
.panel {
  display: grid;
  gap: 18px;
  width: min(100%, 360px);
  margin-left: auto;
  padding: 16px;
  border: 1px solid var(--pub-border);
  border-radius: 18px;
  background: var(--pub-surface);
  box-shadow: 0 20px 48px rgb(16 24 18 / 18%);
}
header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
header button,
nav button,
.actions button,
.actions a {
  border: 0;
  background: transparent;
  color: var(--pub-text);
  font: inherit;
}
nav {
  display: grid;
  gap: 4px;
}
nav button {
  min-height: 42px;
  padding: 0 10px;
  border-radius: 12px;
  text-align: left;
}
nav button:hover { background: color-mix(in srgb, var(--pub-brand) 10%, transparent); }
.actions {
  display: grid;
  gap: 8px;
}
.actions a,
.actions button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 0 12px;
  border: 1px solid var(--pub-border);
  border-radius: 12px;
  text-decoration: none;
}
</style>
