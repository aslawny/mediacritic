<template>
  <div class="podcasts-page">
    <h2>Classement des podcasts (mai 2025)</h2>
    <ul>
      <li v-for="podcast in podcasts" :key="podcast.id">
        {{ podcast.Podcasts }} - {{ podcast.Catégorie }} - {{ podcast.Marque }}
      </li>
    </ul>
  </div>
</template>

<script>
export default {
  name: 'PodcastsPage',
  data() {
    return {
      podcasts: []
    };
  },
  mounted() {
    fetch("http://localhost:5000/podcasts")
      .then(res => res.json())
      .then(data => {
        this.podcasts = data;
      })
      .catch(err => {
        console.error("Erreur lors du fetch :", err);
      });
  }
}
</script>

