<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import PublicHeader from './PublicHeader.vue'
import PublicMobileNav from './PublicMobileNav.vue'
import PublicFooter from './PublicFooter.vue'
import PublicAskSageDrawer from './PublicAskSageDrawer.vue'

const props = defineProps<{
  brand: string
  githubUrl: string
  starLabel?: string | null
  showStars?: boolean
}>()

const askOpen = ref(false)
const mobileOpen = ref(false)
const theme = ref<'light' | 'dark'>('light')

const githubText = computed(() => {
  if (props.showStars && props.starLabel) return `GitHub ★ ${props.starLabel}`
  return 'GitHub'
})

function openAsk(prompt = '') {
  askOpen.value = true
  mobileOpen.value = false
  if (prompt) {
    window.dispatchEvent(new CustomEvent('sage-public-ask', { detail: { prompt } }))
  }
}

function setTheme(next: 'light' | 'dark') {
  theme.value = next
  document.documentElement.dataset.theme = next
  document.documentElement.style.colorScheme = next
  localStorage.setItem('sage-public-theme', next)
}

function toggleTheme() {
  setTheme(theme.value === 'dark' ? 'light' : 'dark')
}

onMounted(() => {
  const stored = localStorage.getItem('sage-public-theme')
  if (stored === 'light' || stored === 'dark') {
    setTheme(stored)
    return
  }
  const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches
  setTheme(prefersDark ? 'dark' : 'light')
})

watch(askOpen, (open) => {
  document.body.style.overflow = open || mobileOpen.value ? 'hidden' : ''
})
watch(mobileOpen, (open) => {
  document.body.style.overflow = open || askOpen.value ? 'hidden' : ''
})

defineExpose({ openAsk })
</script>

<template>
  <div class="public-shell" :data-theme="theme">
    <PublicHeader
      :brand="brand"
      :github-url="githubUrl"
      :github-text="githubText"
      :theme="theme"
      @open-ask="openAsk()"
      @open-mobile="mobileOpen = true"
      @toggle-theme="toggleTheme"
    />
    <PublicMobileNav
      :open="mobileOpen"
      :brand="brand"
      :github-url="githubUrl"
      :github-text="githubText"
      @close="mobileOpen = false"
      @open-ask="openAsk()"
    />
    <main class="public-main">
      <slot :open-ask="openAsk" />
    </main>
    <PublicFooter
      :brand="brand"
      :github-url="githubUrl"
      @open-ask="openAsk()"
    />
    <PublicAskSageDrawer :open="askOpen" @close="askOpen = false" />
  </div>
</template>

<style scoped>
.public-shell {
  min-height: 100dvh;
  color: var(--pub-text);
  background:
    radial-gradient(circle at top left, color-mix(in srgb, var(--pub-brand) 10%, transparent), transparent 34%),
    var(--pub-bg);
  font-family: var(--sage-font-sans, Inter, ui-sans-serif, system-ui, sans-serif);
}
.public-main {
  width: min(1120px, calc(100% - 40px));
  margin: 0 auto;
}
</style>
