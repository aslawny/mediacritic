<template>
  <div id="app">
    <nav class="navbar">
      <div class="nav-container">
        <!-- Logo + zone utilisateur -->
        <div class="logo-user">
          <router-link to="/" class="logo">🎙️ MediaCritic</router-link>
          <div class="auth-zone">
            <div v-if="user">
              <div class="username" @click="toggleUserMenu">
                👤 {{ username }}
                <div class="user-menu" v-if="showUserMenu">
                  <router-link to="/profile" @click="toggleUserMenu">Profil</router-link>
                  <button @click="logout">Se déconnecter</button>
                </div>
              </div>
            </div>
            <div v-else>
              <router-link to="/login" class="login-link">Se connecter</router-link>
            </div>
          </div>
        </div>

        <!-- Barre de recherche -->
        <div class="search-container">
          <input 
            v-model="searchQuery"
            @keyup.enter="performSearch"
            type="text" 
            placeholder="Rechercher un podcast..."
            class="search-input"
          />
          <button @click="performSearch" class="search-btn">🔍</button>
        </div>

        <!-- Menu hamburger -->
        <button class="menu-btn" @click="toggleMenu">☰</button>

        <!-- Menu déroulant -->
        <div class="dropdown-menu" v-if="showMenu">
          <router-link 
            v-for="category in categories" 
            :key="category.slug"
            :to="`/category/${category.slug}`"
            class="dropdown-link"
            @click="toggleMenu"
          >
            {{ category.name }}
          </router-link>
          <router-link to="/podcasts" class="dropdown-link" @click="toggleMenu">
            Podcasts ACPM
          </router-link>
        </div>
      </div>
    </nav>

    <router-view :podcasts="podcasts" :categories="categories" />
    <Footer />
  </div>
</template>

<script>
import Footer from './Footer.vue'
import { auth } from './auth'
import data from './data.json'; // Importation du fichier data.json
import { onAuthStateChanged, signOut } from 'firebase/auth'

export default {
  name: 'App',
  components: { Footer },
  data() {
    return {
      searchQuery: '',
      podcasts: data,
      showMenu: false,
      user: null,
      username: '',
      showUserMenu: false
    }
  },
  computed: {
    categories() {
      const slugs = new Set()
      return this.podcasts
        .map(p => p["Categorie"])
        .filter(c => !!c)
        .filter((cat) => {
          const slug = this.slugify(cat)
          if (slugs.has(slug)) return false
          slugs.add(slug)
          return true
        })
        .map(c => ({
          name: c,
          slug: this.slugify(c)
        }))
    }
  },
  mounted() {
     this.podcasts = data; // Affectation des données du fichier data.json à la variable podcasts
    
    onAuthStateChanged(auth, (user) => {
      this.user = user
      if (user) {
        this.username = user.displayName || user.email.split('@')[0]
      } else {
        this.username = ''
      }
    })
  },
  methods: {
    performSearch() {
      if (this.searchQuery.trim()) {
        this.$router.push(`/search/${encodeURIComponent(this.searchQuery)}`)
      }
    },
    slugify(text) {
      return text
        .toLowerCase()
        .normalize("NFD").replace(/[\u0300-\u036f]/g, '')
        .replace(/\s+/g, '-')
        .replace(/[^\w-]+/g, '')
    },
    toggleMenu() {
      this.showMenu = !this.showMenu
    },
    toggleUserMenu() {
      this.showUserMenu = !this.showUserMenu
    },
    logout() {
      signOut(auth).then(() => {
        this.user = null
        this.username = ''
        this.showUserMenu = false
        this.$router.push('/')
      })
    }
  }
}
</script>

<style scoped>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: 'Arial', sans-serif;
  background-color: #000;
  color: #fff;
  min-height: 100vh;
}

.navbar {
  background: #111;
  padding: 1rem 0;
  border-bottom: 2px solid rgba(229, 9, 20, 0.5);
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-container {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 2rem;
  position: relative;
  flex-wrap: wrap;
}

.logo-user {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.logo {
  font-size: 1.8rem;
  font-weight: bold;
  color: #e50914;
  text-decoration: none;
  transition: transform 0.3s ease;
}

.logo:hover {
  transform: scale(1.05);
}

.auth-zone {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}

.username {
  color: #fff;
  cursor: pointer;
  position: relative;
  font-weight: bold;
}

.user-menu {
  position: absolute;
  top: 100%;
  left: 0;
  background: #111;
  border: 1px solid #333;
  border-radius: 6px;
  padding: 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  z-index: 200;
}

.user-menu a,
.user-menu button {
  color: white;
  background: none;
  border: none;
  text-align: left;
  cursor: pointer;
  padding: 0.4rem;
  font-size: 0.9rem;
}

.user-menu a:hover,
.user-menu button:hover {
  background: #e50914;
}

.login-link {
  color: #e50914;
  font-weight: bold;
  text-decoration: none;
}

.search-container {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 25px;
  padding: 0.4rem;
  margin: 0 2rem;
  box-shadow: 0 2px 6px rgba(0,0,0,0.4);
}

.search-input {
  background: transparent;
  border: none;
  outline: none;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 1rem;
  color: #fff;
}

.search-input::placeholder {
  color: rgba(255, 255, 255, 0.5);
}

.search-btn {
  background: #e50914;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 20px;
  cursor: pointer;
  transition: background-color 0.3s ease;
}

.search-btn:hover {
  background: #b20710;
}

.menu-btn {
  background: transparent;
  color: white;
  border: none;
  font-size: 1.8rem;
  cursor: pointer;
}

.dropdown-menu {
  margin-right: 20px;
  position: absolute;
  top: 100%;
  right: 2rem;
  background: #111;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.4);
  padding: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
  z-index: 200;
}

.dropdown-link {
  color: rgba(255, 255, 255, 0.85);
  text-decoration: none;
  font-weight: 500;
  transition: all 0.3s ease;
  padding: 0.4rem 0.6rem;
  border-radius: 5px;
}

.dropdown-link:hover {
  background: rgba(229, 9, 20, 0.1);
  color: #fff;
}

@media (max-width: 768px) {
  .nav-container {
    flex-direction: column;
    gap: 1rem;
  }

  .search-container {
    margin: 1rem 0;
  }
}
</style>



