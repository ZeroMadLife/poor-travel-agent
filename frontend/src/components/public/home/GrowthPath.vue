<script setup lang="ts">
import { Check, CircleDot } from 'lucide-vue-next'
import type { HomeSections } from '../../../public/content'

defineProps<{
  path: HomeSections['path']
}>()
</script>

<template>
  <section id="path" class="path">
    <div class="heading">
      <span class="eyebrow">{{ path.eyebrow }}</span>
      <h2>{{ path.title }}</h2>
    </div>
    <ol>
      <li v-for="item in path.items" :key="item.title" :class="item.state">
        <span class="mark">
          <Check v-if="item.state === 'done'" :size="14" />
          <CircleDot v-else :size="14" />
        </span>
        <div>
          <time>{{ item.date }}</time>
          <strong>{{ item.title }}</strong>
          <p>{{ item.detail }}</p>
        </div>
      </li>
    </ol>
  </section>
</template>

<style scoped>
.path {
  display: grid;
  grid-template-columns: .9fr 1.1fr;
  gap: 28px;
  padding: 34px 0 18px;
}
.heading { display: grid; gap: 8px; align-content: start; }
.eyebrow {
  color: var(--pub-muted);
  font-size: 11px;
  letter-spacing: 0.08em;
}
h2 {
  margin: 0;
  font-size: clamp(24px, 3vw, 34px);
  letter-spacing: -0.03em;
}
ol {
  position: relative;
  display: grid;
  gap: 0;
  margin: 0;
  padding: 0;
  list-style: none;
}
ol::before {
  position: absolute;
  top: 16px;
  bottom: 16px;
  left: 15px;
  width: 1px;
  background: var(--pub-border);
  content: '';
}
li {
  position: relative;
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr);
  gap: 14px;
  padding: 0 0 22px;
}
li:last-child { padding-bottom: 0; }
.mark {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  border: 1px solid var(--pub-border);
  border-radius: 50%;
  color: var(--pub-muted);
  background: var(--pub-bg);
}
li.done .mark {
  color: var(--pub-brand-strong);
  border-color: color-mix(in srgb, var(--pub-brand) 45%, var(--pub-border));
  background: color-mix(in srgb, var(--pub-brand) 12%, var(--pub-bg));
}
li.now .mark {
  color: #fff;
  border-color: var(--pub-brand);
  background: var(--pub-brand);
  box-shadow: 0 0 0 5px color-mix(in srgb, var(--pub-brand) 16%, transparent);
}
time,
strong,
p { display: block; }
time {
  color: var(--pub-muted);
  font-family: var(--sage-font-mono, ui-monospace, monospace);
  font-size: 11px;
}
strong {
  margin-top: 4px;
  font-size: 15px;
}
p {
  margin: 5px 0 0;
  color: var(--pub-muted);
  font-size: 13px;
  line-height: 1.65;
}
@media (max-width: 800px) {
  .path { grid-template-columns: 1fr; }
}
</style>
