/* Langue du site (23/11/2026) : Français / English, choisie dans l'en-tête.
 * Chargé sur TOUTES les pages par l'en-tête commun (scripts/charte.py).
 * Choix : ?lang=en|fr (lien partageable), sinon localStorage « mc-langue-site »,
 * sinon français. En anglais : dictionnaire /i18n/en.json (textes exacts +
 * règles pour les textes variables), appliqué aux nœuds texte et aux
 * attributs (placeholder, aria-label, title), puis aux contenus ajoutés en JS.
 * Jamais traduit : noms d'émissions et d'auteurs, descriptions d'éditeurs
 * (elles restent dans leur langue d'origine), tout élément [data-i18n-non].
 * Sans JavaScript, ou si le dictionnaire ne charge pas : le français reste. */
(function () {
  'use strict';
  if (window.MCLangue) return;
  var CLE = 'mc-langue-site';
  var LANGUES = {
    fr: { nom: 'Français', drapeau: '/assets/drapeaux/fr.svg' },
    en: { nom: 'English', drapeau: '/assets/drapeaux/gb.svg' }
  };
  var NE_PAS = 'script,style,noscript,textarea,code,pre,[data-i18n-non],[data-i18n-fait],.card-title,.card-author,' +
    '.sim-title,.sim-author,.cl-titre,.cl-auteur,.top-titre,.top-auteur,.rank-title,.mcj-titre,' +
    '.ep-titre,.fiche-desc,.mys-essais,.ecl-titre,.ecl-emission,.mch-lang';

  function lireChoix() {
    try {
      var m = location.search.match(/[?&]lang=(fr|en)\b/);
      if (m) { localStorage.setItem(CLE, m[1]); return m[1]; }
      var s = localStorage.getItem(CLE);
      if (s && LANGUES[s]) return s;
    } catch (e) {}
    return 'fr';
  }
  var langue = lireChoix();

  function montrer() { document.documentElement.classList.remove('mc-i18n'); }

  /* ---------- sélecteur de l'en-tête ---------- */
  function selecteur() {
    var hote = document.getElementById('mch-lang');
    if (!hote || hote.firstChild) return;
    var actuelle = LANGUES[langue];
    var bouton = document.createElement('button');
    bouton.type = 'button'; bouton.className = 'mch-lang-btn';
    bouton.setAttribute('aria-haspopup', 'listbox'); bouton.setAttribute('aria-expanded', 'false');
    bouton.setAttribute('aria-label', langue === 'en' ? 'Language: English' : 'Langue : Français');
    bouton.innerHTML = '<img src="' + actuelle.drapeau + '" alt="" width="20" height="14" />' +
      '<span class="mch-lang-nom">' + actuelle.nom + '</span><span aria-hidden="true">▾</span>';
    var liste = document.createElement('ul');
    liste.className = 'mch-lang-menu'; liste.setAttribute('role', 'listbox'); liste.hidden = true;
    liste.setAttribute('aria-label', langue === 'en' ? 'Choose the language' : 'Choisir la langue');
    Object.keys(LANGUES).forEach(function (code) {
      var li = document.createElement('li');
      li.setAttribute('role', 'option'); li.tabIndex = -1; li.dataset.code = code;
      li.setAttribute('aria-selected', code === langue ? 'true' : 'false');
      li.setAttribute('lang', code);
      li.innerHTML = '<img src="' + LANGUES[code].drapeau + '" alt="" width="20" height="14" /><span>' + LANGUES[code].nom + '</span>';
      liste.appendChild(li);
    });
    function fermer() { liste.hidden = true; bouton.setAttribute('aria-expanded', 'false'); }
    function choisir(code) {
      fermer();
      if (code === langue) return;
      try { localStorage.setItem(CLE, code); } catch (e) {}
      try { if (window.gtag) window.gtag('event', 'langue_site', { langue: code }); } catch (e) {}
      // ?lang= retiré : le choix vaut pour toute la navigation.
      var u = location.href.replace(/([?&])lang=(fr|en)(&|$)/, function (m, a, b, c) { return c ? a : ''; });
      if (u === location.href) location.reload(); else location.href = u;
    }
    bouton.addEventListener('click', function () {
      var ouvrir = liste.hidden;
      liste.hidden = !ouvrir; bouton.setAttribute('aria-expanded', ouvrir ? 'true' : 'false');
      if (ouvrir) { var sel = liste.querySelector('[aria-selected="true"]'); if (sel) sel.focus(); }
    });
    liste.addEventListener('click', function (e) { var li = e.target.closest('[data-code]'); if (li) choisir(li.dataset.code); });
    liste.addEventListener('keydown', function (e) {
      var items = [].slice.call(liste.children), i = items.indexOf(document.activeElement);
      if (e.key === 'ArrowDown') { e.preventDefault(); items[Math.min(i + 1, items.length - 1)].focus(); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); items[Math.max(i - 1, 0)].focus(); }
      else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); if (i >= 0) choisir(items[i].dataset.code); }
      else if (e.key === 'Escape') { fermer(); bouton.focus(); }
    });
    document.addEventListener('click', function (e) { if (!hote.contains(e.target)) fermer(); });
    hote.appendChild(bouton); hote.appendChild(liste);
  }

  /* ---------- traduction ---------- */
  var dico = null, regles = [], cats = {}, blocs = {};
  var BLOCS = 'p,li,h1,h2,h3,h4,blockquote,td,dd,dt,figcaption,summary';
  function cleBloc(el) { return (el.textContent || '').replace(/\s+/g, ' ').trim(); }
  // Textes editoriaux (livraison B) : un paragraphe entier remplace par sa
  // version anglaise, liens et mise en forme compris. Cle = texte francais.
  function appliquerBlocs(racine) {
    if (!blocs || !racine.querySelectorAll) return;
    var els = [].slice.call(racine.querySelectorAll(BLOCS));
    if (racine.matches && racine.matches(BLOCS)) els.unshift(racine);
    els.forEach(function (el) {
      if (el.hasAttribute('data-i18n-fait') || el.closest('[data-i18n-non]')) return;
      var en = blocs[cleBloc(el)];
      if (en != null) { el.innerHTML = en; el.setAttribute('data-i18n-fait', ''); }
    });
  }
  function traduire(s) {
    if (!s) return null;
    var t = s.replace(/\s+/g, ' ').trim();
    if (!t || !/[A-Za-zÀ-ÿ]/.test(t)) return null;
    var r = dico[t];
    if (r == null) {
      for (var i = 0; i < regles.length; i++) {
        var m = t.match(regles[i][0]);
        if (m) {
          r = regles[i][1].replace(/\$(\d)|\{(\w+):(\d)\}/g, function (x, n, fn, k) {
            if (n) return m[+n] || '';
            var v = m[+k] || '';
            if (fn === 'cat') return cats[v.toLowerCase()] || v;
            if (fn === 'tr') return dico[v] || v;
            if (fn === 'date') return dateEn(v);
            return v;
          });
          break;
        }
      }
    }
    // Etiquette de categorie seule (filtres, vignettes) : « histoire » -> « history ».
    if (r == null && t === t.toLowerCase() && cats[t]) r = cats[t];
    if (r == null) return null;
    var avant = s.match(/^\s*/)[0], apres = s.match(/\s*$/)[0];
    return avant + r + apres;
  }
  // « 20 novembre » / « 1er novembre 2026 » -> « November 20 » / « November 1, 2026 ».
  function dateEn(v) {
    var m = String(v).match(/^(\d{1,2}|1er) (\S+)(?: (\d{4}))?$/);
    if (!m || !dico[m[2]]) return v;
    return dico[m[2]] + ' ' + (m[1] === '1er' ? '1' : m[1]) + (m[3] ? ', ' + m[3] : '');
  }
  /* Textes rediges a partir de modeles (podcast du jour, indices du Mystere) :
   * regles de paragraphe, sinon phrase par phrase. Une phrase sans regle
   * (description d'editeur, titre cite) reste dans sa langue d'origine. */
  var PHRASES = '.mcj-s-p,.mcj-pourquoi,.mys-indice-texte';
  var reglesPara = [], reglesPhrase = [];
  function appliquerRegles(t, liste) {
    for (var i = 0; i < liste.length; i++) {
      var m = t.match(liste[i][0]);
      if (m) return liste[i][1].replace(/\$(\d)|\{(\w+):(\d)\}/g, function (x, n, fn, k) {
        if (n) return m[+n] || '';
        var v = m[+k] || '';
        if (fn === 'cat') return cats[v.toLowerCase()] || v;
        if (fn === 'tr') return dico[v] || v;
        if (fn === 'date') return dateEn(v);
        return v;
      });
    }
    return null;
  }
  // Coupe en phrases, jamais a l'interieur de « … » (titres de presse cites).
  function couperPhrases(t) {
    var out = [], cur = '', prof = 0;
    for (var i = 0; i < t.length; i++) {
      var ch = t[i];
      cur += ch;
      if (ch === '«') prof++;
      else if (ch === '»') prof = Math.max(0, prof - 1);
      if (!prof && /[.!?»)]/.test(ch) && /\s/.test(t[i + 1] || '') && /[«A-ZÀ-ÖÙ-Ý0-9]/.test((t.slice(i + 1).trim())[0] || '')) {
        out.push(cur.trim()); cur = '';
      }
    }
    if (cur.trim()) out.push(cur.trim());
    return out;
  }
  function traduirePhrases(s) {
    var t = s.replace(/\s+/g, ' ').trim();
    if (!t) return null;
    var r = dico[t] || appliquerRegles(t, reglesPara);
    if (r == null) {
      var morceaux = couperPhrases(t), change = false;
      r = morceaux.map(function (p) {
        var x = dico[p] || appliquerRegles(p, reglesPhrase);
        if (x != null) { change = true; return x; }
        return p;
      }).join(' ');
      if (!change) return null;
    }
    return s.match(/^\s*/)[0] + r + s.match(/\s*$/)[0];
  }
  function attributs(n) {
    ['placeholder', 'aria-label', 'title'].forEach(function (a) {
      if (!n.hasAttribute(a)) return;
      var v = n.getAttribute(a), r = traduire(v);
      if (r != null && r.trim() !== v) n.setAttribute(a, r.trim());   // jamais de boucle
    });
  }
  function exclu(el) { return el && el.closest && el.closest(NE_PAS); }
  function noeud(n) {
    if (n.nodeType === 3) {
      if (exclu(n.parentElement)) return;
      var r = n.parentElement && n.parentElement.closest(PHRASES) ? traduirePhrases(n.nodeValue) : traduire(n.nodeValue);
      if (r != null && r !== n.nodeValue) n.nodeValue = r;
      return;
    }
    if (n.nodeType !== 1 || exclu(n)) return;
    attributs(n);
    if (n.tagName === 'INPUT' && (n.type === 'button' || n.type === 'submit') && n.value) {
      var v = traduire(n.value); if (v != null) n.value = v.trim();
    }
    for (var c = n.firstChild; c; c = c.nextSibling) noeud(c);
  }
  function appliquer() {
    document.documentElement.lang = 'en';
    var t = traduire(document.title); if (t) document.title = t.trim();
    var d = document.querySelector('meta[name="description"]');
    if (d) { var dt = traduire(d.content); if (dt) d.content = dt.trim(); }
    appliquerBlocs(document.body);
    noeud(document.body);
    new MutationObserver(function (ms) {
      ms.forEach(function (m) {
        if (m.type === 'attributes') { if (!exclu(m.target)) attributs(m.target); return; }
        m.addedNodes.forEach(function (n) { if (n.nodeType === 1) appliquerBlocs(n); noeud(n); });
      });
    }).observe(document.body, { childList: true, subtree: true, attributes: true, attributeFilter: ['placeholder', 'aria-label', 'title'] });
    montrer();
  }
  function demarrer() {
    selecteur();
    if (langue !== 'en') { montrer(); return; }
    fetch('/i18n/en.json', { cache: 'no-cache' }).then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (j) {
        dico = j.textes || {};
        cats = j.categories || {};
        regles = (j.regles || []).map(function (x) { return [new RegExp(x[0]), x[1]]; });
        blocs = j.blocs || {};
        reglesPara = (j.regles_paragraphes || []).map(function (x) { return [new RegExp(x[0]), x[1]]; });
        reglesPhrase = (j.regles_phrases || []).map(function (x) { return [new RegExp(x[0]), x[1]]; });
        // Fichier propre a la page (critiques, categories, equipe…), s'il existe.
        var chemin = location.pathname.replace(/^\//, '') || 'index.html';
        if (/\/$/.test(chemin)) chemin += 'index.html';
        if ((j.pages || []).indexOf(chemin) < 0) { appliquer(); return; }
        return fetch('/i18n/en/pages/' + chemin + '.json', { cache: 'no-cache' })
          .then(function (r) { return r.ok ? r.json() : {}; })
          .then(function (p) { for (var k in p) blocs[k] = p[k]; appliquer(); }, appliquer);
      }).catch(montrer);
  }
  window.MCLangue = { langue: langue, traduire: function (s) { return dico ? (traduire(s) || s) : s; } };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', demarrer); else demarrer();
})();
