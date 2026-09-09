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

  function replier(nav) {
    var menuNav = nav.querySelector(".nav-links");
    boite.style.marginLeft = "";
    boite.style.position = "";
    boite.style.right = boite.style.top = boite.style.transform = "";
    if (menuNav) {
      // Le menu burger accueille deja les liens secondaires : le bouton y est
      // a sa place et ne coute aucune largeur a la barre.
      boite.classList.add("mc-part-replie");
      boite.style.width = "100%";
      menu.style.position = "static";
      menu.style.background = "none";
      menu.style.border = "0";
      menu.style.boxShadow = "none";
      menu.style.minWidth = "0";
      menuNav.appendChild(boite);
    } else {
      boite.style.position = "fixed";
      boite.style.top = "10px";
      boite.style.right = "10px";
      boite.style.zIndex = "700";
      document.body.appendChild(boite);
    }
  }

  function poser() {
    var nav = document.querySelector("nav");
    if (nav) {
      var st = getComputedStyle(nav);
      // Une nav en flex accueille le bouton sans deranger la mise en page ;
      // sinon on le pose en absolu dans la nav, qui devient le repere.
      if (st.display.indexOf("flex") < 0) {
        nav.style.position = nav.style.position || "relative";
        boite.style.position = "absolute";
        boite.style.right = "16px";
        boite.style.top = "50%";
        boite.style.transform = "translateY(-50%)";
      } else {
        boite.style.marginLeft = "auto";
      }
      nav.appendChild(boite);
      if (deborde(nav)) replier(nav);
    } else {
      boite.style.position = "fixed";
      boite.style.top = "12px";
      boite.style.right = "14px";
      boite.style.zIndex = "700";
      document.body.appendChild(boite);
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", poser);
  } else {
    poser();
  }
})();
