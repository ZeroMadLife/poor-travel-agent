<script setup lang="ts">
import { Github, MessageCircle } from 'lucide-vue-next'

defineProps<{
  brand: string
  githubUrl: string
}>()

const emit = defineEmits<{
  openAsk: []
}>()
</script>

<template>
  <footer class="public-footer">
    <div>
      <strong>{{ brand }}</strong>
      <span>记录真实工程判断，发布可验证作品。</span>
    </div>
    <div class="links">
      <a :href="githubUrl" target="_blank" rel="noreferrer"><Github :size="14" />GitHub</a>
      <RouterLink to="/notes">笔记</RouterLink>
      <button type="button" @click="emit('openAsk')"><MessageCircle :size="14" />问 Sage</button>
    </div>
  </footer>
</template>

<style scoped>
.public-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  width: min(1120px, calc(100% - 40px));
  min-height: 104px;
  margin: 0 auto;
  padding: 24px 0 36px;
  border-top: 1px solid var(--pub-border);
}
.public-footer > div:first-child {
  display: grid;
  gap: 4px;
}
.public-footer strong { font-size: 13px; }
.public-footer span { color: var(--pub-muted); font-size: 12px; }
.links {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
}
.links a,
.links button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0;
  border: 0;
  color: var(--pub-muted);
  background: transparent;
  text-decoration: none;
  font-size: 12px;
}
.links a:hover,
.links button:hover { color: var(--pub-brand-strong); }
@media (max-width: 560px) {
  .public-footer {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
