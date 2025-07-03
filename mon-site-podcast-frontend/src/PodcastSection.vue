<template>
  <div class="podcast-section" v-if="podcasts && podcasts.length">
    <div class="section-header">
      <h2>{{ title }}</h2>
    </div>

    <div class="podcasts-container" :class="{ 'large-cards': large }">
      <div class="podcasts-scroll">
        <PodcastCard 
          v-for="(podcast, index) in podcasts"
          :key="podcast.id || podcast.Podcasts || index"
          :podcast="podcast"
          :large="large"
          :clickable="true"
        />
      </div>
    </div>
  </div>
</template>

<script>
import PodcastCard from './PodcastCard.vue'

export default {
  name: 'PodcastSection',
  components: {
    PodcastCard
  },
  props: {
    title: String,
    podcasts: {
      type: Array,
      default: () => []
    },
    large: {
      type: Boolean,
      default: false
    }
  }
}
</script>

<style scoped>
.podcast-section {
  margin-bottom: 3rem;
  padding: 0 2rem;
  background-color: #121212;
}

.section-header {
  margin-bottom: 1.5rem;
}

.section-header h2 {
  font-size: 2rem;
  color: #e50914;
  font-weight: bold;
}

.podcasts-container {
  overflow-x: auto;
  padding-bottom: 1rem;
}

.podcasts-scroll {
  display: flex;
  gap: 1.5rem;
  padding: 0.5rem 0;
}

.large-cards .podcasts-scroll {
  gap: 2rem;
}

/* Scrollbar style adaptée au thème sombre */
.podcasts-container::-webkit-scrollbar {
  height: 8px;
}

.podcasts-container::-webkit-scrollbar-track {
  background: #1e1e1e;
  border-radius: 10px;
}

.podcasts-container::-webkit-scrollbar-thumb {
  background: #e50914;
  border-radius: 10px;
}

.podcasts-container::-webkit-scrollbar-thumb:hover {
  background: #b0060f;
}
</style>
