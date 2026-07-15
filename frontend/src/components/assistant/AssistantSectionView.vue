<script setup lang="ts">
import AssistantNavigation from './AssistantNavigation.vue'

defineProps<{ eyebrow: string; title: string; description: string; tone: 'source' | 'review' | 'public' }>()
</script>

<template>
  <AssistantNavigation>
    <div class="section-page" :data-tone="tone">
      <header><span>{{ eyebrow }}</span><h1>{{ title }}</h1><p>{{ description }}</p></header>
      <slot />
    </div>
  </AssistantNavigation>
</template>

<style scoped>
.section-page { width:min(880px,100%); margin:0 auto; padding:64px 34px 48px; }.section-page header { padding-bottom:22px; border-bottom:2px solid var(--sage-source); }.section-page[data-tone="review"] header { border-color:var(--sage-review); }.section-page[data-tone="public"] header { border-color:var(--sage-coral); }.section-page header span { color:var(--sage-text-muted); font-size:10px; }.section-page h1 { margin:8px 0 7px; font-size:24px; letter-spacing:0; }.section-page p { max-width:680px; margin:0; color:var(--sage-text-secondary); font-size:13px; line-height:1.7; }
:deep(.stage-content) { display:grid; grid-template-columns:180px minmax(0,1fr); gap:28px; padding:28px 0; border-bottom:1px solid var(--sage-border); }:deep(.stage-content h2) { margin:0; font-size:13px; }:deep(.stage-content p) { margin:0; color:var(--sage-text-secondary); font-size:12px; line-height:1.75; }:deep(.stage-content a) { color:var(--sage-source); font-weight:650; text-decoration:none; }
@media (max-width:899px) { .section-page { padding-top:72px; } }
@media (max-width:600px) { .section-page { padding-right:18px; padding-left:18px; }.section-page h1 { font-size:21px; }:deep(.stage-content) { grid-template-columns:1fr; gap:8px; } }
</style>
