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
import data from '../src/data.json'; 

    /**
     * Donn es du composant. Ici, c'est un tableau de podcasts.
     * @type {Object}
     */
export default {
  name: 'PodcastsPage',
  data() {
    return {
      podcasts: data // Affectez les données du fichier data.json à la variable podcasts
    };
  }
}
</script>