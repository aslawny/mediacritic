<template>
  <footer class="footer">
    <div class="footer-container">
      <div class="footer-content">
        <!-- Section À propos -->
        <div class="footer-section">
          <h3>À propos de Podcaddict</h3>
          <p>Podcaddict est une plateforme indépendante de recommandations de podcasts, créée par des passionnés pour des passionnés.</p>
          <router-link to="/about" class="footer-link">En savoir plus</router-link>
        </div>
        
        <!-- Section Liens -->
        <div class="footer-section">
          <h3>Liens utiles</h3>
          <ul class="footer-links">
            <li><router-link to="/mentions-legales" class="footer-link">Mentions légales</router-link></li>
            <li><router-link to="/contact" class="footer-link">Contactez-nous</router-link></li>
            <li><a href="mailto:contact@podcaddict.fr" class="footer-link">contact@podcaddict.fr</a></li>
          </ul>
        </div>
        
        <!-- Section Réseaux sociaux -->
        <div class="footer-section">
          <h3>Suivez-nous</h3>
          <div class="social-links">
            <a href="#" class="social-link" aria-label="Twitter">🐦 Twitter</a>
            <a href="#" class="social-link" aria-label="Instagram">📸 Instagram</a>
            <a href="#" class="social-link" aria-label="LinkedIn">🔗 LinkedIn</a>
            <a href="#" class="social-link" aria-label="YouTube">📺 YouTube</a>
          </div>
        </div>
      </div>
      
      <!-- Copyright -->
      <div class="footer-bottom">
        <p>&copy; {{ currentYear }} Podcaddict. Tous droits réservés.</p>
        <p class="footer-tagline">Découvrez, écoutez, partagez vos podcasts préférés</p>
      </div>
    </div>
  </footer>
</template>

<script>
export default {
  name: 'Footer',
  computed: {
    currentYear() {
      return new Date().getFullYear()
    }
  }
}
</script>

<style scoped>
.footer {
  background: linear-gradient(135deg, #1a0000 0%, #000 50%, #1a0000 100%);
  border-top: 2px solid rgba(229, 9, 20, 0.3);
  margin-top: 4rem;
  padding: 3rem 0 1rem;
}

.footer-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 2rem;
}

.footer-content {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 2rem;
  margin-bottom: 2rem;
}

.footer-section h3 {
  color: #e50914;
  font-size: 1.2rem;
  font-weight: 700;
  margin-bottom: 1rem;
}

.footer-section p {
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.6;
  margin-bottom: 1rem;
}

.footer-links {
  list-style: none;
  padding: 0;
}

.footer-links li {
  margin-bottom: 0.5rem;
}

.footer-link {
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  transition: all 0.3s ease;
  font-size: 0.95rem;
}

.footer-link:hover {
  color: #e50914;
  text-decoration: underline;
}

.social-links {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
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
  transform: translateY(-2px);
}

.footer-bottom {
  text-align: center;
  padding-top: 2rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.footer-bottom p {
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.9rem;
  margin: 0.5rem 0;
}

.footer-tagline {
  font-style: italic;
}

@media (max-width: 768px) {
  .footer {
    padding: 2rem 0 1rem;
  }
  
  .footer-container {
    padding: 0 1rem;
  }
  
  .footer-content {
    grid-template-columns: 1fr;
    gap: 1.5rem;
  }
  
  .social-links {
    justify-content: center;
  }
}
</style>