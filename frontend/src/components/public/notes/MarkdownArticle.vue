<script setup lang="ts">
import { computed } from 'vue'
import { useMarkdown } from '../../../composables/useMarkdown'

const props = defineProps<{
  markdown: string
}>()

const { render } = useMarkdown()
const html = computed(() => render(props.markdown))
</script>

<template>
  <div class="markdown-article message-content" v-html="html" />
</template>

<style scoped>
.markdown-article {
  color: var(--pub-text);
  font-size: 15px;
  line-height: 1.8;
}
.markdown-article :deep(h2),
.markdown-article :deep(h3) {
  margin: 1.4em 0 0.55em;
  letter-spacing: -0.02em;
}
.markdown-article :deep(p),
.markdown-article :deep(ul),
.markdown-article :deep(ol) {
  margin: 0 0 1em;
}
.markdown-article :deep(a) {
  color: var(--pub-brand-strong);
}
.markdown-article :deep(code) {
  font-family: var(--sage-font-mono, ui-monospace, monospace);
  font-size: 0.92em;
}
</style>
