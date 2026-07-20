<script setup lang="ts">
import { Github, Menu, MessageCircle, Moon, Sparkles, Sun } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'

defineProps<{
  brand: string
  githubUrl: string
  githubText: string
  theme: 'light' | 'dark'
}>()

const emit = defineEmits<{
  openAsk: []
  openMobile: []
  toggleTheme: []
}>()

const route = useRoute()
const router = useRouter()

const items = [
  { id: 'home', label: '首页', type: 'route', to: '/' },
  { id: 'harness', label: '体系', type: 'hash', hash: '#harness' },
  { id: 'evidence', label: '证据', type: 'hash', hash: '#evidence' },
  { id: 'notes', label: '笔记', type: 'route', to: '/notes' },
  { id: 'about', label: '关于', type: 'hash', hash: '#about' },
] as const

function isActive(id: string) {
  if (id === 'notes') return route.path.startsWith('/notes')
  if (id === 'home') return route.path === '/'
  return route.path === '/' && route.hash === `#${id}`
}

async function go(item: (typeof items)[number]) {
  if (item.type === 'route') {
    await router.push(item.to)
    return
  }
  if (route.path !== '/') await router.push({ path: '/', hash: item.hash })
  else await router.replace({ hash: item.hash })
  const el = document.querySelector(item.hash)
  el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}
</script>

<template>
  <header class="public-header">
    <button class="mobile-trigger" type="button" aria-label="打开导航菜单" @click="emit('openMobile')">
      <Menu :size="18" />
    </button>

    <RouterLink class="brand" to="/">
      <span class="brand-mark"><Sparkles :size="14" /></span>
      <strong>{{ brand }}</strong>
    </RouterLink>

    <nav class="capsule" aria-label="公开站点导航">
      <button
        v-for="item in items"
        :key="item.id"
        type="button"
        :data-nav="item.id"
        :class="{ active: isActive(item.id) }"
        @click="go(item)"
      >
        {{ item.label }}
      </button>
    </nav>

    <div class="header-actions">
      <button class="icon-btn" type="button" :aria-label="theme === 'dark' ? '切换浅色' : '切换深色'" @click="emit('toggleTheme')">
        <Sun v-if="theme === 'dark'" :size="15" />
        <Moon v-else :size="15" />
      </button>
      <a class="github-link" :href="githubUrl" target="_blank" rel="noreferrer">
        <Github :size="14" />
        <span>{{ githubText }}</span>
      </a>
      <button class="ask-btn" type="button" data-action="ask-sage" @click="emit('openAsk')">
        <MessageCircle :size="14" />
        问 Sage
      </button>
    </div>
  </header>
</template>

<style scoped>
.public-header {
  position: sticky;
  top: 0;
  z-index: 30;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 14px;
  width: min(1120px, calc(100% - 40px));
  min-height: 70px;
  margin: 0 auto;
  padding: 10px 0;
  background: color-mix(in srgb, var(--pub-bg) 88%, transparent);
  backdrop-filter: blur(14px);
}
.brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: inherit;
  text-decoration: none;
}
.brand strong { font-size: 14px; letter-spacing: -0.02em; }
.brand-mark {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 999px;
  color: #fff;
  background: var(--pub-brand);
}
.capsule {
  justify-self: center;
  display: none;
  gap: 2px;
  padding: 4px;
  border: 1px solid var(--pub-border);
  border-radius: 999px;
  background: color-mix(in srgb, var(--pub-surface) 88%, transparent);
}
.capsule button {
  min-height: 34px;
  padding: 0 14px;
  border: 0;
  border-radius: 999px;
  color: var(--pub-muted);
  background: transparent;
  font-size: 12px;
}
.capsule button.active,
.capsule button:hover {
  color: var(--pub-text);
  background: color-mix(in srgb, var(--pub-brand) 14%, var(--pub-surface));
}
.header-actions {
  display: flex;
  align-items: center;
  justify-content: end;
  gap: 8px;
}
.icon-btn,
.ask-btn,
.github-link,
.mobile-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 34px;
  border: 1px solid var(--pub-border);
  border-radius: 999px;
  color: var(--pub-text);
  background: var(--pub-surface);
  text-decoration: none;
  font-size: 12px;
}
.icon-btn,
.mobile-trigger {
  width: 34px;
  padding: 0;
}
.github-link,
.ask-btn { padding: 0 12px; }
.ask-btn {
  border-color: color-mix(in srgb, var(--pub-brand) 35%, var(--pub-border));
  color: var(--pub-brand-strong);
  background: color-mix(in srgb, var(--pub-brand) 12%, var(--pub-surface));
}
.mobile-trigger { display: inline-flex; }
@media (min-width: 920px) {
  .public-header { grid-template-columns: 1fr auto 1fr; }
  .capsule { display: inline-flex; }
  .mobile-trigger { display: none; }
}
@media (max-width: 560px) {
  .github-link span { display: none; }
  .ask-btn { padding: 0 10px; }
}
</style>
