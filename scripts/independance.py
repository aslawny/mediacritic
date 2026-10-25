# -*- coding: utf-8 -*-
"""
Classement « podcast independant » : SOURCE UNIQUE (25/10/2026).

Utilise par generate_independants.py (le guide), generate_fiches.py (label
des fiches et champ `independant` de catalog.json, lu par les vignettes de
l'accueil et de l'annuaire). Ne jamais recopier ces listes ailleurs : deux
definitions finiraient par diverger et le label contredirait le guide.

Definition validee par l'utilisateur : ni media (radio, TV, presse), ni
institution ou marque, ni studio ou reseau de podcasts professionnel ;
podcasts seulement. Apres toute modification des listes, relire a la main
les listes publiees de podcasts-independants.html.
"""
import re
import unicodedata


def _norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s.lower()).strip()


# Editeurs exclus, compares au nom normalise (sans accent, minuscules).
# Un editeur est exclu si son nom CONTIENT l'une de ces chaines.
EDITEURS_EXCLUS = [
    # Audiovisuel public et radios/TV privees
    "radio france", "france inter", "france culture", "france musique",
    "france bleu", "franceinfo", "france info", "france televisions",
    "france tv", "france 24", "france medias monde", "rfi", "fip", "mouv",
    "rtbf", "rts -", "radio television suisse", "radio-canada", "cbc",
    "ici premiere", "tv5", "arte", "ina", "lumni", "public senat", "lcp",
    "rtl", "europe 1", "europe1", "europe 2", "rmc", "bfm", "cnews", "lci",
    "tf1", "m6", "canal+", "nrj", "skyrock", "nostalgie", "cherie fm",
    "rfm", "fun radio", "fun_radio", "virgin radio", "oui fm", "tsf",
    "sud radio", "qub", "cogeco", "iheartradio", "radio nova", "nova",
    "rire et chansons", "kto", "rcj", "radioj", "beur fm", "medi1",
    "eurosport", "radio classique", "bel rtl", "rtl2",
    # Presse
    "le monde", "le figaro", "madame figaro", "les echos", "l'equipe",
    "le parisien", "le point", "l'express", "liberation", "la croix",
    "bayard", "ouest-france", "ouest france", "sud ouest", "la voix du nord",
    "la presse", "l'independant", "le temps", "mediapart", "slate",
    "konbini", "madmoizelle", "elle", "prisma", "unique heritage",
    "challenges", "capital", "l'obs", "telerama", "courrier international",
    "les inrocks", "20 minutes", "huffpost", "brut", "loopsider", "usbek",
    "socialter", "alternatives economiques", "le devoir", "siecle digital",
    # Studios et reseaux de podcasts
    "binge audio", "nouvelles ecoutes", "bababam", "louie media", "engle",
    "choses a savoir", "acast", "audion", "majelan", "initial studio",
    "bliss studio", "bambou studio", "sonique", "orso media", "podcut",
    "audio360", "audioactif", "decode media", "inception point",
    "spotify studios", "paradiso", "studio minuit", "sybel", "audible",
    "label sauvage", "brigitte prod", "cosmic", "europe 1 studio",
    "sportcast", "sunday night productions", "dynamic one", "vocast",
    "sports content", "mylymedias", "wave.audio", "taleming",
    "encore une histoire", "les podcasteurs",
    # Relus a la main le 24/10/2026 dans les listes publiees : magazine,
    # emission de television, editeur, marque, institution.
    "famille chretienne", "quotidien", "cerveau & psycho", "urban comics",
    "les others", "morphee", "cuen",
    # Institutions, administrations, entreprises
    "college de france", "bibliotheque nationale", "bnf", "cinematheque",
    "comedie-francaise", "chateau de versailles", "institut de france",
    "institut du monde arabe", "banque de france", "assurance maladie",
    "totalenergies", "ramsay sante", "acadomia", "boursorama", "ministere",
    "senat", "assemblee nationale", "cnrs", "inserm", "ademe",
]

# Mots qui, dans un nom d'editeur, signalent un media, une institution ou
# un studio (bornes de mot pour eviter « Fabrice FLORENT » -> « fm »).
MOTS_EXCLUS = re.compile(
    r"\b(radio|radios|fm|tv|tele|television|media|medias|studio|studios|"
    r"productions?|prod|network|universite|university|unil|institut|ecole|"
    r"musee|bibliotheque|fondation|ministere|mairie|ville de|region|"
    r"departement|groupe|group|editions|magazine|journal|news|presse|"
    r"podcasts? network|cfak|cism|ckrl|choq|cibl|cjmd)\b")

# Noms qui ne disent rien de l'editeur : impossible de juger, on exclut.
INCONNUS = {"", "?", "unknown", "inconnu", "all", "global"}


def est_independant(item):
    """True si le podcast passe le filtre d'independance."""
    if item.get("type") == "youtube":
        return False
    a = _norm(item.get("author"))
    if a in INCONNUS:
        return False
    if any(e in a for e in EDITEURS_EXCLUS):
        return False
    return not MOTS_EXCLUS.search(a)
