/* MediaCritic — bouton « Partager » en tête de page.
 *
 * Un seul fichier pour les 8 600+ pages du site. Il s'insere dans la <nav>
 * existante quand il y en a une, sinon il se pose en haut a droite. Cette
 * souplesse est necessaire : les familles de pages n'ont pas la meme nav
 * (les fiches en ont deux et aucune .nav-links, mentions-legales n'a pas de
 * .nav-links du tout).
 *
 * Aucun widget tiers : les boutons officiels des reseaux sont des traceurs,
 * pesent des dizaines de Ko et la CSP du site les bloquerait. Ici : des liens
 * <a> construits a la volee. Zero requete reseau, zero cookie.
 *
 * Le titre et l'URL viennent de la page elle-meme (document.title,
 * location.href), donc rien a regenerer quand un titre change.
 */
(function () {
  "use strict";
  if (document.getElementById("mc-partage")) return;   // idempotent

  var CSS = [
    ".mc-part{position:relative;display:inline-flex;flex:0 0 auto}",
    ".mc-part-btn{display:inline-flex;align-items:center;gap:6px;background:rgba(255,255,255,.06);",
    "border:1px solid rgba(255,255,255,.12);color:inherit;font:inherit;font-size:.82rem;font-weight:600;",
    "padding:6px 12px;border-radius:8px;cursor:pointer;line-height:1.3;white-space:nowrap}",
    ".mc-part-btn:hover{border-color:#e8622d;color:#e8622d}",
    ".mc-part-menu{position:absolute;top:calc(100% + 8px);right:0;z-index:600;display:none;",
    "flex-direction:column;gap:2px;min-width:190px;padding:6px;border-radius:11px;",
    "background:rgba(9,18,32,.98);border:1px solid rgba(255,255,255,.12);",
    "box-shadow:0 14px 40px rgba(0,0,0,.5)}",
    ".mc-part-menu.ouvert{display:flex}",
    ".mc-part-menu a,.mc-part-menu button{display:flex;align-items:center;gap:9px;padding:8px 10px;",
    "border:0;border-radius:7px;background:none;color:#e8eaed;font:inherit;font-size:.85rem;",
    "text-align:left;text-decoration:none;cursor:pointer;width:100%}",
    ".mc-part-menu a:hover,.mc-part-menu button:hover{background:rgba(232,98,45,.16);color:#fff}",
    ".mc-part-ic{width:17px;text-align:center;flex:0 0 17px;font-size:.9rem}",
    ".mc-part-replie{display:block;width:100%}",
    ".mc-part-replie .mc-part-btn{width:100%;justify-content:flex-start;background:none;border:0;padding:10px 12px;font-size:.92rem}",
    ".mc-part-replie .mc-lib{display:inline !important}",
    ".mc-part-compact .mc-lib{display:none}",
    ".mc-part-compact .mc-part-btn{padding:6px 9px}",
    "@media(max-width:640px){.mc-part-btn span.mc-lib{display:none}",
    ".mc-part-btn{padding:6px 9px}.mc-part-menu{min-width:170px}}"
  ].join("");

  var titre = (document.title || "MediaCritic").replace(/\s*[|—-]\s*MediaCritic\s*$/, "").trim();
  var url = location.href.split("#")[0];
  var eU = encodeURIComponent(url);
  var eT = encodeURIComponent(titre);
  var eTU = encodeURIComponent(titre + " — " + url);

  var liens = [
    ["X", "🖋", "https://twitter.com/intent/tweet?text=" + eT + "&url=" + eU],
    ["LinkedIn", "in", "https://www.linkedin.com/sharing/share-offsite/?url=" + eU],
    ["Facebook", "f", "https://www.facebook.com/sharer/sharer.php?u=" + eU],
    ["WhatsApp", "💬", "https://wa.me/?text=" + eTU],
    ["E-mail", "✉", "mailto:?subject=" + eT + "&body=" + eTU]
  ];

  var style = document.createElement("style");
  style.textContent = CSS;
  document.head.appendChild(style);

  var boite = document.createElement("div");
  boite.className = "mc-part";
  boite.id = "mc-partage";

  var btn = document.createElement("button");
  btn.type = "button";
  btn.className = "mc-part-btn";
  btn.setAttribute("aria-haspopup", "true");
  btn.setAttribute("aria-expanded", "false");
  btn.setAttribute("aria-label", "Partager cette page");
  btn.innerHTML = '🔗 <span class="mc-lib">Partager</span>';

  var menu = document.createElement("div");
  menu.className = "mc-part-menu";
  menu.setAttribute("role", "menu");

  liens.forEach(function (l) {
    var a = document.createElement("a");
    a.href = l[2];
    a.setAttribute("role", "menuitem");
    // mailto n'ouvre pas d'onglet ; les reseaux si.
    if (l[2].indexOf("mailto:") !== 0) {
      a.target = "_blank";
      a.rel = "noopener noreferrer nofollow";
    }
    a.innerHTML = '<span class="mc-part-ic">' + l[1] + "</span>" + l[0];
    menu.appendChild(a);
  });

  var copie = document.createElement("button");
  copie.type = "button";
  copie.setAttribute("role", "menuitem");
  copie.innerHTML = '<span class="mc-part-ic">⧉</span>Copier le lien';
  copie.addEventListener("click", function () {
    var b = copie;
    navigator.clipboard.writeText(url).then(function () {
      b.lastChild.nodeValue = "Lien copié";
      setTimeout(function () { b.lastChild.nodeValue = "Copier le lien"; }, 2000);
    }, function () {
      b.lastChild.nodeValue = "Copie impossible";
    });
  });
  menu.appendChild(copie);

  function fermer() {
    menu.classList.remove("ouvert");
    btn.setAttribute("aria-expanded", "false");
  }
  btn.addEventListener("click", function (e) {
    e.stopPropagation();
    var ouvert = menu.classList.toggle("ouvert");
    btn.setAttribute("aria-expanded", ouvert ? "true" : "false");
  });
  document.addEventListener("click", function (e) {
    if (!boite.contains(e.target)) fermer();
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") fermer();
  });

  boite.appendChild(btn);
  boite.appendChild(menu);

  // Placement ADAPTATIF. Premiere version : append systematique dans la nav.
  // Sur mobile, la barre est deja saturee (logo, burger, « Ecouter », « Voir »)
  // et le bouton la faisait deborder de 51 px -- exactement ce qu'on voulait
  // eviter. On mesure donc apres insertion : si la nav deborde, le bouton
  // rejoint le menu burger, ou se pose en flottant. Mesurer plutot que de se
  // fier a un point de rupture couvre aussi les navs qu'on n'a pas prevues.
  function deborde(nav) {
    if (nav.scrollWidth > nav.clientWidth + 1) return true;
    // On mesure la contribution PROPRE du bouton : une page peut deja
    // deborder pour une autre raison, et il serait absurde de replier le
    // bouton a cause d'un tableau large ailleurs dans la page.
    var avec = document.documentElement.scrollWidth;
    boite.style.display = "none";
    var sans = document.documentElement.scrollWidth;
    boite.style.display = "";
    return avec > sans;
  }

  // Remet la boite et le menu dans leur etat neutre : chaque placement repart
  // de zero, ce qui permet de re-placer apres chargement ou redimensionnement.
  function neutre() {
    boite.className = "mc-part";
    boite.removeAttribute("style");
    menu.removeAttribute("style");
  }

  // Deuxieme version corrigee, apres deux defauts vus sur l'episode 46 :
  //  1. le repli se declenchait a tort -- la mesure tournait avant que les
  //     polices soient chargees, la nav semblait deborder un instant ;
  //  2. le repli superposait le bouton a un element de la nav (« Episode 46 »
  //     sur les pages episodes, « Ecouter » sur l'accueil a 1 024 px).
  // Desormais : on re-place a chaque evenement de mise en page, et on ne
  // superpose JAMAIS le bouton a la barre -- par ordre de preference : en
  // flux avec libelle, en flux icone seule, dans le burger s'il est actif,
  // et en dernier recours sous la barre, hors de toute zone de texte.
  function placer() {
    if (menu.classList.contains("ouvert")) return;   // ne pas bouger sous le doigt
    var nav = document.querySelector("nav");
    neutre();
    if (!nav) {
      boite.style.position = "fixed";
      boite.style.top = "12px";
      boite.style.right = "14px";
      boite.style.zIndex = "700";
      document.body.appendChild(boite);
      return;
    }
    var enFlex = getComputedStyle(nav).display.indexOf("flex") >= 0;

    if (enFlex) {
      boite.style.marginLeft = "auto";
      nav.appendChild(boite);
      if (!deborde(nav)) return;
      boite.classList.add("mc-part-compact");      // icone seule
      if (!deborde(nav)) return;
      boite.classList.remove("mc-part-compact");
    }

    var burger = nav.querySelector(".nav-burger");
    var enBurger = burger && getComputedStyle(burger).display !== "none";
    var menuNav = enBurger ? nav.querySelector(".nav-links") : null;
    if (menuNav) {
      // Le menu burger accueille deja les liens secondaires : le bouton y est
      // a sa place et ne coute aucune largeur a la barre.
      boite.removeAttribute("style");
      boite.classList.add("mc-part-replie");
      menu.style.position = "static";
      menu.style.background = "none";
      menu.style.border = "0";
      menu.style.boxShadow = "none";
      menu.style.minWidth = "0";
      menuNav.appendChild(boite);
      return;
    }

    // Dernier recours : sous la barre, aligne a droite. Jamais par-dessus.
    if (getComputedStyle(nav).position === "static") nav.style.position = "relative";
    boite.removeAttribute("style");
    boite.style.position = "absolute";
    boite.style.top = "calc(100% + 6px)";
    boite.style.right = "14px";
    boite.style.zIndex = "600";
    nav.appendChild(boite);
  }

  var minuterie = null;
  function replacerBientot() {
    clearTimeout(minuterie);
    minuterie = setTimeout(placer, 150);
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", placer);
  } else {
    placer();
  }
  // Les polices web elargissent la nav apres coup : on re-mesure une fois
  // tout charge, puis a chaque redimensionnement.
  window.addEventListener("load", placer);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(placer);
  window.addEventListener("resize", replacerBientot);
})();
