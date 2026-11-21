/* Le Mystere du Jour — MediaCritic. Vanilla, sans dependance.
 * Donnees : /data/mystere.json (genere par scripts/generate_mystere.py depuis
 * le podcast du jour). La reponse n'y figure que sous forme d'empreinte.
 * Stockage : localStorage, chaque acces protege ; sans stockage, la partie
 * fonctionne quand meme (memoire de la page). */
(function () {
  'use strict';
  var CLE = 'mc-mystere-v1';
  var MAX = 6;
  var $ = function (id) { return document.getElementById(id); };
  var stockageOk = true;
  var memoire = null;            // repli quand le stockage est bloque
  var donnees = null, mystere = null, jour = null, etat = null;
  var lecteursCharges = false;

  /* ---------- outils ---------- */
  // Horloge : un decalage de test peut etre pose via window.__mysDecalage (ms).
  function maintenant() { return new Date(Date.now() + (window.__mysDecalage || 0)); }
  function jourParis(d) {
    return new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Paris', year: 'numeric', month: '2-digit', day: '2-digit' }).format(d || maintenant());
  }
  function secondesAvantMinuit() {
    var p = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Paris', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23' })
      .formatToParts(maintenant()).reduce(function (a, x) { a[x.type] = +x.value; return a; }, {});
    return 86400 - (p.hour * 3600 + p.minute * 60 + p.second);
  }
  function veille(iso) {
    var d = new Date(iso + 'T12:00:00Z'); d.setUTCDate(d.getUTCDate() - 1);
    return d.toISOString().slice(0, 10);
  }
  // DOIT rester identique a normaliser() de scripts/generate_mystere.py.
  function normaliser(s) {
    return String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
      .replace(/&/g, ' et ').replace(/[^a-z0-9]+/g, '');
  }
  // cyrb53, meme graine que generate_mystere.empreinte().
  function empreinte(str) {
    var h1 = 0xdeadbeef ^ 0x4d43, h2 = 0x41c6ce57 ^ 0x4d43;
    for (var i = 0, ch; i < str.length; i++) {
      ch = str.charCodeAt(i);
      h1 = Math.imul(h1 ^ ch, 2654435761);
      h2 = Math.imul(h2 ^ ch, 1597334677);
    }
    h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507);
    h1 ^= Math.imul(h2 ^ (h2 >>> 13), 3266489909);
    h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507);
    h2 ^= Math.imul(h1 ^ (h1 >>> 13), 3266489909);
    return (4294967296 * (2097151 & h2) + (h1 >>> 0)).toString(16);
  }
  function decoder(b64) {
    var bin = atob(b64), oct = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) oct[i] = bin.charCodeAt(i);
    return JSON.parse(new TextDecoder('utf-8').decode(oct));
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

  /* ---------- stockage protege ---------- */
  function etatVide() {
    return { v: 1, parties: {}, stats: { jouees: 0, gagnees: 0, serie: 0, meilleure: 0, distrib: [0, 0, 0, 0, 0, 0], dernierGagne: null } };
  }
  function charger() {
    try {
      var s = window.localStorage.getItem(CLE);
      if (s) { var e = JSON.parse(s); if (e && e.v === 1) return e; }
      return memoire || etatVide();
    } catch (e) { stockageOk = false; return memoire || etatVide(); }
  }
  function sauver() {
    memoire = etat;
    try { window.localStorage.setItem(CLE, JSON.stringify(etat)); } catch (e) { stockageOk = false; }
  }
  function partie() {
    if (!etat.parties[jour]) etat.parties[jour] = { essais: [], fini: false, gagne: false, compte: false };
    return etat.parties[jour];
  }

  /* ---------- humeur (ton MediaCritic : taquin, jamais meprisant) ---------- */
  var HUMEURS = {
    1: 'Du premier coup. Même Alex a mis 4 essais.',
    2: 'Deux essais. Lolo est déjà jaloux, et il le cache mal.',
    3: 'Trois essais : la moyenne de la rédaction. Pile dans le générique.',
    4: 'Quatre essais, comme Alex. Ce n\'est pas un compliment, mais ce n\'est pas une insulte.',
    5: 'Cinq essais. Ça s\'est joué au générique de fin.',
    6: 'Au sixième indice ! Même le podcast n\'y croyait plus.',
    perdu: 'Lolo non plus n\'a pas trouvé. Il a fait un PowerPoint pour s\'en remettre.'
  };

  /* ---------- rendu ---------- */
  function rendreIndices() {
    var p = partie(), ol = $('mys-indices');
    ol.textContent = '';
    var visibles = p.fini ? MAX : Math.min(p.essais.length + 1, MAX);
    mystere.indices.forEach(function (ind, i) {
      if (i < visibles) {
        var corps = ind.image
          ? el('img', { classe: 'mys-flou', referrerpolicy: 'no-referrer', src: ind.image, alt: 'Pochette floutée de l\'émission', width: '120', height: '120', decoding: 'async' })
          : el('p', { classe: 'mys-indice-texte', texte: ind.texte });
        ol.appendChild(el('li', { classe: 'mys-indice', 'aria-label': 'Indice ' + (i + 1) + ', ' + ind.cle + (ind.texte ? ' : ' + ind.texte : '') }, [
          el('span', { classe: 'mys-indice-cle', texte: 'Indice ' + (i + 1) + ' · ' + ind.cle, 'aria-hidden': 'true' }), corps]));
      } else {
        ol.appendChild(el('li', { classe: 'mys-indice mys-indice-cache', texte: 'Indice ' + (i + 1) + ' : se dévoile après une mauvaise réponse' }));
      }
    });
  }
  function carres(p) {
    var s = p.essais.map(function () { return '🟥'; });
    if (p.gagne) s[s.length - 1] = '🟩';
    return s.join('');
  }
  function rendreEssais() {
    var p = partie();
    var vides = Math.max(0, MAX - p.essais.length);
    $('mys-carres').textContent = carres(p) + '⬜'.repeat(p.fini ? 0 : vides);
    var ul = $('mys-essais'); ul.textContent = '';
    p.essais.forEach(function (e, i) {
      if (e !== '—' && !(p.gagne && i === p.essais.length - 1)) ul.appendChild(el('li', { texte: e }));
    });
  }
  function rendreStats() {
    var s = etat.stats;
    var serie = (s.dernierGagne === jour || s.dernierGagne === veille(jour)) ? s.serie : 0;
    var pct = s.jouees ? Math.round(100 * s.gagnees / s.jouees) : 0;
    var dl = $('mys-chiffres'); dl.textContent = '';
    [['Parties', s.jouees], ['Victoires', pct + ' %'], ['Série', serie], ['Record', s.meilleure]].forEach(function (x) {
      dl.appendChild(el('div', {}, [el('dt', { texte: x[0] }), el('dd', { texte: String(x[1]) })]));
    });
    var max = Math.max.apply(null, s.distrib.concat([1]));
    var p = etat.parties[jour];
    var ol = $('mys-distrib'); ol.textContent = '';
    s.distrib.forEach(function (n, i) {
      var b = el('span', { classe: 'mys-barre' + (p && p.gagne && p.essais.length === i + 1 ? ' mys-auj' : ''), texte: String(n) });
      b.style.width = Math.max(8, Math.round(100 * n / max)) + '%';
      ol.appendChild(el('li', { 'aria-label': n + ' victoire(s) en ' + (i + 1) + ' essai(s)' }, [el('span', { texte: String(i + 1), 'aria-hidden': 'true' }), b]));
    });
    $('mys-stockage').hidden = stockageOk;
  }

  function iframe(src, titre, video) {
    // Lecteurs OFFICIELS seulement ; jamais d'autoplay ; crees a la revelation.
    var f = el('iframe', {
      src: src, title: titre, loading: 'lazy', referrerpolicy: 'strict-origin-when-cross-origin',
      allow: 'encrypted-media; fullscreen; picture-in-picture; clipboard-write',
      height: video ? '' : (src.indexOf('spotify') >= 0 ? '152' : '175')
    });
    if (video) { f.className = 'mys-lecteur-video'; f.setAttribute('allowfullscreen', ''); }
    return el('div', { classe: 'mys-lecteur' }, [f]);
  }

  function texteDePartage() {
    var p = partie();
    var score = p.gagne ? p.essais.length : 'X';
    var num = mystere.n >= 1 ? '#' + mystere.n : '(avant-première)';
    return 'Le Mystère du Jour ' + num + ' 🎧 ' + score + '/6\n' + carres(p) + '\nmediacritic.fr/mystere';
  }
  function copier(texte, retour) {
    function ok() { retour.textContent = 'Copié ! Colle-le où tu veux.'; }
    function secours() {
      try {
        var t = el('textarea', { readonly: '' }); t.value = texte;
        t.style.position = 'fixed'; t.style.opacity = '0';
        document.body.appendChild(t); t.select(); document.execCommand('copy'); t.remove(); ok();
      } catch (e) { retour.textContent = 'Copie impossible : sélectionne le texte à la main.'; }
    }
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(texte).then(ok, secours);
    else secours();
  }
  function partager(retour) {
    var texte = texteDePartage();
    var mobile = window.matchMedia && window.matchMedia('(pointer:coarse)').matches;
    if (navigator.share && mobile) {
      navigator.share({ text: texte }).catch(function (e) { if (!e || e.name !== 'AbortError') copier(texte, retour); });
    } else copier(texte, retour);
    try { if (window.gtag) window.gtag('event', 'mystere_partage', { mystere: mystere.n }); } catch (e) {}
  }

  function rendreRevelation() {
    var p = partie(), r = mystere.rev, sec = $('mys-revel');
    sec.textContent = '';
    var titre = el('h2', { id: 'mys-revel-titre', tabindex: '-1', texte: p.gagne ? 'Bravo ! C\'était…' : 'Raté ! C\'était…' });
    sec.appendChild(titre);
    sec.appendChild(el('div', { classe: 'mys-carte' }, [
      r.image ? el('img', { referrerpolicy: 'no-referrer', src: r.image, alt: 'Pochette de ' + r.titre, width: '120', height: '120', decoding: 'async' }) : null,
      el('div', {}, [
        el('p', { classe: 'mys-carte-nom', texte: r.titre }),
        r.auteur && normaliser(r.auteur) !== normaliser(r.titre) ? el('p', { classe: 'mys-carte-auteur', texte: 'par ' + r.auteur }) : null,
        r.phrase ? el('p', { classe: 'mys-carte-phrase', texte: r.phrase }) : null])]));
    sec.appendChild(el('p', { classe: 'mys-humeur', texte: p.gagne ? HUMEURS[p.essais.length] : HUMEURS.perdu }));
    if (r.episode && r.episode.titre) sec.appendChild(el('p', { classe: 'mys-carte-auteur', texte: 'L\'épisode du jour : « ' + r.episode.titre + ' »' }));
    if (r.lecteur && r.lecteur.src) sec.appendChild(iframe(r.lecteur.src, 'Lecteur ' + r.lecteur.type + ' : ' + r.titre, r.lecteur.type === 'youtube'));
    if (r.avis) {
      var bloc = el('div', { classe: 'mys-avis' }, [
        el('h3', { texte: 'Et notre avis 👉' }),
        el('p', {}, [el('span', { classe: 'mys-avis-note', texte: String(r.avis.note).replace('.', ',') + '/10' }),
          document.createTextNode(' — épisode ' + r.avis.episode + ' de MediaCritic')])]);
      if (r.avis.lecteur) bloc.appendChild(iframe(r.avis.lecteur, 'Notre épisode sur ' + r.titre + ' (Spotify)', false));
      bloc.appendChild(el('p', {}, [el('a', { href: r.avis.url, texte: 'Lire notre critique →' })]));
      sec.appendChild(bloc);
    }
    var retour = el('p', { classe: 'mys-copie', role: 'status', 'aria-live': 'polite' });
    var bPartage = el('button', { type: 'button', classe: 'mys-btn mys-btn-plein', texte: '📤 Partager mon score' });
    bPartage.addEventListener('click', function () { partager(retour); });
    sec.appendChild(el('div', { classe: 'mys-actions' }, [
      bPartage,
      el('a', { classe: 'mys-btn', href: 'podcast-du-jour.html', texte: '🎧 Écouter le podcast du jour' }),
      el('a', { classe: 'mys-btn', href: r.fiche, texte: 'Voir sa fiche' })]));
    sec.appendChild(retour);
    sec.hidden = false;
    lecteursCharges = true;
  }

  function rendre() {
    var p = partie();
    $('mys-attente').hidden = true;
    $('mys-jeu').hidden = false;
    $('mys-numero').textContent = (mystere.n >= 1 ? 'Mystère n°' + mystere.n : 'Avant-première') + ' · devine le podcast du jour en 6 indices';
    rendreIndices(); rendreEssais(); rendreStats();
    $('mys-form').hidden = p.fini;
    if (p.fini) { if (!lecteursCharges) rendreRevelation(); }
    else { $('mys-revel').hidden = true; $('mys-revel').textContent = ''; lecteursCharges = false; }
  }

  /* ---------- logique de jeu ---------- */
  function terminer(gagne) {
    var p = partie(), s = etat.stats;
    p.fini = true; p.gagne = gagne;
    if (!p.compte) {
      p.compte = true;
      s.jouees += 1;
      if (gagne) {
        s.gagnees += 1;
        s.distrib[p.essais.length - 1] += 1;
        s.serie = (s.dernierGagne === veille(jour)) ? s.serie + 1 : 1;
        s.meilleure = Math.max(s.meilleure, s.serie);
        s.dernierGagne = jour;
      } else s.serie = 0;
    }
    sauver();
    try { if (window.gtag) window.gtag('event', 'mystere_fin', { resultat: gagne ? 'gagne' : 'perdu', essais: p.essais.length }); } catch (e) {}
    rendre();
    var t = $('mys-revel-titre'); if (t) t.focus();
  }
  function proposer(valeur) {
    var p = partie(), retour = $('mys-retour');
    var v = String(valeur || '').trim();
    if (p.fini) return;
    if (!v) { retour.textContent = 'Écris le nom d\'un podcast ou d\'une chaîne.'; return; }
    var n = normaliser(v);
    if (!n) { retour.textContent = 'Ce nom ne contient ni lettre ni chiffre.'; return; }
    if (p.essais.some(function (e) { return normaliser(e) === n; })) { retour.textContent = 'Déjà proposé ! Essaie autre chose.'; return; }
    p.essais.push(v);
    $('mys-saisie').value = '';
    if (mystere.r.indexOf(empreinte(n)) >= 0) { retour.textContent = ''; terminer(true); return; }
    if (p.essais.length >= MAX) { retour.textContent = ''; terminer(false); return; }
    retour.textContent = 'Non, ce n\'est pas « ' + v + ' ». Nouvel indice dévoilé.';
    sauver(); rendre();
  }

  /* ---------- cycle du jour ---------- */
  function afficherAttente() {
    $('mys-jeu').hidden = true; $('mys-revel').hidden = true;
    $('mys-attente').hidden = false;
    $('mys-numero').textContent = 'Le mystère du jour arrive avant 10 h';
    rendreStats();
  }
  function demarrer() {
    jour = jourParis();
    etat = charger();
    var b64 = donnees && donnees.jours && donnees.jours[jour];
    if (!b64) { mystere = null; afficherAttente(); return; }
    try { mystere = decoder(b64); } catch (e) { mystere = null; afficherAttente(); return; }
    lecteursCharges = false;
    rendre();
  }
  function chargerDonnees() {
    return fetch('/data/mystere.json', { cache: 'no-cache' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function (d) {
      donnees = d;
      var dl = $('mys-noms'); dl.textContent = '';
      (d.noms || []).forEach(function (nom) { dl.appendChild(el('option', { value: nom })); });
    });
  }
  function tic() {
    var s = secondesAvantMinuit();
    var hh = String(Math.floor(s / 3600)).padStart(2, '0'), mm = String(Math.floor(s % 3600 / 60)).padStart(2, '0'), ss = String(s % 60).padStart(2, '0');
    $('mys-compte').textContent = hh + ':' + mm + ':' + ss;
    // Passage de minuit (Paris) : nouveau mystere sans recharger la page.
    if (jour && jourParis() !== jour) chargerDonnees().then(demarrer, demarrer);
  }

  function init() {
    if (!$('mys')) return;
    $('mys-form').addEventListener('submit', function (e) { e.preventDefault(); proposer($('mys-saisie').value); });
    var b = $('mys-passer'), arme = false;
    b.addEventListener('click', function () {
      if (!mystere || partie().fini) return;
      if (!arme) { arme = true; b.textContent = 'Sûr ? Ça compte comme une défaite (cliquer pour confirmer)'; return; }
      arme = false; b.textContent = 'Je donne ma langue au chat';
      var p = partie(); while (p.essais.length < MAX) p.essais.push('—');
      terminer(false);
    });
    chargerDonnees().then(demarrer, function () {
      etat = charger(); jour = jourParis(); afficherAttente();
      $('mys-attente').querySelector('p').textContent = 'Impossible de charger le mystère. Vérifie ta connexion et recharge la page.';
    });
    tic(); setInterval(tic, 1000);
    // Avant le choix du matin : on revient voir toutes les 5 minutes.
    setInterval(function () { if (!mystere) chargerDonnees().then(demarrer, function () {}); }, 300000);
  }
  // Acces de test (verification) : aucune donnee de la reponse n'y figure.
  window.MCMystere = { normaliser: normaliser, empreinte: empreinte, jourParis: jourParis, redemarrer: function () { return chargerDonnees().then(demarrer); } };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
