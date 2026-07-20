<script setup lang="ts">
import PublicAppShell from '../../components/public/PublicAppShell.vue'
import NoteCard from '../../components/public/notes/NoteCard.vue'
import { getSiteMeta, listNotes } from '../../public/content'
import { resolveGithubProof } from '../../public/githubMeta'

const site = getSiteMeta()
const notes = listNotes()
const github = resolveGithubProof()
</script>

<template>
  <PublicAppShell
    :brand="site.brand"
    :github-url="github.htmlUrl"
    :star-label="github.starLabel"
    :show-stars="github.showStars"
  >
    <section class="notes-page">
      <div class="heading">
        <span class="eyebrow">ENGINEERING NOTES</span>
        <h1>工程笔记</h1>
        <p>只记录可验证的设计与落地判断，不写成生活流水账。</p>
      </div>
      <div class="list">
        <NoteCard v-for="note in notes" :key="note.slug" :note="note" />
      </div>
    </section>
  </PublicAppShell>
</template>

<style scoped>
.notes-page { padding: 36px 0 48px; }
.heading {
  display: grid;
  gap: 10px;
  margin-bottom: 22px;
}
.eyebrow {
  color: var(--pub-muted);
  font-size: 11px;
  letter-spacing: 0.08em;
}
h1 {
  margin: 0;
  font-size: clamp(30px, 4vw, 42px);
  letter-spacing: -0.03em;
}
p {
  margin: 0;
  color: var(--pub-muted);
  font-size: 14px;
  line-height: 1.7;
}
.list {
  display: grid;
  gap: 12px;
}
</style>
