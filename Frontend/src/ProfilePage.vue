<!-- src/pages/ProfilePage.vue -->
<template>
  <div class="profile-container">
    <h1>Mon Profil</h1>

    <div class="profile-info">
      <p><strong>Nom d'utilisateur :</strong> {{ username }}</p>
      <p><strong>Email :</strong> {{ email }}</p>
    </div>

    <div class="user-comments" v-if="comments.length">
      <h2>Mes Commentaires</h2>
      <div v-for="comment in comments" :key="comment.id" class="comment">
        <p><strong>{{ comment.podcastId }}</strong></p>
        <p>"{{ comment.comment }}"</p>
        <p>Note : {{ comment.rating }}/100 – {{ formatDate(comment.timestamp) }}</p>
      </div>
    </div>

    <div v-else>
      <p>Vous n'avez encore laissé aucun commentaire.</p>
    </div>
  </div>
</template>

<script>
import { getAuth, onAuthStateChanged } from 'firebase/auth'

export default {
  name: 'ProfilePage',
  data() {
    return {
      username: '',
      email: '',
      userId: '',
      comments: []
    }
  },
  methods: {
    async fetchUserComments() {
      try {
        const res = await fetch(`http://localhost:5001/api/comments/user/${this.userId}`)
        const data = await res.json()
        this.comments = data
      } catch (err) {
        console.error('Erreur fetch commentaires utilisateur :', err)
      }
    },
    formatDate(timestamp) {
      try {
        const ts = new Date(timestamp._seconds * 1000)
        return ts.toLocaleString()
      } catch {
        return 'Date inconnue'
      }
    }
  },
  mounted() {
    const auth = getAuth()
    onAuthStateChanged(auth, (user) => {
      if (user) {
        this.username = user.displayName || user.email.split('@')[0]
        this.email = user.email
        this.userId = user.uid
        this.fetchUserComments()
      } else {
        this.$router.push('/login')
      }
    })
  }
}
</script>

<style scoped>
.profile-container {
  padding: 2rem;
}
.profile-info {
  margin-bottom: 2rem;
}
.comment {
  border-bottom: 1px solid #ccc;
  padding: 1rem 0;
}
</style>
