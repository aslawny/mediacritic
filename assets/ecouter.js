/* Lecteur du site — page /ecouter.html.
 * Etape 1 (21/11/2026) : lecteur, file, enchainement, reprise, vitesse.
 * Etape 2 : plusieurs listes nommees + partage d'une liste par lien.
 * Stockage : localStorage « mc-liste-v1 », format v2 (partage avec
 * assets/liste.js) : {v:2, listes:[{id,nom,items}], active, courant,
 * positions, vitesse, ecoutes}. Positions, vitesse et « ecoute » sont
 * communes a toutes les listes.
 * Audio : fichier publie par le podcasteur (lu chez son hebergeur).
 * Video : lecteur OFFICIEL YouTube, pilote par son API publique.
 * Jamais de lecture automatique a l'ouverture : la premiere lecture part d'un
 * geste du visiteur ; ensuite la liste s'enchaine.
 * Lien de partage : /ecouter.html#l=<liste compressee> — tout est dans le
 * fragment (jamais envoye au serveur) ; a l'arrivee, chaque element est
 * VERIFIE (audio https, id YouTube, textes bornes, liens internes) et la
 * liste est montree avant d'etre ajoutee. */
(function () {
  'use strict';
  var CLE = 'mc-liste-v1';
  var MAX_PARTAGE = 100;
  var $ = function (id) { return document.getElementById(id); };
  var memoire = null, stockageOk = true;
  var liste, courant = null, yt = null, ytPret = false, ytCharge = false;
  var audio = $('ecl-audio');
  var dernierSave = 0, glisse = false;

  /* ---------- stockage protege ---------- */
  // DOIT rester identique a migrer() de assets/liste.js.
  function migrer(l) {
    if (!l || typeof l !== 'object') l = {};
    if (l.v === 2 && Array.isArray(l.listes) && l.listes.length) return l;
    return { v: 2, listes: [{ id: 'l1', nom: 'Ma liste', items: Array.isArray(l.items) ? l.items : [] }],
             active: 'l1', courant: l.courant || null, positions: l.positions || {},
             vitesse: l.vitesse || 1, ecoutes: l.ecoutes || {}, aJouer: l.aJouer };
  }
  function listeActive(r) {
    return r.listes.find(function (x) { return x.id === r.active; }) || r.listes[0];
  }
  // `items` = elements de la liste ACTIVE (propriete non enumerable : elle
  // n'est pas ecrite dans le stockage). Le moteur de lecture n'a pas change.
  function equiper(r) {
    Object.defineProperty(r, 'items', {
      configurable: true, enumerable: false,
      get: function () { return listeActive(r).items; },
      set: function (v) { listeActive(r).items = v; }
    });
    r.positions = r.positions || {};
    return r;
  }
  function lire() {
    try { var s = localStorage.getItem(CLE); if (s) return equiper(migrer(JSON.parse(s))); }
    catch (e) { stockageOk = false; }
    return memoire ? equiper(JSON.parse(JSON.stringify(memoire))) : equiper(migrer(null));
  }
  function sauver() {
    memoire = JSON.parse(JSON.stringify(liste));
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
          if (jouer) yt.loadVideoById({ videoId: item.src, startSeconds: depart });
          else yt.cueVideoById({ videoId: item.src, startSeconds: depart });
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
    // Element en cours hors de la liste active (on a change de liste pendant
    // la lecture) : on enchaine sur le debut de la liste active.
    if (i < 0 && liste.items.length) preparer(liste.items[0], true);
    else if (i >= 0 && i < liste.items.length - 1) preparer(liste.items[i + 1], true);
    else { message('Fin de la liste. Ajoute d\'autres épisodes depuis l\'annuaire !'); rendreListe(); majBouton(); }
  }
  function voisin(d) {
    if (!courant) return;
    var i = index(courant.id) + d;
    if (i >= 0 && i < liste.items.length) preparer(liste.items[i], true);
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
  function rendreListes() {
    var sel = $('ecl-choix'); sel.textContent = '';
    liste.listes.forEach(function (l) {
      var o = el('option', { value: l.id, texte: l.nom + ' (' + l.items.length + ')' });
      if (l.id === liste.active) o.selected = true;
      sel.appendChild(o);
    });
    $('ecl-supprimer').disabled = liste.listes.length < 2;
    $('ecl-partager').disabled = liste.items.length === 0;
  }
  function rendreListe() {
    rendreListes();
    var ol = $('ecl-liste'); ol.textContent = '';
    var n = liste.items.length;
    $('ecl-nombre').textContent = n ? '(' + n + ')' : '';
    $('ecl-vide').hidden = n > 0;
    $('ecl-ecoutes').hidden = $('ecl-vider').hidden = n === 0;
    if (!n && !courant) { $('ecl-lecteur').hidden = true; }
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

  /* ---------- plusieurs listes ---------- */
  function nomLibre(nom) {
    var base = String(nom || 'Ma liste').trim().slice(0, 60) || 'Ma liste', n = base, k = 2;
    while (liste.listes.some(function (l) { return l.nom === n; })) n = base + ' (' + (k++) + ')';
    return n;
  }
  function nouvelleListe(nom, items) {
    var l = { id: 'l' + Date.now().toString(36) + Math.floor(Math.random() * 1e4).toString(36),
              nom: nomLibre(nom), items: items || [] };
    liste.listes.push(l); liste.active = l.id; sauver(); rendreListe();
    return l;
  }

  /* ---------- partage par lien ---------- */
  function b64url(octets) {
    var s = '', pas = 0x8000;
    for (var i = 0; i < octets.length; i += pas) s += String.fromCharCode.apply(null, octets.subarray(i, i + pas));
    return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }
  function deb64url(s) {
    s = s.replace(/-/g, '+').replace(/_/g, '/'); while (s.length % 4) s += '=';
    var b = atob(s), o = new Uint8Array(b.length);
    for (var i = 0; i < b.length; i++) o[i] = b.charCodeAt(i);
    return o;
  }
  function flux(octets, transfo) {
    return new Response(new Blob([octets]).stream().pipeThrough(transfo)).arrayBuffer()
      .then(function (b) { return new Uint8Array(b); });
  }
  function encoder(l) {
    var p = { n: l.nom, i: l.items.slice(0, MAX_PARTAGE).map(function (x) {
      return [x.type === 'youtube' ? 'y' : 'a', x.src, x.titre, x.emission, x.lien || '', x.image || '', x.duree || 0, x.id];
    }) };
    var octets = new TextEncoder().encode(JSON.stringify(p));
    if (window.CompressionStream) {
      return flux(octets, new CompressionStream('deflate-raw')).then(function (c) { return '1' + b64url(c); });
    }
    return Promise.resolve('0' + b64url(octets));
  }
  function decoder(code) {
    var brut = deb64url(code.slice(1));
    var p = code[0] === '1'
      ? (window.DecompressionStream ? flux(brut, new DecompressionStream('deflate-raw'))
                                    : Promise.reject(new Error('navigateur')))
      : Promise.resolve(brut);
    return p.then(function (o) { return JSON.parse(new TextDecoder('utf-8').decode(o)); });
  }
  // Un lien peut avoir ete fabrique par n'importe qui : on ne garde que ce
  // qui est sain, et on le montre avant de l'ajouter.
  function texte(v, max) { return typeof v === 'string' ? v.replace(/[\u0000-\u001f]/g, ' ').trim().slice(0, max) : ''; }
  function valider(p) {
    if (!p || !Array.isArray(p.i)) return null;
    var items = [], vus = {};
    p.i.slice(0, MAX_PARTAGE).forEach(function (x) {
      if (!Array.isArray(x)) return;
      var type = x[0] === 'y' ? 'youtube' : x[0] === 'a' ? 'audio' : null;
      var src = typeof x[1] === 'string' ? x[1].trim() : '';
      if (type === 'audio' && !(/^https:\/\/[^\s"'<>]+$/.test(src) && src.length <= 1000)) return;
      if (type === 'youtube' && !/^[\w-]{11}$/.test(src)) return;
      if (!type) return;
      var id = typeof x[7] === 'string' && /^[0-9a-z]{6,16}$/.test(x[7]) ? x[7] : null;
      if (!id || vus[id]) return;
      vus[id] = 1;
      var lien = typeof x[4] === 'string' && /^\/(fiches|episodes)\/[\w.-]+\.html$/.test(x[4]) ? x[4] : '';
      var image = typeof x[5] === 'string' && /^https:\/\/[^\s"'<>]+$/.test(x[5]) && x[5].length <= 500 ? x[5] : '';
      var d = parseInt(x[6], 10);
      items.push({ id: id, type: type, src: src, titre: texte(x[2], 200) || 'Épisode sans titre',
                   emission: texte(x[3], 120), lien: lien, image: image, date: '',
                   duree: d > 0 && d < 86400 ? d : null });
    });
    return items.length ? { nom: texte(p.n, 60) || 'Liste partagée', items: items } : null;
  }
  function partager() {
    var l = listeActive(liste), retour = $('ecl-partage-retour');
    if (!l.items.length) return;
    encoder(l).then(function (code) {
      var url = location.origin + '/ecouter.html#l=' + code;
      var txt = '🎧 « ' + l.nom + ' » : ' + l.items.length + ' épisode' + (l.items.length > 1 ? 's' : '') +
        ' à écouter sur MediaCritic';
      var mobile = window.matchMedia && window.matchMedia('(pointer:coarse)').matches;
      if (navigator.share && mobile) {
        navigator.share({ title: l.nom, text: txt, url: url }).catch(function () {});
      } else if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(txt + '\n' + url).then(function () {
          retour.textContent = 'Lien copié ! Colle-le où tu veux.';
        }, function () { retour.textContent = url; });
      } else retour.textContent = url;
      if (l.items.length > MAX_PARTAGE) retour.textContent += ' (les ' + MAX_PARTAGE + ' premiers épisodes)';
      try { if (window.gtag) window.gtag('event', 'liste_partager', { nombre: l.items.length }); } catch (e) {}
    }, function () { retour.textContent = 'Partage impossible depuis ce navigateur.'; });
  }
  function importer() {
    var m = /^#l=([01][\w-]+)$/.exec(location.hash || '');
    var zone = $('ecl-import');
    if (!m) { zone.hidden = true; return; }
    decoder(m[1]).then(valider).then(function (l) {
      zone.textContent = '';
      if (!l) { zone.appendChild(el('p', { texte: 'Ce lien de liste est vide ou abîmé.' })); zone.hidden = false; return; }
      zone.appendChild(el('h2', { id: 'ecl-import-titre', texte: '📥 Une liste t\'a été partagée' }));
      zone.appendChild(el('p', { classe: 'ecl-import-nom', texte: '« ' + l.nom + ' » · ' + l.items.length + ' épisode' + (l.items.length > 1 ? 's' : '') }));
      var ul = el('ul', { classe: 'ecl-import-liste' });
      l.items.slice(0, 6).forEach(function (x) { ul.appendChild(el('li', { texte: x.titre + (x.emission ? ' — ' + x.emission : '') })); });
      if (l.items.length > 6) ul.appendChild(el('li', { texte: '… et ' + (l.items.length - 6) + ' autre(s)' }));
      zone.appendChild(ul);
      var oui = el('button', { type: 'button', classe: 'ecl-btn ecl-btn-plein ecl-btn-txt', texte: 'Ajouter à mes listes' });
      var non = el('button', { type: 'button', classe: 'ecl-btn ecl-btn-txt', texte: 'Ignorer' });
      function fermer() { zone.hidden = true; try { history.replaceState(null, '', location.pathname); } catch (e) {} }
      oui.addEventListener('click', function () {
        var nl = nouvelleListe(l.nom, l.items);
        fermer();
        message('Liste « ' + nl.nom + ' » ajoutée. Appuie sur ▶ pour l\'écouter.');
        if (!courant && liste.items.length) preparer(liste.items[0], false);
        try { if (window.gtag) window.gtag('event', 'liste_importer', { nombre: l.items.length }); } catch (e) {}
      });
      non.addEventListener('click', fermer);
      zone.appendChild(el('div', { classe: 'ecl-import-actions' }, [oui, non]));
      zone.appendChild(el('p', { classe: 'ecl-note', texte: 'Les podcasts sont lus depuis le fichier publié par leur auteur, les vidéos dans le lecteur officiel de YouTube.' }));
      zone.hidden = false;
      oui.focus();
    }, function (e) {
      zone.textContent = '';
      zone.appendChild(el('p', { texte: e && e.message === 'navigateur'
        ? 'Ton navigateur est trop ancien pour ouvrir ce lien de liste.' : 'Ce lien de liste est abîmé.' }));
      zone.hidden = false;
    });
  }

  /* ---------- synchronisation avec les autres onglets ---------- */
  function relire() {
    var nouv = lire();
    var pos = Object.assign({}, nouv.positions, liste.positions);
    liste.listes = nouv.listes; liste.active = nouv.active; liste.positions = pos;
    liste.ecoutes = Object.assign({}, nouv.ecoutes, liste.ecoutes);
    var a = nouv.aJouer;
    if (a) { delete liste.aJouer; sauver(); }
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
      if (!confirm('Vider la liste « ' + listeActive(liste).nom + ' » ?')) return;
      if (courant && index(courant.id) >= 0) { pause(); courant = null; liste.courant = null; }
      liste.items = []; sauver(); rendreListe();
    });
    $('ecl-ecoutes').addEventListener('click', function () {
      var e = liste.ecoutes || {};
      liste.items = liste.items.filter(function (x) { return !e[x.id] || (courant && x.id === courant.id); });
      sauver(); rendreListe();
    });
    $('ecl-choix').addEventListener('change', function () { liste.active = this.value; sauver(); rendreListe(); });
    $('ecl-nouvelle').addEventListener('click', function () {
      var nom = prompt('Nom de la nouvelle liste :', 'Liste ' + (liste.listes.length + 1));
      if (nom === null) return;
      nouvelleListe(nom, []);
      message('Nouvelle liste active : les ▶ et + du site l\'alimentent désormais.');
    });
    $('ecl-renommer').addEventListener('click', function () {
      var l = listeActive(liste), nom = prompt('Nouveau nom de la liste :', l.nom);
      if (nom === null || !nom.trim()) return;
      l.nom = nom.trim().slice(0, 60); sauver(); rendreListe();
    });
    $('ecl-supprimer').addEventListener('click', function () {
      if (liste.listes.length < 2) return;
      var l = listeActive(liste);
      if (!confirm('Supprimer la liste « ' + l.nom + ' » ? Cette action est définitive.')) return;
      if (courant && l.items.some(function (x) { return x.id === courant.id; })) { pause(); courant = null; liste.courant = null; }
      liste.listes = liste.listes.filter(function (x) { return x.id !== l.id; });
      liste.active = liste.listes[0].id; sauver(); rendreListe();
    });
    $('ecl-partager').addEventListener('click', partager);

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
    window.addEventListener('hashchange', importer);
    try {
      var c = new BroadcastChannel('mc-lecteur');
      c.onmessage = function (m) { if (m.data && m.data.jouer) setTimeout(relire, 50); };
    } catch (e) {}
    importer();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
