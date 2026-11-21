/* Ma liste d'ecoute — boutons « ▶ / + » des pages du site (21/11/2026).
 * La liste vit dans localStorage (cle mc-liste-v1), protegee par try/catch.
 * Le lecteur est la page /ecouter.html, ouverte dans UN onglet nomme
 * « mc-lecteur » : changer de page sur le site ne coupe donc pas le son.
 * Donnees des episodes : blocs <script type="application/json"
 * class="mc-ecoute-data"> (jamais de texte tiers dans un attribut). */
(function () {
  'use strict';
  var CLE = 'mc-liste-v1';
  var memoire = null;

  function lire() {
    try { var s = localStorage.getItem(CLE); if (s) return JSON.parse(s); } catch (e) {}
    return memoire || { v: 1, items: [], courant: null, positions: {}, vitesse: 1 };
  }
  function ecrire(l) {
    memoire = l;
    try { localStorage.setItem(CLE, JSON.stringify(l)); return true; } catch (e) { return false; }
  }
  function catalogue() {
    var tout = {};
    document.querySelectorAll('script.mc-ecoute-data').forEach(function (s) {
      try { var o = JSON.parse(s.textContent); for (var k in o) tout[k] = o[k]; } catch (e) {}
    });
    return tout;
  }
  function canal() {
    try { return new BroadcastChannel('mc-lecteur'); } catch (e) { return null; }
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
    var l = lire(), n = l.items.length, p = document.getElementById('mc-liste-pill');
    if (!n) { if (p) p.hidden = true; return; }
    if (!p) {
      p = document.createElement('button'); p.type = 'button'; p.id = 'mc-liste-pill'; p.className = 'mc-liste-pill';
      p.addEventListener('click', function () { ouvrirLecteur(null); });
      document.body.appendChild(p);
    }
    p.hidden = false;
    p.textContent = '🎧 Ma liste (' + n + ')';
    p.setAttribute('aria-label', 'Ouvrir ma liste d\'écoute, ' + n + ' élément' + (n > 1 ? 's' : ''));
  }

  function ajouter(item, enTete) {
    var l = lire();
    var deja = l.items.findIndex(function (x) { return x.id === item.id; });
    if (deja >= 0) {
      if (!enTete) return 'deja';
      l.items.splice(deja, 1);
    }
    // « Ecouter » : juste apres l'element en cours ; « + » : en fin de liste.
    if (enTete) {
      var i = l.items.findIndex(function (x) { return x.id === l.courant; });
      l.items.splice(i >= 0 ? i + 1 : 0, 0, item);
    } else l.items.push(item);
    ecrire(l);
    pastille();
    return 'ok';
  }

  function ouvrirLecteur(id) {
    var l = lire();
    if (id) { l.aJouer = id; ecrire(l); }
    var c = canal();
    if (c && id) { c.postMessage({ jouer: id }); c.close(); }
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
      toast(r === 'deja' ? 'Déjà dans ta liste' : 'Ajouté à ta liste 🎧');
      try { if (window.gtag) window.gtag('event', 'ecoute_ajouter', { type: item.type }); } catch (x) {}
    }
  }

  document.addEventListener('click', clic);
  window.addEventListener('storage', function (e) { if (e.key === CLE) pastille(); });
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', pastille); else pastille();
  // Pour les pages qui construisent leurs boutons en JS (Le Mystere du Jour).
  window.MCListe = { ajouter: function (item) { return ajouter(item, false); },
                     ecouter: function (item) { ajouter(item, true); ouvrirLecteur(item.id); },
                     toast: toast };
})();
