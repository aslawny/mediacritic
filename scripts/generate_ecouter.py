#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Page « Ma liste d'ecoute » (/ecouter.html), lecteur du site (21/11/2026).

Page-outil personnelle (la liste vit dans le navigateur) : noindex, hors
sitemap. Lecteur audio (fichiers publies par les podcasteurs) + lecteur
officiel YouTube, file d'attente, enchainement, reprise, vitesse, commandes
de l'ecran verrouille. Logique : assets/ecouter.js ; boutons des autres
pages : assets/liste.js ; donnees : scripts/ecoute.py.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from charte import appliquer as charte_appliquer, MARQUEUR_LECTEURS  # noqa: E402

ROOT = Path(__file__).parent.parent
GA = "G-3W2VTTEWG8"


def main():
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
{MARQUEUR_LECTEURS}
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Ma liste d'écoute | MediaCritic</title>
<meta name="description" content="Écoute les épisodes des podcasts et chaînes YouTube de l'annuaire MediaCritic et compose ta propre liste." />
<meta name="robots" content="noindex, follow" />
<meta name="referrer" content="strict-origin-when-cross-origin" />
<meta property="og:type" content="website" />
<meta property="og:url" content="https://www.mediacritic.fr/ecouter.html" />
<meta property="og:title" content="Une liste d'écoute à découvrir sur MediaCritic" />
<meta property="og:description" content="Des épisodes de podcasts et de chaînes YouTube francophones, à écouter à la suite. Ouvre la liste et ajoute-la à tes listes." />
<meta property="og:image" content="https://www.mediacritic.fr/assets/ecouter-og.png" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:locale" content="fr_FR" />
<meta property="og:site_name" content="MediaCritic" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="Une liste d'écoute à découvrir sur MediaCritic" />
<meta name="twitter:image" content="https://www.mediacritic.fr/assets/ecouter-og.png" />
<link rel="icon" href="assets/logo.png" type="image/png" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Syne:wght@700;800&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="/assets/ecouter.css" />
</head>
<body>
<nav></nav>
<main class="ecl" id="ecl">
  <h1>Ma liste d'écoute</h1>
  <p class="ecl-intro">Les épisodes que tu ajoutes avec <strong>▶</strong> ou <strong>+</strong> depuis l'annuaire s'enchaînent ici. Garde cet onglet ouvert : tu peux continuer à naviguer sur le site sans couper le son.</p>
  <section class="ecl-import" id="ecl-import" aria-labelledby="ecl-import-titre" hidden></section>

  <section class="ecl-lecteur" id="ecl-lecteur" aria-label="Lecteur" hidden>
    <div class="ecl-entete">
      <img id="ecl-image" class="ecl-image" alt="" width="96" height="96" referrerpolicy="no-referrer" />
      <div class="ecl-infos">
        <p class="ecl-emission" id="ecl-emission"></p>
        <h2 class="ecl-titre" id="ecl-titre"></h2>
        <a class="ecl-lien" id="ecl-lien" href="#">Voir la fiche</a>
      </div>
    </div>
    <div class="ecl-video" id="ecl-video" hidden><div id="ecl-yt"></div></div>
    <audio id="ecl-audio" preload="none"></audio>
    <div class="ecl-progres">
      <input type="range" id="ecl-barre" min="0" max="1000" value="0" step="1" aria-label="Position dans l'épisode" />
      <div class="ecl-temps"><span id="ecl-ecoule">0:00</span><span id="ecl-total">--:--</span></div>
    </div>
    <div class="ecl-commandes">
      <button type="button" class="ecl-btn" id="ecl-prec" aria-label="Élément précédent">⏮</button>
      <button type="button" class="ecl-btn" id="ecl-moins" aria-label="Reculer de 15 secondes">↺ 15</button>
      <button type="button" class="ecl-btn ecl-play" id="ecl-play" aria-label="Lecture">▶</button>
      <button type="button" class="ecl-btn" id="ecl-plus" aria-label="Avancer de 30 secondes">30 ↻</button>
      <button type="button" class="ecl-btn" id="ecl-suiv" aria-label="Élément suivant">⏭</button>
    </div>
    <div class="ecl-options">
      <label for="ecl-vitesse">Vitesse</label>
      <select id="ecl-vitesse">
        <option value="0.8">0,8×</option><option value="1" selected>1×</option><option value="1.25">1,25×</option>
        <option value="1.5">1,5×</option><option value="1.75">1,75×</option><option value="2">2×</option>
      </select>
    </div>
    <p class="ecl-message" id="ecl-message" role="status" aria-live="polite"></p>
  </section>

  <section class="ecl-file" aria-labelledby="ecl-file-titre">
    <div class="ecl-listes">
      <label for="ecl-choix" class="ecl-listes-lib">Mes listes</label>
      <select id="ecl-choix" class="ecl-choix"></select>
      <div class="ecl-listes-actions">
        <button type="button" class="ecl-btn ecl-btn-txt" id="ecl-nouvelle">+ Nouvelle</button>
        <button type="button" class="ecl-btn ecl-btn-txt" id="ecl-renommer">Renommer</button>
        <button type="button" class="ecl-btn ecl-btn-txt" id="ecl-supprimer">Supprimer</button>
        <button type="button" class="ecl-btn ecl-btn-txt ecl-btn-plein" id="ecl-partager">🔗 Partager cette liste</button>
      </div>
      <p class="ecl-partage-retour" id="ecl-partage-retour" role="status" aria-live="polite"></p>
    </div>
    <div class="ecl-file-tete">
      <h2 id="ecl-file-titre">À suivre <span id="ecl-nombre"></span></h2>
      <div class="ecl-file-actions">
        <button type="button" class="ecl-btn ecl-btn-txt" id="ecl-ecoutes">Retirer les écoutés</button>
        <button type="button" class="ecl-btn ecl-btn-txt" id="ecl-vider">Vider</button>
      </div>
    </div>
    <ol class="ecl-liste" id="ecl-liste"></ol>
    <div class="ecl-vide" id="ecl-vide" hidden>
      <p><strong>Ta liste est vide.</strong> Ouvre la fiche d'un podcast ou d'une chaîne YouTube : chaque épisode récent a un bouton <strong>▶</strong> (écouter tout de suite) et <strong>+</strong> (ajouter à ta liste).</p>
      <p><a class="ecl-btn ecl-btn-plein" href="podcast-du-jour.html">Le podcast du jour</a> <a class="ecl-btn" href="catalogue.html">L'annuaire</a></p>
    </div>
    <p class="ecl-note" id="ecl-stockage" hidden>Ton navigateur bloque l'enregistrement : la liste ne sera pas conservée après fermeture.</p>
  </section>
  <p class="ecl-mentions">Les podcasts sont lus directement depuis le fichier publié par leur auteur, chez son hébergeur ; les vidéos, dans le lecteur officiel de YouTube. MediaCritic n'héberge aucun de ces contenus. Ta liste reste dans ton navigateur.</p>
</main>
<footer></footer>
<script async src="https://www.googletagmanager.com/gtag/js?id={GA}"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}gtag('js',new Date());gtag('config','{GA}');</script>
<script defer src="/assets/ecouter.js"></script>
<script defer src="/assets/partage.js"></script>
</body>
</html>"""
    html, etat = charte_appliquer(html, "liste")
    assert etat is not None, "charte non appliquée"
    (ROOT / "ecouter.html").write_text(html, encoding="utf-8")
    print("  ecouter.html générée")


if __name__ == "__main__":
    main()
