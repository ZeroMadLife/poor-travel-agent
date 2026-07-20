<script setup lang="ts">
import assistantImage from '../../../assets/public/assistant-desktop.webp'
import knowledgeImage from '../../../assets/public/knowledge-desktop.webp'
import practiceImage from '../../../assets/public/practice-desktop.webp'
import type { HomeSections } from '../../../public/content'

defineProps<{
  evidence: HomeSections['evidence']
}>()

const images = {
  assistant: assistantImage,
  knowledge: knowledgeImage,
  practice: practiceImage,
} as const
</script>

<template>
  <section id="evidence" class="evidence">
    <div class="heading">
      <span class="eyebrow">{{ evidence.eyebrow }}</span>
      <h2>{{ evidence.title }}</h2>
    </div>
    <div class="gallery">
      <figure v-for="item in evidence.items" :key="item.id">
        <div class="frame">
          <img :src="images[item.image as keyof typeof images]" :alt="`${item.title} 工作台截图`" loading="lazy" />
        </div>
        <figcaption>
          <strong>{{ item.title }}</strong>
          <span>{{ item.caption }}</span>
        </figcaption>
      </figure>
    </div>
  </section>
</template>

<style scoped>
.evidence { padding: 34px 0 18px; }
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
.gallery {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
figure {
  margin: 0;
  overflow: hidden;
  border: 1px solid var(--pub-border);
  border-radius: 16px;
  background: var(--pub-surface);
  box-shadow: 0 12px 28px rgb(24 40 28 / 6%);
}
.frame {
  aspect-ratio: 16 / 10;
  overflow: hidden;
  background: color-mix(in srgb, var(--pub-brand) 8%, var(--pub-bg));
}
img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: top center;
}
figcaption {
  display: grid;
  gap: 3px;
  padding: 12px 14px 14px;
}
figcaption strong { font-size: 13px; }
figcaption span {
  color: var(--pub-muted);
  font-size: 12px;
}
@media (max-width: 900px) {
  .gallery { grid-template-columns: 1fr; }
}
</style>
