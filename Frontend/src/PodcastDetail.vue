<template>
  <div v-if="podcast" class="podcast-detail">
    <div class="container">

      <!-- Colonne gauche : Infos -->
      <div class="left-panel">
        <h1 class="title">{{ title }}</h1>
        <img :src="imageUrl" alt="Illustration du podcast" class="podcast-image" />

        <div class="details">
          <p><strong>Catégorie :</strong> {{ podcast.Catégorie }}</p>
          <p><strong>Marque :</strong> {{ podcast.Marque }}</p>
          <p><strong>Nombre d'épisodes :</strong> {{ podcast["Nombre d'épisodes"] }}</p>
          <p><strong>Téléchargements :</strong> {{ podcast["Téléchargements Monde"] }}</p>
        </div>

        <div v-if="rating !== null" class="rating-estimée">
          <strong>Note estimée :</strong>
          <span :class="getRatingClass(rating)">{{ rating }}/100</span>
        </div>

        <p class="description">{{ description }}</p>

        <div class="platforms">
          <strong>Écouter sur :</strong>
          <ul>
            <li v-for="platform in platforms" :key="platform">
              <a :href="getPlatformUrl(platform)" target="_blank">{{ platform }}</a>
            </li>
          </ul>
        </div>
      </div>

      <!-- Colonne droite : Commentaires -->
      <div class="right-panel">
        <h2>Avis & Commentaires</h2>

        <div v-if="averageUserRating !== null" class="note-container">
          <div class="note-label">⭐ Note moyenne des utilisateurs</div>
          <div class="note-bar-background">
            <div class="note-bar-filled" :style="{ width: averageUserRating + '%' }"></div>
            <div class="note-value">{{ averageUserRating }}/100</div>
          </div>
        </div>

        <div v-if="comments.length" class="avis-bar-container">
          <div class="avis-bar-label">Répartition des avis utilisateurs</div>
          <div class="avis-bar">
            <div class="avis-segment avis-bon" :style="{ width: percentageBon + '%' }">
              {{ countBon }}
            </div>
            <div class="avis-segment avis-moyen" :style="{ width: percentageMoyen + '%' }">
              {{ countMoyen }}
            </div>
            <div class="avis-segment avis-mauvais" :style="{ width: percentageMauvais + '%' }">
              {{ countMauvais }}
            </div>
          </div>
        </div>

        <div v-if="successMessage" class="success-message">{{ successMessage }}</div>

        <div class="form">
          <textarea v-model="userComment" placeholder="Votre commentaire"></textarea>
          <input v-model="userRating" type="number" min="0" max="100" placeholder="Votre note sur 100" />
          <button @click="submitReview">Envoyer</button>
        </div>

        <!-- ✅ Commentaire de l'utilisateur connecté -->
        <div v-if="currentUserComment" class="comment user-comment">
          <p><strong>Votre commentaire :</strong> "{{ truncateComment(currentUserComment.comment) }}"</p>
          <span class="note">Note : {{ currentUserComment.rating }}/100 – {{ currentUserComment.timestamp }}</span>
          <button @click="deleteUserComment">🗑️ Supprimer mon commentaire</button>
        </div>

        <!-- ✅ Les autres commentaires -->
        <div class="comments-section">
  <div
    class="comment"
    v-for="c in otherComments"
    :key="c.id"
    :class="getCommentStyle(c.rating)"
  >
    <p class="comment-text">"{{ truncateComment(c.comment) }}"</p>
    <div class="comment-meta">
      <span class="comment-user">Par {{ c.username || 'Anonyme' }}</span>
      <span class="note">– Note : {{ c.rating }}/100 – {{ c.timestamp }}</span>
    </div>
  </div>
</div>
      </div>
    </div>
  </div>

  <div v-else class="loading">
    <p>Chargement du podcast...</p>
  </div>
</template>

<script>
import { auth } from './auth'
import { onAuthStateChanged, getAuth } from 'firebase/auth'

export default {
  name: 'PodcastDetail',
  props: {
    podcasts: Array
  },
  data() {
    return {
      userComment: '',
      userRating: '',
      comments: [],
      successMessage: '',
      submitting: false,
      currentUser: null
    }
  },
  computed: {
    podcastId() {
      return this.$route.params.name
    },
    podcast() {
      return this.podcasts.find(p =>
        (p.id && p.id.toString() === this.podcastId) ||
        (p.Podcasts && p.Podcasts.toString() === this.podcastId)
      )
    },
    rating() {
      const d = this.podcast?.["Téléchargements Monde"]
      if (!d || isNaN(d)) return null
      const downloads = Number(d)
      if (downloads > 500000) return 95
      if (downloads > 100000) return 85
      if (downloads > 50000) return 75
      if (downloads > 10000) return 60
      return 50
    },
    imageUrl() {
      return this.podcast?.image || 'https://via.placeholder.com/600x400?text=Podcast'
    },
    title() {
      return this.podcast?.title || this.podcast?.Podcasts || 'Titre inconnu'
    },
    description() {
      return this.podcast?.description || 'Aucune description disponible.'
    },
    platforms() {
      return this.podcast?.platforms || ['Spotify', 'Apple Podcasts']
    },
    averageUserRating() {
      if (!this.comments.length) return null
      const sum = this.comments.reduce((total, c) => total + Number(c.rating), 0)
      return Math.round(sum / this.comments.length)
    },
    countBon() {
      return this.comments.filter(c => c.rating > 75).length
    },
    countMoyen() {
      return this.comments.filter(c => c.rating <= 75 && c.rating >= 40).length
    },
    countMauvais() {
      return this.comments.filter(c => c.rating < 40).length
    },
    percentageBon() {
      return Math.round((this.countBon / this.comments.length) * 100)
    },
    percentageMoyen() {
      return Math.round((this.countMoyen / this.comments.length) * 100)
    },
    percentageMauvais() {
      return Math.round((this.countMauvais / this.comments.length) * 100)
    },
    currentUserComment() {
      if (!this.currentUser) return null
      return this.comments.find(c => c.userId === this.currentUser.uid)
    },
    otherComments() {
      if (!this.currentUser) return this.comments
      return this.comments.filter(c => c.userId !== this.currentUser.uid)
    }
  },
  methods: {
    getPlatformUrl(platform) {
      const urls = {
        'Spotify': 'https://spotify.com',
        'Apple Podcasts': 'https://podcasts.apple.com',
        'Deezer': 'https://deezer.com'
      }
      return urls[platform] || '#'
    },
    getRatingClass(rating) {
      if (rating >= 90) return 'excellent'
      if (rating >= 70) return 'good'
      if (rating >= 50) return 'average'
      return 'poor'
    },
    getCommentStyle(rating) {
      if (rating >= 90) return 'highlight-excellent'
      if (rating <= 30) return 'highlight-poor'
      return ''
    },
    truncateComment(comment) {
      return comment.length > 150 ? comment.slice(0, 150) + '…' : comment
    },
    async fetchComments() {
  try {
    const res = await fetch(`http://localhost:5001/api/comments/${encodeURIComponent(this.podcastId)}`);
    const data = await res.json();

    if (!Array.isArray(data)) {
      console.error("Réponse inattendue du backend :", data);
      return;
    }

    this.comments = data.map(c => {
      let formattedDate = 'Date inconnue';
      if (c.timestamp && typeof c.timestamp === 'object') {
        try {
          const ts = new Date(c.timestamp._seconds * 1000);
          formattedDate = ts.toLocaleString();
        } catch (e) {}
      }
      return { ...c, timestamp: formattedDate };
    });

  } catch (e) {
    console.error("Erreur dans fetchComments :", e);
  }
},
    async submitReview() {
      const ratingNum = Number(this.userRating)
      if (!this.userComment.trim() || isNaN(ratingNum)) return
      if (ratingNum < 0 || ratingNum > 100) {
        alert('Veuillez entrer une note entre 0 et 100.')
        return
      }

      const currentUser = getAuth().currentUser
      if (!currentUser) {
        alert("Vous devez être connecté pour laisser un commentaire.")
        this.$router.push('/login')
        return
      }

      const userId = currentUser.uid
      const username = currentUser.displayName || currentUser.email.split('@')[0] || 'Utilisateur'

      const body = {
        podcastId: this.podcastId,
        comment: this.userComment,
        rating: ratingNum,
        userId,
        username
      }

      try {
        const res = await fetch('http://localhost:5001/api/comments', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body)
        })

        if (res.ok) {
          this.userComment = ''
          this.userRating = ''
          this.successMessage = '✅ Commentaire ajouté !'
          this.fetchComments()
          setTimeout(() => { this.successMessage = '' }, 3000)
        } else if (res.status === 409) {
          alert("Vous avez déjà commenté ce podcast. Supprimez-le pour en ajouter un nouveau.")
        } else {
          const error = await res.json()
          console.error('Erreur API :', error)
          alert("Erreur lors de l'envoi du commentaire.")
        }

      } catch (e) {
        console.error("Erreur fetch :", e)
      }
    },
   async deleteUserComment() {
  try {
    const res = await fetch('http://localhost:5001/api/comments', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        podcastId: this.podcastId,
        userId: this.currentUser.uid
      })
    });

    if (res.ok) {
      this.successMessage = '✅ Commentaire supprimé.';
      this.userComment = '';
      this.userRating = '';
      this.fetchComments();
      setTimeout(() => this.successMessage = '', 3000);
    } else {
      const error = await res.json();
      alert('Erreur : ' + (error.error || 'Suppression impossible'));
    }
  } catch (e) {
    console.error('Erreur fetch delete :', e);
  }
}

  },
  mounted() {
    this.fetchComments()
    onAuthStateChanged(auth, (user) => {
      this.currentUser = user
    })
  }
}
</script>


<style scoped>
/* Styles personnalisés pour les commentaires */

.highlight-excellent {
  border: 2px solid #00cc66;
  background-color: #f0fff5;
}

.highlight-poor {
  border: 2px solid #cc0033;
  background-color: #fff5f5;
}

.note-container {
  margin-bottom: 1rem;
}

.note-bar-background {
  position: relative;
  background: #eee;
  height: 20px;
  border-radius: 10px;
}

.note-bar-filled {
  height: 100%;
  background: linear-gradient(to right, #d60000, #cc0000);
  border-radius: 10px 0 0 10px;
}

.note-value {
  position: absolute;
  top: 0;
  right: 10px;
  font-size: 12px;
  line-height: 20px;
  font-weight: bold;
}

.podcast-detail {
  padding: 2rem;
  background-color: #121212;
  color: #f2f2f2;
}
.container {
  display: flex;
  flex-wrap: wrap;
  gap: 2rem;
}
.left-panel {
  flex: 2;
  min-width: 300px;
}
.right-panel {
  flex: 1;
  background-color: #1e1e1e;
  border-radius: 12px;
  padding: 1rem;
  max-height: 90vh;
  overflow-y: auto;
}
.title {
  color: #e50914;
  font-size: 2.5rem;
}
.podcast-image {
  width: 100%;
  border-radius: 12px;
  margin-bottom: 1rem;
}
.description {
  margin: 1rem 0;
}
.platforms ul {
  list-style-type: disc;
  padding-left: 1rem;
}
.platforms a {
  color: #e50914;
}
.form textarea,
.form input {
  width: 100%;
  margin-bottom: 0.5rem;
  padding: 0.5rem;
  background: #2a2a2a;
  border: 1px solid #444;
  color: #fff;
  border-radius: 6px;
}
.form button {
  width: 100%;
  background: #e50914;
  color: white;
  border: none;
  padding: 0.6rem;
  font-weight: bold;
  cursor: pointer;
  border-radius: 6px;
}
.success-message {
  background: #4caf50;
  color: white;
  padding: 0.5rem;
  text-align: center;
  border-radius: 6px;
  margin-bottom: 1rem;
}
.comments-section {
  max-height: 300px;
  overflow-y: auto;
  padding: 0.5rem 0;
}
.comment {
  background-color: #2a2a2a;
  padding: 0.75rem;
  margin-bottom: 0.5rem;
  border-radius: 6px;
}
.note {
  font-size: 0.8rem;
  color: #aaa;
}
.note-moyenne {
  background: #e50914;
  color: white;
  padding: 0.5rem;
  text-align: center;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-weight: bold;
}
.excellent { color: #4caf50; }
.good { color: #8bc34a; }
.average { color: #ff9800; }
.poor { color: #f44336; }

.note-container {
  margin-top: 10px;
}

.note-label {
  font-weight: bold;
  margin-bottom: 4px;
  font-size: 14px;
  color: #e50914; /* Rouge Netflix */
}

.note-bar-background {
  background-color: #ccc;
  border-radius: 6px;
  height: 16px;
  width: 100%;
  position: relative;
  overflow: hidden;
}

.note-bar-filled {
  background-color: #e50914; /* Rouge Netflix */
  height: 100%;
  transition: width 0.5s ease;
}

.note-value {
  position: absolute;
  right: 8px;
  top: 0;
  font-size: 12px;
  line-height: 16px;
  color: white;
  font-weight: bold;
}

.avis-bar-container {
  margin-top: 1rem;
}
.avis-bar-label {
  font-weight: bold;
  margin-bottom: 0.5rem;
  font-size: 14px;
  color: #e50914;
}
.avis-bar {
  display: flex;
  height: 20px;
  border-radius: 6px;
  overflow: hidden;
  background-color: #444;
  font-size: 12px;
  font-weight: bold;
  color: #fff;
  text-align: center;
}
.avis-segment {
  display: flex;
  align-items: center;
  justify-content: center;
}
.avis-bon {
  background-color: #4caf50;
}
.avis-moyen {
  background-color: #ff9800;
}
.avis-mauvais {
  background-color: #f44336;
}

.user-comment {
  background-color: #444;
  border: 1px solid #ff9999;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
}
.user-comment button {
  margin-top: 0.5rem;
  background: #ff5555;
  color: white;
  border: none;
  padding: 0.5rem;
  border-radius: 5px;
  cursor: pointer;
}

.comment-user {
  font-weight: bold;
  color: #444;
}
.comment-meta {
  font-size: 0.9rem;
  color: #666;
  margin-top: 4px;
}
.comment-text {
  font-style: italic;
}

</style>


