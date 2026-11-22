/* Ma liste d'ecoute — boutons « ▶ / + » des pages du site.
 * Etape 1 (21/11/2026) : une liste. Etape 2 : plusieurs listes nommees ; la
 * liste ACTIVE recoit les ajouts. Stockage : localStorage « mc-liste-v1 »
 * (nom de cle conserve), format v2, protege par try/catch.
 * Le lecteur est /ecouter.html, ouvert dans UN onglet nomme « mc-lecteur » :
 * changer de page sur le site ne coupe donc pas le son.
 * Donnees des episodes : blocs <script type="application/json"
 * class="mc-ecoute-data"> (jamais de texte tiers dans un attribut). */
(function () {
  'use strict';
  // Charge sur TOUTES les pages par l'en-tete commun (charte.py) et parfois
  // aussi par la page elle-meme : une seule execution.
  if (window.MCListe) return;
  var CLE = 'mc-liste-v1';
  var memoire = null;

  /* v1 {items,…} -> v2 {listes:[{id,nom,items}], active,…}. DOIT rester
   * identique a migrer() de assets/ecouter.js. */
  function migrer(l) {
    if (!l || typeof l !== 'object') l = {};
    if (l.v === 2 && Array.isArray(l.listes) && l.listes.length) return l;
    return { v: 2, listes: [{ id: 'l1', nom: 'Ma liste', items: Array.isArray(l.items) ? l.items : [] }],
             active: 'l1', courant: l.courant || null, positions: l.positions || {},
             vitesse: l.vitesse || 1, ecoutes: l.ecoutes || {}, aJouer: l.aJouer };
  }
  function lire() {
    try { var s = localStorage.getItem(CLE); if (s) return migrer(JSON.parse(s)); } catch (e) {}
    return memoire || migrer(null);
  }
  function ecrire(l) {
    memoire = l;
    try { localStorage.setItem(CLE, JSON.stringify(l)); return true; } catch (e) { return false; }
  }
  function active(l) {
    return l.listes.find(function (x) { return x.id === l.active; }) || l.listes[0];
  }
  function catalogue() {
    var tout = {};
    document.querySelectorAll('script.mc-ecoute-data').forEach(function (s) {
      try { var o = JSON.parse(s.textContent); for (var k in o) tout[k] = o[k]; } catch (e) {}
    });
    return tout;
  }

  function toast(texte) {
    var t = document.getElementById('mc-toast');
    if (!t) {
      t = document.createElement('div'); t.id = 'mc-toast'; t.className = 'mc-toast';
      t.setAttribute('role', 'status'); t.setAttribute('aria-live', 'polite');
      document.body.appendChild(t);
    }
    t.textContent = texte; t.classList.add('mc-toast-on');
    clearTimeout(t._h); t._h = setTimeout(function () { t.classList.remove('mc-toast-on'); }, 2200);
  }

  function pastille() {
    if (document.getElementById('ecl')) return;            // pas sur le lecteur lui-meme
    var l = lire(), a = active(l), n = a.items.length, p = document.getElementById('mc-liste-pill');
    if (!n) { if (p) p.hidden = true; return; }
    if (!p) {
      p = document.createElement('button'); p.type = 'button'; p.id = 'mc-liste-pill'; p.className = 'mc-liste-pill';
      p.addEventListener('click', function () { ouvrirLecteur(null); });
      document.body.appendChild(p);
    }
    p.hidden = false;
    p.textContent = '🎧 ' + a.nom + ' (' + n + ')';
    p.setAttribute('aria-label', 'Ouvrir la liste d\'écoute « ' + a.nom + ' », ' + n + ' élément' + (n > 1 ? 's' : ''));
  }

  function ajouter(item, enTete) {
    var l = lire(), a = active(l);
    // Meme episode sous deux identifiants (fiche / API Apple) : on compare aussi la source.
    var deja = a.items.findIndex(function (x) { return x.id === item.id || (x.src && x.src === item.src); });
    if (deja >= 0) {
      if (!enTete) return 'deja';
      a.items.splice(deja, 1);
    }
    // « Ecouter » : juste apres l'element en cours ; « + » : en fin de liste.
    if (enTete) {
      var i = a.items.findIndex(function (x) { return x.id === l.courant; });
      a.items.splice(i >= 0 ? i + 1 : 0, 0, item);
    } else a.items.push(item);
    ecrire(l);
    pastille();
    return 'ok';
  }

  function ouvrirLecteur(id) {
    var l = lire();
    if (id) { l.aJouer = id; ecrire(l); }
    try { var c = new BroadcastChannel('mc-lecteur'); if (id) c.postMessage({ jouer: id }); c.close(); } catch (e) {}
    // window.open('', nom) retrouve l'onglet du lecteur s'il est deja ouvert
    // (sans le recharger : la lecture en cours n'est pas coupee).
    var w = null;
    try { w = window.open('', 'mc-lecteur'); } catch (e) {}
    if (!w) { location.href = '/ecouter.html'; return; }
    try {
      if (!w.location.href || w.location.href === 'about:blank') w.location.href = '/ecouter.html';
    } catch (e) { w.location.href = '/ecouter.html'; }
    try { w.focus(); } catch (e) {}
  }

  function nomActif() { return active(lire()).nom; }

  function clic(e) {
    var b = e.target.closest('[data-mc-ec]');
    if (!b) return;
    var item = catalogue()[b.getAttribute('data-mc-ec')];
    if (!item) return;
    if (b.classList.contains('mc-ec-play')) {
      ajouter(item, true);
      ouvrirLecteur(item.id);
      try { if (window.gtag) window.gtag('event', 'ecoute_lancer', { type: item.type }); } catch (x) {}
    } else {
      var r = ajouter(item, false);
      toast(r === 'deja' ? 'Déjà dans « ' + nomActif() + ' »' : 'Ajouté à « ' + nomActif() + ' » 🎧');
      try { if (window.gtag) window.gtag('event', 'ecoute_ajouter', { type: item.type }); } catch (x) {}
    }
  }

  /* ---------- « + » sur TOUTE carte de contenu du site (22/11/2026) ----------
   * Lien vers une fiche (fiches/slug.html) ou vers une critique MediaCritic
   * (episodes/page.html) portant une image : on y greffe un bouton « + » qui
   * ajoute le DERNIER episode lisible. Resolution au clic seulement :
   *   critique MC -> /data/ecoute-mc.json (patch_ecoute_episodes.py) ;
   *   fiche -> /data/content/slug.json (episodes_recents, videos), sinon API
   *   publique d'Apple (trackId) ; rien de lisible -> message, pas d'ajout. */
  function cyrb(s) {
    var h1 = 0xdeadbeef, h2 = 0x41c6ce57;
    for (var i = 0, c; i < s.length; i++) { c = s.charCodeAt(i); h1 = Math.imul(h1 ^ c, 2654435761); h2 = Math.imul(h2 ^ c, 1597334677); }
    h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
    h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
    return (4294967296 * (2097151 & h2) + (h1 >>> 0)).toString(16);
  }
  var RE_FICHE = /(?:^|\/)fiches\/([a-z0-9][a-z0-9-]*)\.html(?:[?#].*)?$/;
  var RE_EP = /(?:^|\/)episodes\/([a-z0-9][a-z0-9-]*\.html)(?:[?#].*)?$/;
  var EXCLU = 'header,footer,nav,.mch,.mcf,.mcj,.ecl,#mys,.mc-ec,.ep-list,.ep-tous,.ep-nav,.bd-apercu';
  var cacheMC = null;
  function jsonDe(url) {
    return fetch(url, { cache: 'no-cache' }).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); });
  }
  function texte(s) { return typeof s === 'string' ? s : ''; }
  function depuisFiche(slug) {
    return jsonDe('/data/content/' + slug + '.json').then(function (d) {
      var base = { emission: texte(d.title), lien: '/fiches/' + slug + '.html',
                   image: /^https:\/\//.test(d.image || '') ? d.image : '' };
      function fait(type, src, titre, date, duree) {
        return { id: cyrb(src), type: type, src: src, titre: texte(titre), emission: base.emission,
                 lien: base.lien, image: base.image, date: texte(date), duree: typeof duree === 'number' ? duree : null };
      }
      var eps = (d.episodes_recents || []).slice().sort(function (a, b) { return (a.date || '') < (b.date || '') ? 1 : -1; });
      for (var i = 0; i < eps.length; i++) {
        if (/^https:\/\//.test(eps[i].audio || '')) return fait('audio', eps[i].audio, eps[i].titre, eps[i].date, eps[i].duree);
        if (/^[\w-]{11}$/.test(eps[i].video || '')) return fait('youtube', eps[i].video, eps[i].titre, eps[i].date, null);
      }
      var vids = d.videos || [];
      for (var j = 0; j < vids.length; j++) if (/^[\w-]{11}$/.test(vids[j].video || '')) return fait('youtube', vids[j].video, vids[j].titre, vids[j].date, null);
      var tid = ((d.platforms || {}).apple || {}).trackId;
      if (!tid) return null;
      return jsonDe('https://itunes.apple.com/lookup?id=' + encodeURIComponent(tid) + '&country=fr&entity=podcastEpisode&limit=10').then(function (j) {
        var r = (j.results || []).filter(function (x) { return x.wrapperType === 'podcastEpisode' && /^https:\/\//.test(x.episodeUrl || ''); })
          .sort(function (a, b) { return (a.releaseDate || '') < (b.releaseDate || '') ? 1 : -1; })[0];
        return r ? fait('audio', r.episodeUrl, r.trackName, (r.releaseDate || '').slice(0, 10),
                        r.trackTimeMillis ? Math.round(r.trackTimeMillis / 1000) : null) : null;
      });
    });
  }
  function depuisCritique(page) {
    cacheMC = cacheMC || jsonDe('/data/ecoute-mc.json');
    return cacheMC.then(function (t) { return t[page] || null; });
  }
  function nomCarte(a) {
    var t = a.querySelector('.card-title,.cl-titre,.top-titre,.sim-title,.c-title,h2,h3');
    var img = a.querySelector('img');
    return ((t && t.textContent) || (img && img.alt) || a.getAttribute('aria-label') || '').trim();
  }
  function equiperCarte(a) {
    if (a.hasAttribute('data-mc-plus')) return;
    a.setAttribute('data-mc-plus', '');
    // URL resolue : les fiches se lient entre elles en relatif (« autre.html »).
    var href = '';
    try { var u = new URL(a.href, location.href); if (u.origin === location.origin) href = u.pathname; } catch (x) {}
    var m = href.match(RE_FICHE), e = m ? null : href.match(RE_EP);
    if (!(m || e) || a.closest(EXCLU)) return;
    var img = a.querySelector('img,.card-cover-ph,.card-cover-placeholder');
    if (!img) return;
    var nom = nomCarte(a);
    var b = document.createElement('button');
    b.type = 'button'; b.className = 'mc-ec-carte'; b.textContent = '+';
    b.setAttribute(m ? 'data-mc-fiche' : 'data-mc-critique', m ? m[1] : e[1]);
    b.setAttribute('aria-label', (m ? 'Ajouter le dernier épisode de ' : 'Ajouter notre critique de ') + (nom || 'ce contenu') + ' à ma liste d\'écoute');
    b.title = m ? 'Ajouter le dernier épisode à ma liste' : 'Ajouter notre épisode à ma liste';
    // Petite vignette (lignes de classement) : bouton a cote du lien ;
    // grande vignette (cartes) : bouton pose dans le coin de l'image.
    var hote = img.parentElement === a ? a : img.parentElement;
    var petit = (img.getBoundingClientRect().width || img.width || 0) < 90;
    if (petit) {
      // Ligne de classement : jamais en surimpression (elle masquerait la note,
      // palmares). Dans un <li> : apres le lien ; ligne en flex : en fin de ligne.
      b.classList.add('mc-ec-carte-ligne');
      var flex = /flex/.test(getComputedStyle(a).display);
      if (a.parentElement && a.parentElement.tagName === 'LI') a.insertAdjacentElement('afterend', b);
      else if (flex) a.appendChild(b);
      else a.insertAdjacentElement('afterend', b);
    } else {
      hote.classList.add('mc-ec-hote');
      // Image posee directement dans la carte : coin haut droit (le bas porte le texte).
      if (hote === a) b.classList.add('mc-ec-carte-coin');
      hote.appendChild(b);
    }
  }
  function balayer(racine) {
    if (document.getElementById('ecl')) return;            // lecteur : rien a greffer
    (racine.querySelectorAll ? racine : document).querySelectorAll('a[href]').forEach(equiperCarte);
  }
  function clicCarte(ev) {
    var b = ev.target.closest && ev.target.closest('.mc-ec-carte');
    if (!b) return;
    ev.preventDefault(); ev.stopPropagation();
    if (b.getAttribute('aria-busy') === 'true') return;
    b.setAttribute('aria-busy', 'true'); b.textContent = '…';
    var slug = b.getAttribute('data-mc-fiche'), page = b.getAttribute('data-mc-critique');
    (slug ? depuisFiche(slug) : depuisCritique(page)).then(function (item) {
      if (!item) { toast('Pas encore d\'épisode lisible ici : ouvre la fiche pour l\'écouter sur ta plateforme.'); b.textContent = '+'; return; }
      var r = ajouter(item, false);
      toast(r === 'deja' ? 'Déjà dans « ' + nomActif() + ' »' : 'Ajouté à « ' + nomActif() + ' » 🎧 ' + (item.titre ? '· ' + item.titre.slice(0, 60) : ''));
      b.textContent = '✓';
      setTimeout(function () { b.textContent = '+'; }, 2500);
      try { if (window.gtag) window.gtag('event', 'ecoute_ajouter', { type: item.type, depuis: 'carte' }); } catch (x) {}
    }, function () {
      toast('Impossible de récupérer l\'épisode. Vérifie ta connexion et réessaie.'); b.textContent = '+';
    }).then(function () { b.removeAttribute('aria-busy'); });
  }

  document.addEventListener('click', clicCarte, true);
  document.addEventListener('click', clic);
  window.addEventListener('storage', function (e) { if (e.key === CLE) pastille(); });
  function demarrer() {
    pastille();
    balayer(document);
    // Grilles construites en JS (accueil, annuaire, comparateur) et « afficher plus ».
    try {
      new MutationObserver(function (ms) {
        ms.forEach(function (m) { m.addedNodes.forEach(function (n) {
          if (n.nodeType !== 1) return;
          if (n.matches && n.matches('a[href]')) equiperCarte(n); else balayer(n);
        }); });
      }).observe(document.body, { childList: true, subtree: true });
    } catch (e) {}
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', demarrer); else demarrer();
  // Pages qui construisent leurs boutons en JS (Mystere du Jour, tous les episodes).
  window.MCListe = {
    ajouter: function (item) { return ajouter(item, false); },
    ecouter: function (item) { ajouter(item, true); ouvrirLecteur(item.id); },
    toast: toast,
    nomActif: nomActif
  };
})();
