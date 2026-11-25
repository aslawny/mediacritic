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
  // L'Oreille (25/11/2026) : extrait de plus en plus long a chaque essai.
  var PALIERS = [1, 3, 6, 10, 16, 25];

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
  // DOIT rester identique a la regle d'alias() de scripts/generate_mystere.py.
  function sansArticle(s) { return String(s || '').trim().replace(/^(les|le|la|l['’]|un|une|the)\s*/i, ''); }
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
    6: 'Au sixième essai ! Même le podcast n\'y croyait plus.',
    perdu: 'Lolo non plus n\'a pas trouvé. Il a fait un PowerPoint pour s\'en remettre.'
  };

  /* ---------- rendu ---------- */
  function rendreSon() {
    var p = partie(), ol = $('mys-paliers'), n = p.essais.length;
    ol.textContent = '';
    PALIERS.forEach(function (s, i) {
      var cls = '';
      if (p.gagne && i === n - 1) cls = 'gagne';
      else if (i < n) cls = 'rate';
      else if (!p.fini && i === n) cls = 'ouvert';
      ol.appendChild(el('li', { classe: cls, style: 'height:' + (16 + i * 9) + 'px', 'aria-label': s + ' s' }, [el('span', { texte: s + ' s', 'aria-hidden': 'true' })]));
    });
    var d = dureeExtrait();
    var lib = p.fini ? 'Écouter la suite de l\'épisode' : 'Écouter ' + d + (d > 1 ? ' secondes' : ' seconde');
    $('mys-libelle').textContent = lib; $('mys-jouer').setAttribute('aria-label', lib);
    // Coups de pouce : la categorie au 4e essai, le titre de l'episode au 6e.
    var coup = $('mys-coup'), cle = null, texte = null;
    if (!p.fini && n >= 5 && mystere.son.episode) { cle = 'Dernier coup de pouce · titre de l\'épisode'; texte = mystere.son.episode; }
    else if (!p.fini && n >= 3) { cle = 'Coup de pouce · ' + mystere.indices[0].cle.toLowerCase(); texte = mystere.indices[0].texte; }
    coup.hidden = !cle; coup.textContent = '';
    if (cle) { coup.appendChild(el('b', { texte: cle })); coup.appendChild(document.createTextNode(texte)); }
  }
  function rendreIndices() {
    var p = partie(), ol = $('mys-indices');
    ol.textContent = '';
    if (mystere.son) return;
    var visibles = p.fini ? MAX : Math.min(p.essais.length + 1, MAX);
    mystere.indices.forEach(function (ind, i) {
      if (i < visibles) {
        var corps = ind.image
          ? el('img', { classe: 'mys-flou', referrerpolicy: 'no-referrer', src: ind.image, alt: 'Pochette floutée de l\'émission', width: '120', height: '120', decoding: 'async' })
          : el('p', { classe: 'mys-indice-texte', texte: ind.texte });
        ol.appendChild(el('li', { classe: 'mys-indice' + (!p.fini && i === visibles - 1 && i > 0 ? ' mys-indice-neuf' : ''), id: 'mys-indice-' + (i + 1), 'aria-label': 'Indice ' + (i + 1) + ', ' + ind.cle + (ind.texte ? ' : ' + ind.texte : '') }, [
          el('span', { classe: 'mys-indice-cle', texte: 'Indice ' + (i + 1) + ' · ' + ind.cle, 'aria-hidden': 'true' }), corps]));
      } else if (i === visibles) {
        // Mobile : une seule ligne pour les indices caches, pas cinq cartes
        // vides qui repoussent le champ de saisie sous le clavier.
        ol.appendChild(el('li', { classe: 'mys-indice mys-indice-cache', texte: (MAX - visibles > 1 ? 'Indices ' + (i + 1) + ' à ' + MAX : 'Indice ' + MAX) + ' : un de plus à chaque mauvaise réponse' }));
      }
    });
  }
  function carres(p) {
    var s = p.essais.map(function (e) { return e === '' ? '⬛' : '🟥'; });
    if (p.gagne) s[s.length - 1] = '🟩';
    return s.join('');
  }
  function rendreEssais() {
    var p = partie();
    var vides = Math.max(0, MAX - p.essais.length);
    $('mys-carres').textContent = mystere.son ? '' : carres(p) + '⬜'.repeat(p.fini ? 0 : vides);
    var ul = $('mys-essais'); ul.textContent = '';
    p.essais.forEach(function (e, i) {
      if (e === '') ul.appendChild(el('li', { classe: 'mys-passe', texte: 'passé' }));
      else if (e !== '—' && !(p.gagne && i === p.essais.length - 1)) ul.appendChild(el('li', { texte: e }));
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
    var num = mystere.n >= 1 ? 'n°' + mystere.n : '(avant-première)';
    if (mystere.son) {
      return '👂 L\'Oreille ' + num + ' · ' + (p.gagne ? 'trouvé en ' + PALIERS[p.essais.length - 1] + ' s' : 'pas trouvé') +
        '\n' + carres(p) + '\nmediacritic.fr/mystere';
    }
    var score = p.gagne ? p.essais.length : 'X';
    return '👂 L\'Oreille ' + num + ' (sans le son) 🕵️ ' + score + '/6\n' + carres(p) + '\nmediacritic.fr/mystere';
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
    var titre = el('h2', { id: 'mys-revel-titre', tabindex: '-1', texte: p.gagne
      ? (mystere.son ? 'Bien entendu ! Trouvé en ' + PALIERS[p.essais.length - 1] + ' s 👂' : 'Bravo ! C\'était…')
      : 'Raté ! C\'était…' });
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
    // Lecteur du site : l'episode du jour dans « Ma liste d'ecoute ».
    if (r.ecoute && window.MCListe) {
      var bAjout = el('button', { type: 'button', classe: 'mys-btn', texte: '+ Ajouter l\'épisode à ma liste' });
      bAjout.addEventListener('click', function () {
        bAjout.textContent = window.MCListe.ajouter(r.ecoute) === 'deja' ? 'Déjà dans ta liste' : 'Ajouté à ta liste ✓';
      });
      sec.querySelector('.mys-actions').appendChild(bAjout);
    }
    sec.appendChild(retour);
    sec.hidden = false;
    lecteursCharges = true;
  }

  function rendre() {
    var p = partie();
    $('mys-attente').hidden = true;
    $('mys-jeu').hidden = false;
    var num = mystere.n >= 1 ? 'Partie n°' + mystere.n : 'Avant-première';
    $('mys-numero').textContent = mystere.son ? num + ' · reconnais le podcast du jour au son'
      : num + ' · pas de son aujourd\'hui : c\'est une chaîne YouTube, devine-la en 6 indices';
    $('mys-son').hidden = !mystere.son;
    $('mys-plus').hidden = !mystere.son;
    $('mys-indices').hidden = !!mystere.son;
    if (mystere.son) rendreSon();
    rendreIndices(); rendreEssais(); rendreStats();
    $('mys-form').hidden = p.fini;
    if (p.fini) { if (!lecteursCharges) rendreRevelation(); }
    else { $('mys-revel').hidden = true; $('mys-revel').textContent = ''; lecteursCharges = false; }
  }

  /* ---------- logique de jeu ---------- */
  function terminer(gagne) {
    var p = partie(), s = etat.stats;
    p.fini = true; p.gagne = gagne;
    arreterSon();
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
    var court = normaliser(sansArticle(v));
    if (mystere.r.indexOf(empreinte(n)) >= 0 || (court.length >= 3 && mystere.r.indexOf(empreinte(court)) >= 0)) { retour.textContent = ''; terminer(true); return; }
    erreur('Non, ce n\'est pas « ' + v + ' ».');
  }
  function erreur(msg) {
    var p = partie(), retour = $('mys-retour');
    if (p.essais.length >= MAX) { retour.textContent = ''; terminer(false); return; }
    retour.textContent = msg + (mystere.son ? ' Tu as droit à ' + PALIERS[p.essais.length] + ' s de son.' : ' Nouvel indice dévoilé.');
    arreterSon(); anneau(0);
    sauver(); rendre();
    montrerNouvelIndice(p.essais.length + 1);
  }
  // Sur ecran tactile, le clavier cacherait l'indice qui vient d'apparaitre :
  // on le ferme et on amene l'indice a l'ecran. Au clavier physique, on garde
  // le focus dans le champ pour enchainer.
  function montrerNouvelIndice(n) {
    var li = mystere.son ? $('mys-son') : $('mys-indice-' + n);
    if (!li) return;
    var tactile = window.matchMedia && window.matchMedia('(pointer: coarse)').matches;
    if (tactile) {
      $('mys-saisie').blur();
      setTimeout(function () { li.scrollIntoView({ behavior: 'smooth', block: 'center' }); }, 250);
    }
  }

  /* ---------- son : extrait lu depuis le flux officiel ---------- */
  var audio = null, finExtrait = 0, rafId = 0, enLecture = false;
  var CIRC = 2 * Math.PI * 72;
  function dureeExtrait() { var p = partie(); return PALIERS[Math.min(p.essais.length, MAX - 1)]; }
  function anneau(f) { var c = $('mys-prog'); if (c) c.style.strokeDashoffset = String(CIRC * (1 - Math.max(0, Math.min(1, f)))); }
  function icone(pause) {
    $('mys-ico').innerHTML = pause
      ? '<rect x="6.5" y="5" width="4" height="14" rx="1" fill="currentColor"/><rect x="13.5" y="5" width="4" height="14" rx="1" fill="currentColor"/>'
      : '<path fill="currentColor" d="M8 5.5v13a1 1 0 0 0 1.5.86l10.5-6.5a1 1 0 0 0 0-1.72L9.5 4.64A1 1 0 0 0 8 5.5z"/>';
  }
  function arreterSon() {
    if (audio) audio.pause();
    enLecture = false; cancelAnimationFrame(rafId);
    var b = $('mys-jouer'); if (b) b.classList.remove('charge');
    if ($('mys-ico')) icone(false);
  }
  function boucle() {
    if (!partie().fini) {
      anneau((audio.currentTime - mystere.son.debut) / dureeExtrait());
      if (audio.currentTime >= finExtrait) {
        arreterSon(); anneau(1);
        setTimeout(function () { if (!enLecture) anneau(0); }, 500);
        return;
      }
    }
    rafId = requestAnimationFrame(boucle);
  }
  function preparerAudio() {
    if (audio) return;
    audio = new Audio(); audio.preload = 'none';
    audio.addEventListener('playing', function () {
      $('mys-jouer').classList.remove('charge');
      if (!partie().fini && audio.currentTime < mystere.son.debut - 0.5) audio.currentTime = mystere.son.debut;
      cancelAnimationFrame(rafId); rafId = requestAnimationFrame(boucle);
    });
    audio.addEventListener('waiting', function () { if (enLecture) $('mys-jouer').classList.add('charge'); });
    audio.addEventListener('error', function () { arreterSon(); $('mys-libelle').textContent = 'Le son ne se charge pas. Vérifie ta connexion.'; });
  }
  function jouer() {
    if (!mystere || !mystere.son) return;
    preparerAudio();
    if (enLecture) { arreterSon(); anneau(0); return; }
    var p = partie(), son = mystere.son;
    finExtrait = p.fini ? Infinity : son.debut + dureeExtrait();
    var depart = p.fini ? Math.max(son.debut, audio.currentTime || son.debut) : son.debut;
    // play() doit partir du geste (iOS) : au 1er appui on pose la source avec
    // un fragment #t= pour que le navigateur demarre deja au bon endroit.
    if (audio.dataset.src !== son.audio) { audio.dataset.src = son.audio; audio.src = son.audio + '#t=' + son.debut; }
    else if (Math.abs(audio.currentTime - depart) > 0.3) audio.currentTime = depart;
    $('mys-jouer').classList.add('charge'); icone(true); enLecture = true;
    var pr = audio.play();
    if (pr && pr.catch) pr.catch(function () { arreterSon(); $('mys-libelle').textContent = 'Lecture impossible, réessaie.'; });
    try { if (window.gtag) window.gtag('event', 'oreille_ecoute', { palier: p.fini ? 0 : dureeExtrait() }); } catch (e) {}
  }

  /* ---------- suggestions (remplace <datalist>, inutilisable sur mobile) ---------- */
  var noms = [], nomsCherche = [], suggestions = [], actif = -1;
  // Recherche tolerante : sans accents ni casse, mais en gardant les mots.
  function pourRecherche(s) {
    return ' ' + String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
      .replace(/&/g, ' et ').replace(/[^a-z0-9]+/g, ' ').trim() + ' ';
  }
  function chercher(q) {
    var x = pourRecherche(q).trim();
    if (!x) return [];
    var deja = partie().essais.map(normaliser), debut = [], mot = [], dedans = [];
    noms.forEach(function (nom, i) {
      if (deja.indexOf(normaliser(nom)) >= 0) return;
      var c = nomsCherche[i];
      if (c.indexOf(' ' + x) === 0) debut.push(nom);
      else if (c.indexOf(' ' + x) > 0) mot.push(nom);
      else if (c.replace(/ /g, '').indexOf(x.replace(/ /g, '')) >= 0) dedans.push(nom);
    });
    return debut.concat(mot, dedans).slice(0, 6);
  }
  function fermerSuggestions() {
    var ul = $('mys-sugg'), inp = $('mys-saisie');
    suggestions = []; actif = -1;
    ul.hidden = true; ul.textContent = '';
    inp.setAttribute('aria-expanded', 'false');
    inp.removeAttribute('aria-activedescendant');
  }
  function marquerActif() {
    var inp = $('mys-saisie');
    Array.prototype.forEach.call($('mys-sugg').children, function (li, i) {
      li.setAttribute('aria-selected', i === actif ? 'true' : 'false');
      if (i === actif) { inp.setAttribute('aria-activedescendant', li.id); li.scrollIntoView({ block: 'nearest' }); }
    });
    if (actif < 0) inp.removeAttribute('aria-activedescendant');
  }
  function choisir(nom) {
    var inp = $('mys-saisie');
    inp.value = nom;
    fermerSuggestions();
    inp.focus();
    // Un nom de la liste : on peut valider tout de suite, on le signale.
    $('mys-form').classList.add('mys-pret');
  }
  function afficherSuggestions() {
    var inp = $('mys-saisie'), ul = $('mys-sugg');
    $('mys-form').classList.remove('mys-pret');
    suggestions = chercher(inp.value); actif = -1;
    ul.textContent = '';
    if (!suggestions.length) {
      if (inp.value.trim().length >= 3) {
        ul.appendChild(el('li', { classe: 'mys-sugg-vide', role: 'presentation', texte: 'Pas dans la liste : tu peux quand même valider ton idée.' }));
        ul.hidden = false;
      } else ul.hidden = true;
      inp.setAttribute('aria-expanded', 'false');
      return;
    }
    suggestions.forEach(function (nom, i) {
      var li = el('li', { id: 'mys-sugg-' + i, role: 'option', 'aria-selected': 'false', classe: 'mys-sugg-opt', texte: nom });
      // pointerdown + preventDefault : le champ garde le focus (pas de
      // fermeture/reouverture du clavier entre le toucher et le choix).
      li.addEventListener('pointerdown', function (e) { e.preventDefault(); });
      li.addEventListener('click', function () { choisir(nom); });
      ul.appendChild(li);
    });
    ul.hidden = false;
    inp.setAttribute('aria-expanded', 'true');
    ajusterHauteur();
  }
  // La liste s'arrete au-dessus du clavier (visualViewport : la zone vraiment
  // visible, que 'vh' ignore sur iOS).
  function ajusterHauteur() {
    var ul = $('mys-sugg'), vv = window.visualViewport;
    if (!vv || ul.hidden) return;
    var dispo = vv.height + vv.offsetTop - ul.getBoundingClientRect().top - 8;
    ul.style.maxHeight = Math.max(144, Math.min(300, dispo)) + 'px';
  }
  // Au focus sur mobile : on remonte le champ en haut de l'ecran pour que les
  // suggestions tiennent au-dessus du clavier.
  function remonterChamp() {
    if (!(window.matchMedia && window.matchMedia('(pointer: coarse)').matches)) return;
    setTimeout(function () {
      var r = $('mys-form').getBoundingClientRect();
      var marge = (document.getElementById('mc-header') || {}).offsetHeight || 0;
      if (r.top < marge + 8 || r.top > window.innerHeight * 0.25) {
        window.scrollBy({ top: r.top - marge - 12, behavior: 'smooth' });
      }
    }, 300);
  }
  function brancherSuggestions() {
    var inp = $('mys-saisie');
    inp.addEventListener('input', afficherSuggestions);
    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', ajusterHauteur);
      window.visualViewport.addEventListener('scroll', ajusterHauteur);
    }
    inp.addEventListener('focus', function () { remonterChamp(); if (inp.value) afficherSuggestions(); });
    inp.addEventListener('blur', function () { setTimeout(fermerSuggestions, 150); });
    inp.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown' && suggestions.length) { e.preventDefault(); actif = (actif + 1) % suggestions.length; marquerActif(); }
      else if (e.key === 'ArrowUp' && suggestions.length) { e.preventDefault(); actif = (actif - 1 + suggestions.length) % suggestions.length; marquerActif(); }
      else if (e.key === 'Enter' && actif >= 0) { e.preventDefault(); choisir(suggestions[actif]); }
      else if (e.key === 'Escape') fermerSuggestions();
    });
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
    arreterSon(); if (audio) { audio.removeAttribute('src'); audio.dataset.src = ''; } anneau(0);
    rendre();
  }
  function chargerDonnees() {
    return fetch('/data/mystere.json', { cache: 'no-cache' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function (d) {
      donnees = d;
      noms = (d.noms || []).slice();
      nomsCherche = noms.map(pourRecherche);
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
    $('mys-form').addEventListener('submit', function (e) {
      e.preventDefault(); fermerSuggestions(); $('mys-form').classList.remove('mys-pret');
      proposer($('mys-saisie').value);
    });
    brancherSuggestions();
    $('mys-prog').style.strokeDasharray = String(CIRC); anneau(0);
    $('mys-jouer').addEventListener('click', jouer);
    $('mys-plus').addEventListener('click', function () {
      if (!mystere || partie().fini) return;
      partie().essais.push(''); erreur('Passé.');
    });
    var b = $('mys-passer'), arme = false;
    b.addEventListener('click', function () {
      if (!mystere || partie().fini) return;
      if (!arme) { arme = true; b.textContent = 'Sûr ? Ça compte comme une défaite (appuie à nouveau pour confirmer)'; return; }
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
