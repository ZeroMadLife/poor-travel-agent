<script setup lang="ts">
import type { HomeSections } from '../../../public/content'

defineProps<{
  harness: HomeSections['harness']
}>()
</script>

<template>
  <section id="harness" class="harness">
    <div class="heading">
      <span class="eyebrow">{{ harness.eyebrow }}</span>
      <h2>{{ harness.title }}</h2>
      <p>{{ harness.support }}</p>
    </div>
    <div class="grid">
      <article v-for="item in harness.items" :key="item.id">
        <strong>{{ item.title }}</strong>
        <span>{{ item.detail }}</span>
      </article>
    </div>
  </section>
</template>

<style scoped>
.harness {
  padding: 28px 0 18px;
}
.heading {
  display: grid;
  gap: 8px;
  margin-bottom: 18px;
}
.eyebrow {
  color: var(--pub-muted);
  font-size: 11px;
  letter-spacing: 0.08em;
}
.heading h2 {
  margin: 0;
  font-size: clamp(24px, 3vw, 34px);
  letter-spacing: -0.03em;
}
.heading p {
  max-width: 60ch;
  margin: 0;
  color: var(--pub-muted);
  font-size: 14px;
  line-height: 1.7;
}
.grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}
article {
  display: grid;
  gap: 8px;
  min-height: 112px;
  padding: 16px;
  border: 1px solid var(--pub-border);
  border-radius: 16px;
  background: var(--pub-surface);
}
article strong { font-size: 15px; }
article span {
  color: var(--pub-muted);
  font-size: 12px;
  line-height: 1.6;
}
@media (max-width: 900px) {
  .grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 560px) {
  .grid { grid-template-columns: 1fr; }
}
</style>
