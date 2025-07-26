<template>
  <div class="home-page">
    <div class="beta-banner">
      🚧 <strong>Version Bêta</strong> : ce site est en construction. Améliorations et correctifs à venir !
    </div>

    <PodcastSection 
      v-if="favoritePodcasts.length"
      title="❤️ Mes favoris"
      :podcasts="favoritePodcasts"
    />

<!-- ici on pourrait mettre des recommendations très précise = mise en avant de certaines chaînes = pour le moment aléatoire-->

    <PodcastSection 
      v-if="recommendedPodcasts.length"
      title="🎯 Ils pourraient vous plaire..."   
      :podcasts="recommendedPodcasts"   
    />


    <PodcastSection 
      title="🔥 Les plus écoutés"
      :podcasts="mostListened"
    />

    <PodcastSection 
      title="🎧 Podcasts du moment"
      :podcasts="trending"
    />

    <PodcastSection 
      title="✨ Nos suggestions"
      :podcasts="topSuggestions"
      :large="true"
    />
  </div>
</template>

<script>
import PodcastSection from './PodcastSection.vue'
import { getAuth, onAuthStateChanged } from 'firebase/auth'
import { doc, getDoc } from 'firebase/firestore'
import { db } from './firebase'

export default {
  name: 'HomePage',
  components: {
    PodcastSection
  },
  props: {
    podcasts: {
      type: Array,
      required: true
    }, 
    categories: {
      type: Array,
      required: false
    }
  },
  data() {
    return {
      favoritePodcasts: [],
      recommendedPodcasts: []
    }
  },
  computed: {
    topSuggestions() {
      return [...this.podcasts].sort(() => Math.random() - 0.5).slice(10, 18)
    },
    mostListened() {
      return [...this.podcasts]
        .sort((a, b) => b["Monde"] - a["Monde"])
        .slice(0, 10)
    },
    trending() {
      return [...this.podcasts]
        .filter(p => p["Monde"] > 1000)
        .sort(() => Math.random() - 0.5)
        .slice(0, 10)
    }
  },
  mounted() {
    onAuthStateChanged(getAuth(), async (user) => {
      if (user) {
        const userRef = doc(db, 'users', user.uid)
        const snap = await getDoc(userRef)
        if (snap.exists()) {
          const favIds = snap.data().favorites || []
          this.favoritePodcasts = this.podcasts.filter(p => favIds.includes(p.id ?? p.Podcasts))
          const favCategories = this.favoritePodcasts.map(p => p.category || p.Categorie)
          const uniqueCategories = [...new Set(favCategories)]
          this.recommendedPodcasts = this.podcasts.filter(p =>
            uniqueCategories.includes(p.category || p.Categorie) &&
            !favIds.includes(p.id ?? p.Podcasts)
          ).slice(0, 10)
        }
      }
    })
  }
}
</script>

<style scoped>
.home-page {
  padding: 2rem 0;
  background-color: #000;
  color: #fff;
  min-height: 100vh;
}

.beta-banner {
  background-color: #fffbeb;
  color: #92400e;
  border: 1px solid #facc15;
  padding: 12px;
  text-align: center;
  font-weight: bold;
  font-size: 1.1rem;
  border-radius: 8px;
  margin: 1rem auto;
  max-width: 800px;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
}
</style>
