<script setup lang="ts">
import type { PublicNote } from '../../../public/content'

defineProps<{
  note: PublicNote
}>()
</script>

<template>
  <RouterLink class="note-card" :to="`/notes/${note.slug}`">
    <time>{{ note.date }}</time>
    <strong>{{ note.title }}</strong>
    <p>{{ note.summary }}</p>
    <div class="tags">
      <em v-for="tag in note.tags" :key="tag">{{ tag }}</em>
    </div>
  </RouterLink>
</template>

<style scoped>
.note-card {
  display: grid;
  gap: 8px;
  padding: 18px;
  border: 1px solid var(--pub-border);
  border-radius: 16px;
  color: inherit;
  background: var(--pub-surface);
  text-decoration: none;
}
.note-card:hover {
  border-color: color-mix(in srgb, var(--pub-brand) 35%, var(--pub-border));
}
time {
  color: var(--pub-muted);
  font-family: var(--sage-font-mono, ui-monospace, monospace);
  font-size: 11px;
}
strong {
  font-size: 18px;
  letter-spacing: -0.02em;
}
p {
  margin: 0;
  color: var(--pub-muted);
  font-size: 14px;
  line-height: 1.7;
}
.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.tags em {
  padding: 4px 8px;
  border: 1px solid var(--pub-border);
  border-radius: 999px;
  color: var(--pub-brand-strong);
  background: color-mix(in srgb, var(--pub-brand) 8%, var(--pub-bg));
  font-size: 10px;
  font-style: normal;
}
</style>
