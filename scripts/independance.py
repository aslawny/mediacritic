# -*- coding: utf-8 -*-
"""
Classement « independant » (podcasts ET chaines YouTube) : SOURCE UNIQUE.

Utilise par generate_independants.py (le guide), generate_fiches.py (label
des fiches et champ `independant` de catalog.json, lu par les vignettes de
l'accueil et de l'annuaire). Ne jamais recopier ces listes ailleurs : deux
definitions finiraient par diverger et le label contredirait le guide.

Definition validee par l'utilisateur : ni media (radio, TV, presse), ni
institution ou marque, ni studio ou reseau de podcasts professionnel ;
etendu aux chaines YouTube le 25/10/2026 (meme definition, plus : ni club ou
federation sportive, ni ferme a contenu, ni chaine d'artiste geree par une
maison de disques — « uniquement les independants », choix de l'utilisateur).
Apres toute modification des listes, relire a la main les listes publiees
de podcasts-independants.html.

Comparaison MOT A MOT depuis le 25/10/2026 : la recherche de sous-chaines
excluait « Nina Gorlier » et « Winamax » (ina), « Estelle » (elle),
« Clement Viktorovitch » (kto)… Les noms faits de mots courants (« Le Monde »,
« Elle », « Arte ») ne comptent que s'ils sont le nom ENTIER de l'editeur :
« Le Monde a l'envers » est une chaine independante.
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

# Ajouts mot a mot (variantes collees que la recherche de sous-chaines
# attrapait par hasard).
EDITEURS_EXCLUS += ["rtl2", "tsfjazz", "bfmtv", "rts", "l equipe", "quelle histoire",
                    # Marques (paris sportifs) : jamais « independant » ni mises en avant.
                    "winamax", "betclic", "unibet", "parions sport", "pmu", "fdj"]

# Noms faits de mots courants : exclus seulement s'ils sont le nom entier.
NOMS_ENTIERS = {"le monde", "elle", "capital", "challenges", "brut",
                "quotidien", "cosmic", "sonique", "paradiso", "nova", "mouv",
                "global", "la vie", "investigation"}

# Chaines YouTube : clubs et institutions sportives, studios de groupes TV,
# fermes a contenu et societes, maisons de disques. Les plus suivies ont ete
# relues a la main le 25/10/2026.
EXCLUS_YOUTUBE = [
    "psg", "paris saint germain", "federation francaise", "ligue 1", "ligue 2",
    "olympique", "as monaco", "stade rennais", "losc", "fc", "football club",
    "uefa", "fifa", "nba", "roland garros", "tour de france",
    "golden moustache", "studio bagel", "webedia", "jeuxvideo com", "gamekult",
    "brico sympa", "sympa", "5 minute", "bebefinn", "pinkfong", "cocomelon",
    "thesoul", "vevo", "records", "music group", "universal", "sony music",
    "warner", "def jam", "believe", "polydor", "capitol", "rec 118", "label",
    # Relecture des 160 chaines les plus suivies (25/10/2026)
    "the first take", "tv5monde", "bein sports", "c est pas sorcier",
    "telefoot", "foot mercato", "montreux comedy", "watchmojo", "nat geo",
    "disney", "boxoffice", "films complets", "africanews", "blast", "cercle",
    "bugatti", "diana and roma", "cartoon network",
    "om", "tvl", "aj+", "karate bushido", "ortm", "trt", "100% docs", "100 docs",
    "winamax", "un gars une fille",
    "jv jeux video", "unisport", "chefclub", "marmiton", "investig action", "automoto",
    "automotomagazine", "medi1tv", "prime video", "dc super hero", "francetv", "flapacha",
    "lou la serie",
    "quelle histoire",
    # Une chaine d'homme ou de parti politique n'est pas un « createur
    # independant » : le mot y prendrait un sens politique.
    "jean luc melenchon", "florian philippot", "eric zemmour", "emmanuel macron",
]
# Chaines d'artistes signes en maison de disques (relecture du 25/10/2026).
# Un artiste ne figure ici que si sa chaine est celle d'un artiste en label.
ARTISTES_EN_LABEL = {"gims", "ninho", "lacrim", "sch", "le rappeur damso",
                     "gazo officiel", "maes officiel", "rk officiel",
                     "sofiane officiel", "plk tv", "b20baofficiel"}
# Verifies independants malgre un nom qui ferait douter (ex. : PNL, autoproduit
# sur son propre label QLF Records).
INDEPENDANTS_VERIFIES = {"pnl"}

# Noms qui ne disent rien de l'editeur : impossible de juger, on exclut.
INCONNUS = {"", "?", "unknown", "inconnu", "all", "global"}


def _mots(s):
    return " " + " ".join(re.sub(r"[^a-z0-9&+]+", " ", _norm(s)).split()) + " "


_EXCLUS_MOTS = [_mots(e) for e in EDITEURS_EXCLUS if _norm(e) not in NOMS_ENTIERS]
_EXCLUS_YT = [_mots(e) for e in EXCLUS_YOUTUBE]


def est_independant(item):
    """True si le podcast ou la chaine passe le filtre d'independance."""
    yt = item.get("type") == "youtube"
    # Pour une chaine, l'« editeur » est le nom de la chaine (le bot y
    # recopie le titre) : on juge les deux.
    noms = {_norm(item.get("author"))}
    if yt:
        noms.add(_norm(item.get("title")))
    for a in noms:
        m = _mots(a)
        if m.strip() in INDEPENDANTS_VERIFIES:
            return True
    for a in noms:
        if a in INCONNUS:
            return False
        m = _mots(a)
        if m.strip() in NOMS_ENTIERS:
            return False
        if any(e in m for e in _EXCLUS_MOTS):
            return False
        mots = " ".join(m.split())
        if yt:
            # « TV » dans un nom de chaine est courant chez les createurs
            # seuls (« Anyme TV ») : il ne prouve rien sur YouTube.
            mots = re.sub(r"(^| )tv( |$)", " ", mots)
        if MOTS_EXCLUS.search(mots):
            return False
        if yt and (any(e in m for e in _EXCLUS_YT) or m.strip() in ARTISTES_EN_LABEL):
            return False
    return True


# Textes du label, partages par les fiches, les pages episodes et le JS.
INFOBULLE = "Publié hors médias, studios, marques et institutions : voir le guide"


def libelle(item):
    return "Chaîne indépendante" if item.get("type") == "youtube" else "Podcast indépendant"
