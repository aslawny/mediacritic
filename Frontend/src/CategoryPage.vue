<template>
  <div class="category-page">
    <div class="category-header">
      <h1>{{ categoryTitle }}</h1>
      <p>Découvrez les meilleurs podcasts de {{ categoryTitle.toLowerCase() }}</p>
    </div>

    <div v-if="categoryPodcasts.length > 0">
      <PodcastSection 
        title="Meilleures suggestions"
        :podcasts="topRated"
        :large="true"
      />

      <PodcastSection 
        :title="`Populaires en ${categoryTitle}`"
        :podcasts="popular"
      />

      <PodcastSection 
        title="Recommandés pour vous"
        :podcasts="recommended"
      />
    </div>

    <div v-else class="text-center py-10 text-gray-500 text-lg">
      Aucun podcast trouvé pour cette catégorie.
    </div>
  </div>
</template>

<script>
import PodcastSection from './PodcastSection.vue'

export default {
  name: 'CategoryPage',
  components: {
    PodcastSection
  },
  props: {
    podcasts: Array,
    categories: Array
  },
  computed: {
    categorySlug() {
      return this.$route.params.slug
    },
    categoryTitle() {
      const category = this.categories.find(c => c.slug === this.categorySlug)
      return category ? category.name : 'Catégorie'
    },
    categoryPodcasts() {
      const result = this.podcasts.filter(p => {
        const cat = p["Catégorie"] || p.category
        const slug = this.slugify(cat?.toString().trim())
        return slug === this.categorySlug
      })
      return result
    },
    topRated() {
      return this.categoryPodcasts
        .map(p => ({
          ...p,
          rating: this.estimateRatingFromDownloads(p["Téléchargements Monde"])
        }))
        .filter(p => p.rating !== null)
        .sort((a, b) => b.rating - a.rating)
        .slice(0, 8)
    },
    popular() {
      return this.topRated.filter(p => p.rating >= 80).slice(0, 10)
    },
    recommended() {
      return [...this.categoryPodcasts]
        .sort(() => Math.random() - 0.5)
        .slice(0, 10)
    }
  },
  methods: {
    slugify(text) {
      return text
        ?.toString()
        .trim()
        .toLowerCase()
        .normalize("NFD").replace(/[\u0300-\u036f]/g, '')
        .replace(/\s+/g, '-')
        .replace(/[^\w-]+/g, '')
    },
    estimateRatingFromDownloads(downloads) {
      if (!downloads || isNaN(downloads)) return null
      const val = Number(downloads)
      if (val > 500000) return 95
      if (val > 100000) return 85
      if (val > 50000) return 75
      if (val > 10000) return 65
      return 50
    }
  },
  mounted() {
    console.log("📍 Slug dans l'URL :", this.categorySlug)

    const categoriesBrutes = this.podcasts
      .map(p => p["Catégorie"])
      .filter(Boolean)
      .map(cat => `"${cat}"`)

    console.log("📚 Catégories trouvées dans les données :", [...new Set(categoriesBrutes)])
  }
}
</script>


<style scoped>
.category-page {
  padding: 2rem 0;
  background-color: #000;
  color: #fff;
}

.category-header {
  text-align: center;
  margin-bottom: 3rem;
  padding: 0 2rem;
}

.category-header h1 {
  font-size: 3rem;
  color: #e50914;
  margin-bottom: 1rem;
  font-weight: bold;
}

.category-header p {
  font-size: 1.2rem;
  color: rgba(255, 255, 255, 0.7);
}
</style>
