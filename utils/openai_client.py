# ────────────────────────────────────────────────────────────────────────────────
# 📌 openai_client.py — Gestion des appels à l'API OpenAI
# Objectif : Fournir une fonction get_story_continuation() pour le mini-RPG
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import os
from openai import OpenAI

# ────────────────────────────────────────────────────────────────────────────────
# Vérifier la clé
# ────────────────────────────────────────────────────────────────────────────────
print("🔑 Clé OpenAI détectée :", bool(os.getenv("OPENAI_API_KEY")))

# ────────────────────────────────────────────────────────────────────────────────
# ⚙️ Initialisation du client OpenAI
# ────────────────────────────────────────────────────────────────────────────────
# Clé API stockée dans les variables d'environnement
# Exemple : dans ton hébergeur ou ton .env ➜ OPENAI_API_KEY="ta_clé_ici"
# ────────────────────────────────────────────────────────────────────────────────

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ────────────────────────────────────────────────────────────────────────────────
# 💬 Fonction principale — génération du texte narratif
# ────────────────────────────────────────────────────────────────────────────────
def get_story_continuation(history: list[str]) -> str:
    """
    Envoie l'historique du RPG à l'API OpenAI et renvoie la suite de l'histoire.
    Chaque élément de 'history' est une dict : {role: 'user'/'assistant'/'system', content: str}
    """

    try:
        # Appel à l'API Chat Completions
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # 🔹 rapide et économique, idéal pour ce type de jeu
            messages=history,
            max_tokens=300,        # limite la longueur des réponses
            temperature=0.9,       # un peu de créativité pour les descriptions
            presence_penalty=0.3,  # encourage un peu de nouveauté
            frequency_penalty=0.4  # évite les répétitions
        )

        # Récupération du texte
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"[Erreur OpenAI] {e}")
        raise RuntimeError("Erreur API OpenAI") from e
