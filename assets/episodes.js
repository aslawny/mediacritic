/* Tous les episodes d'une emission (lecteur du site, etape 3, 21/11/2026).
 * Podcast : liste chargee A LA DEMANDE dans l'API publique d'Apple (jusqu'a
 * 200 episodes, avec le fichier audio publie par l'auteur ; rien n'est
 * stocke chez nous). Chaine YouTube : les 15 dernieres videos gardees par le
 * bot (maximum du flux public de YouTube).
 * Donnees de la fiche : <script type="application/json" id="mc-fiche-ecoute">.
 * Ajout a la liste : window.MCListe (assets/liste.js). */
(function () {
  'use strict';
  var PAGE = 30;
  var zone = document.getElementById('ep-tous');
  var src = document.getElementById('mc-fiche-ecoute');
  if (!zone || !src) return;
  var f; try { f = JSON.parse(src.textContent); } catch (e) { return; }

  function el(tag, attrs, enfants) {
    var n = document.createElement(tag);
    for (var k in (attrs || {})) {
      if (k === 'texte') n.textContent = attrs[k];
      else if (k === 'classe') n.className = attrs[k];
      else n.setAttribute(k, attrs[k]);
    }
    (enfants || []).forEach(function (e) { if (e) n.appendChild(e); });
    return n;
  }
  function norm(s) { return String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase(); }
  function hash(s) {                       // cyrb53 : identifiant stable d'un episode
    var h1 = 0xdeadbeef, h2 = 0x41c6ce57;
    for (var i = 0, c; i < s.length; i++) { c = s.charCodeAt(i); h1 = Math.imul(h1 ^ c, 2654435761); h2 = Math.imul(h2 ^ c, 1597334677); }
    h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
    h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
    return (4294967296 * (2097151 & h2) + (h1 >>> 0)).toString(16);
  }
  function duree(s) {
    if (!s) return '';
    var h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60);
    return h ? h + ' h ' + String(m).padStart(2, '0') : m + ' min';
  }
  function dateFr(iso) {
    try { return new Date(iso + 'T12:00:00Z').toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' }); }
    catch (e) { return iso || ''; }
  }

  var tous = [], filtre = '', montres = PAGE;
  var bouton = el('button', { type: 'button', classe: 'mc-btn-tous',
    texte: f.videos ? '🎬 Les ' + f.videos.length + ' dernières vidéos' : '📚 Tous les épisodes' });
  var corps = el('div', { classe: 'ep-tous-corps', hidden: '' });
  zone.appendChild(bouton); zone.appendChild(corps);

  function element(o) {
    return { id: hash(o.src), type: o.type, src: o.src, titre: o.titre, emission: f.emission,
             lien: f.lien, image: f.image, date: o.date || '', duree: o.duree || null };
  }

  function rendre() {
    corps.textContent = '';
    var cherche = el('input', { type: 'search', classe: 'ep-tous-cherche', placeholder: 'Chercher un épisode…',
      'aria-label': 'Chercher un épisode de ' + f.emission });
    cherche.value = filtre;
    cherche.addEventListener('input', function () { filtre = cherche.value; montres = PAGE; liste(); cherche.focus(); });
    corps.appendChild(cherche);
    var info = el('p', { classe: 'ep-tous-info', id: 'ep-tous-info', 'aria-live': 'polite' });
    corps.appendChild(info);
    var ul = el('ul', { classe: 'ep-list ep-tous-liste', id: 'ep-tous-liste' });
    corps.appendChild(ul);
    var plus = el('button', { type: 'button', classe: 'mc-btn-tous ep-tous-plus', id: 'ep-tous-plus', texte: 'Afficher plus' });
    plus.addEventListener('click', function () { montres += PAGE; liste(); });
    corps.appendChild(plus);
    corps.appendChild(el('p', { classe: 'ep-tous-source', texte: f.videos
      ? 'Les 15 dernières vidéos de la chaîne (limite du flux public de YouTube). Les plus anciennes sont sur YouTube.'
      : 'Liste fournie par Apple Podcasts (200 épisodes les plus récents au plus). Lecture depuis le fichier publié par l\'auteur.' }));
    liste();
  }
  function liste() {
    var q = norm(filtre).trim();
    var vus = q ? tous.filter(function (e) { return norm(e.titre).indexOf(q) >= 0; }) : tous;
    var ul = document.getElementById('ep-tous-liste'); ul.textContent = '';
    vus.slice(0, montres).forEach(function (e) {
      var item = element(e);
      var jouer = el('button', { type: 'button', classe: 'mc-ec-btn mc-ec-play', texte: '▶', 'aria-label': 'Écouter « ' + e.titre + ' »' });
      var ajout = el('button', { type: 'button', classe: 'mc-ec-btn mc-ec-add', texte: '+', 'aria-label': 'Ajouter « ' + e.titre + ' » à ma liste' });
      jouer.addEventListener('click', function () { if (window.MCListe) window.MCListe.ecouter(item); });
      ajout.addEventListener('click', function () {
        if (!window.MCListe) return;
        var r = window.MCListe.ajouter(item);
        var nom = window.MCListe.nomActif ? window.MCListe.nomActif() : 'ta liste';
        if (window.MCListe.toast) window.MCListe.toast(r === 'deja' ? 'Déjà dans « ' + nom + ' »' : 'Ajouté à « ' + nom + ' » 🎧');
      });
      ul.appendChild(el('li', {}, [
        el('span', { classe: 'ep-date', texte: e.date || '' }),
        el('span', { classe: 'ep-titre', texte: e.titre + (e.duree ? ' · ' + duree(e.duree) : '') }),
        el('span', { classe: 'mc-ec' }, [jouer, ajout])]));
    });
    document.getElementById('ep-tous-info').textContent = q
      ? vus.length + ' épisode' + (vus.length > 1 ? 's' : '') + ' pour « ' + filtre.trim() + ' »'
      : tous.length + (f.videos ? ' vidéos' : ' épisodes');
    document.getElementById('ep-tous-plus').hidden = vus.length <= montres;
  }

  function charger() {
    if (f.videos) {
      tous = f.videos.map(function (v) { return { type: 'youtube', src: v.video, titre: v.titre, date: v.date }; });
      return Promise.resolve();
    }
    var url = 'https://itunes.apple.com/lookup?id=' + encodeURIComponent(f.trackId) +
      '&country=fr&entity=podcastEpisode&limit=200';
    return fetch(url).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); }).then(function (j) {
      tous = (j.results || []).filter(function (r) {
        return r.wrapperType === 'podcastEpisode' && /^https:\/\//.test(r.episodeUrl || '');
      }).map(function (r) {
        return { type: 'audio', src: r.episodeUrl, titre: r.trackName || '', date: (r.releaseDate || '').slice(0, 10),
                 duree: r.trackTimeMillis ? Math.round(r.trackTimeMillis / 1000) : null };
      }).sort(function (a, b) { return a.date < b.date ? 1 : -1; });
    });
  }

  var charge = false;
  bouton.addEventListener('click', function () {
    if (!corps.hidden) { corps.hidden = true; bouton.setAttribute('aria-expanded', 'false'); return; }
    corps.hidden = false; bouton.setAttribute('aria-expanded', 'true');
    if (charge) return;
    corps.textContent = 'Chargement des épisodes…';
    charger().then(function () {
      charge = true;
      if (!tous.length) { corps.textContent = 'Aucun épisode lisible trouvé pour cette émission.'; return; }
      rendre();
      try { if (window.gtag) window.gtag('event', 'episodes_tous', { type: f.videos ? 'youtube' : 'podcast', nombre: tous.length }); } catch (e) {}
    }, function () {
      corps.textContent = 'Impossible de charger la liste complète pour le moment. Réessaie plus tard.';
    });
  });
  bouton.setAttribute('aria-expanded', 'false');
})();
