<template>
  <div class="auth-container">
    <h2>{{ isLogin ? 'Se connecter' : 'Créer un compte' }}</h2>

    <div v-if="error" class="error-message">{{ error }}</div>
    <div v-if="success" class="success-message">{{ success }}</div>

    <form @submit.prevent="submitForm">
      <input
        v-if="!isLogin"
        v-model="username"
        type="text"
        placeholder="Nom d'utilisateur"
        required
      />
      <input
        v-model="email"
        type="email"
        placeholder="Adresse email"
        required
      />
      <input
        v-model="password"
        type="password"
        placeholder="Mot de passe"
        required
      />

      <button type="submit">
        {{ isLogin ? 'Connexion' : 'Créer un compte' }}
      </button>
    </form>

    <p class="switch-mode">
      {{ isLogin ? "Pas encore de compte ?" : "Déjà inscrit ?" }}
      <a href="#" @click.prevent="toggleMode">
        {{ isLogin ? "Créer un compte" : "Se connecter" }}
      </a>
    </p>
  </div>
</template>

<script>
import { signInWithEmailAndPassword, createUserWithEmailAndPassword, updateProfile } from "firebase/auth";
import { auth } from './auth'; // ✅

export default {
  name: "AuthForm",
  data() {
    return {
      email: '',
      password: '',
      username: '',
      isLogin: true,
      error: '',
      success: ''
    }
  },
  methods: {
    toggleMode() {
      this.isLogin = !this.isLogin;
      this.error = '';
      this.success = '';
    },
    async submitForm() {
      this.error = '';
      this.success = '';

      if (!this.email || !this.password || (!this.isLogin && !this.username)) {
        this.error = 'Veuillez remplir tous les champs.';
        return;
      }

      try {
        if (this.isLogin) {
          await signInWithEmailAndPassword(auth, this.email, this.password);
          this.success = '✅ Connexion réussie !';
          this.$router.push('/');
        } else {
          const userCredential = await createUserWithEmailAndPassword(auth, this.email, this.password);
          await updateProfile(userCredential.user, { displayName: this.username });
          this.success = '✅ Compte créé avec succès ! Vous pouvez maintenant vous connecter.';
          this.isLogin = true;
          this.email = '';
          this.password = '';
          this.username = '';
        }
      } catch (err) {
        if (err.code === 'auth/invalid-email') {
          this.error = 'Adresse email invalide.';
        } else if (err.code === 'auth/email-already-in-use') {
          this.error = 'Cette adresse email est déjà utilisée.';
        } else if (err.code === 'auth/weak-password') {
          this.error = 'Mot de passe trop faible (minimum 6 caractères).';
        } else if (err.code === 'auth/user-not-found' || err.code === 'auth/wrong-password') {
          this.error = 'Email ou mot de passe incorrect.';
        } else {
          this.error = 'Erreur : ' + err.message;
        }
      }
    }
  }
}
</script>

<style scoped>
.auth-container {
  max-width: 400px;
  margin: 3rem auto;
  background: #1e1e1e;
  padding: 2rem;
  border-radius: 10px;
  box-shadow: 0 0 12px rgba(255, 255, 255, 0.1);
  color: #fff;
}

.auth-container h2 {
  text-align: center;
  margin-bottom: 1.5rem;
  color: #e50914;
}

form {
  display: flex;
  flex-direction: column;
}

input {
  padding: 0.7rem;
  margin-bottom: 1rem;
  border: none;
  border-radius: 6px;
  background: #2a2a2a;
  color: #fff;
}

input::placeholder {
  color: #aaa;
}

button {
  background: #e50914;
  color: white;
  padding: 0.8rem;
  border: none;
  border-radius: 6px;
  font-weight: bold;
  cursor: pointer;
  transition: background 0.3s ease;
}

button:hover {
  background: #b20710;
}

.switch-mode {
  text-align: center;
  margin-top: 1rem;
  font-size: 0.9rem;
}

.switch-mode a {
  color: #e50914;
  font-weight: bold;
  cursor: pointer;
}

.error-message {
  background: #330000;
  color: #ff4d4d;
  padding: 0.6rem;
  margin-bottom: 1rem;
  border-radius: 6px;
  text-align: center;
}

.success-message {
  background: #0f3f1f;
  color: #4caf50;
  padding: 0.6rem;
  margin-bottom: 1rem;
  border-radius: 6px;
  text-align: center;
}
</style>

