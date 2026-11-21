# Le Mystère du Jour — publier chaque matin (moins de 2 minutes)

**En temps normal : rien à faire.** Le mystère *est* le podcast du jour. Chaque
matin, le robot GitHub choisit le podcast du jour (`du_jour.py`, avant 10 h),
puis `generate_mystere.py` en dérive le mystère : indices, réponse encodée,
lecteurs, page `/mystere`. Le dimanche, c'est l'émission de notre épisode, avec
notre note et notre lecteur, sans intervention non plus.

## Le contrôle de 2 minutes (recommandé)

1. Ouvrir https://www.mediacritic.fr/mystere en navigation privée (ta propre
   partie n'est pas touchée) et jouer « Je donne ma langue au chat » :
   la révélation montre la réponse, les 6 indices et le lecteur.
2. Si un indice est faux ou faible (année, durée, initiales), ou si le lecteur
   ne joue pas : ouvrir `manifests/mystere-corrections.json` sur GitHub
   (bouton crayon), remplir la date du jour, valider (« Commit changes »).
   Exemple :
   ```json
   "2026-11-24": {"annee": 2017, "animateur": "Matthieu Stefani",
                  "lecteur": {"type": "spotify", "src": "https://open.spotify.com/embed/show/XXXX"}}
   ```
   La correction est prise en compte au passage suivant du robot (podcast du
   jour ou enrichissement de nuit), ou tout de suite en lançant
   `python scripts/generate_mystere.py` puis en poussant.

Clés possibles : `annee`, `duree_min`, `animateur`, `phrase`, `lecteur`
(`type` : spotify, apple, deezer ou youtube ; `src` : URL du lecteur
*officiel* intégrable), `indices` (`{"2": {"cle": "…", "texte": "…"}}` pour
remplacer l'indice n). Une valeur vide est ignorée.

## Bon à savoir

- **Avant le choix du matin** (minuit → ~10 h), la page affiche « le mystère
  arrive avant 10 h » et se met à jour seule.
- **Données calculées** une seule fois par date et mises en cache dans
  `data/_mystere_cache.json` : année (1er épisode du flux, ou « Actif depuis »
  de la chaîne YouTube ; « depuis au moins » si le flux est tronqué), durée
  médiane des derniers épisodes, lecteur (YouTube pour une chaîne ; Spotify si
  l'émission y est connue, sinon Apple). Pour forcer un recalcul : supprimer
  la date du cache.
- **Si le podcast du jour est refait** (choix remplacé), le mystère suit.
- **Anti-triche léger** : la réponse n'est dans `data/mystere.json` que sous
  forme d'empreinte (cyrb53 du nom normalisé) ; le reste est en base64.
- **Numéro** : n°1 = lundi 23/11/2026 (`LANCEMENT` dans le script).
- Les statistiques des joueurs restent dans leur navigateur (localStorage).
