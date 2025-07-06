// 📁 backend/index.js

const express = require('express');
const admin = require('firebase-admin');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

// 🔐 Initialisation Firebase
const serviceAccount = require('./serviceAccountKey.json');

admin.initializeApp({
  credential: admin.credential.cert(serviceAccount)
});

const db = admin.firestore();

// ✅ ROUTE POST : Ajout d’un commentaire
app.post('/api/comments', async (req, res) => {
  const { podcastId, comment, rating, userId, username } = req.body;

  if (!podcastId || !comment || rating == null || !userId || !username) {
    return res.status(400).json({ error: 'Données incomplètes' });
  }

  try {
    const existing = await db.collection('comments')
      .where('podcastId', '==', podcastId)
      .where('userId', '==', userId)
      .get();

    if (!existing.empty) {
      return res.status(409).json({
        error: 'Commentaire déjà existant',
        message: 'Vous avez déjà commenté ce podcast. Supprimez votre commentaire pour en ajouter un nouveau.'
      });
    }

    await db.collection('comments').add({
      podcastId,
      comment,
      rating: Number(rating),
      userId,
      username,
      timestamp: admin.firestore.FieldValue.serverTimestamp()
    });

    return res.status(200).json({ message: 'Commentaire enregistré avec succès' });
  } catch (err) {
    console.error('❌ Erreur POST /api/comments:', err.message);
    return res.status(500).json({ error: 'Erreur serveur', details: err.message });
  }
});

// ✅ ROUTE GET : Récupération des commentaires pour un podcast
app.get('/api/comments/:podcastId', async (req, res) => {
  const { podcastId } = req.params;

  try {
    const snapshot = await db.collection('comments')
      .where('podcastId', '==', podcastId)
      // ✅ Enlève temporairement l'orderBy si le champ n'est pas garanti présent
      // .orderBy('timestamp', 'desc')
      .get();

    const comments = snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }));

    return res.status(200).json(comments);
  } catch (error) {
    console.error('Erreur GET /api/comments:', error.message);
    return res.status(500).json({ error: 'Erreur serveur', details: error.message });
  }
});

// ✅ Récupérer les commentaires d’un utilisateur
app.get('/api/comments/user/:userId', async (req, res) => {
  const { userId } = req.params

  try {
    const snapshot = await db.collection('comments')
      .where('userId', '==', userId)
      .orderBy('timestamp', 'desc')
      .get()

    const comments = snapshot.docs.map(doc => ({
      id: doc.id,
      ...doc.data()
    }))

    res.status(200).json(comments)
  } catch (error) {
    console.error('Erreur GET /api/comments/user:', error.message)
    res.status(500).json({ error: 'Erreur serveur', details: error.message })
  }
})

// ✅ ROUTE DELETE : Suppression d’un commentaire d’un user sur un podcast
app.delete('/api/comments', async (req, res) => {
  const { podcastId, userId } = req.body;

  if (!podcastId || !userId) {
    return res.status(400).json({ error: 'Requête incomplète' });
  }

  try {
    const snapshot = await db.collection('comments')
      .where('podcastId', '==', podcastId)
      .where('userId', '==', userId)
      .get();

    if (snapshot.empty) {
      return res.status(404).json({ error: 'Commentaire non trouvé' });
    }

    const batch = db.batch();
    snapshot.forEach(doc => batch.delete(doc.ref));
    await batch.commit();

    return res.status(200).json({ message: 'Commentaire supprimé' });
  } catch (err) {
    console.error('❌ Erreur DELETE /api/comments:', err.message);
    return res.status(500).json({ error: 'Erreur serveur', details: err.message });
  }
});

// 🚀 Démarrage du serveur
const PORT = 5001;
app.listen(PORT, () => {
  console.log(`✅ API backend démarrée sur http://localhost:${PORT}`);
});
