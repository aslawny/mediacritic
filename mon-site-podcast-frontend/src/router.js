import { createRouter, createWebHistory } from 'vue-router'

import HomePage from './HomePage.vue'
import CategoryPage from './CategoryPage.vue'
import SearchPage from './SearchPage.vue'
import PodcastDetail from './PodcastDetail.vue'
import PodcastsPage from './PodcastsPage.vue'
import AboutPage from './AboutPage.vue'
import MentionsLegales from './MentionsLegales.vue'
import ContactPage from './ContactPage.vue'
import AuthForm from './AuthForm.vue'
import ProfilePage from './ProfilePage.vue'

const routes = [
  { path: '/', name: 'Home', component: HomePage },
  { path: '/category/:slug', name: 'Category', component: CategoryPage },
  { path: '/search/:query', name: 'Search', component: SearchPage },
  { path: '/podcast/:name', name: 'PodcastDetail', component: PodcastDetail },
  { path: '/podcasts', name: 'AllPodcasts', component: PodcastsPage },
  { path: '/about', name: 'About', component: AboutPage },
  { path: '/mentions-legales', name: 'MentionsLegales', component: MentionsLegales },
  { path: '/contact', name: 'Contact', component: ContactPage },
  {path: '/login',name: 'Login', component: AuthForm},
  { path: '/profile', component: ProfilePage },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
