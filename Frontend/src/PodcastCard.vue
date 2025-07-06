<template>
  <div class="relative group podcast-card" :class="{ 'large': large, 'clickable': clickable }" @click="handleClick">
    
    <!-- Image du podcast -->
    <img :src="podcast.image || 'https://via.placeholder.com/400x200?text=Podcast'" class="w-full h-full object-cover rounded-xl" />

    <!-- Contenu de la carte (titre, catégorie, note) -->
    <div class="card-content absolute bottom-0 left-0 w-full p-3 bg-black/60 text-white">
      <h3 class="podcast-title text-lg font-bold truncate">{{ displayTitle }}</h3>
      <p class="podcast-category text-sm italic">{{ displayCategory }}</p>
      <div v-if="hasRating" class="rating text-sm mt-1" :class="getRatingClass(rating)">
        {{ rating }}/100
      </div>
    </div>

    <!-- ❤️ Bouton favori, fixé en bas à droite -->
    <div class="favorite-button" @click.stop="toggleFavorite">
      <span v-if="isFavorite">❤️</span>
      <span v-else>🤍</span>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { doc, getDoc, updateDoc, arrayUnion, arrayRemove, setDoc } from 'firebase/firestore'
import { getAuth, onAuthStateChanged } from 'firebase/auth'
import data from './data.json'; // Importation du fichier data.json
import { db } from './firebase'

const props = defineProps({
  podcast: Object,
  large: {
    type: Boolean,
    default: false
  },
  clickable: {
    type: Boolean,
    default: false
  }
})

const isFavorite = ref(false)
const user = ref(null)

onMounted(() => {
  const auth = getAuth()
  onAuthStateChanged(auth, async (u) => {
    user.value = u
    if (user.value) {
      const userRef = doc(db, 'users', user.value.uid)
      const snap = await getDoc(userRef)
      if (snap.exists()) {
        isFavorite.value = snap.data().favorites?.includes(podcastId.value)
      }
    }
  })
})

const podcastId = computed(() => props.podcast.id ?? props.podcast.Podcasts)

const toggleFavorite = async () => {
  if (!user.value) {
    alert('Connecte-toi pour ajouter un favori !')
    return
  }

  const userRef = doc(db, 'users', user.value.uid)
  const snap = await getDoc(userRef)
  if (!snap.exists()) {
    await setDoc(userRef, { favorites: [] })
  }

  await updateDoc(userRef, {
    favorites: isFavorite.value
      ? arrayRemove(podcastId.value)
      : arrayUnion(podcastId.value)
  })

  isFavorite.value = !isFavorite.value
}

const displayTitle = computed(() => props.podcast.title || props.podcast.Podcasts || 'Sans titre')
const displayCategory = computed(() => {
  const slug = props.podcast.category || props.podcast.Catégorie
  const categories = {
    'tech': 'Tech', 'culture': 'Culture', 'sport': 'Sport', 'musique': 'Musique',
    'histoire': 'Histoire', 'humour': 'Humour', 'true-crime': 'True Crime',
    'business': 'Business', 'societe': 'Société', 'science': 'Science', 'actualites': 'Actualités'
  }
  return categories[slug?.toLowerCase()] || slug || 'Inconnu'
})

const rating = computed(() => {
  if (props.podcast.rating != null) return props.podcast.rating
  const downloads = props.podcast["Téléchargements Monde"]
  const val = Number(downloads)
  if (!downloads || isNaN(val)) return null
  if (val > 500000) return 95
  if (val > 100000) return 85
  if (val > 50000) return 75
  if (val > 10000) return 65
  return 50
})

const hasRating = computed(() => rating.value !== undefined && rating.value !== null)

const getRatingClass = (r) => {
  if (r >= 90) return 'text-green-400'
  if (r >= 70) return 'text-yellow-300'
  if (r >= 50) return 'text-orange-300'
  return 'text-red-400'
}

const handleClick = () => {
  if (props.clickable) {
    const id = podcastId.value
    if (id) {
      const encoded = encodeURIComponent(id)
      window.location.href = `/podcast/${encoded}`
    }
  }
}
</script>


<style scoped>
.podcast-card {
  flex: 0 0 auto;
  width: 250px;
  background: #121212;
  border-radius: 15px;
  overflow: hidden;
  box-shadow: 0 5px 15px rgba(0,0,0,0.5);
  transition: all 0.3s ease;
  position: relative;
  color: white;
}

.podcast-card.large {
  width: 350px;
}

.podcast-card.clickable {
  cursor: pointer;
}

.podcast-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 25px rgba(0,0,0,0.7);
}

.card-image {
  position: relative;
  width: 100%;
  height: 150px;
  overflow: hidden;
}

.large .card-image {
  height: 200px;
}

.card-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.podcast-card:hover .card-image img {
  transform: scale(1.05);
}

.rating {
  position: absolute;
  top: 10px;
  right: 10px;
  padding: 0.4rem 0.7rem;
  border-radius: 6px;
  font-weight: bold;
  font-size: 0.9rem;
  color: white;
  background-color: #e50914;
  box-shadow: 0 0 5px rgba(229, 9, 20, 0.6);
}

.card-content {
  padding: 1rem;
}

.large .card-content {
  padding: 1.5rem;
}

.podcast-title {
  font-size: 1.1rem;
  font-weight: bold;
  color: white;
  margin-bottom: 0.5rem;
  line-height: 1.3;

  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  overflow: hidden;
  text-overflow: ellipsis;
}

.large .podcast-title {
  font-size: 1.3rem;
}

.podcast-category {
  font-size: 0.85rem;
  color: #e50914;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.excellent { background-color: #1e7e34; }
.good { background-color: #28a745; }
.average { background-color: #ffc107; color: #000; }
.poor { background-color: #dc3545; }

@media (max-width: 768px) {
  .podcast-card {
    width: 200px;
  }

  .podcast-card.large {
    width: 280px;
  }

  .card-image {
    height: 120px;
  }

  .large .card-image {
    height: 160px;
  }
}

.favorite-button {
  position: absolute;
  bottom: 10px;
  right: 10px;
  background-color: rgba(255, 255, 255, 0.15);
  color: white;
  border-radius: 50%;
  width: 36px;
  height: 36px;
  display: flex;
  justify-content: center;
  align-items: center;
  cursor: pointer;
  font-size: 18px;
  transition: background-color 0.3s ease, transform 0.2s ease;
  z-index: 10;
}

.favorite-button:hover {
  background-color: #e50914;
  transform: scale(1.1);
}

</style>
