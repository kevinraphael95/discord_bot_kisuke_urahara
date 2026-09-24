# ================================================================================
# 📌 gpt_oss_client.py — Connexion cloud NVIDIA GPT-OSS (pour !!gpt et /rpgpt)
# ================================================================================
import os
from openai import OpenAI
import requests

# ================================================================================
# 🔑 Clé NVIDIA (cloud)
# ================================================================================
API_KEY = os.getenv("GPT_OSS_API_KEY")
BASE_URL = "https://integrate.api.nvidia.com/v1"

if not API_KEY:
    print("❌ Aucune clé GPT-OSS détectée. Configure GPT_OSS_API_KEY dans ton environnement.")
else:
    print("✅ Clé NVIDIA GPT-OSS détectée — utilisation du cloud.")

# ================================================================================
# ⚙️ Initialisation du client NVIDIA Cloud
# ================================================================================
client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

# ================================================================================
# 💬 Réponse simple (commande !!gpt)
# ================================================================================
def get_simple_response(prompt: str) -> str:
    """
    Envoie un simple prompt texte à GPT-OSS NVIDIA (cloud) et renvoie la réponse directe.
    Utilisé pour la commande !!gpt.
    """
    try:
        # Consigne ajoutée automatiquement sans compter dans la limite utilisateur
        full_prompt = (
            prompt.strip()
            + "\n\nRéponds brièvement et clairement, en français, en 1 à 3 phrases maximum."
        )

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Tu es un assistant conversationnel précis, bienveillant et toujours francophone. "
                        "Réponds de manière naturelle et fluide."
                    ),
                },
                {"role": "user", "content": full_prompt},
            ],
            temperature=0.8,   # un peu plus libre pour éviter les non-réponses
            top_p=0.8,
            max_tokens=512,    # limite interne confortable (pas coupée brutalement)
        )

        msg = response.choices[0].message.content
        if not msg or not msg.strip():
            return "⚠️ Le modèle n’a rien répondu."
        msg = msg.strip()

        # Tronquer à 500 caractères maximum
        if len(msg) > 500:
            msg = msg[:500].rstrip() + "…"

        return msg

    except Exception as e:
        print(f"[Erreur GPT-OSS Simple] {type(e)} — {e}")
        return "⚠️ Le modèle est silencieux pour le moment..."

# ================================================================================
# 💬 Continuation d’histoire (utilisée par RPGPT)
# ================================================================================
def get_story_continuation(history: list[dict]) -> str:
    """
    Envoie l'historique du RPG à GPT-OSS NVIDIA (cloud) et renvoie la suite de l'histoire.
    Chaque élément de 'history' est une dict : {role: 'user'/'assistant'/'system', content: str}
    """
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=history,
            temperature=0.95,
            top_p=0.7,
            max_tokens=1024
        )
        msg = response.choices[0].message.content
        if not msg:
            return "⚠️ Le narrateur se tait..."
        return msg.strip()
    except Exception as e:
        print(f"[Erreur GPT-OSS Histoire] {type(e)} — {e}")
        return "⚠️ Le narrateur se tait... (*erreur du modèle ou limite atteinte*)"

# --------------------------------------------------------------------- #
# Fonction pour récupérer le quota restant
# --------------------------------------------------------------------- #
def remaining_tokens() -> int:
    """
    Retourne le nombre de tokens restants dans le quota mensuel NVIDIA GPT-OSS.
    Approximation : 100 000 tokens par mois (free-tier)
    """
    try:
        resp = requests.get(
            f"{BASE_URL}/usage",
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=5
        )
        resp.raise_for_status()
        data = resp.json()
        used = data.get("token_used", 0)
        quota = data.get("token_quota", 100_000)
        return quota - used
    except Exception as e:
        print(f"[Erreur remaining_tokens] {e}")
        return 100_000
