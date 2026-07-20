import { createRouter, createWebHistory } from 'vue-router'
import PublicHomeView from '../views/public/PublicHomeView.vue'
import NotesListView from '../views/public/NotesListView.vue'
import NoteDetailView from '../views/public/NoteDetailView.vue'

const publicRouter = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'public.home',
      component: PublicHomeView,
    },
    {
      path: '/notes',
      name: 'public.notes',
      component: NotesListView,
    },
    {
      path: '/notes/:slug',
      name: 'public.note',
      component: NoteDetailView,
      props: true,
    },
    {
      path: '/public',
      redirect: '/',
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/',
    },
  ],
  scrollBehavior(to) {
    if (to.hash) return { el: to.hash, behavior: 'smooth' }
    return { top: 0 }
  },
})

export default publicRouter
