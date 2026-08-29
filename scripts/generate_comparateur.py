#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Genere comparer.html : le comparateur de podcasts et chaines YouTube.

La comparaison est entierement cote client : la page ne depend d'aucune
donnee a la generation. Elle est quand meme generee (et pas ecrite a la main)
pour que le CSS, la nav et le pied de page restent une seule source --
meme regle que generate_categories.py et generate_classement.py.

⚠️ SEO -- le canonical est FIXE sur /comparer.html, sans parametres.
Avec 8 348 contenus, les URL ?a=..&b=.. representent des dizaines de millions
de combinaisons. Les laisser indexables reviendrait a produire des pages
satellites en masse. On indexe la page, jamais les paires.

Les axes de comparaison affichés dependent de ce qui existe reellement :
  note MediaCritic /10  45 fiches      note Apple + avis   66 %
  abonnes YouTube       14 %           frequence / activite 11-13 %
Une ligne dont aucun des deux contenus n'a la valeur n'est pas affichee.
On n'invente rien pour remplir le tableau.

Usage : python scripts/generate_comparateur.py
"""
import html
import json
import re
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
BASE = "https://www.mediacritic.fr"
GA = "G-3W2VTTEWG8"
NB_SUGGESTIONS = 12
MAX_PAR_CONTENU = 2



def h(s):
    return html.escape(str(s or ""), quote=True)


def _css():
    src = subprocess.run(["git", "show", "HEAD:categories/gaming.html"],
                         cwd=ROOT, capture_output=True, text=True,
                         encoding="utf-8").stdout
    m = re.search(r"<style>.*?</style>", src, re.DOTALL)
    return m.group(0) if m else "<style></style>"


def suggestions(cat):
    """Paires proposees : deux contenus analyses par MediaCritic partageant une
    categorie. Ce sont de vrais liens internes, presents dans le HTML servi --
    la page n'est donc pas vide pour un moteur qui n'execute pas le JS."""
    mc = [x for x in cat if x.get("mcNote")]
    vues, paires = set(), []
    for i, a in enumerate(mc):
        for b in mc[i + 1:]:
            communes = set(a.get("categories") or []) & set(b.get("categories") or [])
            if not communes:
                continue
            cle = (a["slug"], b["slug"])
            if cle in vues:
                continue
            vues.add(cle)
            paires.append((a, b, sorted(communes)[0]))
    # Les paires aux notes proches sont les plus interessantes a lire, mais un
    # tri sur ce seul critere faisait remonter le meme contenu six fois : beaucoup
    # de fiches partagent la note 8, donc un ecart nul. Plafond par contenu.
    paires.sort(key=lambda p: abs(float(p[0]["mcNote"]) - float(p[1]["mcNote"])))
    vus, retenues = {}, []
    for a, b, c in paires:
        if vus.get(a["slug"], 0) >= MAX_PAR_CONTENU or vus.get(b["slug"], 0) >= MAX_PAR_CONTENU:
            continue
        vus[a["slug"]] = vus.get(a["slug"], 0) + 1
        vus[b["slug"]] = vus.get(b["slug"], 0) + 1
        retenues.append((a, b, c))
        if len(retenues) >= NB_SUGGESTIONS:
            break
    return retenues


CMP_CSS = """<style>/* mc-cmp : comparateur */
.cmp-wrap{max-width:1000px;margin:0 auto;padding:0 20px 60px}
.cmp-slots{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:26px}
.cmp-slot{background:rgba(13,26,48,.7);border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:14px;min-height:132px;display:flex;flex-direction:column;gap:10px}
.cmp-slot.vide{border-style:dashed;align-items:center;justify-content:center}
.cmp-search{width:100%;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.12);border-radius:9px;color:inherit;font:inherit;font-size:.9rem;padding:9px 12px}
.cmp-search:focus{outline:none;border-color:#e8622d}
.cmp-res{list-style:none;margin:6px 0 0;padding:0;max-height:230px;overflow-y:auto;display:flex;flex-direction:column;gap:1px}
.cmp-res li{padding:7px 9px;border-radius:7px;cursor:pointer;display:flex;align-items:center;gap:9px;font-size:.86rem}
.cmp-res li:hover,.cmp-res li[aria-selected=true]{background:rgba(232,98,45,.16)}
.cmp-res img{width:30px;height:30px;border-radius:6px;object-fit:cover;flex:0 0 30px}
.cmp-res span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cmp-choisi{display:flex;gap:12px;align-items:flex-start}
.cmp-choisi img{width:64px;height:64px;border-radius:10px;object-fit:cover;flex:0 0 64px}
.cmp-choisi h3{font-size:1rem;line-height:1.25;margin:0 0 3px}
.cmp-choisi h3 a{color:inherit;text-decoration:none}
.cmp-choisi h3 a:hover{color:#e8622d}
.cmp-choisi p{font-size:.78rem;color:rgba(240,244,250,.5);margin:0}
.cmp-vider{background:none;border:none;color:rgba(240,244,250,.4);cursor:pointer;font-size:1.1rem;line-height:1;padding:2px 4px;margin-left:auto}
.cmp-vider:hover{color:#e8622d}
.cmp-table{width:100%;border-collapse:collapse;font-size:.9rem}
.cmp-table th,.cmp-table td{padding:11px 12px;text-align:center;border-top:1px solid rgba(255,255,255,.07)}
.cmp-table th[scope=row]{text-align:left;font-weight:500;color:rgba(240,244,250,.55);width:31%;font-size:.84rem}
.cmp-table td{font-weight:600;font-variant-numeric:tabular-nums}
.cmp-table td.gagne{color:#e8622d}
.cmp-table td.nd{color:rgba(240,244,250,.25);font-weight:400}
.cmp-cats{font-weight:400;font-size:.8rem;color:rgba(240,244,250,.6)}
.cmp-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:22px}
/* display:flex l'emporte sur l'attribut hidden : sans cette regle, la barre
   d'actions reste visible tant qu'aucun contenu n'est choisi. */
[hidden]{display:none !important}
.cmp-btn{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);color:inherit;font:inherit;font-size:.85rem;padding:9px 15px;border-radius:9px;cursor:pointer;text-decoration:none}
.cmp-btn:hover{border-color:#e8622d;color:#e8622d}
.cmp-note{font-size:.82rem;color:rgba(240,244,250,.45);margin-top:18px;line-height:1.6}
.cmp-sugg{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(285px,1fr));gap:8px}
.cmp-sugg a{display:block;padding:11px 13px;border:1px solid rgba(255,255,255,.07);border-radius:10px;text-decoration:none;color:inherit;font-size:.87rem;line-height:1.4}
.cmp-sugg a:hover{border-color:#e8622d}
.cmp-sugg em{font-style:normal;color:rgba(240,244,250,.4);font-size:.78rem;display:block;margin-top:2px}
@media(max-width:700px){
.cmp-slots{grid-template-columns:1fr}
.cmp-table th[scope=row]{width:40%;font-size:.79rem}
.cmp-table th,.cmp-table td{padding:9px 7px;font-size:.85rem}
}</style>"""


# JS garde hors f-string : les accolades d'un script dans un f-string sont un
# nid a bugs, et les doubler rend le code illisible a la relecture.
CMP_JS = r"""<script>
(function(){
var LITE='data/catalog-lite.json', FULL='data/catalog.json';
var cat=[], parSlug={}, plein=false, chargement=false, sel=[null,null], detail={};

function $(s){return document.querySelector(s);}
function esc(s){var d=document.createElement('div');d.textContent=s==null?'':s;return d.innerHTML;}

function indexer(d){
  cat=d; parSlug={};
  for(var i=0;i<d.length;i++) parSlug[d[i].slug]=d[i];
}
function chargerPlein(cb){
  if(plein){cb&&cb();return;}
  if(chargement){cb&&setTimeout(function(){chargerPlein(cb);},250);return;}
  chargement=true;
  fetch(FULL).then(function(r){return r.json();}).then(function(d){
    plein=true;chargement=false;indexer(d);
    for(var i=0;i<2;i++) if(sel[i]&&parSlug[sel[i].slug]) sel[i]=parSlug[sel[i].slug];
    rendre();cb&&cb();
  }).catch(function(){chargement=false;cb&&cb();});
}

/* Recherche volontairement simple : sous-chaine sur titre puis auteur, les
   plus populaires d'abord. Fuse.js n'apporterait rien ici -- on cherche un
   titre qu'on connait deja, pas un theme. */
function chercher(q){
  q=q.trim().toLowerCase(); if(q.length<2) return [];
  var t=[],a=[];
  for(var i=0;i<cat.length;i++){
    var x=cat[i];
    if((x.title||'').toLowerCase().indexOf(q)>=0) t.push(x);
    else if((x.author||'').toLowerCase().indexOf(q)>=0) a.push(x);
    if(t.length>60) break;
  }
  var pop=function(u,v){return (v.ratingCount||v.subscribers||0)-(u.ratingCount||u.subscribers||0);};
  return t.sort(pop).concat(a.sort(pop)).slice(0,8);
}

function detailsDe(slug){
  if(detail[slug]!==undefined) return Promise.resolve(detail[slug]);
  return fetch('data/content/'+slug+'.json').then(function(r){
    return r.ok?r.json():null;
  }).catch(function(){return null;}).then(function(d){detail[slug]=d;return d;});
}

function choisir(i,x){
  sel[i]=x; rendre(); majUrl();
  if(x) detailsDe(x.slug).then(function(){rendre();});
}

function majUrl(){
  var p=[];
  if(sel[0]) p.push('a='+encodeURIComponent(sel[0].slug));
  if(sel[1]) p.push('b='+encodeURIComponent(sel[1].slug));
  history.replaceState(null,'',location.pathname+(p.length?'?'+p.join('&'):''));
}

function slot(i){
  var x=sel[i], d=document.createElement('div');
  d.className='cmp-slot'+(x?'':' vide');
  if(x){
    var img=x.image?'<img src="'+esc(x.image)+'" alt="" loading="lazy">':'';
    d.innerHTML='<div class="cmp-choisi">'+img+'<div><h3><a href="fiches/'+esc(x.slug)+
      '.html">'+esc(x.title)+'</a></h3><p>'+esc((x.author||'').slice(0,46))+'</p></div>'+
      '<button class="cmp-vider" aria-label="Retirer ce contenu">&#215;</button></div>';
    d.querySelector('.cmp-vider').onclick=function(){choisir(i,null);};
  }else{
    d.innerHTML='<input class="cmp-search" type="search" placeholder="Chercher un podcast ou une chaîne…" '+
      'aria-label="Chercher le contenu '+(i+1)+' à comparer"><ul class="cmp-res"></ul>';
    var inp=d.querySelector('.cmp-search'), ul=d.querySelector('.cmp-res');
    inp.addEventListener('input',function(){
      if(!plein) chargerPlein(function(){inp.dispatchEvent(new Event('input'));});
      var r=chercher(inp.value); ul.innerHTML='';
      r.forEach(function(x){
        var li=document.createElement('li');
        li.innerHTML=(x.image?'<img src="'+esc(x.image)+'" alt="" loading="lazy">':'')+
          '<span>'+esc(x.title)+'</span>';
        li.onclick=function(){choisir(i,x);};
        ul.appendChild(li);
      });
      if(inp.value.trim().length>=2&&!r.length)
        ul.innerHTML='<li style="cursor:default;color:rgba(240,244,250,.4)">Aucun résultat'+
          (plein?'':' — chargement du catalogue…')+'</li>';
    });
  }
  return d;
}

function nb(n){return String(n).replace(/\B(?=(\d{3})+(?!\d))/g,' ');}

/* Une ligne n'existe que si au moins un des deux contenus porte la valeur :
   pas de case vide en face d'une autre case vide. */
function lignes(){
  var A=sel[0], B=sel[1], dA=A?detail[A.slug]:null, dB=B?detail[B.slug]:null;
  var v=function(x,d,f){return x?f(x,d||{}):null;};
  var typ=function(x){return x.type==='youtube'?'Chaîne YouTube':'Podcast';};
  var freq=function(x,d){var j=d.frequence_jours;
    if(!j) return null;
    if(j<=1.5) return 'Quotidien';
    if(j<=9) return 'Hebdomadaire';
    if(j<=17) return 'Bimensuel';
    if(j<=45) return 'Mensuel';
    return 'Irrégulier';};
  var mc=function(x){return x.mcNote?String(x.mcNote).replace('.',',')+'/10':null;};
  var ap=function(x){return x.rating?(+x.rating).toFixed(1).replace('.',',')+'/5':null;};
  var av=function(x){return x.ratingCount?nb(x.ratingCount):null;};
  var ab=function(x){return x.subscribers?nb(x.subscribers):null;};
  var ct=function(x){return (x.categories||[]).slice(0,4).join(', ')||null;};
  var ac=function(x,d){return d.derniere_activite||null;};
  return [
    {l:'Type', a:v(A,dA,typ), b:v(B,dB,typ), cmp:0},
    {l:'Note MediaCritic', a:v(A,dA,mc), b:v(B,dB,mc), cmp:1,
     na:A&&A.mcNote?+A.mcNote:null, nbv:B&&B.mcNote?+B.mcNote:null},
    {l:'Note Apple Podcasts', a:v(A,dA,ap), b:v(B,dB,ap), cmp:1,
     na:A&&A.rating?+A.rating:null, nbv:B&&B.rating?+B.rating:null},
    {l:'Nombre d’avis', brut:1, a:v(A,dA,av), b:v(B,dB,av), cmp:1,
     na:A&&A.ratingCount?+A.ratingCount:null, nbv:B&&B.ratingCount?+B.ratingCount:null},
    {l:'Abonnés YouTube', a:v(A,dA,ab), b:v(B,dB,ab), cmp:1,
     na:A&&A.subscribers?+A.subscribers:null, nbv:B&&B.subscribers?+B.subscribers:null},
    {l:'Rythme de publication', a:v(A,dA,freq), b:v(B,dB,freq), cmp:0},
    {l:'Dernière activité', a:v(A,dA,ac), b:v(B,dB,ac), cmp:0},
    {l:'Catégories', cls:'cmp-cats', a:v(A,dA,ct), b:v(B,dB,ct), cmp:0}
  ].filter(function(r){return r.a||r.b;});
}

function rendre(){
  var s=$('#cmp-slots'); s.innerHTML=''; s.appendChild(slot(0)); s.appendChild(slot(1));
  var z=$('#cmp-zone');
  if(!sel[0]||!sel[1]){
    z.innerHTML=''; $('#cmp-actions').hidden=true; $('#cmp-sugg-bloc').hidden=false;
    document.title=TITRE; return;
  }
  $('#cmp-sugg-bloc').hidden=true;
  var h='<table class="cmp-table"><thead><tr><td></td><th scope="col">'+
    esc(sel[0].title)+'</th><th scope="col">'+esc(sel[1].title)+'</th></tr></thead><tbody>';
  lignes().forEach(function(r){
    var ca='',cb='';
    if(r.cmp&&r.na!=null&&r.nbv!=null&&r.na!==r.nbv){ if(r.na>r.nbv) ca='gagne'; else cb='gagne'; }
    var cl=r.cls||'';
    h+='<tr><th scope="row">'+r.l+'</th>'+
       '<td class="'+(r.a?ca+' '+cl:'nd')+'">'+(r.a?esc(r.a):'&#8212;')+'</td>'+
       '<td class="'+(r.b?cb+' '+cl:'nd')+'">'+(r.b?esc(r.b):'&#8212;')+'</td></tr>';
  });
  z.innerHTML=h+'</tbody></table>';
  $('#cmp-actions').hidden=false;
  $('#cmp-a').href='fiches/'+sel[0].slug+'.html'; $('#cmp-a').textContent='Fiche : '+sel[0].title;
  $('#cmp-b').href='fiches/'+sel[1].slug+'.html'; $('#cmp-b').textContent='Fiche : '+sel[1].title;
  document.title=sel[0].title+' ou '+sel[1].title+' ? Comparateur MediaCritic';
}

var TITRE=document.title;
$('#cmp-lien').onclick=function(){
  var b=this;
  navigator.clipboard.writeText(location.href).then(function(){
    b.textContent='Lien copié';setTimeout(function(){b.textContent='Copier le lien';},2000);
  }).catch(function(){});
};
$('#cmp-inverser').onclick=function(){sel=[sel[1],sel[0]];rendre();majUrl();};

var q=new URLSearchParams(location.search), pa=q.get('a'), pb=q.get('b');
fetch(LITE).then(function(r){return r.json();}).then(function(d){
  indexer(d);
  if(pa||pb){
    chargerPlein(function(){
      if(pa&&parSlug[pa]) choisir(0,parSlug[pa]);
      if(pb&&parSlug[pb]) choisir(1,parSlug[pb]);
    });
  }
  rendre();
}).catch(function(){chargerPlein();});
})();
</script>"""


def main():
    cat = json.loads((ROOT / "data" / "catalog.json").read_text(encoding="utf-8"))
    paires = suggestions(cat)

    sugg = "".join(
        '<li><a href="comparer.html?a=%s&amp;b=%s">%s <span aria-hidden="true">vs</span> %s'
        '<em>%s &middot; %s/10 contre %s/10</em></a></li>' % (
            a["slug"], b["slug"], h(a["title"]), h(b["title"]), h(c.capitalize()),
            str(a["mcNote"]).replace(".", ","), str(b["mcNote"]).replace(".", ","))
        for a, b, c in paires)

    titre = "Comparateur de podcasts francophones | MediaCritic"
    desc = ("Comparez deux podcasts ou chaînes YouTube francophones côte à côte : "
            "notes MediaCritic et Apple Podcasts, nombre d'avis, abonnés, rythme "
            "de publication.")

    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebApplication", "name": "Comparateur MediaCritic",
         "url": f"{BASE}/comparer.html",
         "applicationCategory": "ReferenceApplication",
         "operatingSystem": "Tout navigateur web",
         "inLanguage": "fr-FR", "isAccessibleForFree": True,
         "description": desc,
         "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR"},
         "isPartOf": {"@id": BASE + "/#annuaire"}},
        {"@type": "DataCatalog", "@id": BASE + "/#annuaire",
         "name": "Annuaire MediaCritic des podcasts et chaînes YouTube francophones",
         "alternateName": ["Annuaire podcast francophone",
                           "Répertoire collaboratif de podcasts",
                           "Le guide des podcasts indépendants"],
         "url": f"{BASE}/catalogue.html",
         "inLanguage": "fr-FR", "isAccessibleForFree": True},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "MediaCritic", "item": BASE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Comparateur",
             "item": f"{BASE}/comparer.html"}]}]}

    page = """<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>%(titre)s</title>
<meta name="description" content="%(desc)s" />
<meta name="robots" content="index, follow" />
<!-- Meme politique de securite que l'accueil et l'annuaire : une page
     generee ne doit pas etre le maillon faible. -->
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; img-src 'self' data: https://*.spotifycdn.com https://*.spotify.com https://*.googleusercontent.com https://yt3.ggpht.com https://yt3.googleusercontent.com https://*.ytimg.com https://*.mzstatic.com https://image-cdn-fa.spotifycdn.com https://image-cdn-ak.spotifycdn.com https://i.scdn.co https://is1-ssl.mzstatic.com https://*.podcloud.fr; script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; connect-src 'self' https://www.google-analytics.com https://analytics.google.com https://region1.google-analytics.com; frame-src 'none'; object-src 'none'; base-uri 'self'; form-action 'self' mailto:; frame-ancestors 'none';" />
<meta name="referrer" content="strict-origin-when-cross-origin" />
<meta http-equiv="Permissions-Policy" content="camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()" />
<!-- Canonical FIXE, sans parametres : les paires ?a=..&b=.. representent des
     dizaines de millions d'URL. On indexe l'outil, jamais les combinaisons. -->
<link rel="canonical" href="%(base)s/comparer.html" />
<meta property="og:type" content="website" />
<meta property="og:url" content="%(base)s/comparer.html" />
<meta property="og:title" content="%(titre)s" />
<meta property="og:description" content="%(desc)s" />
<meta property="og:image" content="%(base)s/assets/banner.png" />
<meta property="og:locale" content="fr_FR" />
<meta property="og:site_name" content="MediaCritic" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:site" content="@MediaCriticInc" />
<link rel="icon" href="assets/logo.png" type="image/png" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&amp;family=Syne:wght@600;700;800&amp;display=swap" rel="stylesheet" />
<script type="application/ld+json">%(ld)s</script>
%(css)s
%(cmpcss)s
</head>
<body>
<nav><div class="nav-left">
<a href="index.html" class="nav-back">&larr; Accueil</a>
<span class="nav-brand">MediaCritic</span></div>
<div class="nav-links">
<a href="catalogue.html">Annuaire</a>
<a href="classement.html">Classement</a>
<a href="comparer.html" class="active">Comparateur</a>
<a href="palmares.html">&#127942; Palmar&egrave;s</a></div></nav>

<header class="page-header">
<div class="breadcrumb"><a href="index.html">MediaCritic</a> &middot; <strong>Comparateur</strong></div>
<h1>Comparer deux podcasts ou cha&icirc;nes YouTube</h1>
<p class="lede">Choisissez deux contenus de l&rsquo;annuaire : notes MediaCritic et Apple
Podcasts, nombre d&rsquo;avis, abonn&eacute;s, rythme de publication et derni&egrave;re
activit&eacute; s&rsquo;affichent c&ocirc;te &agrave; c&ocirc;te. Le lien de la comparaison
est partageable.</p>
</header>

<div class="cmp-wrap">
<div class="cmp-slots" id="cmp-slots"></div>
<div id="cmp-zone"></div>

<div class="cmp-actions" id="cmp-actions" hidden>
<button class="cmp-btn" id="cmp-inverser" type="button">Inverser</button>
<button class="cmp-btn" id="cmp-lien" type="button">Copier le lien</button>
<a class="cmp-btn" id="cmp-a" href="#"></a>
<a class="cmp-btn" id="cmp-b" href="#"></a>
</div>

<section id="cmp-sugg-bloc">
<h2>Comparaisons sugg&eacute;r&eacute;es</h2>
<p class="cmp-note" style="margin-top:-6px;margin-bottom:14px">Des contenus que
nous avons analys&eacute;s dans le podcast et qui partagent un th&egrave;me.</p>
<ul class="cmp-sugg">%(sugg)s</ul>
</section>

<p class="cmp-note">Une ligne n&rsquo;appara&icirc;t que si au moins un des deux
contenus porte la donn&eacute;e. Les notes Apple Podcasts et le nombre d&rsquo;abonn&eacute;s
proviennent des plateformes ; la note sur 10 est la n&ocirc;tre, attribu&eacute;e dans
l&rsquo;&eacute;pisode consacr&eacute; au contenu. Le rythme de publication est calcul&eacute;
&agrave; partir du flux et n&rsquo;est connu que pour une partie de l&rsquo;annuaire.
&mdash; <a href="classement.html" style="color:inherit">Voir les classements</a>
&middot; <a href="catalogue.html" style="color:inherit">parcourir l&rsquo;annuaire</a>.</p>
</div>

<footer style="text-align:center;padding:30px;border-top:1px solid var(--c-border);color:var(--c-muted);font-size:.8rem">
<p>&copy; %(annee)s <a href="index.html" style="color:var(--c-muted)">MediaCritic</a> &mdash;
<a href="catalogue.html" style="color:var(--c-muted)">Annuaire</a> &mdash;
<a href="classement.html" style="color:var(--c-muted)">Classement</a> &mdash;
<a href="palmares.html" style="color:var(--c-muted)">Palmar&egrave;s</a></p>
</footer>
%(js)s
<script async src="https://www.googletagmanager.com/gtag/js?id=%(ga)s"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','%(ga)s');</script>
</body>
</html>""" % {
        "titre": h(titre), "desc": h(desc), "base": BASE,
        "ld": json.dumps(ld, ensure_ascii=False),
        "css": _css(), "cmpcss": CMP_CSS, "js": CMP_JS,
        "sugg": sugg, "annee": date.today().year, "ga": GA,
    }

    (ROOT / "comparer.html").write_text(page, encoding="utf-8")
    print("comparer.html généré")
    print(f"  {len(paires)} comparaisons suggérées (liens internes servis en HTML)")
    print(f"  title : {len(titre)} car.  |  meta : {len(desc)} car.")


if __name__ == "__main__":
    main()
