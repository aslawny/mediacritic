from flask import Flask, jsonify
import pandas as pd
from flask_cors import CORS 
import os

app = Flask(__name__)
CORS(app)

@app.route("/podcasts")
def get_podcasts():
    # 🔁 Récupère le chemin du fichier Excel relatif au dossier backend
    base_dir = os.path.dirname(__file__)  # répertoire courant (mon-site-podcast-backend)
    filepath = filepath = os.path.join(base_dir, "classement_podcast.xlsx")  # fichier à la racine du dossier backend

    # 🧠 Lecture + nettoyage
    df = pd.read_excel(filepath)
    df = df[["Podcasts", "Téléchargements Monde", "Catégorie", "Marque", "Nombre d'épisodes"]]

    # 📤 Envoi des données au frontend
    podcasts = df.to_dict(orient="records")
    return jsonify(podcasts)

if __name__ == "__main__":
    app.run(debug=True)
