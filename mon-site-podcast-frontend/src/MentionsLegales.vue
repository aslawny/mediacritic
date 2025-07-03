<template>
  <div class="mentions-page">
    <div class="mentions-container">
      <div class="mentions-header">
        <h1>Mentions légales</h1>
      </div>
      
      <div class="mentions-content">
        <section class="mentions-section">
          <h2>Éditeur du site</h2>
          <p>
            <strong>MediaCritic</strong><br>
            Plateforme de recommandations de podcasts<br>
            Email : contact@MediaCritic.fr
          </p>
        </section>
        
        <section class="mentions-section">
          <h2>Hébergement</h2>
          <p>
            Ce site est hébergé par Vercel Inc.<br>
            340 S Lemon Ave #4133<br>
            Walnut, CA 91789, États-Unis
          </p>
        </section>
        
        <section class="mentions-section">
          <h2>Propriété intellectuelle</h2>
          <p>
            L'ensemble de ce site relève de la législation française et internationale 
            sur le droit d'auteur et la propriété intellectuelle. Tous les droits de 
            reproduction sont réservés, y compris pour les documents téléchargeables 
            et les représentations iconographiques et photographiques.
          </p>
        </section>
        
        <section class="mentions-section">
          <h2>Données personnelles</h2>
          <p>
            Conformément à la loi "Informatique et Libertés" du 6 janvier 1978 modifiée 
            et au Règlement Général sur la Protection des Données (RGPD), vous disposez 
            d'un droit d'accès, de rectification et de suppression des données vous concernant.
          </p>
        </section>
        
        <section class="mentions-section">
          <h2>Cookies</h2>
          <p>
            Ce site utilise des cookies techniques nécessaires à son bon fonctionnement. 
            Aucun cookie de tracking ou publicitaire n'est utilisé sans votre consentement.
          </p>
        </section>
      </div>
      
      <div class="mentions-footer">
        <router-link to="/" class="back-button">
          Retour à l'accueil
        </router-link>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'MentionsLegales'
}
</script>

<style scoped>
.mentions-page {
  background: #000;
  min-height: 100vh;
  padding: 2rem 0;
}

.mentions-container {
  max-width: 800px;
  margin: 0 auto;
  padding: 0 2rem;
}

.mentions-header {
  text-align: center;
  margin-bottom: 3rem;
}

.mentions-header h1 {
  font-size: clamp(2.5rem, 5vw, 3.5rem);
  font-weight: 900;
  background: linear-gradient(135deg, #fff 0%, #e50914 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.mentions-content {
  margin-bottom: 3rem;
}

.mentions-section {
  background: rgba(20, 20, 20, 0.5);
  border-radius: 15px;
  padding: 2rem;
  margin-bottom: 2rem;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.mentions-section h2 {
  color: #e50914;
  font-size: 1.5rem;
  margin-bottom: 1rem;
}

.mentions-section p {
  color: rgba(255, 255, 255, 0.9);
  line-height: 1.7;
}

.mentions-section strong {
  color: #fff;
}

.mentions-footer {
  text-align: center;
}

.back-button {
  display: inline-block;
  background: linear-gradient(135deg, #e50914 0%, #b8070f 100%);
  color: #fff;
  padding: 1rem 2rem;
  border-radius: 25px;
  text-decoration: none;
  font-weight: 600;
  transition: all 0.3s ease;
}

.back-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(229, 9, 20, 0.4);
}

@media (max-width: 768px) {
  .mentions-container {
    padding: 0 1rem;
  }
  
  .mentions-section {
    padding: 1.5rem;
  }
}
</style>