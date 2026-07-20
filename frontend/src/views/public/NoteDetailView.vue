<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import PublicAppShell from '../../components/public/PublicAppShell.vue'
import MarkdownArticle from '../../components/public/notes/MarkdownArticle.vue'
import { getNoteBySlug, getSiteMeta } from '../../public/content'
import { resolveGithubProof } from '../../public/githubMeta'

const props = defineProps<{
  slug: string
}>()

const router = useRouter()
const site = getSiteMeta()
const github = resolveGithubProof()
const note = computed(() => getNoteBySlug(props.slug))

if (!note.value) {
  void router.replace('/notes')
}
</script>

<template>
  <PublicAppShell
    :brand="site.brand"
    :github-url="github.htmlUrl"
    :star-label="github.starLabel"
    :show-stars="github.showStars"
  >
    <article v-if="note" class="note-detail">
      <RouterLink class="back" to="/notes">← 全部笔记</RouterLink>
      <header>
        <time>{{ note.date }}</time>
        <h1>{{ note.title }}</h1>
        <p>{{ note.summary }}</p>
        <div class="tags">
          <em v-for="tag in note.tags" :key="tag">{{ tag }}</em>
        </div>
      </header>
      <MarkdownArticle :markdown="note.body" />
      <footer v-if="note.related.length">
        <strong>相关链接</strong>
        <a
          v-for="item in note.related"
          :key="item.href"
          :href="item.href"
          target="_blank"
          rel="noreferrer"
        >
          {{ item.label }}
        </a>
      </footer>
    </article>
  </PublicAppShell>
</template>

<style scoped>
.note-detail {
  width: min(760px, 100%);
  margin: 0 auto;
  padding: 34px 0 56px;
}
.back {
  display: inline-flex;
  margin-bottom: 18px;
  color: var(--pub-brand-strong);
  text-decoration: none;
  font-size: 13px;
}
header {
  display: grid;
  gap: 10px;
  margin-bottom: 24px;
  padding-bottom: 18px;
  border-bottom: 1px solid var(--pub-border);
}
time {
  color: var(--pub-muted);
  font-family: var(--sage-font-mono, ui-monospace, monospace);
  font-size: 12px;
}
h1 {
  margin: 0;
  font-size: clamp(28px, 4vw, 40px);
  letter-spacing: -0.03em;
  line-height: 1.15;
}
header p {
  margin: 0;
  color: var(--pub-muted);
  font-size: 15px;
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
footer {
  display: grid;
  gap: 8px;
  margin-top: 28px;
  padding-top: 18px;
  border-top: 1px solid var(--pub-border);
}
footer strong {
  color: var(--pub-muted);
  font-size: 11px;
}
footer a {
  color: var(--pub-brand-strong);
  text-decoration: none;
  font-size: 13px;
}
</style>
