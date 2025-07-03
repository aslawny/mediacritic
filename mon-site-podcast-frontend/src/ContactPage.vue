<template>
  <div class="contact-page">
    <div class="contact-container">
      <div class="contact-header">
        <h1>Contactez-nous</h1>
        <p class="contact-subtitle">Une question, une suggestion ? Nous sommes là pour vous écouter</p>
      </div>
      
      <div class="contact-content">
        <div class="contact-info">
          <h2>Nos coordonnées</h2>
          <div class="contact-item">
            <strong>Email :</strong>
            <a href="mailto:contact@podcaddict.fr">contact@podcaddict.fr</a>
          </div>
          <div class="contact-item">
            <strong>Réseaux sociaux :</strong>
            <div class="social-links">
              <a href="#" class="social-link">🐦 Twitter</a>
              <a href="#" class="social-link">📸 Instagram</a>
              <a href="#" class="social-link">🔗 LinkedIn</a>
            </div>
          </div>
        </div>
        
        <div class="contact-form-section">
          <h2>Envoyez-nous un message</h2>
          <form @submit.prevent="submitForm" class="contact-form">
            <div class="form-group">
              <label for="name">Nom *</label>
              <input 
                type="text" 
                id="name" 
                v-model="form.name" 
                required 
                class="form-input"
              >
            </div>
            
            <div class="form-group">
              <label for="email">Email *</label>
              <input 
                type="email" 
                id="email" 
                v-model="form.email" 
                required 
                class="form-input"
              >
            </div>
            
            <div class="form-group">
              <label for="subject">Sujet</label>
              <select id="subject" v-model="form.subject" class="form-input">
                <option value="">Choisir un sujet</option>
                <option value="suggestion">Suggestion de podcast</option>
                <option value="bug">Signaler un bug</option>
                <option value="partenariat">Partenariat</option>
                <option value="autre">Autre</option>
              </select>
            </div>
            
            <div class="form-group">
              <label for="message">Message *</label>
              <textarea 
                id="message" 
                v-model="form.message" 
                required 
                rows="5" 
                class="form-input"
                placeholder="Votre message..."
              ></textarea>
            </div>
            
            <button type="submit" class="submit-btn" :disabled="!canSubmit">
              Envoyer le message
            </button>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ContactPage',
  data() {
    return {
      form: {
        name: '',
        email: '',
        subject: '',
        message: ''
      }
    }
  },
  computed: {
    canSubmit() {
      return this.form.name.trim() && 
             this.form.email.trim() && 
             this.form.message.trim()
    }
  },
  methods: {
    submitForm() {
      if (!this.canSubmit) return
      
      // Simulation de l'envoi
      alert('Merci pour votre message ! Nous vous répondrons dans les plus brefs délais.')
      
      // Reset du formulaire
      this.form = {
        name: '',
        email: '',
        subject: '',
        message: ''
      }
    }
  }
}
</script>

<style scoped>
.contact-page {
  background: #000;
  min-height: 100vh;
  padding: 2rem 0;
}

.contact-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 0 2rem;
}

.contact-header {
  text-align: center;
  margin-bottom: 3rem;
}

.contact-header h1 {
  font-size: clamp(2.5rem, 5vw, 3.5rem);
  font-weight: 900;
  background: linear-gradient(135deg, #fff 0%, #e50914 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 1rem;
}

.contact-subtitle {
  font-size: 1.2rem;
  color: rgba(255, 255, 255, 0.8);
}

.contact-content {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 3rem;
  align-items: start;
}

.contact-info,
.contact-form-section {
  background: rgba(20, 20, 20, 0.5);
  border-radius: 15px;
  padding: 2rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.contact-info h2,
.contact-form-section h2 {
  color: #e50914;
  font-size: 1.5rem;
  margin-bottom: 1.5rem;
}

.contact-item {
  margin-bottom: 1.5rem;
}

.contact-item strong {
  color: #fff;
  display: block;
  margin-bottom: 0.5rem;
}

.contact-item a {
  color: rgba(255, 255, 255, 0.8);
  text-decoration: none;
}

.contact-item a:hover {
  color: #e50914;
}

.social-links {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.social-link {
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  padding: 0.5rem 1rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 20px;
  transition: all 0.3s ease;
  font-size: 0.9rem;
}

.social-link:hover {
  color: #fff;
  border-color: #e50914;
  background: rgba(229, 9, 20, 0.1);
}

.contact-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-group label {
  color: #fff;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-input {
  background: rgba(0, 0, 0, 0.5);
  border: 2px solid rgba(255, 255, 255, 0.2);
  border-radius: 10px;
  color: #fff;
  padding: 0.75rem;
  font-size: 1rem;
  transition: border-color 0.3s ease;
}

.form-input:focus {
  outline: none;
  border-color: #e50914;
}

.form-input::placeholder {
  color: rgba(255, 255, 255, 0.5);
}

textarea.form-input {
  resize: vertical;
  font-family: inherit;
}

.submit-btn {
  background: linear-gradient(135deg, #e50914 0%, #b8070f 100%);
  color: #fff;
  border: none;
  padding: 1rem 2rem;
  border-radius: 25px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  align-self: flex-start;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(229, 9, 20, 0.4);
}

.submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .contact-container {
    padding: 0 1rem;
  }
  
  .contact-content {
    grid-template-columns: 1fr;
    gap: 2rem;
  }
  
  .contact-info,
  .contact-form-section {
    padding: 1.5rem;
  }
}
</style>