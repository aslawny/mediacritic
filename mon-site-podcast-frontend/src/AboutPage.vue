<template>
  <div class="about-page">
    <div class="about-container">
      <div class="about-header">
        <h1>À propos de MediaCritic</h1>
        <p class="about-subtitle">La passion des podcasts au cœur de notre mission</p>
      </div>
      
      <div class="about-content">
        <section class="about-section">
          <h2>Notre histoire</h2>
          <p>
            MediaCritic est né de la passion de quelques amateurs de podcasts qui souhaitaient créer 
            une plateforme dédiée à la découverte et au partage de contenus audio de qualité. 
            Nous croyons que chaque podcast a sa place et mérite d'être découvert par son public.
          </p>
        </section>
        
        <section class="about-section">
          <h2>Notre mission</h2>
          <p>
            Nous nous efforçons de créer un espace où les passionnés de podcasts peuvent :
          </p>
          <ul>
            <li>Découvrir de nouveaux contenus adaptés à leurs goûts</li>
            <li>Partager leurs coups de cœur avec la communauté</li>
            <li>Noter et commenter leurs épisodes préférés</li>
            <li>Explorer des catégories variées et enrichissantes</li>
          </ul>
        </section>
        
        <section class="about-section">
          <h2>L'équipe</h2>
          <p>
            Notre équipe est composée de développeurs, designers et passionnés de podcasts 
            qui travaillent ensemble pour améliorer constamment votre expérience d'écoute.
          </p>
        </section>
      </div>
      
      <div class="about-cta">
        <router-link to="/" class="cta-button">
          Découvrir nos podcasts
        </router-link>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'AboutPage'
}
</script>

<style scoped>
.about-page {
  background: #000;
  min-height: 100vh;
  padding: 2rem 0;
}

.about-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 0 2rem;
}

.about-header {
  text-align: center;
  margin-bottom: 3rem;
}

.about-header h1 {
  font-size: clamp(2.5rem, 5vw, 3.5rem);
  font-weight: 900;
  background: linear-gradient(135deg, #fff 0%, #e50914 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 1rem;
}

.about-subtitle {
  font-size: 1.2rem;
  color: rgba(255, 255, 255, 0.8);
}

.about-content {
  margin-bottom: 3rem;
}

.about-section {
  background: rgba(20, 20, 20, 0.5);
  border-radius: 15px;
  padding: 2rem;
  margin-bottom: 2rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.about-section h2 {
  color: #e50914;
  font-size: 1.5rem;
  margin-bottom: 1rem;
}

.about-section p {
  color: rgba(255, 255, 255, 0.9);
  line-height: 1.7;
  margin-bottom: 1rem;
}

.about-section ul {
  color: rgba(255, 255, 255, 0.9);
  padding-left: 1.5rem;
}

.about-section li {
  margin-bottom: 0.5rem;
  line-height: 1.6;
}

.about-cta {
  text-align: center;
}

.cta-button {
  display: inline-block;
  background: linear-gradient(135deg, #e50914 0%, #b8070f 100%);
  color: #fff;
  padding: 1rem 2rem;
  border-radius: 25px;
  text-decoration: none;
  font-weight: 600;
  font-size: 1.1rem;
  transition: all 0.3s ease;
}

.cta-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(229, 9, 20, 0.4);
}

@media (max-width: 768px) {
  .about-container {
    padding: 0 1rem;
  }
  
  .about-section {
    padding: 1.5rem;
  }
}
</style>