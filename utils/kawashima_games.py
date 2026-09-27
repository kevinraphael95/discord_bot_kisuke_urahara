# ================================================================================
# 📌 kawashima_games.py — Mini-jeux Professeur Kawashima
# Version unifiée : TOUS les jeux répondent via un bouton + modale
# ================================================================================

import random
import asyncio
import discord
from discord.ui import View, Button, Modal, TextInput

# ================================================================================
# 📦 Paramètres
# ================================================================================
TIMEOUT = 60  # secondes pour répondre

# ================================================================================
# 🛠️ Helper unique — bouton + modale
# ================================================================================
async def _ask_text_answer(ctx, embed, get_user_id, bot, modal_label="Ta réponse", timeout=TIMEOUT):
    """
    Affiche un bouton '✏️ Répondre' sur le message. Au clic, ouvre une modale.
    Retourne le texte saisi (str) ou None si timeout / pas de réponse.
    """

    class AnswerModal(Modal):
        def __init__(self, outer_view):
            super().__init__(title=modal_label)
            self.outer_view = outer_view
            self.reponse = TextInput(
                label=modal_label,
                placeholder="Tape ta réponse ici",
                max_length=200
            )
            self.add_item(self.reponse)

        async def on_submit(self, interaction: discord.Interaction):
            self.outer_view.result = self.reponse.value
            self.outer_view.stop()
            try:
                await interaction.response.defer()
            except Exception:
                pass

    class AnswerView(View):
        def __init__(self):
            super().__init__(timeout=timeout)
            self.result = None

        @discord.ui.button(label="✏️ Répondre", style=discord.ButtonStyle.primary)
        async def answer_btn(self, interaction: discord.Interaction, button: Button):
            # En solo : seul le joueur peut cliquer
            # En multi : n'importe qui (get_user_id renvoie None)
            expected = get_user_id()
            if expected is not None and interaction.user.id != expected:
                await interaction.response.send_message("🚫 Ce n'est pas ton tour.", ephemeral=True)
                return
            await interaction.response.send_modal(AnswerModal(self))

    view = AnswerView()
    try:
        await ctx.edit(view=view)
    except Exception:
        return None
    await view.wait()
    try:
        await ctx.edit(view=None)
    except Exception:
        pass
    return view.result


# ================================================================================
# 🔹 🧮 Addition à la suite
# ================================================================================
async def addition_cachee(ctx, embed, get_user_id, bot, msg_override=None):
    additions = [random.randint(-9, 9) for _ in range(6)]
    total = sum(additions)

    embed.clear_fields()
    embed.add_field(name="🧮 Additions à la suite", value="Observe bien les additions successives...", inline=False)
    await ctx.edit(embed=embed)
    await asyncio.sleep(3)

    for add in additions:
        embed.clear_fields()
        embed.add_field(name="🧮 Additions à la suite", value=f"{add:+d}", inline=False)
        await ctx.edit(embed=embed)
        await asyncio.sleep(1.8)

    embed.clear_fields()
    embed.add_field(name="🧮 Additions à la suite", value="Quel est le total final ?", inline=False)
    await ctx.edit(embed=embed)

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(ctx, embed, get_user_id, bot, modal_label="Total")

    if text is None:
        return False
    try:
        return int(text.strip()) == total
    except Exception:
        return False

addition_cachee.title = "Addition à la suite"
addition_cachee.emoji = "➕"
addition_cachee.prep_time = 3 + 1.8 * 6


# ================================================================================
# 🔹 🧮 Calcul rapide
# ================================================================================
async def calcul_rapide(ctx, embed, get_user_id, bot, msg_override=None):
    op = random.choice(["+", "-", "*", "/"])
    if op == "*":
        a, b = random.randint(1, 10), random.randint(1, 10)
        answer = a * b
    elif op == "/":
        b = random.randint(1, 10)
        answer = random.randint(1, 10)
        a = b * answer
    else:
        a, b = random.randint(10, 50), random.randint(10, 50)
        answer = a + b if op == "+" else a - b

    embed.clear_fields()
    embed.add_field(name="🧮 Calcul rapide", value=f"{a} {op} {b} = ?", inline=False)
    await ctx.edit(embed=embed)

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(ctx, embed, get_user_id, bot, modal_label="Résultat")

    if text is None:
        return False
    try:
        return int(text.strip()) == answer
    except Exception:
        return False

calcul_rapide.title = "Calcul rapide"
calcul_rapide.emoji = "🧮"
calcul_rapide.prep_time = 0


# ================================================================================
# 🔹 🔢 Carré magique 3x3
# ================================================================================
async def carre_magique_fiable_emoji(ctx, embed, get_user_id, bot, msg_override=None):
    base = [
        [8, 1, 6],
        [3, 5, 7],
        [4, 9, 2]
    ]

    def rotate(square):
        return [list(x) for x in zip(*square[::-1])]

    def flip(square):
        return [row[::-1] for row in square]

    for _ in range(random.randint(0, 3)):
        base = rotate(base)
    if random.choice([True, False]):
        base = flip(base)

    row, col = random.randint(0, 2), random.randint(0, 2)
    answer = base[row][col]
    base[row][col] = "❓"

    num_to_emoji = {i: f"{i}\ufe0f\u20e3" for i in range(1, 10)}
    display = "\n".join("|".join(num_to_emoji.get(x, x) for x in r) for r in base)

    embed.clear_fields()
    embed.add_field(
        name="🔢 Carré magique",
        value=f"Complète le carré magique pour que toutes les lignes, colonnes et diagonales fassent 15 :\n{display}\n\n➡️ Donne le chiffre manquant (1 à 9).",
        inline=False
    )
    await ctx.edit(embed=embed)

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(ctx, embed, get_user_id, bot, modal_label="Chiffre manquant")

    if text is None:
        return False
    try:
        return int(text.strip()) == answer
    except Exception:
        return False

carre_magique_fiable_emoji.title = "Carré magique 3x3"
carre_magique_fiable_emoji.emoji = "🔢"
carre_magique_fiable_emoji.prep_time = 0


# ================================================================================
# 🔹 👀 Compter les emojis
# ================================================================================
async def compter_emojis(ctx, embed, get_user_id, bot, msg_override=None):
    emojis = ["🍎", "🍌", "🍒", "🍇", "🍊"]
    cible = random.choice(emojis)

    grille = [[random.choice(emojis) for _ in range(4)] for _ in range(4)]
    texte_grille = "\n".join("".join(ligne) for ligne in grille)
    total = sum(ligne.count(cible) for ligne in grille)

    embed.clear_fields()
    embed.add_field(
        name="👀 Compter les emojis",
        value=f"{texte_grille}\n\n➡️ Combien de {cible} dans cette grille ?",
        inline=False
    )
    await ctx.edit(embed=embed)

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(ctx, embed, get_user_id, bot, modal_label="Nombre")

    if text is None:
        return False
    return text.strip().isdigit() and int(text.strip()) == total

compter_emojis.title = "Compter les emojis"
compter_emojis.emoji = "👀"
compter_emojis.prep_time = 1.5


# ================================================================================
# 🔹 🎨 Couleurs (Stroop)
# ================================================================================
async def couleurs(ctx, embed, get_user_id, bot, msg_override=None):
    couleurs_list = ["bleu", "vert", "rouge", "gris"]
    mots = couleurs_list.copy()
    random.shuffle(mots)

    question_type = random.choice(["mot", "couleur"])

    if question_type == "mot":
        cible = random.choice(mots)
        question = (
            f"Les mots affichés sont : {', '.join(m.upper() for m in mots)}\n\n"
            f"➡️ Quel mot est écrit en **{cible.upper()}** dans la liste ?\n"
            f"(Tape le mot, pas la couleur)"
        )
        answer = cible
    else:
        cible = random.choice(couleurs_list)
        question = (
            f"Les couleurs dans l'ordre sont : {', '.join(couleurs_list)}\n\n"
            f"➡️ Quel est le mot associé à la couleur **{cible.upper()}** ?\n"
            f"(Tape le mot)"
        )
        # Ici on simplifie : on associe chaque couleur à un mot
        # Pour éviter la confusion Stroop en modale, on demande juste le mot
        # qui correspond à la couleur cible (toujours le même mot que la couleur)
        answer = cible

    embed.clear_fields()
    embed.add_field(name="🎨 Couleurs (Stroop)", value=question, inline=False)
    await ctx.edit(embed=embed)

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(ctx, embed, get_user_id, bot, modal_label="Mot")

    if text is None:
        return False
    return text.strip().lower() == answer.lower()

couleurs.title = "Couleurs"
couleurs.emoji = "🎨"
couleurs.prep_time = 0.5


# ================================================================================
# 🔹 📅 Datation
# ================================================================================
async def datation(msg, embed, get_user_id, bot, msg_override=None):
    import datetime

    today = datetime.date.today()
    delta_days = random.randint(-7, 7)
    date = today + datetime.timedelta(days=delta_days)

    jours_fr_liste = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    jour_correct = jours_fr_liste[date.weekday()]

    embed.clear_fields()
    embed.title = "📅 Datation"
    embed.description = f"Quel jour était le **{date.day}/{date.month}/{date.year}** ?\n(Tape le jour en toutes lettres)"
    await msg.edit(embed=embed)

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(msg, embed, get_user_id, bot, modal_label="Jour de la semaine")

    if text is None:
        return False
    return text.strip().lower() == jour_correct

datation.title = "Datation"
datation.emoji = "📅"
datation.prep_time = 0


# ================================================================================
# 🔹 🧭 Directions opposées
# ================================================================================
async def directions_opposees(ctx, embed, get_user_id, bot, msg_override=None):
    arrows_map = {
        "⬆️": ("haut", "bas"),
        "⬇️": ("bas", "haut"),
        "⬅️": ("gauche", "droite"),
        "➡️": ("droite", "gauche"),
    }
    arrow = random.choice(list(arrows_map.keys()))
    _, correct_word = arrows_map[arrow]

    embed.clear_fields()
    embed.add_field(
        name="🧭 Directions opposées",
        value=f"Flèche affichée : {arrow}\n➡️ Quelle est la direction opposée ?\n(Tape : haut, bas, gauche ou droite)",
        inline=False
    )
    await ctx.edit(embed=embed)

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(ctx, embed, get_user_id, bot, modal_label="Direction opposée")

    if text is None:
        return False
    return text.strip().lower() == correct_word

directions_opposees.title = "Directions opposées"
directions_opposees.emoji = "🧭"
directions_opposees.prep_time = 1


# ================================================================================
# 🔹 ➗ Équation à trou
# ================================================================================
async def equation_trou(ctx, embed, get_user_id, bot, msg_override=None):
    op = random.choice(["+", "-", "*"])
    if op == "+":
        a, b = random.randint(1, 20), random.randint(1, 20)
        answer = random.choice([a, b])
        question = f"? + {b} = {a + b}" if answer == a else f"{a} + ? = {a + b}"
    elif op == "-":
        a, b = random.randint(10, 30), random.randint(1, 10)
        answer = random.choice([a, b])
        question = f"? - {b} = {a - b}" if answer == a else f"{a} - ? = {a - b}"
    else:
        a, b = random.randint(1, 10), random.randint(1, 10)
        answer = random.choice([a, b])
        question = f"? × {b} = {a * b}" if answer == a else f"{a} × ? = {a * b}"

    embed.clear_fields()
    embed.add_field(name="➗ Équation à trou", value=question, inline=False)
    await ctx.edit(embed=embed)

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(ctx, embed, get_user_id, bot, modal_label="Valeur manquante")

    if text is None:
        return False
    try:
        return int(text.strip()) == answer
    except Exception:
        return False

equation_trou.title = "Equation à trou"
equation_trou.emoji = "➗"
equation_trou.prep_time = 0


# ================================================================================
# 🔹 🕒 Heures
# ================================================================================
async def heures(ctx, embed, get_user_id, bot, msg_override=None):
    h1, m1 = random.randint(0, 23), random.randint(0, 59)
    h2, m2 = random.randint(0, 23), random.randint(0, 59)
    diff = abs((h1 * 60 + m1) - (h2 * 60 + m2))
    hours, mins = divmod(diff, 60)

    heure_1, heure_2 = f"{h1:02d}:{m1:02d}", f"{h2:02d}:{m2:02d}"
    question_type = f"Quelle est la différence entre {heure_1} et {heure_2} ?\n(Ex: 1h30)"

    embed.clear_fields()
    embed.add_field(name="🕒 Heures", value=question_type, inline=False)
    await ctx.edit(embed=embed)

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(ctx, embed, get_user_id, bot, modal_label="Différence")

    if text is None:
        return False
    try:
        rep = text.lower().replace("h", " ").replace(":", " ").replace("min", " ").replace("m", " ")
        nums = [int(x) for x in rep.split() if x.isdigit()]
        if len(nums) == 1:
            user_hours, user_mins = divmod(nums[0], 60)
        elif len(nums) >= 2:
            user_hours, user_mins = nums[0], nums[1]
        else:
            return False
        diff_user = user_hours * 60 + user_mins
        diff_real = hours * 60 + mins
        return abs(diff_user - diff_real) <= 1
    except Exception:
        return False

heures.title = "Heures"
heures.emoji = "🕒"
heures.prep_time = 0


# ================================================================================
# 🔹 🔢 Mémoire numérique
# ================================================================================
async def memoire_numerique(ctx, embed, get_user_id, bot, msg_override=None):
    sequence = [random.randint(0, 9) for _ in range(6)]
    embed.clear_fields()
    embed.add_field(name="🔢 Mémoire numérique", value=str(sequence), inline=False)
    await ctx.edit(embed=embed)
    await asyncio.sleep(5)

    embed.clear_fields()
    embed.add_field(name="🔢 Mémoire numérique", value="🕵️‍♂️ Retape la séquence !", inline=False)
    await ctx.edit(embed=embed)

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(ctx, embed, get_user_id, bot, modal_label="Séquence")

    if text is None:
        return False
    cleaned = text.strip().replace(" ", "").replace(",", "")
    return cleaned == "".join(map(str, sequence))

memoire_numerique.title = "Mémoire numérique"
memoire_numerique.emoji = "🔢"
memoire_numerique.prep_time = 5


# ================================================================================
# 🔹 👁️ Mémoire visuelle
# ================================================================================
async def memoire_visuelle(ctx, embed, get_user_id, bot, msg_override=None):
    prep_time = 4
    base_emojis = ["🍎", "🚗", "🐶", "🌟", "⚽", "🎲", "💎", "🎵", "🍕", "🐱", "🚀", "🎁"]
    shown_emojis = random.sample(base_emojis, 4)

    embed.clear_fields()
    embed.add_field(
        name="👁️ Mémoire visuelle",
        value=f"Mémorise bien ces 4 emojis :\n{' '.join(shown_emojis)}",
        inline=False
    )
    await ctx.edit(embed=embed)
    await asyncio.sleep(prep_time)

    embed.clear_fields()
    embed.add_field(
        name="👁️ Mémoire visuelle",
        value="🔒 Les emojis ont disparu... **tape l'emoji qui n'était PAS dans la liste** (ex: 🍎).",
        inline=False
    )
    await ctx.edit(embed=embed)

    intrus = random.choice([e for e in base_emojis if e not in shown_emojis])

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(ctx, embed, get_user_id, bot, modal_label="Emoji intrus")

    if text is None:
        return False
    return text.strip() == intrus

memoire_visuelle.title = "Mémoire visuelle"
memoire_visuelle.emoji = "👁️"
memoire_visuelle.prep_time = 4


# ================================================================================
# 🔹 💰 Monnaie
# ================================================================================
async def monnaie(ctx, embed, get_user_id, bot, msg_override=None):
    prep_time = 2
    prix = random.randint(1, 20) + random.choice([0, 0.5, 0.2])
    donne = prix + random.choice([0.5, 1, 2])
    rendu = round(donne - prix, 2)

    embed.clear_fields()
    embed.add_field(
        name="💰 Monnaie",
        value=f"Prix : {prix:.2f} €\nPayé : {donne:.2f} €\n➡️ Quelle monnaie rends-tu ? (en €)",
        inline=False
    )
    await ctx.edit(embed=embed)
    await asyncio.sleep(prep_time)

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(ctx, embed, get_user_id, bot, modal_label="Monnaie rendue")

    if text is None:
        return False
    try:
        return abs(float(text.replace(',', '.')) - rendu) < 0.01
    except Exception:
        return False

monnaie.title = "Monnaie"
monnaie.emoji = "💰"
monnaie.prep_time = 2


# ================================================================================
# 🔹 🔁 Mot miroir
# ================================================================================
async def mot_miroir(ctx, embed, get_user_id, bot, msg_override=None):
    prep_time = 2
    mots = ["maison", "cerveau", "banane", "ordinateur", "voiture"]
    mot = random.choice(mots)
    mot_inverse = mot[::-1]

    embed.clear_fields()
    embed.add_field(name="🔁 Mot miroir", value=f"Tape ce mot à l'envers : **{mot}**", inline=False)
    await ctx.edit(embed=embed)
    await asyncio.sleep(prep_time)

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(ctx, embed, get_user_id, bot, modal_label="Mot à l'envers")

    if text is None:
        return False
    return text.strip().lower() == mot_inverse

mot_miroir.title = "Mot miroir"
mot_miroir.emoji = "🔁"
mot_miroir.prep_time = 2


# ================================================================================
# 🔹 🔤 Pagaille
# ================================================================================
async def pagaille(ctx, embed, get_user_id, bot, msg_override=None):
    prep_time = 2
    mot = random.choice(["amour", "cerveau", "maison", "voiture", "banane"])
    melange = "".join(random.sample(mot, len(mot)))

    embed.clear_fields()
    embed.add_field(name="🔤 Pagaille", value=f"{melange}\n➡️ Remets les lettres dans l'ordre !", inline=False)
    await ctx.edit(embed=embed)
    await asyncio.sleep(prep_time)

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(ctx, embed, get_user_id, bot, modal_label="Mot reconstitué")

    if text is None:
        return False
    return text.strip().lower() == mot

pagaille.title = "Pagaille"
pagaille.emoji = "🔤"
pagaille.prep_time = 2


# ================================================================================
# 🔹 ⚖️ Pair ou impair
# ================================================================================
async def pair_ou_impair(msg, embed, get_user, bot, msg_override=None):
    number = random.randint(1, 100)
    correct = "Pair" if number % 2 == 0 else "Impair"

    embed.clear_fields()
    embed.title = "⚖️ Pair ou impair ?"
    embed.description = f"Le nombre est : **{number}**\n➡️ Tape **Pair** ou **Impair**."
    await msg.edit(embed=embed)

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(msg, embed, get_user, bot, modal_label="Pair ou Impair")

    if text is None:
        return False
    return text.strip().lower() == correct.lower()

pair_ou_impair.title = "Pair ou impair"
pair_ou_impair.emoji = "⚖️"
pair_ou_impair.prep_time = 1.5


# ================================================================================
# 🔹 ⚡ Rapidité
# ================================================================================
async def rapidite(ctx, embed, get_user_id, bot, msg_override=None):
    prep_time = 2
    nums = random.sample(range(10, 99), 5)
    mode = random.choice(["grand", "petit"])

    embed.clear_fields()
    embed.add_field(
        name="⚡ Rapidité",
        value=f"Trouve le plus **{mode}** : {', '.join(map(str, nums))}",
        inline=False
    )
    await ctx.edit(embed=embed)
    await asyncio.sleep(prep_time)

    correct = max(nums) if mode == "grand" else min(nums)

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(ctx, embed, get_user_id, bot, modal_label="Nombre")

    if text is None:
        return False
    try:
        return int(text.strip()) == correct
    except Exception:
        return False

rapidite.title = "Rapidité"
rapidite.emoji = "⚡"
rapidite.prep_time = 2


# ================================================================================
# 🔹 ⚡ Réflexe couleur
# ================================================================================
async def reflexe_couleur(ctx, embed, get_user_id, bot, msg_override=None):
    prep_time = 2
    embed.clear_fields()
    embed.add_field(
        name="⚡ Réflexe couleur",
        value="Tu vas devoir cliquer le plus vite possible sur le bouton **✏️ Répondre**\nquand le signal **🟢 GO !** apparaît.\n\nPrépare-toi...",
        inline=False
    )
    await ctx.edit(embed=embed)
    await asyncio.sleep(prep_time)

    # Affiche "Attends..."
    embed.clear_fields()
    embed.add_field(name="⚡ Réflexe couleur", value="🔴 **ATTENDS...**", inline=False)
    msg = await ctx.edit(embed=embed)

    # Attend 2-5 secondes
    await asyncio.sleep(random.uniform(2, 5))

    # Affiche GO !
    embed.clear_fields()
    embed.add_field(name="⚡ Réflexe couleur", value="🟢 **GO ! Clique sur ✏️ Répondre !**", inline=False)
    await msg.edit(embed=embed)

    start_time = time.perf_counter()

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(msg, embed, get_user_id, bot, modal_label="Vite ! Écris OK", timeout=5)

    elapsed = time.perf_counter() - start_time

    if text is None:
        return False
    return elapsed < 2.0

reflexe_couleur.title = "Réflexe couleur"
reflexe_couleur.emoji = "🟢"
reflexe_couleur.prep_time = 2


# ================================================================================
# 🔹 🧩 Séquence de symboles
# ================================================================================
async def sequence_symboles(ctx, embed, get_user_id, bot, msg_override=None):
    symbols = ["⭐", "🍎", "🐍", "⚡", "🎲", "🍀", "🐱", "🔥"]
    seq = random.sample(symbols, 4)

    embed.clear_fields()
    embed.add_field(name="🧩 Séquence de symboles", value="Observe bien la séquence suivante :", inline=False)
    embed.add_field(name="Séquence :", value=" ".join(seq), inline=False)
    await ctx.edit(embed=embed)
    await asyncio.sleep(sequence_symboles.prep_time)

    index = random.randint(0, len(seq) - 1)
    embed.clear_fields()
    embed.add_field(
        name="🧩 Séquence de symboles",
        value=f"Quel était le **{index+1}ᵉ** emoji ?\n(Tape l'emoji, ex: 🍎)",
        inline=False
    )
    await ctx.edit(embed=embed)

    correct = seq[index]

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(ctx, embed, get_user_id, bot, modal_label="Emoji")

    if text is None:
        return False
    return text.strip() == correct

sequence_symboles.title = "Séquence de symboles"
sequence_symboles.emoji = "🧩"
sequence_symboles.prep_time = 8


# ================================================================================
# 🔹 🧩 Suite alphabétique
# ================================================================================
async def suite_alpha(ctx, embed, get_user_id, bot, msg_override=None):
    prep_time = 1
    sens_normal = random.choice([True, False])

    if sens_normal:
        start = random.randint(65, 70)
        step = random.randint(1, 3)
        serie = [chr(start + i * step) for i in range(4)]
        answer = chr(start + 4 * step)
    else:
        start = random.randint(85, 90)
        step = random.randint(1, 3)
        serie = [chr(start - i * step) for i in range(4)]
        answer = chr(start - 4 * step)

    embed.clear_fields()
    embed.add_field(name="🧩 Suite alphabétique", value=f"{', '.join(serie)} ... ?", inline=False)
    await ctx.edit(embed=embed)
    await asyncio.sleep(prep_time)

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(ctx, embed, get_user_id, bot, modal_label="Lettre suivante")

    if text is None:
        return False
    return text.strip().upper() == answer

suite_alpha.title = "Suite alphabétique"
suite_alpha.emoji = "🧩"
suite_alpha.prep_time = 1


# ================================================================================
# 🔹 ➗ Suite logique
# ================================================================================
async def suite_logique(ctx, embed, get_user_id, bot, msg_override=None):
    prep_time = 2
    type_suite = random.choice(["arithmétique", "géométrique", "alternée", "carrés", "fibonacci"])
    serie = []

    if type_suite == "arithmétique":
        start = random.randint(1, 10)
        step = random.randint(2, 6)
        serie = [start + i * step for i in range(5)]
    elif type_suite == "géométrique":
        start = random.randint(1, 5)
        ratio = random.randint(2, 3)
        serie = [start * (ratio ** i) for i in range(5)]
    elif type_suite == "alternée":
        start = random.randint(1, 10)
        add, sub = random.randint(2, 5), random.randint(1, 4)
        serie = [start]
        for i in range(1, 5):
            serie.append(serie[-1] + add if i % 2 == 1 else serie[-1] - sub)
    elif type_suite == "carrés":
        start = random.randint(1, 5)
        serie = [i ** 2 for i in range(start, start + 5)]
    elif type_suite == "fibonacci":
        a, b = random.randint(1, 5), random.randint(1, 5)
        serie = [a, b]
        for _ in range(3):
            serie.append(serie[-1] + serie[-2])

    answer_index = random.randint(0, 4)
    answer = serie[answer_index]
    display_serie = serie.copy()
    display_serie[answer_index] = "?"

    embed.clear_fields()
    display_text = ", ".join(str(v) for v in display_serie)
    embed.add_field(name="➗ Suite logique", value=f"{display_text} ...", inline=False)
    await ctx.edit(embed=embed)
    await asyncio.sleep(prep_time)

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(ctx, embed, get_user_id, bot, modal_label="Valeur manquante")

    if text is None:
        return False
    try:
        return int(text.strip()) == answer
    except Exception:
        return False

suite_logique.title = "Suite logique"
suite_logique.emoji = "➗"
suite_logique.prep_time = 2


# ================================================================================
# 🔹 🔎 Trouver la différence
# ================================================================================
async def trouver_difference(ctx, embed, get_user_id, bot, msg_override=None):
    liste1 = [random.randint(1, 9) for _ in range(6)]
    liste2 = liste1.copy()
    diff_index = random.randint(0, 5)

    while True:
        new_val = random.randint(1, 9)
        if new_val != liste1[diff_index]:
            liste2[diff_index] = new_val
            break

    embed.clear_fields()
    embed.add_field(
        name="🔎 Trouver la différence",
        value=(
            f"Voici deux suites de nombres :\n"
            f"**1️⃣** {', '.join(map(str, liste1))}\n"
            f"**2️⃣** {', '.join(map(str, liste2))}\n\n"
            f"➡️ Quelle **position (1 à 6)** est différente dans la deuxième suite ?"
        ),
        inline=False
    )
    await ctx.edit(embed=embed)
    await asyncio.sleep(trouver_difference.prep_time)

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(ctx, embed, get_user_id, bot, modal_label="Position (1 à 6)")

    if text is None:
        return False
    if not text.strip().isdigit():
        return False
    return int(text.strip()) == diff_index + 1

trouver_difference.title = "Trouver la différence"
trouver_difference.emoji = "🔎"
trouver_difference.prep_time = 1# ================================================================================
# 🔹 ✏️ Typographie erreur
# ================================================================================
async def typo_trap(ctx, embed, get_user_id, bot, msg_override=None):
    prep_time = 2

    mot = random.choice(["chien", "maison", "voiture", "ordinateur", "banane", "chocolat"])
    typo_index = random.randint(0, len(mot) - 1)
    mot_mod = list(mot)

    original = mot_mod[typo_index]
    nouvelle_lettre = random.choice([chr(i) for i in range(97, 123) if chr(i) != original])
    mot_mod[typo_index] = nouvelle_lettre
    mot_mod = "".join(mot_mod)

    embed.clear_fields()
    embed.add_field(
        name="✏️ Typographie erreur",
        value=f"{mot_mod}\n➡️ Quelle lettre est incorrecte dans ce mot ? (ex: 'x')",
        inline=False
    )
    await ctx.edit(embed=embed)
    await asyncio.sleep(prep_time)

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(ctx, embed, get_user_id, bot, modal_label="Lettre incorrecte")

    if text is None:
        return False
    return text.lower().strip() == nouvelle_lettre

typo_trap.title = "Typographie erreur"
typo_trap.emoji = "✏️"
typo_trap.prep_time = 2


# ================================================================================
# 🔖 Tous les jeux utilisent le bouton + modale
# ================================================================================
# Plus besoin de distinguer boutons/texte : tout est uniforme.
# (On garde l'attribut pour compatibilité avec entrainement_cerebral.py)
for _f in [
    addition_cachee, calcul_rapide, carre_magique_fiable_emoji,
    compter_emojis, couleurs, datation, directions_opposees,
    equation_trou, heures, memoire_numerique, memoire_visuelle,
    monnaie, mot_miroir, pagaille, pair_ou_impair, rapidite,
    reflexe_couleur, sequence_symboles, suite_alpha, suite_logique,
    trouver_difference, typo_trap,
]:
    _f.uses_buttons = False  # tout est géré par modale, plus de "boutons de choix"

# the end
