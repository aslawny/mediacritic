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
    var deja = a.items.findIndex(function (x) { return x.id === item.id; });
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

  document.addEventListener('click', clic);
  window.addEventListener('storage', function (e) { if (e.key === CLE) pastille(); });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', pastille); else pastille();
  // Pages qui construisent leurs boutons en JS (Mystere du Jour, tous les episodes).
  window.MCListe = {
    ajouter: function (item) { return ajouter(item, false); },
    ecouter: function (item) { ajouter(item, true); ouvrirLecteur(item.id); },
    toast: toast,
    nomActif: nomActif
  };
})();
