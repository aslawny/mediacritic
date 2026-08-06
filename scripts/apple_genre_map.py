# -*- coding: utf-8 -*-
"""
Mapping des genres officiels Apple Podcasts (libellés français renvoyés par
l'API iTunes avec country=fr) vers le vocabulaire de catégories MediaCritic.

C'est la SOURCE DE VÉRITÉ des catégories : le bot ne doit plus jamais déduire
une catégorie de la requête de recherche utilisée pour découvrir un podcast.

Les catégories produites alimentent les pages de categories/ ; garder ce
vocabulaire stable et restreint.
"""

APPLE_GENRE_MAP = {
    # ── Culture & société ────────────────────────────────────────────────
    "Culture et société":            ["culture", "societe"],
    "Journaux personnels":           ["societe", "temoignage"],
    "Relations":                     ["societe", "psychologie"],
    "Philosophie":                   ["culture", "philosophie"],
    "Sciences sociales":             ["societe", "sciences"],
    "Sexualité":                     ["societe", "psychologie"],
    "À but non lucratif":            ["societe"],

    # ── Voyage (catégorie qui manquait : 686 contenus mal classés) ───────
    "Destinations et voyages":       ["voyage", "culture"],

    # ── Arts & création ──────────────────────────────────────────────────
    "Arts":                          ["arts", "culture"],
    "Arts du spectacle":             ["arts", "spectacle"],
    "Arts visuels":                  ["arts", "design"],
    "Design":                        ["design", "arts"],
    "Mode et beauté":                ["mode", "lifestyle"],
    "Livres":                        ["litterature", "culture"],
    "Romans et nouvelles":           ["litterature", "fiction"],
    "Drame":                         ["fiction", "arts"],
    "Science-fiction":               ["fiction", "science-fiction"],

    # ── Cinéma & séries ──────────────────────────────────────────────────
    "Télévision et cinéma":          ["cinema", "series"],
    "Cinéma : les critiques":        ["cinema", "critique"],
    "Cinéma : les interviews":       ["cinema", "interview"],
    "Histoire du cinéma":            ["cinema", "histoire"],
    "Séries : les critiques":        ["series", "critique"],
    "Dans les coulisses":            ["cinema", "coulisses"],
    "Actualité du divertissement":   ["culture", "divertissement"],
    "Animation et manga":            ["anime", "culture geek"],
    "Documentaire":                  ["documentaire", "culture"],

    # ── Musique ──────────────────────────────────────────────────────────
    "Musique":                       ["musique"],
    "Musique : analyses":            ["musique", "critique"],
    "Musique : les interviews":      ["musique", "interview"],
    "Histoire de la musique":        ["musique", "histoire"],

    # ── Humour ───────────────────────────────────────────────────────────
    "Humour":                        ["humour"],
    "Comédie : les interviews":      ["humour", "interview"],
    "Comédies":                      ["humour", "comedie"],
    "Stand-up":                      ["humour", "stand-up"],
    "Improvisation":                 ["humour", "improvisation"],

    # ── Tech ─────────────────────────────────────────────────────────────
    "Technologies":                  ["tech", "numerique"],
    "Actualités technologiques":     ["tech", "actualite"],

    # ── Business & économie ──────────────────────────────────────────────
    "Affaires":                      ["business"],
    "Entrepreneuriat":               ["entrepreneuriat", "business"],
    "Carrière":                      ["carriere", "business"],
    "Gestion":                       ["management", "business"],
    "Marketing":                     ["marketing", "business"],
    "Investissement":                ["investissement", "economie"],
    "Actualité économique":          ["economie", "actualite"],

    # ── Actualité & politique ────────────────────────────────────────────
    "Actualités":                    ["actualite"],
    "Actualité : analyses":          ["actualite", "analyse"],
    "Actus du jour":                 ["actualite"],
    "Politique":                     ["politique", "societe"],
    "Gouvernement":                  ["politique", "societe"],

    # ── Éducation & savoirs ──────────────────────────────────────────────
    "Éducation":                     ["education"],
    "Cours":                         ["education", "cours"],
    "Tuto":                          ["education", "tuto"],
    "Apprentissage des langues":     ["langues", "education"],
    "Développement personnel":       ["developpement personnel", "bien-etre"],

    # ── Sciences ─────────────────────────────────────────────────────────
    "Sciences":                      ["sciences", "vulgarisation"],
    "Nature":                        ["nature", "sciences"],
    "Sciences naturelles":           ["nature", "sciences"],
    "Sciences de la Terre":          ["sciences", "environnement"],
    "Science de la vie":             ["sciences", "biologie"],
    "Astronomie":                    ["sciences", "espace"],
    "Mathématiques":                 ["sciences", "mathematiques"],
    "Physique":                      ["sciences", "physique"],
    "Chimie":                        ["sciences", "chimie"],
    "Médecine":                      ["sante", "sciences"],

    # ── Histoire ─────────────────────────────────────────────────────────
    "Histoire":                      ["histoire"],

    # ── True crime ───────────────────────────────────────────────────────
    "Criminologie":                  ["true crime", "societe"],

    # ── Santé & bien-être ────────────────────────────────────────────────
    "Forme et santé":                ["sante", "bien-etre"],
    "Santé mentale":                 ["psychologie", "bien-etre"],
    "Fitness":                       ["fitness", "sport"],
    "Médecine parallèle":            ["bien-etre", "sante"],

    # ── Sport ────────────────────────────────────────────────────────────
    "Sports":                        ["sport"],
    "Actualités sportives":          ["sport", "actualite"],
    "Course à pied":                 ["running", "sport"],
    "Football":                      ["football", "sport"],
    "Football américain":            ["football americain", "sport"],
    "Basketball":                    ["basket", "sport"],
    "Tennis":                        ["tennis", "sport"],
    "Rugby":                         ["rugby", "sport"],
    "Golf":                          ["golf", "sport"],
    "Natation":                      ["natation", "sport"],
    "Hockey sur glace":              ["hockey", "sport"],
    "Catch":                         ["catch", "sport"],
    "Sports virtuels":               ["esport", "sport"],
    "Aviation":                      ["aviation", "loisirs"],
    "Automobile":                    ["automobile", "loisirs"],

    # ── Jeux & loisirs ───────────────────────────────────────────────────
    "Jeux vidéo":                    ["gaming", "culture geek"],
    "Jeux":                          ["jeux", "loisirs"],
    "Loisirs":                       ["loisirs"],
    "Hobbies":                       ["loisirs"],
    "Travaux manuels":               ["DIY", "loisirs"],
    "Maison et jardin":              ["maison", "DIY"],
    "Animaux":                       ["animaux", "nature"],

    # ── Gastronomie ──────────────────────────────────────────────────────
    "Gastronomie":                   ["gastronomie", "cuisine"],
    "Alimentation":                  ["cuisine", "gastronomie"],

    # ── Enfants & famille ────────────────────────────────────────────────
    "Enfants et parents":            ["enfants", "famille"],
    "Parentalité":                   ["famille", "parentalite"],
    "Histoires pour enfants":        ["enfants", "fiction"],
    "Contenu éducatif pour enfants": ["enfants", "education"],

    # ── Religion & spiritualité ──────────────────────────────────────────
    "Religion et spiritualité":      ["religion", "spiritualite"],
    "Spiritualité":                  ["spiritualite"],
    "Religion":                      ["religion"],
    "Christianisme":                 ["religion", "christianisme"],
    "Islam":                         ["religion", "islam"],
    "Judaïsme":                      ["religion", "judaisme"],
    "Bouddhisme":                    ["spiritualite", "bouddhisme"],
}

# Genres trop génériques : ignorés (n'apportent aucune information)
IGNORED_GENRES = {"Podcasts"}

MAX_CATEGORIES = 4


def categories_from_apple(genres):
    """Genres Apple -> catégories MediaCritic, dédupliquées, ordre stable."""
    out = []
    for g in genres or []:
        if g in IGNORED_GENRES:
            continue
        for c in APPLE_GENRE_MAP.get(g, []):
            if c not in out:
                out.append(c)
    return out[:MAX_CATEGORIES]
