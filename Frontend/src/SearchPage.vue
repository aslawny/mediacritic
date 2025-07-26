<template>
  <div class="search-page p-6">
    <h1 class="text-2xl font-bold mb-4">Résultats pour "{{ query }}"</h1>

    <PodcastSection
      v-if="filteredResults.length > 0"
      title="Podcasts trouvés"
      :podcasts="filteredResults"
      :large="true"
    />

    <p v-else class="text-gray-500 text-lg mt-10">
      Aucun podcast trouvé pour "{{ query }}".
    </p>
  </div>
</template>

<script>
import PodcastSection from './PodcastSection.vue'

export default {
  name: 'SearchPage',
  components: { PodcastSection },
  props: {
    podcasts: Array
  },
  computed: {
    query() {
      return this.$route.params.query.toLowerCase()
    },
    filteredResults() {
      return this.podcasts.filter(p => {
        const title = (p.Podcasts || '').toLowerCase()
        const brand = (p.Marque || '').toLowerCase()
        const category = (p["Categorie"] || '').toLowerCase()
        return (
          title.includes(this.query) ||
          brand.includes(this.query) ||
          category.includes(this.query)
        )
      })
    }
  }
}
</script>

<style scoped>
.search-page {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
  background-color: #121212;
  min-height: 100vh;
}

.search-header {
  text-align: center;
  margin-bottom: 3rem;
}

.search-header h1 {
  font-size: 2.5rem;
  color: #e50914;
  margin-bottom: 1rem;
}

.search-header p {
  font-size: 1.1rem;
  color: rgba(255, 255, 255, 0.7);
}

.search-results {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 2rem;
  margin-top: 2rem;
}

.no-results {
  text-align: center;
  padding: 4rem 2rem;
}

.no-results h2 {
  font-size: 2rem;
  color: #e50914;
  margin-bottom: 1rem;
}

.no-results p {
  font-size: 1.1rem;
  color: rgba(255, 255, 255, 0.6);
}
</style>
