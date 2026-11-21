/* Lecteur du site — page /ecouter.html (21/11/2026).
 * Liste : localStorage « mc-liste-v1 » (partagee avec assets/liste.js).
 * Audio : fichier publie par le podcasteur (lu chez son hebergeur).
 * Video : lecteur OFFICIEL YouTube, pilote par son API publique.
 * Jamais de lecture automatique a l'ouverture : la premiere lecture part d'un
 * geste du visiteur ; ensuite la liste s'enchaine. */
(function () {
  'use strict';
  var CLE = 'mc-liste-v1';
  var $ = function (id) { return document.getElementById(id); };
  var memoire = null, stockageOk = true;
  var liste, courant = null, yt = null, ytPret = false, ytCharge = false, aPrevu = null;
  var audio = $('ecl-audio');
  var dernierSave = 0, glisse = false;

  /* ---------- stockage protege ---------- */
  function lire() {
    try { var s = localStorage.getItem(CLE); if (s) { var l = JSON.parse(s); if (l && l.items) return l; } }
    catch (e) { stockageOk = false; }
    return memoire || { v: 1, items: [], courant: null, positions: {}, vitesse: 1 };
  }
  function sauver() {
    memoire = liste;
    try { localStorage.setItem(CLE, JSON.stringify(liste)); } catch (e) { stockageOk = false; }
    $('ecl-stockage').hidden = stockageOk;
  }
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
  function hms(s) {
    s = Math.max(0, Math.floor(s || 0));
    var h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), x = String(s % 60).padStart(2, '0');
    return h ? h + ':' + String(m).padStart(2, '0') + ':' + x : m + ':' + x;
  }
  function index(id) { return liste.items.findIndex(function (x) { return x.id === id; }); }
  function message(t) { $('ecl-message').textContent = t || ''; }

  /* ---------- moteur : audio ou YouTube ---------- */
  function estVideo() { return courant && courant.type === 'youtube'; }
  function position() {
    if (estVideo()) return (yt && ytPret && yt.getCurrentTime) ? yt.getCurrentTime() : 0;
    return audio.currentTime || 0;
  }
  function duree() {
    if (estVideo()) return (yt && ytPret && yt.getDuration) ? yt.getDuration() : (courant.duree || 0);
    return isFinite(audio.duration) && audio.duration ? audio.duration : (courant ? courant.duree || 0 : 0);
  }
  function enLecture() {
    if (estVideo()) return !!(yt && ytPret && yt.getPlayerState && yt.getPlayerState() === 1);
    return !audio.paused && !audio.ended;
  }
  function lecture() {
    message('');
    if (estVideo()) { if (yt && ytPret) yt.playVideo(); return; }
    var p = audio.play();
    if (p && p.catch) p.catch(function (e) {
      if (e && e.name === 'NotAllowedError') message('Appuie sur ▶ pour lancer la lecture.');
    });
  }
  function pause() { if (estVideo()) { if (yt && ytPret) yt.pauseVideo(); } else audio.pause(); }
  function aller(s) {
    s = Math.max(0, Math.min(s, duree() || s));
    if (estVideo()) { if (yt && ytPret) yt.seekTo(s, true); } else audio.currentTime = s;
    memoriser(true);
  }
  function vitesse(v) {
    liste.vitesse = v; sauver();
    audio.playbackRate = v;
    if (yt && ytPret && yt.setPlaybackRate) yt.setPlaybackRate(v);
  }
  function memoriser(force) {
    if (!courant) return;
    var t = Date.now();
    if (!force && t - dernierSave < 5000) return;
    dernierSave = t;
    liste.positions[courant.id] = Math.floor(position());
    sauver();
  }

  function chargerYouTube(pret) {
    if (window.YT && window.YT.Player) { pret(); return; }
    var prec = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = function () { if (prec) prec(); pret(); };
    if (!ytCharge) {
      ytCharge = true;
      var s = document.createElement('script'); s.src = 'https://www.youtube.com/iframe_api'; s.async = true;
      document.head.appendChild(s);
    }
  }

  function preparer(item, jouer) {
    if (courant && courant.id !== item.id) memoriser(true);
    courant = item; liste.courant = item.id; sauver();
    var depart = liste.positions[item.id] || 0;
    if (item.duree && depart > item.duree - 5) depart = 0;
    $('ecl-lecteur').hidden = false;
    $('ecl-titre').textContent = item.titre;
    $('ecl-emission').textContent = item.emission;
    var img = $('ecl-image');
    if (item.image) { img.src = item.image; img.hidden = false; } else img.hidden = true;
    $('ecl-lien').href = item.lien || '#';
    $('ecl-lien').hidden = !item.lien;
    document.title = item.titre + ' — Ma liste d\'écoute | MediaCritic';
    message('');
    if (item.type === 'youtube') {
      audio.pause(); audio.removeAttribute('src'); audio.load();
      $('ecl-video').hidden = false;
      chargerYouTube(function () {
        if (yt && ytPret) {
          yt.loadVideoById ? (jouer ? yt.loadVideoById({ videoId: item.src, startSeconds: depart })
                                    : yt.cueVideoById({ videoId: item.src, startSeconds: depart })) : null;
          vitesse(liste.vitesse || 1);
          return;
        }
        yt = new YT.Player('ecl-yt', {
          host: 'https://www.youtube-nocookie.com', videoId: item.src,
          playerVars: { start: Math.floor(depart), playsinline: 1, rel: 0 },
          events: {
            onReady: function () { ytPret = true; vitesse(liste.vitesse || 1); if (jouer) yt.playVideo(); },
            onStateChange: function (e) { if (e.data === 0) fin(); majBouton(); },
            onError: function () { message('Cette vidéo ne peut pas être lue ici (intégration refusée par la chaîne).'); }
          }
        });
      });
    } else {
      if (yt && ytPret) yt.pauseVideo();
      $('ecl-video').hidden = true;
      audio.src = item.src;
      audio.preload = 'metadata';
      audio.playbackRate = liste.vitesse || 1;
      var poser = function () { try { if (depart) audio.currentTime = depart; } catch (e) {} audio.removeEventListener('loadedmetadata', poser); };
      audio.addEventListener('loadedmetadata', poser);
      if (jouer) lecture();
    }
    medias(item);
    rendreListe();
  }

  function fin() {
    if (!courant) return;
    liste.positions[courant.id] = 0;
    liste.ecoutes = liste.ecoutes || {};
    liste.ecoutes[courant.id] = 1;
    sauver();
    var i = index(courant.id);
    if (i >= 0 && i < liste.items.length - 1) preparer(liste.items[i + 1], true);
    else { message('Fin de la liste. Ajoute d\'autres épisodes depuis l\'annuaire !'); rendreListe(); majBouton(); }
  }
  function voisin(d) {
    if (!courant) return;
    var i = index(courant.id) + d;
    if (i >= 0 && i < liste.items.length) preparer(liste.items[i], enLecture() || true);
  }

  /* ---------- ecran verrouille / casque ---------- */
  function medias(item) {
    if (!('mediaSession' in navigator)) return;
    try {
      navigator.mediaSession.metadata = new MediaMetadata({
        title: item.titre, artist: item.emission, album: 'Ma liste d\'écoute — MediaCritic',
        artwork: item.image ? [{ src: item.image, sizes: '512x512' }] : []
      });
      var a = navigator.mediaSession;
      a.setActionHandler('play', lecture);
      a.setActionHandler('pause', pause);
      a.setActionHandler('seekbackward', function () { aller(position() - 15); });
      a.setActionHandler('seekforward', function () { aller(position() + 30); });
      a.setActionHandler('previoustrack', function () { voisin(-1); });
      a.setActionHandler('nexttrack', function () { voisin(1); });
    } catch (e) {}
  }

  /* ---------- rendu ---------- */
  function majBouton() {
    var b = $('ecl-play'), on = enLecture();
    b.textContent = on ? '⏸' : '▶';
    b.setAttribute('aria-label', on ? 'Pause' : 'Lecture');
  }
  function majTemps() {
    if (glisse) return;
    var d = duree(), p = position();
    $('ecl-ecoule').textContent = hms(p);
    $('ecl-total').textContent = d ? hms(d) : '--:--';
    $('ecl-barre').value = d ? Math.round(1000 * p / d) : 0;
    $('ecl-barre').setAttribute('aria-valuetext', hms(p) + ' sur ' + (d ? hms(d) : 'durée inconnue'));
  }
  function rendreListe() {
    var ol = $('ecl-liste'); ol.textContent = '';
    var n = liste.items.length;
    $('ecl-nombre').textContent = n ? '(' + n + ')' : '';
    $('ecl-vide').hidden = n > 0;
    $('ecl-ecoutes').hidden = $('ecl-vider').hidden = n === 0;
    if (!n) { $('ecl-lecteur').hidden = true; }
    var ecoutes = liste.ecoutes || {};
    liste.items.forEach(function (it, i) {
      var pos = liste.positions[it.id];
      var meta = it.emission + (it.duree ? ' · ' + hms(it.duree) : '') +
        (it.type === 'youtube' ? ' · vidéo' : '') +
        (ecoutes[it.id] ? ' · ✓ écouté' : (pos ? ' · reprise à ' + hms(pos) : ''));
      var jouer = el('button', { type: 'button', classe: 'ecl-el-jouer' }, [
        el('span', { classe: 'ecl-el-titre', texte: it.titre }), el('span', { classe: 'ecl-el-meta', texte: meta })]);
      jouer.addEventListener('click', function () { preparer(it, true); });
      var haut = el('button', { type: 'button', classe: 'ecl-btn', texte: '↑', 'aria-label': 'Monter « ' + it.titre + ' »' });
      var bas = el('button', { type: 'button', classe: 'ecl-btn', texte: '↓', 'aria-label': 'Descendre « ' + it.titre + ' »' });
      var suppr = el('button', { type: 'button', classe: 'ecl-btn', texte: '✕', 'aria-label': 'Retirer « ' + it.titre + ' » de la liste' });
      haut.disabled = i === 0; bas.disabled = i === n - 1;
      haut.addEventListener('click', function () { deplacer(i, -1); });
      bas.addEventListener('click', function () { deplacer(i, 1); });
      suppr.addEventListener('click', function () { retirer(it.id); });
      ol.appendChild(el('li', { classe: 'ecl-el' + (courant && courant.id === it.id ? ' ecl-courant' : ''),
        'aria-current': courant && courant.id === it.id ? 'true' : 'false' }, [
        it.image ? el('img', { src: it.image, alt: '', width: '48', height: '48', loading: 'lazy', referrerpolicy: 'no-referrer' }) : null,
        jouer, el('div', { classe: 'ecl-el-actions' }, [haut, bas, suppr])]));
    });
  }
  function deplacer(i, d) {
    var j = i + d; if (j < 0 || j >= liste.items.length) return;
    var x = liste.items.splice(i, 1)[0]; liste.items.splice(j, 0, x); sauver(); rendreListe();
  }
  function retirer(id) {
    var i = index(id); if (i < 0) return;
    var enCours = courant && courant.id === id;
    liste.items.splice(i, 1); delete liste.positions[id];
    if (enCours) {
      pause(); courant = null; liste.courant = null;
      if (liste.items.length) preparer(liste.items[Math.min(i, liste.items.length - 1)], false);
    }
    sauver(); rendreListe();
  }

  /* ---------- synchronisation avec les autres onglets ---------- */
  function relire() {
    var nouv = lire();
    liste.items = nouv.items; liste.positions = Object.assign({}, nouv.positions, liste.positions);
    var a = nouv.aJouer;
    if (a) { delete nouv.aJouer; liste.aJouer = undefined; sauver(); }
    rendreListe();
    if (a) { var i = index(a); if (i >= 0) preparer(liste.items[i], !!courant); }
    else if (!courant && liste.items.length) preparer(liste.items[0], false);
  }

  function init() {
    liste = lire();
    $('ecl-stockage').hidden = stockageOk;
    var aJouer = liste.aJouer; delete liste.aJouer; sauver();
    var depart = (aJouer && liste.items[index(aJouer)]) || liste.items[index(liste.courant)] || liste.items[0];
    rendreListe();
    if (depart) preparer(depart, false);
    $('ecl-vitesse').value = String(liste.vitesse || 1);

    $('ecl-play').addEventListener('click', function () { enLecture() ? pause() : lecture(); setTimeout(majBouton, 200); });
    $('ecl-moins').addEventListener('click', function () { aller(position() - 15); });
    $('ecl-plus').addEventListener('click', function () { aller(position() + 30); });
    $('ecl-prec').addEventListener('click', function () { voisin(-1); });
    $('ecl-suiv').addEventListener('click', function () { voisin(1); });
    $('ecl-vitesse').addEventListener('change', function () { vitesse(parseFloat(this.value) || 1); });
    var barre = $('ecl-barre');
    barre.addEventListener('input', function () { glisse = true; $('ecl-ecoule').textContent = hms(duree() * barre.value / 1000); });
    barre.addEventListener('change', function () { glisse = false; aller(duree() * barre.value / 1000); });
    $('ecl-vider').addEventListener('click', function () {
      if (!confirm('Vider toute ta liste d\'écoute ?')) return;
      pause(); liste.items = []; liste.positions = {}; liste.ecoutes = {}; courant = null; liste.courant = null; sauver(); rendreListe();
    });
    $('ecl-ecoutes').addEventListener('click', function () {
      var e = liste.ecoutes || {};
      liste.items = liste.items.filter(function (x) { return !e[x.id] || (courant && x.id === courant.id); });
      sauver(); rendreListe();
    });

    audio.addEventListener('timeupdate', function () { majTemps(); memoriser(false); });
    audio.addEventListener('play', majBouton);
    audio.addEventListener('pause', function () { majBouton(); memoriser(true); });
    audio.addEventListener('ended', fin);
    audio.addEventListener('loadedmetadata', majTemps);
    audio.addEventListener('error', function () {
      if (!courant || estVideo() || !audio.getAttribute('src')) return;
      message('Épisode indisponible chez son hébergeur. Passe au suivant avec ⏭.');
    });
    setInterval(function () { if (estVideo()) { majTemps(); memoriser(false); majBouton(); } }, 1000);
    window.addEventListener('pagehide', function () { memoriser(true); });
    window.addEventListener('storage', function (e) { if (e.key === CLE) relire(); });
    try {
      var c = new BroadcastChannel('mc-lecteur');
      c.onmessage = function (m) { if (m.data && m.data.jouer) setTimeout(relire, 50); };
    } catch (e) {}
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
