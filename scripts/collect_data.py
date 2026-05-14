#!/usr/bin/env python3
"""
MediaCritic -- Collecte de donnees catalogue
Sources : iTunes Search API (gratuit), YouTube Data API v3, Spotify API
Usage   : python collect_data.py [--mode podcast|youtube|all] [--youtube-key KEY]
"""

import json, os, re, time, urllib.request, urllib.parse, hashlib, argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    import requests as _requests_lib
    def _http_get(url, params=None, headers=None, timeout=15):
        r = _requests_lib.get(url, params=params, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()
except ImportError:
    _requests_lib = None
    def _http_get(url, params=None, headers=None, timeout=15):
        if params:
            url = url + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers=headers or {"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())

# --- Chemins ------------------------------------------------------------------
ROOT        = Path(__file__).parent.parent
DATA_DIR    = ROOT / "data" / "content"
CATALOG_OUT = ROOT / "data" / "catalog.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# --- Episodes MediaCritic -----------------------------------------------------
MEDIACRITIC_EPISODES = [
    {"ep": 1,  "slug": "la-5e-de-couv",             "title": "La 5e de Couv'",            "type": "podcast", "categories": ["livres","culture"],            "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 2,  "slug": "lesprit-critique",           "title": "L'Esprit Critique",         "type": "podcast", "categories": ["sciences","societe"],          "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 3,  "slug": "hardisk-stories",            "title": "Hardisk Stories",            "type": "podcast", "categories": ["tech","geek"],                 "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 4,  "slug": "le-podcast-du-weekend",      "title": "Le Podcast du Weekend",      "type": "podcast", "categories": ["culture","actualite"],         "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 5,  "slug": "braincast",                  "title": "BrainCast",                  "type": "podcast", "categories": ["sciences","vulgarisation"],    "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 6,  "slug": "floodcast",                  "title": "Floodcast",                  "type": "podcast", "categories": ["gaming","culture geek"],       "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 7,  "slug": "fin-du-game",                "title": "Fin du Game",                "type": "podcast", "categories": ["gaming"],                      "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 8,  "slug": "blockbusters",               "title": "BlockBusters",               "type": "podcast", "categories": ["cinema","series"],             "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 9,  "slug": "la-story-des-echos",         "title": "La Story des Echos",         "type": "podcast", "categories": ["economie","business"],         "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 10, "slug": "le-rendez-vous-tech",        "title": "Le Rendez-vous Tech",        "type": "podcast", "categories": ["tech","numerique"],            "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 11, "slug": "emotions",                   "title": "Emotions",                   "type": "podcast", "categories": ["bien-etre","psychologie"],     "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 12, "slug": "safepace",                   "title": "SafePace",                   "type": "podcast", "categories": ["sport","running","endurance"],  "itunes_id": None, "spotify_show": "7AH8nT1CoTmV1MfhxyTl3n", "youtube": None},
    {"ep": 13, "slug": "entrez-dans-lhistoire",      "title": "Entrez dans l'Histoire",    "type": "podcast", "categories": ["histoire"],                    "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 14, "slug": "seldell",                    "title": "Seldell",                    "type": "youtube", "categories": ["gaming","jeux inde"],           "itunes_id": None, "spotify_show": None,                      "youtube": "@seldell"},
    {"ep": 15, "slug": "passion-renovation",         "title": "Passion Renovation",         "type": "youtube", "categories": ["renovation","DIY","maison"],   "itunes_id": None, "spotify_show": None,                      "youtube": "@passionrenovation"},
    {"ep": 16, "slug": "chef-otaku",                 "title": "Chef Otaku",                 "type": "youtube", "categories": ["cuisine","anime","culture"],   "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 17, "slug": "lheure-du-crime",            "title": "L'Heure du Crime",          "type": "podcast", "categories": ["true crime","societe"],        "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 18, "slug": "on-va-deguster",             "title": "On va deguster",             "type": "podcast", "categories": ["gastronomie","cuisine"],       "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 19, "slug": "silicon-carne",              "title": "Silicon Carne",              "type": "podcast", "categories": ["tech","humour"],               "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 20, "slug": "extraterrien",               "title": "Extraterrien",               "type": "podcast", "categories": ["sport","societe"],             "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 21, "slug": "lafter-foot",                "title": "L'After Foot",              "type": "podcast", "categories": ["football","sport"],            "itunes_id": None, "spotify_show": None,                      "youtube": None},
    {"ep": 22, "slug": "notabene",                   "title": "NotaBene",                   "type": "youtube", "categories": ["histoire","geopolitique"],     "itunes_id": None, "spotify_show": None,                      "youtube": "@nota.bene"},
    {"ep": 23, "slug": "re-take",                    "title": "Re-Take",                    "type": "youtube", "categories": ["gaming","critique"],           "itunes_id": None, "spotify_show": None,                      "youtube": "@Retake"},
    {"ep": 24, "slug": "cest-plus-complique-que-ca", "title": "C'est plus complique que ca","type": "podcast","categories": ["histoire","societe"],          "itunes_id": None, "spotify_show": "1pvsIBHWTfk9aROklANap8",  "youtube": None},
    {"ep": 25, "slug": "le-joueur-du-grenier",       "title": "Le Joueur du Grenier",       "type": "youtube", "categories": ["gaming","retro","nostalgie"],  "itunes_id": None, "spotify_show": None,                      "youtube": "@joueurdugrenier"},
    {"ep": 26, "slug": "quelle-histoire",            "title": "Quelle Histoire",            "type": "podcast", "categories": ["histoire","enfants","education"],"itunes_id":None, "spotify_show": "76IarJo3W3YmD3e9V43wD0",  "youtube": "@quellehistoire_podcast"},
]

# --- Chaines YouTube curees ---------------------------------------------------
YOUTUBE_CHANNELS = [
    # (handle, slug, title, categories)
    ("@LeMondeOfficiel",      "le-monde",                 "Le Monde",                    ["actualite","news"]),
    ("@franceinfo",           "france-info-yt",           "franceinfo",                  ["actualite","news"]),
    ("@BFMTV",                "bfmtv",                    "BFMTV",                       ["actualite","news"]),
    ("@franceinter",          "france-inter-yt",          "France Inter",                ["actualite","culture"]),
    ("@LCP",                  "lcp",                      "LCP",                         ["actualite","politique"]),
    ("@LeMonde",              "le-monde-video",           "Le Monde Video",              ["actualite","societe"]),
    ("@mediapart",            "mediapart",                "Mediapart",                   ["actualite","societe"]),
    ("@nota.bene",            "notabene",                 "NotaBene",                    ["histoire","geopolitique"]),
    ("@Nota.Bene.History",    "notabene-history",         "NotaBene History",            ["histoire"]),
    ("@AstronoGeek",          "astronomgeek",             "AstronoGeek",                 ["sciences","espace"]),
    ("@scienceetonnante",     "science-etonnante",        "Science Etonnante",           ["sciences","vulgarisation"]),
    ("@cestpassorcier",       "cest-pas-sorcier",         "C'est pas sorcier",          ["sciences","education"]),
    ("@e-penser",             "e-penser",                 "e-penser",                    ["sciences","philosophie"]),
    ("@Kurzgesagt",           "kurzgesagt-fr",            "Kurzgesagt FR",               ["sciences","vulgarisation"]),
    ("@dirtybiology",         "dirty-biology",            "DirtyBiology",                ["sciences","biologie"]),
    ("@LeReveilleur",         "le-revilleur",             "Le Revilleur",                ["sciences","energie"]),
    ("@Hygiene_Mentale",      "hygiene-mentale",          "Hygiene Mentale",             ["sciences","philosophie"]),
    ("@videodechat",          "video-de-chat",            "Video de Chat",               ["humour","comedie"]),
    ("@joueurdugrenier",      "le-joueur-du-grenier",     "Le Joueur du Grenier",        ["gaming","retro","nostalgie"]),
    ("@Seldell",              "seldell",                  "Seldell",                     ["gaming","jeux inde"]),
    ("@Retake",               "re-take",                  "Re-Take",                     ["gaming","critique"]),
    ("@MontesinosPierre",     "pierre-montesinos",        "Pierre Montesinos",           ["gaming"]),
    ("@Benzaie",              "benzaie",                  "Benzaie",                     ["gaming","culture geek"]),
    ("@Balade_Mentale",       "balade-mentale",           "Balade Mentale",              ["psychologie","bien-etre"]),
    ("@Axolot",               "axolot",                   "Axolot",                      ["culture","curiosites"]),
    ("@LaCinetek",            "la-cinetek",               "La Cinetek",                  ["cinema","culture"]),
    ("@CritiquePlusCinema",   "critique-plus",            "Critique +",                  ["cinema","series"]),
    ("@PresentationNight",    "presentation-night",       "Presentation Night",          ["cinema","animation"]),
    ("@PassionRenovation",    "passion-renovation",       "Passion Renovation",          ["renovation","DIY","maison"]),
    ("@ChefOtakuOfficial",    "chef-otaku",               "Chef Otaku",                  ["cuisine","anime"]),
    ("@750g",                 "750g",                     "750g",                        ["gastronomie","cuisine"]),
    ("@FinDuGame",            "fin-du-game-yt",           "Fin du Game",                 ["gaming"]),
    ("@HugoDecrypte",         "hugo-decrypte",            "HugoDecrypte",                ["actualite","societe"]),
    ("@Osons_Causer",         "osons-causer",             "Osons Causer",                ["politique","societe"]),
    ("@LaPrimaire",           "la-primaire",              "La Primaire",                 ["politique","societe"]),
    ("@Blast_info",           "blast",                    "Blast",                       ["actualite","societe"]),
    ("@Bricevido",            "brice-vido",               "Brice Vido",                  ["sport","football"]),
    ("@Thibaud_Velo",         "thibaud-velo",             "Thibaud Velo",                ["sport","cyclisme"]),
    ("@AthleteFactory",       "athlete-factory",          "Athlete Factory",             ["sport","running"]),
    ("@HistoireEtCivilisation","histoire-et-civilisation","Histoire et Civilisation",    ["histoire"]),
    ("@histoirebreve",        "histoire-breve",           "Histoire Breve",              ["histoire"]),
    ("@CurieuxDeNature",      "curieux-de-nature",        "Curieux de Nature",           ["sciences","nature"]),
    ("@GoldenMoustache",      "golden-moustache",         "Golden Moustache",            ["humour","comedie"]),
    ("@LeVrai_Pore",          "le-vrai-pore",             "Le Vrai Pore",                ["humour","gaming"]),
    ("@Antlion",              "antlion",                  "Antlion",                     ["cinema","critique"]),
    ("@laboiteimages",        "la-boite-images",          "La Boite Images",             ["cinema","culture"]),
    ("@MisterJDay",           "mister-jday",              "MisterJDay",                  ["gaming","culture geek"]),
    ("@FibreTigre",           "fibre-tigre",              "FibreTigre",                  ["gaming","jeux de role"]),
    ("@Nexus6",               "nexus6",                   "Nexus6",                      ["gaming"]),
    ("@ScienceInfuse",        "science-infuse",           "Science Infuse",              ["sciences","vulgarisation"]),
    ("@Micka_Breizh",         "micka-breizh",             "Micka Breizh",                ["gaming","culture geek"]),
    ("@quellehistoire_podcast","quelle-histoire",         "Quelle Histoire",             ["histoire","enfants","education"]),
    ("@LaTerreBleue",         "la-terre-bleue",           "La Terre Bleue",              ["sciences","environnement"]),
    ("@monsieurphi",          "monsieur-phi",             "Monsieur Phi",                ["philosophie","sciences"]),
    ("@Spe_spe",              "spe-spe",                  "Spe Spe",                     ["sciences","education"]),
    ("@GauthierThullen",      "gauthier-thullen",         "Gauthier Thullen",            ["histoire","culture"]),
    ("@HistoireParis",        "histoire-paris",           "Histoire de Paris",           ["histoire","culture"]),
    ("@MissClick",            "miss-click",               "Miss Click",                  ["gaming","culture geek"]),
    ("@LamissaThiam",         "lamissa",                  "Lamissa",                     ["societe","culture"]),
    ("@LeDesordreDesChoses",  "le-desordre-des-choses",  "Le Desordre des Choses",      ["societe","culture"]),
    ("@CharlieBocheux",       "charlie-bocheux",          "Charlie Bocheux",             ["humour","societe"]),
    ("@Psykocouac",           "psykocouac",               "Psykocouac",                  ["politique","societe"]),
    ("@HistoireSociale",      "histoire-sociale",         "Histoire Sociale",            ["histoire","societe"]),
    ("@EmilikoLemon",         "emiliko-lemon",            "Emiliko Lemon",               ["gaming","jeux inde"]),
    ("@TinkerHome",           "tinker-home",              "Tinker Home",                 ["DIY","maison"]),
    ("@Amixem",               "amixem",                   "Amixem",                      ["humour","vlogs"]),
    ("@PatateMolleProd",      "patate-molle",             "Patate Molle",                ["humour","gaming"]),
    ("@BenchmarkReviews",     "benchmark-reviews",        "Benchmark Reviews FR",        ["tech","numerique"]),
    ("@LiNuXFr",              "linux-fr",                 "LinuxFr",                     ["tech","numerique"]),
    ("@HardwareFR",           "hardware-fr",              "HardwareFR",                  ["tech","numerique"]),
    ("@TopAchat",             "top-achat",                "TopAchat",                    ["tech","numerique"]),
    ("@cestquoidemaindoc",    "cest-quoi-demain",         "C'est quoi demain?",         ["environnement","societe"]),
    ("@Suricate",             "suricate",                 "Suricate",                    ["humour","comedie"]),
    ("@WandaProductions",     "wanda-productions",        "Wanda Productions",           ["humour","comedie"]),
    ("@RoflCopter2110",       "roflcopter",               "RoflCopter",                  ["gaming","humour"]),
    ("@XiaoMaNiuFan",         "xiao-ma-niu",              "Xiao Ma Niu",                 ["culture","international"]),
    ("@ChefSimon",            "chef-simon",               "Chef Simon",                  ["gastronomie","cuisine"]),
    ("@SportVsChampions",     "sport-vs-champions",       "Sport vs Champions",          ["sport"]),
    ("@bde_france",           "bde-france",               "BDE France",                  ["societe","humour"]),
]

# --- Requetes de decouverte YouTube (pool large, rotation par run) ------------
YOUTUBE_DISCOVERY_QUERIES = [
    # Histoire
    ("chaine youtube histoire france",                 ["histoire"]),
    ("chaine youtube revolution francaise guerre",     ["histoire"]),
    ("chaine youtube antiquite rome grece",            ["histoire"]),
    ("chaine youtube medieval moyen age",              ["histoire"]),
    ("chaine youtube biographie historique france",    ["histoire"]),
    ("chaine youtube mythologie greco romaine",        ["histoire"]),
    ("chaine youtube histoire mondiale civilisation",  ["histoire", "geopolitique"]),
    ("chaine youtube archeologie fouilles",            ["histoire", "sciences"]),
    # Sciences
    ("chaine youtube science vulgarisation france",    ["sciences", "vulgarisation"]),
    ("chaine youtube espace astronomie cosmos",        ["sciences", "espace"]),
    ("chaine youtube biologie nature animal",          ["sciences", "nature"]),
    ("chaine youtube physique chimie experience",      ["sciences"]),
    ("chaine youtube mathematiques maths",             ["sciences", "education"]),
    ("chaine youtube environnement ecologie",          ["environnement", "sciences"]),
    ("chaine youtube geologie mineraux",               ["sciences", "nature"]),
    ("chaine youtube medecine sante corps humain",     ["sante", "sciences"]),
    ("chaine youtube geographie pays carte",           ["sciences", "culture"]),
    # Gaming
    ("chaine youtube gaming jeux video france",        ["gaming"]),
    ("chaine youtube retrogaming retro nostalgie",     ["gaming", "retro"]),
    ("chaine youtube lets play gameplay fr",           ["gaming"]),
    ("chaine youtube jeux independants indie game",    ["gaming", "jeux inde"]),
    ("chaine youtube test critique jeu video",         ["gaming", "critique"]),
    ("chaine youtube rpg jeu de role",                 ["gaming"]),
    ("chaine youtube jeux de strategie",               ["gaming"]),
    ("chaine youtube speedrun gaming",                 ["gaming"]),
    # Cuisine
    ("chaine youtube cuisine gastronomie france",      ["gastronomie", "cuisine"]),
    ("chaine youtube recette facile rapide",           ["gastronomie", "cuisine"]),
    ("chaine youtube patisserie boulangerie",          ["gastronomie", "cuisine"]),
    ("chaine youtube vegan vegetarien cuisine",        ["gastronomie", "cuisine"]),
    ("chaine youtube vin degustation sommelier",       ["gastronomie"]),
    ("chaine youtube barbecue plancha grill",          ["gastronomie", "cuisine"]),
    # Humour
    ("chaine youtube humour comedie france",           ["humour", "comedie"]),
    ("chaine youtube sketch comedie",                  ["humour"]),
    ("chaine youtube stand up one man show",           ["humour"]),
    ("chaine youtube parodie humour",                  ["humour"]),
    # Actualite / Politique
    ("chaine youtube actualite politique france",      ["actualite", "politique"]),
    ("chaine youtube geopolitique monde",              ["geopolitique", "international"]),
    ("chaine youtube media journalisme",               ["actualite", "culture"]),
    ("chaine youtube economie finances france",        ["economie", "business"]),
    ("chaine youtube ecologie politique sociale",      ["societe", "politique"]),
    # Tech / Numerique
    ("chaine youtube tech numerique france",           ["tech", "numerique"]),
    ("chaine youtube intelligence artificielle ia",    ["tech", "numerique"]),
    ("chaine youtube developpement web code",          ["tech", "numerique"]),
    ("chaine youtube cybersecurite hacking",           ["tech", "numerique"]),
    ("chaine youtube hardware composants pc",          ["tech", "numerique"]),
    ("chaine youtube smartphone test telephone",       ["tech", "numerique"]),
    ("chaine youtube linux open source",               ["tech", "numerique"]),
    # Cinema / Series
    ("chaine youtube cinema analyse film france",      ["cinema", "culture"]),
    ("chaine youtube serie critique review",           ["series", "cinema"]),
    ("chaine youtube documentaire societe",            ["cinema", "societe"]),
    ("chaine youtube animation dessin anime",          ["cinema", "enfants"]),
    # Sport
    ("chaine youtube sport fitness france",            ["sport"]),
    ("chaine youtube football foot france",            ["football", "sport"]),
    ("chaine youtube trail running montagne",          ["sport", "running"]),
    ("chaine youtube musculation fitness gym",         ["sport", "sante"]),
    ("chaine youtube cyclisme velo",                   ["sport"]),
    ("chaine youtube arts martiaux boxe",              ["sport"]),
    ("chaine youtube yoga pilates bien etre",          ["sport", "bien-etre"]),
    ("chaine youtube natation triathlon",              ["sport", "endurance"]),
    ("chaine youtube escalade outdoor aventure",       ["sport", "nature"]),
    # Bien-etre / Psychologie
    ("chaine youtube psychologie developpement personnel", ["psychologie", "bien-etre"]),
    ("chaine youtube meditation pleine conscience",    ["bien-etre"]),
    ("chaine youtube sophrologie coaching vie",        ["bien-etre", "psychologie"]),
    # DIY / Maison
    ("chaine youtube bricolage renovation DIY",        ["renovation", "DIY"]),
    ("chaine youtube jardinage potager plantes",       ["nature", "DIY"]),
    ("chaine youtube decoration interieur maison",     ["maison", "culture"]),
    ("chaine youtube van amenagement tiny house",      ["DIY", "voyage"]),
    # Musique / Arts
    ("chaine youtube musique culture france",          ["musique", "culture"]),
    ("chaine youtube guitare instrument lecon",        ["musique", "education"]),
    ("chaine youtube rap hip hop france",              ["musique"]),
    ("chaine youtube peinture dessin art",             ["arts", "culture"]),
    # Voyage
    ("chaine youtube voyage aventure monde",           ["voyage", "culture"]),
    ("chaine youtube van life road trip",              ["voyage"]),
    ("chaine youtube expatrie expat vie",              ["voyage", "societe"]),
    # Education / Enfants
    ("chaine youtube education enfants famille",       ["enfants", "education"]),
    ("chaine youtube langue apprentissage francais",   ["education", "culture"]),
    ("chaine youtube philosophie vulgarisation",       ["philosophie", "culture"]),
    # Manga / Anime
    ("chaine youtube manga anime critique france",     ["anime", "culture geek"]),
    ("chaine youtube japan japon culture otaku",       ["anime", "culture"]),
    # Automobile / Moto
    ("chaine youtube automobile voiture essai",        ["culture", "sport"]),
    ("chaine youtube moto biker motocycle",            ["culture", "sport"]),
    # Business
    ("chaine youtube entrepreneuriat startup france",  ["business", "entrepreneuriat"]),
    ("chaine youtube investissement bourse crypto",    ["economie", "business"]),
    ("chaine youtube immobilier investir",             ["business", "economie"]),
    # Livres / Litterature
    ("chaine youtube livres lecture critique",         ["livres", "culture"]),
    # Mode / Lifestyle
    ("chaine youtube mode beaute cosmetique",          ["culture", "societe"]),
    ("chaine youtube lifestyle vlog quotidien",        ["societe", "culture"]),
    # Paranormal / Mystere
    ("chaine youtube paranormal mystere enquete",      ["culture", "societe"]),
    # Science-fiction / Geek
    ("chaine youtube science fiction geek culture",    ["culture geek", "cinema"]),
    ("chaine youtube comics super heros marvel",       ["culture geek", "cinema"]),
    ("chaine youtube jeux de societe boardgame",       ["gaming", "culture geek"]),
    # Francophonie
    ("chaine youtube francophone afrique belgique",    ["culture", "international"]),
    ("chaine youtube quebec canada francophone",       ["culture", "international"]),
]
YOUTUBE_QUERIES_PER_RUN = 20   # nombre de requetes utilisees par run

# --- iTunes Top Charts genres (RSS gratuit, renouvelé chaque semaine) ---------
ITUNES_GENRE_IDS = [
    (1311, ["actualite", "news"]),
    (1318, ["tech", "numerique"]),
    (1314, ["sciences", "vulgarisation"]),
    (1315, ["societe", "culture"]),
    (1316, ["sport"]),
    (1307, ["sante", "bien-etre"]),
    (1320, ["true crime", "societe"]),
    (1303, ["humour", "comedie"]),
    (1304, ["education"]),
    (1305, ["enfants", "famille"]),
    (1309, ["cinema", "series"]),
    (1310, ["musique", "culture"]),
    (1301, ["arts", "culture"]),
    (26,   ["business", "entrepreneuriat"]),
    (1321, ["histoire"]),
]

# --- Requetes iTunes (pool large, rotation par run) ---------------------------
ITUNES_QUERIES = [
    # Histoire
    ("podcast histoire francais",                  ["histoire"]),
    ("podcast revolution francaise",               ["histoire"]),
    ("podcast deuxieme guerre mondiale",           ["histoire"]),
    ("podcast antiquite rome grece",               ["histoire"]),
    ("podcast moyen age medieval france",          ["histoire"]),
    ("podcast biographies historiques france",     ["histoire"]),
    # True crime
    ("podcast true crime francais",                ["true crime", "societe"]),
    ("podcast affaires criminelles france",        ["true crime", "societe"]),
    ("podcast faits divers france",                ["true crime", "societe"]),
    ("podcast enquete criminelle",                 ["true crime", "societe"]),
    # Tech
    ("podcast tech numerique francais",            ["tech", "numerique"]),
    ("podcast intelligence artificielle ia",       ["tech", "numerique"]),
    ("podcast startup innovation france",          ["tech", "entrepreneuriat"]),
    ("podcast cybersecurite informatique",         ["tech", "numerique"]),
    ("podcast developpement web programmation",    ["tech", "numerique"]),
    # Gaming
    ("podcast gaming jeux video francais",         ["gaming"]),
    ("podcast retrogaming nostalgie jeux",         ["gaming", "retro"]),
    ("podcast jeux independants indie",            ["gaming", "jeux inde"]),
    ("podcast esport competitif france",           ["gaming", "sport"]),
    # Cinema / Series
    ("podcast cinema series francais",             ["cinema", "series"]),
    ("podcast critique film analyse",              ["cinema", "culture"]),
    ("podcast series netflix streaming",           ["series", "cinema"]),
    ("podcast animation manga anime",              ["anime", "culture"]),
    # Sport
    ("podcast sport running francais",             ["sport", "running"]),
    ("podcast football francais",                  ["football", "sport"]),
    ("podcast trail montagne ultra",               ["sport", "running"]),
    ("podcast cyclisme velo france",               ["sport"]),
    ("podcast basketball nba france",              ["sport"]),
    ("podcast rugby france",                       ["sport"]),
    ("podcast tennis france",                      ["sport"]),
    ("podcast natation triathlon",                 ["sport", "endurance"]),
    # Economie / Business
    ("podcast economie business francais",         ["economie", "business"]),
    ("podcast bourse investissement finance",      ["economie", "business"]),
    ("podcast entrepreneuriat startup founders",   ["entrepreneuriat", "business"]),
    ("podcast management leadership",             ["business", "entrepreneuriat"]),
    ("podcast immobilier investissement",          ["business", "economie"]),
    ("podcast marketing digital",                  ["business", "numerique"]),
    # Bien-etre / Sante
    ("podcast bien etre psychologie",              ["bien-etre", "psychologie"]),
    ("podcast meditation mindfulness",             ["bien-etre", "psychologie"]),
    ("podcast developpement personnel",            ["bien-etre", "psychologie"]),
    ("podcast sante medecine",                     ["sante"]),
    ("podcast nutrition alimentation",             ["sante", "bien-etre"]),
    ("podcast sante mentale anxiete",              ["sante", "psychologie"]),
    # Sciences
    ("podcast science vulgarisation",              ["sciences", "vulgarisation"]),
    ("podcast espace astronomie",                  ["sciences", "espace"]),
    ("podcast biologie nature environnement",      ["sciences", "nature"]),
    ("podcast physique chimie sciences",           ["sciences"]),
    ("podcast philosophie ethique",                ["philosophie", "culture"]),
    # Gastronomie
    ("podcast gastronomie cuisine",                ["gastronomie", "cuisine"]),
    ("podcast vin oenologie",                      ["gastronomie"]),
    ("podcast recette chef cuisinier",             ["gastronomie", "cuisine"]),
    # Enfants / Education
    ("podcast enfants education",                  ["enfants", "education"]),
    ("podcast famille parentalite",                ["enfants", "famille"]),
    ("podcast apprendre langue francais",          ["education", "culture"]),
    # Geopolitique
    ("podcast geopolitique international",         ["geopolitique", "international"]),
    ("podcast politique france actualite",         ["actualite", "politique"]),
    ("podcast diplomatie relations internationales",["geopolitique", "international"]),
    # Humour / Divertissement
    ("podcast humour comedie francais",            ["humour", "comedie"]),
    ("podcast stand up comique france",            ["humour"]),
    # Actualite / News
    ("podcast actualite news francais",            ["actualite", "news"]),
    ("podcast media journalisme presse",           ["actualite", "culture"]),
    ("podcast enquete investigation",              ["actualite", "societe"]),
    # Culture
    ("podcast livres litterature",                 ["livres", "culture"]),
    ("podcast musique culture",                    ["musique", "culture"]),
    ("podcast arts theatre spectacle",             ["arts", "culture"]),
    ("podcast voyage decouverte monde",            ["voyage", "culture"]),
    # Societe
    ("podcast societe feminisme",                  ["societe", "culture"]),
    ("podcast environnement ecologie",             ["environnement", "sciences"]),
    # Niches
    ("podcast droit justice legal france",         ["societe", "culture"]),
    ("podcast automobile moto",                    ["culture", "sport"]),
    ("podcast mode beaute lifestyle",              ["culture", "societe"]),
    ("podcast jeux de societe boardgame",          ["gaming", "culture geek"]),
    ("podcast crypto blockchain",                  ["tech", "economie"]),
    ("podcast spiritualite religion",              ["culture", "societe"]),
    ("podcast sante feminine gynecologie",         ["sante", "societe"]),
    ("podcast sciences politiques democratie",     ["geopolitique", "politique"]),
]
ITUNES_QUERIES_PER_RUN = 15   # nombre de requetes utilisees par run

# --- Helpers ------------------------------------------------------------------
def slugify(text):
    text = text.lower()
    for src, dst in [("aaoaa","a"),("eeeeee","e"),("ii","i"),("oo","o"),("uuuu","u"),("c","c")]:
        pass  # simplified - real accents handled below
    import unicodedata
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:80]

def load_existing(slug):
    path = DATA_DIR / f"{slug}.json"
    if path.exists():
        with open(path, encoding="utf-8") as f: return json.load(f)
    return None

def save_content(data):
    slug = data["slug"]
    path = DATA_DIR / f"{slug}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  + {slug}")

def today():
    from datetime import date
    return date.today().isoformat()

# --- Gestion de l'etat de rotation des requetes ------------------------------
QUERY_STATE_PATH = ROOT / ".query_state.json"

def load_query_state():
    if QUERY_STATE_PATH.exists():
        try:
            with open(QUERY_STATE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"podcast_idx": 0, "youtube_idx": 0}

def save_query_state(state):
    with open(QUERY_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f)

def get_query_slice(pool, idx, count):
    """Retourne un sous-ensemble de `count` requetes depuis `pool` en commencant a idx (cyclique)."""
    n = len(pool)
    indices = [i % n for i in range(idx, idx + count)]
    return [pool[i] for i in indices], (idx + count) % n

# --- Collecte iTunes ----------------------------------------------------------
def fetch_itunes(term, limit=200):
    url = "https://itunes.apple.com/search"
    params = {"term": term, "country": "fr", "media": "podcast", "limit": limit, "lang": "fr_fr"}
    try:
        return _http_get(url, params=params, timeout=15).get("results", [])
    except Exception as e:
        print(f"  ! iTunes error for '{term}': {e}")
        return []

def itunes_to_content(item, categories):
    name   = item.get("collectionName", "").strip()
    artist = item.get("artistName", "").strip()
    if not name: return None
    slug = slugify(name)
    if not slug: return None

    existing = load_existing(slug)
    if existing:
        if not existing.get("platforms", {}).get("apple"):
            existing.setdefault("platforms", {})["apple"] = {
                "url":         item.get("collectionViewUrl"),
                "trackId":     item.get("collectionId"),
                "rating":      item.get("averageUserRating"),
                "ratingCount": item.get("userRatingCount"),
                "episodeCount":item.get("trackCount"),
            }
            existing["updatedAt"] = today()
            save_content(existing)
        return existing

    return {
        "slug":        slug,
        "title":       name,
        "author":      artist,
        "type":        "podcast",
        "categories":  categories,
        "description": item.get("description") or item.get("shortDescription") or "",
        "image":       item.get("artworkUrl600") or item.get("artworkUrl100"),
        "language":    item.get("primaryGenreName", ""),
        "platforms": {
            "apple": {
                "url":         item.get("collectionViewUrl"),
                "trackId":     item.get("collectionId"),
                "rating":      item.get("averageUserRating"),
                "ratingCount": item.get("userRatingCount"),
                "episodeCount":item.get("trackCount"),
            }
        },
        "mediacritic": None,
        "tags":        categories,
        "addedAt":     today(),
        "updatedAt":   today(),
    }

# --- Collecte YouTube (API) ---------------------------------------------------
def fetch_youtube_channel(handle_or_id, api_key, name=None):
    if not api_key: return None
    base = "https://www.googleapis.com/youtube/v3/channels"
    try:
        # 1. Try forHandle
        data = _http_get(base, params={"part":"snippet,statistics","forHandle":handle_or_id.lstrip("@"),"key":api_key}, timeout=15)
        items = data.get("items", [])
        if not items:
            # 2. Try as channel ID
            data = _http_get(base, params={"part":"snippet,statistics","id":handle_or_id,"key":api_key}, timeout=15)
            items = data.get("items", [])
        if not items and name:
            # 3. Fallback: search by channel name
            sdata = _http_get("https://www.googleapis.com/youtube/v3/search",
                params={"part":"snippet","type":"channel","q":name,"maxResults":1,"key":api_key}, timeout=15)
            sitems = sdata.get("items", [])
            if sitems:
                cid = sitems[0]["id"]["channelId"]
                data = _http_get(base, params={"part":"snippet,statistics","id":cid,"key":api_key}, timeout=15)
                items = data.get("items", [])
        return items[0] if items else None
    except Exception as e:
        print(f"  ! YouTube API error for '{handle_or_id}': {e}")
        return None

def fetch_yt_oembed(handle):
    """Fetch thumbnail/title via YouTube oEmbed (no API key needed)."""
    url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/{handle}&format=json"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            return json.loads(r.read())
    except Exception:
        return None

# --- Collecte YouTube catalogue cure -----------------------------------------
def collect_youtube_catalog(api_key=None):
    print("\n-- Catalogue YouTube --")
    added = 0
    skipped = 0
    for handle, slug, title, categories in YOUTUBE_CHANNELS:
        existing = load_existing(slug)
        if existing and existing.get("type") == "youtube":
            # Skip only if already enriched with API data (has subscribers)
            if existing.get("platforms", {}).get("youtube", {}).get("subscribers"):
                skipped += 1
                continue

        data = existing or {
            "slug":        slug,
            "title":       title,
            "author":      title,
            "type":        "youtube",
            "categories":  categories,
            "description": "",
            "image":       None,
            "language":    "fr",
            "platforms":   {"youtube": {"url": f"https://www.youtube.com/{handle}"}},
            "mediacritic": None,
            "tags":        categories,
            "updatedAt":   today(),
        }

        if api_key:
            ch = fetch_youtube_channel(handle, api_key, name=title)
            if ch:
                sn = ch.get("snippet", {})
                st = ch.get("statistics", {})
                data["description"] = sn.get("description", "")
                data["image"] = sn.get("thumbnails", {}).get("high", {}).get("url")
                data.setdefault("platforms", {})["youtube"] = {
                    "url":         f"https://www.youtube.com/{handle}",
                    "channelId":   ch["id"],
                    "subscribers": int(st.get("subscriberCount", 0)),
                    "totalViews":  int(st.get("viewCount", 0)),
                    "videoCount":  int(st.get("videoCount", 0)),
                }
                data["updatedAt"] = today()
                save_content(data)
                added += 1
                continue

        if not data.get("image"):
            oembed = fetch_yt_oembed(handle)
            if oembed:
                data["image"] = oembed.get("thumbnail_url")
                if not data.get("title") or data["title"] == slug:
                    data["title"] = oembed.get("author_name", title)

        data["updatedAt"] = today()
        save_content(data)
        added += 1
        time.sleep(0.2)

    print(f"  YouTube: {added} ajoutees, {skipped} deja presentes")


def harvest_youtube_related(api_key):
    """Recupere les chaines en vedette (featuredChannelsUrls) des chaines deja en base.
    Chaque chaine peut en recommander d'autres — source tres fiable de nouvelles decouverts."""
    if not api_key:
        return
    print("\n-- Harvest chaines liees (featuredChannels) --")

    known_ids = set()
    known_handles = set()
    for path in DATA_DIR.glob("*.json"):
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            cid = d.get("platforms", {}).get("youtube", {}).get("channelId")
            if cid:
                known_ids.add(cid)
        except Exception:
            pass

    # Recupere les featured channels de toutes les chaines connues avec un channelId
    candidates = list(known_ids)[:80]  # limiter pour economiser le quota
    related_ids = set()

    base_chan = "https://www.googleapis.com/youtube/v3/channels"
    try:
        # Appel par lots de 50 (max autorise par l'API)
        for i in range(0, len(candidates), 50):
            batch = candidates[i:i+50]
            data = _http_get(base_chan, params={
                "part": "brandingSettings",
                "id":   ",".join(batch),
                "key":  api_key,
            })
            for item in data.get("items", []):
                urls = item.get("brandingSettings", {}).get("channel", {}).get("featuredChannelsUrls", [])
                for url in urls:
                    # url est soit un channelId soit un handle
                    cid = url.replace("https://www.youtube.com/channel/", "").strip()
                    if cid not in known_ids:
                        related_ids.add(cid)
            time.sleep(0.3)
    except Exception as e:
        print(f"  ! Harvest error: {e}")
        return

    if not related_ids:
        print("  Aucune chaine liee trouvee")
        return

    print(f"  {len(related_ids)} chaines candidates trouvees via featuredChannels")
    added = 0

    for i in range(0, len(related_ids), 50):
        batch = list(related_ids)[i:i+50]
        try:
            data = _http_get(base_chan, params={
                "part": "snippet,statistics",
                "id":   ",".join(batch),
                "key":  api_key,
            })
            for ch in data.get("items", []):
                sn   = ch.get("snippet", {})
                st   = ch.get("statistics", {})
                subs = int(st.get("subscriberCount", 0))
                if subs < 2000:
                    continue
                # Filtre langue : description ou pays francophone
                country = sn.get("country", "")
                desc    = (sn.get("description") or "").lower()
                title   = sn.get("title", "")
                # Heuristique simple : pays FR/BE/CH/CA ou description en francais
                if country not in ("FR", "BE", "CH", "CA", "LU", "MG", "SN", "CI") and not any(
                    w in desc for w in ["france", "francais", "français", "podcast", "bonjour", "bienvenue", "épisode"]
                ):
                    continue

                slug = slugify(title)
                if not slug or load_existing(slug):
                    continue

                handle = sn.get("customUrl") or f"@{ch['id']}"
                categories = ["culture", "societe"]  # categorie par defaut, raffinee ulterieurement

                new_entry = {
                    "slug":        slug,
                    "title":       title,
                    "author":      title,
                    "type":        "youtube",
                    "categories":  categories,
                    "description": (sn.get("description") or "")[:500],
                    "image":       sn.get("thumbnails", {}).get("high", {}).get("url"),
                    "language":    "fr",
                    "platforms":   {"youtube": {
                        "url":         f"https://www.youtube.com/{handle}",
                        "channelId":   ch["id"],
                        "subscribers": subs,
                        "totalViews":  int(st.get("viewCount", 0)),
                        "videoCount":  int(st.get("videoCount", 0)),
                    }},
                    "mediacritic": None,
                    "tags":        categories,
                    "addedAt":     today(),
                    "updatedAt":   today(),
                }
                save_content(new_entry)
                known_ids.add(ch["id"])
                added += 1
        except Exception as e:
            print(f"  ! Harvest batch error: {e}")
        time.sleep(0.3)

    print(f"  Harvest: {added} nouvelles chaines ajoutees")
    return added


def discover_youtube_channels(api_key, query_list=None, max_per_query=15, min_subscribers=2000):
    """Decouvre de nouvelles chaines YouTube francophones via l'API de recherche."""
    if not api_key:
        print("\n-- Decouverte YouTube ignoree (pas de cle API) --")
        return

    queries_to_use = query_list or YOUTUBE_DISCOVERY_QUERIES
    print(f"\n-- Decouverte de nouvelles chaines YouTube ({len(queries_to_use)} requetes) --")

    # Charge les channel IDs deja connus pour eviter les doublons
    known_ids = set()
    for path in DATA_DIR.glob("*.json"):
        try:
            with open(path, encoding="utf-8") as f:
                d = json.load(f)
            cid = d.get("platforms", {}).get("youtube", {}).get("channelId")
            if cid:
                known_ids.add(cid)
        except Exception:
            pass

    added = 0
    base_search = "https://www.googleapis.com/youtube/v3/search"
    base_chan   = "https://www.googleapis.com/youtube/v3/channels"

    for query, categories in queries_to_use:
        print(f"  -> {query}")
        results = _http_get(base_search, params={
            "part":              "snippet",
            "type":              "channel",
            "q":                 query,
            "relevanceLanguage": "fr",
            "regionCode":        "FR",
            "maxResults":        max_per_query,
            "key":               api_key,
        })
        for item in results.get("items", []):
            channel_id = item.get("id", {}).get("channelId")
            if not channel_id or channel_id in known_ids:
                continue

            # Recupere les details complets de la chaine
            ch_data = _http_get(base_chan, params={
                "part": "snippet,statistics",
                "id":   channel_id,
                "key":  api_key,
            })
            items = ch_data.get("items", [])
            if not items:
                continue
            ch = items[0]
            sn = ch.get("snippet", {})
            st = ch.get("statistics", {})

            subs = int(st.get("subscriberCount", 0))
            if subs < min_subscribers:
                continue  # ignore les petites chaines

            title  = sn.get("title", "")
            slug   = slugify(title)
            handle = sn.get("customUrl") or f"@{channel_id}"

            # Verifie que le slug n'existe pas deja
            if load_existing(slug):
                known_ids.add(channel_id)
                continue

            data = {
                "slug":        slug,
                "title":       title,
                "author":      title,
                "type":        "youtube",
                "categories":  categories,
                "description": (sn.get("description") or "")[:500],
                "image":       sn.get("thumbnails", {}).get("high", {}).get("url"),
                "language":    "fr",
                "platforms":   {"youtube": {
                    "url":         f"https://www.youtube.com/{handle}",
                    "channelId":   channel_id,
                    "subscribers": subs,
                    "totalViews":  int(st.get("viewCount", 0)),
                    "videoCount":  int(st.get("videoCount", 0)),
                }},
                "mediacritic": None,
                "tags":        categories,
                "addedAt":     today(),
                "updatedAt":   today(),
            }
            save_content(data)
            known_ids.add(channel_id)
            added += 1

        time.sleep(0.3)

    print(f"  Decouverte YouTube: {added} nouvelles chaines ajoutees")


# --- Collecte Spotify (optionnel) ---------------------------------------------
def get_spotify_token(client_id, client_secret):
    if not client_id or not client_secret: return None
    try:
        import base64
        credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        req = urllib.request.Request(
            "https://accounts.spotify.com/api/token",
            data=b"grant_type=client_credentials",
            headers={"Authorization": f"Basic {credentials}", "Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()).get("access_token")
    except Exception:
        return None

def fetch_spotify_show(show_id, token):
    if not token or not show_id: return None
    try:
        req = urllib.request.Request(
            f"https://api.spotify.com/v1/shows/{show_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception:
        return None

# --- Construction des fiches MediaCritic -------------------------------------
def build_mediacritic_entries(youtube_key=None, spotify_token=None):
    print("\n-- Episodes MediaCritic --")
    for ep in MEDIACRITIC_EPISODES:
        slug = ep["slug"]
        existing = load_existing(slug)
        data = existing or {
            "slug":        slug,
            "title":       ep["title"],
            "author":      "MediaCritic",
            "type":        ep["type"],
            "categories":  ep["categories"],
            "description": "",
            "image":       None,
            "language":    "fr",
            "platforms":   {},
            "mediacritic": {
                "episodeNumber": ep["ep"],
                "episodeSlug":   slug,
                "analyseUrl":    f"/episodes/{slug}.html",
            },
            "tags":      ep["categories"],
            "updatedAt": today(),
        }

        if ep.get("spotify_show") and spotify_token:
            show = fetch_spotify_show(ep["spotify_show"], spotify_token)
            if show:
                data.setdefault("platforms", {})["spotify"] = {
                    "url":          f"https://open.spotify.com/show/{ep['spotify_show']}",
                    "showId":       ep["spotify_show"],
                    "followers":    show.get("followers", {}).get("total"),
                    "episodeCount": show.get("total_episodes"),
                    "description":  show.get("description"),
                }
                if not data.get("image"):
                    images = show.get("images", [])
                    data["image"] = images[0]["url"] if images else None
                if not data.get("description"):
                    data["description"] = show.get("description", "")

        if ep.get("youtube") and youtube_key:
            ch = fetch_youtube_channel(ep["youtube"], youtube_key, name=ep.get("title"))
            if ch:
                sn = ch.get("snippet", {})
                st = ch.get("statistics", {})
                data.setdefault("platforms", {})["youtube"] = {
                    "url":         f"https://www.youtube.com/{ep['youtube']}",
                    "channelId":   ch["id"],
                    "subscribers": int(st.get("subscriberCount", 0)),
                    "totalViews":  int(st.get("viewCount", 0)),
                    "videoCount":  int(st.get("videoCount", 0)),
                }
                if not data.get("image"):
                    data["image"] = sn.get("thumbnails", {}).get("high", {}).get("url")
                if not data.get("description"):
                    data["description"] = sn.get("description", "")

        data["updatedAt"] = today()
        save_content(data)

# --- iTunes Top Charts (RSS public, source principale) -----------------------
def collect_itunes_top_charts():
    """Recupere le top 100 podcasts par genre depuis les RSS Apple France.
    Source sans quota, renouvelee chaque semaine — bien meilleure que la recherche."""
    print("\n-- iTunes Top Charts par genre --")
    added = 0
    for genre_id, categories in ITUNES_GENRE_IDS:
        url = f"https://itunes.apple.com/fr/rss/toppodcasts/limit=100/genre={genre_id}/json"
        try:
            data = _http_get(url, timeout=15)
            entries = data.get("feed", {}).get("entry", [])
            for entry in entries:
                name     = entry.get("im:name", {}).get("label", "").strip()
                artist   = entry.get("im:artist", {}).get("label", "").strip()
                track_id = entry.get("id", {}).get("attributes", {}).get("im:id")
                img_list = entry.get("im:image", [])
                image    = img_list[-1].get("label") if img_list else None
                ep_count = entry.get("im:contentType", {}).get("im:contentType", {}).get("im:count", {}).get("label")
                link     = entry.get("link", {}).get("attributes", {}).get("href", "")

                if not name: continue
                slug = slugify(name)
                if not slug: continue
                if load_existing(slug): continue

                new_entry = {
                    "slug":        slug,
                    "title":       name,
                    "author":      artist,
                    "type":        "podcast",
                    "categories":  categories,
                    "description": "",
                    "image":       image,
                    "language":    "fr",
                    "platforms": {
                        "apple": {
                            "url":         link or f"https://podcasts.apple.com/fr/podcast/id{track_id}",
                            "trackId":     int(track_id) if track_id else None,
                            "rating":      None,
                            "ratingCount": None,
                            "episodeCount":int(ep_count) if ep_count else None,
                        }
                    },
                    "mediacritic": None,
                    "tags":        categories,
                    "addedAt":     today(),
                    "updatedAt":   today(),
                }
                save_content(new_entry)
                added += 1
            print(f"  Genre {genre_id}: {len(entries)} entrees, {added} nouvelles total")
        except Exception as e:
            print(f"  ! Top Charts genre {genre_id}: {e}")
        time.sleep(0.4)
    print(f"  Top Charts: {added} nouveaux podcasts ajoutes")
    return added


# --- Collecte iTunes en masse ------------------------------------------------
def collect_itunes_catalog():
    print("\n-- Catalogue iTunes --")
    seen_slugs = set()
    total = 0
    for term, cats in ITUNES_QUERIES:
        print(f"  -> {term}")
        results = fetch_itunes(term, limit=200)
        new = 0
        for item in results:
            data = itunes_to_content(item, cats)
            if not data: continue
            if data["slug"] in seen_slugs: continue
            seen_slugs.add(data["slug"])
            existing = load_existing(data["slug"])
            if existing and existing.get("mediacritic"): continue
            save_content(data)
            new += 1
        total += new
        print(f"     {new} nouvelles fiches ({len(results)} resultats iTunes)")
        time.sleep(0.5)
    print(f"\n  Total nouvelles fiches : {total}")

# --- Scraping notes Apple Podcasts -------------------------------------------
def fetch_apple_rating_page(track_id):
    """Scrape Apple Podcasts page to get aggregate rating and review count."""
    url = f"https://podcasts.apple.com/fr/podcast/id{track_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "fr-FR,fr;q=0.9"
    }
    try:
        r = _requests_lib.get(url, headers=headers, timeout=12) if _requests_lib else None
        if r is None:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                text = resp.read().decode("utf-8", errors="ignore")
        else:
            r.raise_for_status()
            text = r.text
        m = re.search(r'"ratingValue":([0-9.]+),"reviewCount":([0-9]+)', text)
        if m:
            rv = float(m.group(1))
            rc = int(m.group(2))
            return rv if rv > 0 else None, rc if rc > 0 else None
    except Exception:
        pass
    return None, None

def update_ratings_missing():
    """Fetch Apple Podcasts ratings for entries that have trackId but no rating."""
    print("Mise a jour des notes Apple Podcasts (manquantes)")
    needs_update = []
    for path in DATA_DIR.glob("*.json"):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        apple = d.get("platforms", {}).get("apple", {})
        tid = apple.get("trackId")
        if tid and apple.get("rating") is None:
            needs_update.append((path, d, tid))

    if not needs_update:
        print("  Toutes les notes sont deja renseignees.")
        return

    print(f"  {len(needs_update)} fiches sans note a recuperer...")
    updated = 0

    def _fetch(args):
        path, d, tid = args
        rating, count = fetch_apple_rating_page(tid)
        return path, d, rating, count

    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = [ex.submit(_fetch, args) for args in needs_update]
        for fut in as_completed(futures):
            path, d, rating, count = fut.result()
            if rating is not None:
                d["platforms"]["apple"]["rating"] = rating
                d["platforms"]["apple"]["ratingCount"] = count
                save_content(d)
                updated += 1

    print(f"  Notes mises a jour : {updated}/{len(needs_update)}")


def refresh_all_ratings():
    """Re-fetch Apple Podcasts ratings for ALL entries with a trackId (mode refresh)."""
    print("\n-- Refresh notes Apple Podcasts (toutes les fiches) --")
    needs_update = []
    for path in DATA_DIR.glob("*.json"):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        apple = d.get("platforms", {}).get("apple", {})
        tid = apple.get("trackId")
        if tid:
            needs_update.append((path, d, tid))

    print(f"  {len(needs_update)} fiches podcasts a rafraichir...")
    updated = 0

    def _fetch(args):
        path, d, tid = args
        rating, count = fetch_apple_rating_page(tid)
        return path, d, rating, count

    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = [ex.submit(_fetch, args) for args in needs_update]
        for fut in as_completed(futures):
            path, d, rating, count = fut.result()
            if rating is not None:
                d.setdefault("platforms", {}).setdefault("apple", {})
                d["platforms"]["apple"]["rating"] = rating
                d["platforms"]["apple"]["ratingCount"] = count
                d["updatedAt"] = today()
                save_content(d)
                updated += 1

    print(f"  Notes mises a jour : {updated}/{len(needs_update)}")


def refresh_all_youtube(api_key=None):
    """Re-fetch YouTube subscriber counts and images for ALL existing YouTube channels."""
    if not api_key:
        print("\n-- Refresh YouTube ignoré (pas de clé API) --")
        return
    print("\n-- Refresh abonnés YouTube (toutes les chaînes) --")
    updated = 0
    skipped = 0
    for handle, slug, title, _ in YOUTUBE_CHANNELS:
        existing = load_existing(slug)
        if not existing or existing.get("type") != "youtube":
            skipped += 1
            continue
        ch = fetch_youtube_channel(handle, api_key, name=title)
        if ch:
            sn = ch.get("snippet", {})
            st = ch.get("statistics", {})
            existing["description"] = sn.get("description", existing.get("description", ""))
            existing["image"] = sn.get("thumbnails", {}).get("high", {}).get("url") or existing.get("image")
            existing.setdefault("platforms", {})["youtube"] = {
                "url":         f"https://www.youtube.com/{handle}",
                "channelId":   ch["id"],
                "subscribers": int(st.get("subscriberCount", 0)),
                "totalViews":  int(st.get("viewCount", 0)),
                "videoCount":  int(st.get("videoCount", 0)),
            }
            existing["updatedAt"] = today()
            save_content(existing)
            updated += 1
        else:
            skipped += 1
    print(f"  YouTube: {updated} mis a jour, {skipped} ignores (absents ou API ko)")

# --- Generation du catalog.json ----------------------------------------------
def generate_catalog():
    print("\n-- Generation catalog.json --")
    catalog = []
    for path in sorted(DATA_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        catalog.append({
            "slug":          d.get("slug"),
            "title":         d.get("title"),
            "author":        d.get("author", ""),
            "type":          d.get("type"),
            "categories":    d.get("categories", []),
            "tags":          d.get("tags", []),
            "image":         d.get("image"),
            "description":   (d.get("description") or "")[:200],
            "hasMediacritic":bool(d.get("mediacritic")),
            "mcEpisode":     d.get("mediacritic", {}).get("episodeNumber") if d.get("mediacritic") else None,
            "rating":        d.get("platforms", {}).get("apple", {}).get("rating"),
            "ratingCount":   d.get("platforms", {}).get("apple", {}).get("ratingCount"),
            "subscribers":   d.get("platforms", {}).get("youtube", {}).get("subscribers"),
        })

    with open(CATALOG_OUT, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, separators=(",", ":"))
    print(f"  {len(catalog)} entrees -> data/catalog.json ({CATALOG_OUT.stat().st_size // 1024} KB)")

# --- Main --------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode",           choices=["podcast", "youtube", "refresh", "all"], default="all")
    parser.add_argument("--youtube-key",    default=os.getenv("YOUTUBE_API_KEY"))
    parser.add_argument("--spotify-id",     default=os.getenv("SPOTIFY_CLIENT_ID"))
    parser.add_argument("--spotify-secret", default=os.getenv("SPOTIFY_CLIENT_SECRET"))
    args = parser.parse_args()

    spotify_token = get_spotify_token(args.spotify_id, args.spotify_secret)
    if spotify_token: print("Spotify connecte")
    if args.youtube_key: print("YouTube connecte")

    build_mediacritic_entries(args.youtube_key, spotify_token)

    # Charge l'etat de rotation des requetes
    qstate = load_query_state()

    if args.mode == "refresh":
        # Jour 1 : mettre a jour TOUTES les donnees existantes
        refresh_all_ratings()
        refresh_all_youtube(args.youtube_key)

    elif args.mode == "podcast":
        # Jour 2 : decouvrir de nouveaux podcasts
        # Source 1 : iTunes Top Charts (renouvelé chaque semaine, sans quota)
        collect_itunes_top_charts()
        # Source 2 : Requetes de recherche iTunes (rotation dans le pool)
        query_slice, next_idx = get_query_slice(ITUNES_QUERIES, qstate.get("podcast_idx", 0), ITUNES_QUERIES_PER_RUN)
        print(f"\n-- Requetes iTunes (rotation : {qstate.get('podcast_idx',0)} → {next_idx}) --")
        # Sauvegarde temporairement pour collect_itunes_catalog qui lit ITUNES_QUERIES globalement
        _orig = ITUNES_QUERIES[:]
        ITUNES_QUERIES.clear()
        ITUNES_QUERIES.extend(query_slice)
        collect_itunes_catalog()
        ITUNES_QUERIES.clear()
        ITUNES_QUERIES.extend(_orig)
        qstate["podcast_idx"] = next_idx
        # Source 3 : notes manquantes
        update_ratings_missing()

    elif args.mode == "youtube":
        # Jour 3 : decouvrir de nouvelles chaines YouTube
        collect_youtube_catalog(args.youtube_key)   # liste statique (nouvelles entrees si ajoutees)
        # Source 1 : harvest depuis les chaines connues (featuredChannels)
        harvest_youtube_related(args.youtube_key)
        # Source 2 : requetes de recherche YouTube (rotation dans le pool)
        yt_slice, next_yt_idx = get_query_slice(YOUTUBE_DISCOVERY_QUERIES, qstate.get("youtube_idx", 0), YOUTUBE_QUERIES_PER_RUN)
        discover_youtube_channels(args.youtube_key, query_list=yt_slice)
        qstate["youtube_idx"] = next_yt_idx

    elif args.mode == "all":
        collect_itunes_top_charts()
        collect_itunes_catalog()
        collect_youtube_catalog(args.youtube_key)
        harvest_youtube_related(args.youtube_key)
        discover_youtube_channels(args.youtube_key)
        update_ratings_missing()

    # Sauvegarde l'etat de rotation
    save_query_state(qstate)

    generate_catalog()
    print("\nTermine.")
