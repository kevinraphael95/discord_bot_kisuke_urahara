# ================================================================================
# 📌 kawashima_games.py — Mini-jeux Professeur Kawashima
# Objectif : Contient tous les mini-jeux cérébraux détectés automatiquement
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import random
import asyncio
import discord
from discord.ui import View, Button, Modal, TextInput

# ================================================================================
# 📦 Paramètres
# ================================================================================
TIMEOUT = 60  # 1 minute pour répondre à chaque mini-jeu

# ================================================================================
# 🛠️ Helper — Répondre via bouton + fenêtre modale (au lieu d'un message texte)
# ================================================================================
async def _ask_text_answer(ctx, embed, get_user_id, bot, button_label="✏️ Répondre", modal_label="Ta réponse", timeout=TIMEOUT):
    """
    Affiche un bouton sur le message `ctx`. Au clic, ouvre une fenêtre modale où le
    joueur tape sa réponse. Retourne le texte saisi (str) ou None si le temps est
    écoulé / personne n'a répondu.
    """

    class AnswerModal(Modal, title=modal_label):
        reponse = TextInput(label=modal_label, placeholder="Tape ta réponse ici", max_length=200)

        def __init__(self, outer_view):
            super().__init__()
            self.outer_view = outer_view

        async def on_submit(self, interaction: discord.Interaction):
            self.outer_view.result = self.reponse.value
            self.outer_view.stop()
            await interaction.response.defer()

    class AnswerView(View):
        def __init__(self):
            super().__init__(timeout=timeout)
            self.result = None

        @discord.ui.button(label=button_label, style=discord.ButtonStyle.primary)
        async def answer_btn(self, interaction: discord.Interaction, button: Button):
            if interaction.user.id != get_user_id():
                await interaction.response.send_message("🚫 Ce n'est pas ton tour.", ephemeral=True)
                return
            await interaction.response.send_modal(AnswerModal(self))

    view = AnswerView()
    await ctx.edit(view=view)
    await view.wait()
    try:
        await ctx.edit(view=None)
    except Exception:
        pass
    return view.result

# ================================================================================
# 🔹 Mini-jeux (chacun avec .emoji et .title)
# ================================================================================

# ================================================================================
# 🔹 🧮 Addition à la suite
# ================================================================================
async def addition_cachee(ctx, embed, get_user_id, bot, msg_override=None):
    additions = [random.randint(-9, 9) for _ in range(6)]
    total = sum(additions)

    embed.clear_fields()
    embed.add_field(name="🧮 Additions à la suite", value="Observe bien les additions successives...", inline=False)
    await ctx.edit(embed=embed)
    await asyncio.sleep(3)  # prep_time

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
    except:
        return False

addition_cachee.title = "Addition à la suite"
addition_cachee.emoji = "➕"
addition_cachee.prep_time = 3 + 1.8 * 6  # temps total avant question

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
        answer = eval(f"{a}{op}{b}")

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
    except:
        return False

calcul_rapide.title = "Calcul rapide"
calcul_rapide.emoji = "🧮"
calcul_rapide.prep_time = 0

# ================================================================================
# 🔹 🔢 Carré magique 3x3 fiable emoji (avec boutons)
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

    num_to_emoji = {i: f"{i}\ufe0f\u20e3" for i in range(1, 10)}  # ex: "3️⃣" (le \ufe0f manquait)
    display = "\n".join("|".join(num_to_emoji.get(x, x) for x in r) for r in base)

    embed.clear_fields()
    embed.add_field(
        name="🔢 Carré magique",
        value=f"Complète le carré magique pour que toutes les lignes, colonnes et diagonales fassent 15 :\n{display}",
        inline=False
    )
    msg = await ctx.edit(embed=embed)

    # ====== Vue avec boutons ======
    class CarreView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=TIMEOUT)
            self.selected = None
            # Ajout des boutons 1 à 9
            for n in range(1, 10):
                button = discord.ui.Button(label=str(n), style=discord.ButtonStyle.primary)
                async def callback(interaction, n=n):
                    if interaction.user.id != get_user_id():
                        await interaction.response.send_message("🚫 Pas pour toi.", ephemeral=True)
                        return
                    self.selected = n
                    for child in self.children:
                        child.disabled = True
                    await interaction.response.edit_message(view=self)
                    self.stop()
                button.callback = callback
                self.add_item(button)

    view = CarreView()
    await msg.edit(view=view)
    await view.wait()

    return view.selected == answer if view.selected is not None else None

carre_magique_fiable_emoji.title = "Carré magique 3x3"
carre_magique_fiable_emoji.emoji = "🔢"
carre_magique_fiable_emoji.prep_time = 0



# ================================================================================
# 🔹 👀 Compter les emojis
# ================================================================================
async def compter_emojis(ctx, embed, get_user_id, bot, msg_override=None):
    import random

    emojis = ["🍎", "🍌", "🍒", "🍇", "🍊"]
    cible = random.choice(emojis)

    # Génère une grille 4x4
    grille = [[random.choice(emojis) for _ in range(4)] for _ in range(4)]
    texte_grille = "\n".join("".join(ligne) for ligne in grille)

    # Compte combien de fois l'emoji cible apparaît
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
# 🎨 Couleurs (Stroop complet)
# ================================================================================
async def couleurs(ctx, embed, get_user_id, bot, msg_override=None):
    styles = {
        "bleu": discord.ButtonStyle.primary,
        "vert": discord.ButtonStyle.success,
        "rouge": discord.ButtonStyle.danger,
        "gris": discord.ButtonStyle.secondary
    }

    couleurs_list = list(styles.keys())
    mots = couleurs_list.copy()
    random.shuffle(mots)

    buttons = []
    for couleur, mot in zip(couleurs_list, mots):
        button = Button(label=mot.upper(), style=styles[couleur])
        buttons.append(button)

    question_type = random.choice(["mot", "couleur"])
    if question_type == "mot":
        cible = random.choice(mots)
        question = f"Appuie sur le bouton où est écrit le **MOT** `{cible.upper()}` !"
        condition = lambda b: b.label.lower() == cible
    else:
        cible = random.choice(couleurs_list)
        question = f"Appuie sur le bouton de **COULEUR** `{cible.upper()}` !"
        condition = lambda b: b.style == styles[cible]

    view = View(timeout=TIMEOUT)
    for button in buttons:
        async def callback(interaction, b=button):
            if interaction.user.id != get_user_id():
                await interaction.response.send_message("🚫 Ce jeu n’est pas pour toi !", ephemeral=True)
                return
            view.value = condition(b)
            view.stop()
            await interaction.response.defer()

        button.callback = callback
        view.add_item(button)

    embed.clear_fields()
    embed.add_field(name="🎨 Couleurs (Stroop)", value=question, inline=False)
    await ctx.edit(embed=embed, view=view)

    await asyncio.sleep(0.5)  # prep_time
    await view.wait()
    for child in view.children:
        child.disabled = True
    await ctx.edit(view=view)

    return getattr(view, "value", False)

couleurs.title = "Couleurs"
couleurs.emoji = "🎨"
couleurs.prep_time = 0.5

# ================================================================================
# 🔹 📅 Datation (Version boutons)
# ================================================================================
async def datation(msg, embed, get_user_id, bot, msg_override=None):
    import datetime, random
    user_id = get_user_id()

    # Générer une date autour d'aujourd'hui
    today = datetime.date.today()
    delta_days = random.randint(-7, 7)
    date = today + datetime.timedelta(days=delta_days)

    # ⚠️ On évite strftime("%A") : le nom du jour dépend de la locale du système
    # (peut planter avec un KeyError si le serveur n'est pas en locale anglaise).
    # date.weekday() est indépendant de la locale (0 = lundi ... 6 = dimanche).
    jours_fr_liste = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    jour_correct = jours_fr_liste[date.weekday()]

    # Affichage
    embed.clear_fields()
    embed.title = "📅 Datation"
    embed.description = f"Quel jour était le **{date.day}/{date.month}/{date.year}** ?"
    await msg.edit(embed=embed)

    # Vue de 7 boutons
    class DayView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=15)
            jours = ["lundi","mardi","mercredi","jeudi","vendredi","samedi","dimanche"]
            for j in jours:
                self.add_item(self.DayButton(j))

        class DayButton(discord.ui.Button):
            def __init__(self, jour):
                super().__init__(label=jour.capitalize(), style=discord.ButtonStyle.blurple)
                self.jour = jour

            async def callback(self, interaction: discord.Interaction):
                if interaction.user.id != user_id:
                    return await interaction.response.send_message("❌ Ce n'est pas ta partie.", ephemeral=True)
                
                self.view.answer = self.jour
                self.view.stop()
                await interaction.response.defer()

    view = DayView()
    await msg.edit(view=view)

    timeout = await view.wait()
    if timeout:
        return False

    # Vérifier la bonne réponse
    return view.answer == jour_correct

datation.title = "Datation"
datation.emoji = "📅"
datation.prep_time = 0

# ================================================================================
# 🔹 🧭 Directions opposées
# ================================================================================
async def directions_opposees(ctx, embed, get_user_id, bot, msg_override=None):
    import random
    from discord.ui import View, Button
    from discord import ButtonStyle

    arrows = ["⬆️", "⬇️", "⬅️", "➡️"]
    opposites = {"⬆️": "⬇️", "⬇️": "⬆️", "⬅️": "➡️", "➡️": "⬅️"}

    arrow = random.choice(arrows)
    correct = opposites[arrow]

    embed.clear_fields()
    embed.add_field(
        name="🧭 Directions opposées",
        value=f"Flèche affichée : {arrow}\n➡️ Clique sur **la direction opposée** !",
        inline=False
    )

    class ArrowView(View):
        def __init__(self):
            super().__init__(timeout=TIMEOUT)
            self.result = False

    view = ArrowView()

    for symbol in arrows:
        async def callback(interaction, s=symbol):
            if interaction.user.id != get_user_id():
                await interaction.response.send_message("🚫 Pas ton tour !", ephemeral=True)
                return
            view.result = (s == correct)
            view.stop()
            await interaction.response.defer()

        btn = Button(label=symbol, style=ButtonStyle.primary)
        btn.callback = callback
        view.add_item(btn)

    # ctx est un Message → on édite le message existant
    await ctx.edit(embed=embed, view=view)

    await view.wait()
    await ctx.edit(view=None)  # Supprime les boutons
    return view.result


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
    except:
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
    question_type = f"Quelle est la différence entre {heure_1} et {heure_2} ?"

    embed.clear_fields()
    embed.add_field(name="🕒 Heures", value=question_type, inline=False)
    await ctx.edit(embed=embed)

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(ctx, embed, get_user_id, bot, modal_label="Différence (ex: 1h30)")

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
    except:
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
    await asyncio.sleep(5)  # prep_time

    embed.clear_fields()
    embed.add_field(name="🔢 Mémoire numérique", value="🕵️‍♂️ Retape la séquence !", inline=False)
    await ctx.edit(embed=embed)

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(ctx, embed, get_user_id, bot, modal_label="Séquence (ex: 123456)")

    if text is None:
        return False
    return text.strip() == "".join(map(str, sequence))

memoire_numerique.title = "Mémoire numérique"
memoire_numerique.emoji = "🔢"
memoire_numerique.prep_time = 5

# ================================================================================
# 🔹 👁️ Mémoire visuelle (boutons)
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
        value="🔒 Les emojis ont disparu... retrouve celui qui **n'était PAS dans la liste !**",
        inline=False
    )
    await ctx.edit(embed=embed)
    await asyncio.sleep(1)

    all_choices = shown_emojis.copy()
    intrus = random.choice([e for e in base_emojis if e not in shown_emojis])
    all_choices.append(intrus)
    random.shuffle(all_choices)

    class EmojiView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=TIMEOUT)
            self.selected = None

    view = EmojiView()
    for e in all_choices:
        async def make_callback(emoji=e):
            async def callback(interaction: discord.Interaction):
                if interaction.user.id != get_user_id():
                    await interaction.response.send_message("🚫 Pas ton tour.", ephemeral=True)
                    return
                view.selected = emoji
                view.stop()
                await interaction.response.defer()
            return callback

        button = discord.ui.Button(label=e, style=discord.ButtonStyle.secondary)
        button.callback = await make_callback(e)
        view.add_item(button)

    await ctx.edit(embed=embed, view=view)
    await view.wait()
    return getattr(view, "selected", None) == intrus

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
        value=f"Prix : {prix:.2f} €\nPayé : {donne:.2f} €\n➡️ Quelle monnaie rends-tu ?",
        inline=False
    )
    await ctx.edit(embed=embed)
    await asyncio.sleep(prep_time)

    if msg_override is not None:
        text = msg_override.content
    else:
        text = await _ask_text_answer(ctx, embed, get_user_id, bot, modal_label="Monnaie rendue (€)")

    if text is None:
        return False
    try:
        return abs(float(text.replace(',', '.')) - rendu) < 0.01
    except:
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
    embed.add_field(
        name="🔁 Mot miroir",
        value=f"Tape ce mot à l'envers : {mot}",
        inline=False
    )
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
    embed.add_field(name="🔤 Pagaille", value=f"{melange}\n➡️ Remets les lettres dans l’ordre !", inline=False)
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
    import random

    number = random.randint(1, 100)
    correct = "Pair" if number % 2 == 0 else "Impair"

    embed.title = "⚖️ Pair ou impair ?"
    embed.description = f"Le nombre est : **{number}**"
    await msg.edit(embed=embed)

    class POIView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=10)

        @discord.ui.button(label="Pair", style=discord.ButtonStyle.blurple)
        async def pair(self, interaction: discord.Interaction, button):
            if interaction.user.id != get_user():
                return await interaction.response.send_message("❌ Pas pour toi.", ephemeral=True)
            self.answer = "Pair"
            self.stop()

        @discord.ui.button(label="Impair", style=discord.ButtonStyle.green)
        async def impair(self, interaction: discord.Interaction, button):
            if interaction.user.id != get_user():
                return await interaction.response.send_message("❌ Pas pour toi.", ephemeral=True)
            self.answer = "Impair"
            self.stop()

    view = POIView()
    await msg.edit(view=view)

    timeout = await view.wait()
    if timeout:
        return False

    return view.answer == correct

pair_ou_impair.title = "Pair ou impair"
pair_ou_impair.emoji = "⚖️"
pair_ou_impair.prep_time = 1.5

# ================================================================
# 🔹 ⚡ Rapidité (version boutons)
# ================================================================
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

    # ----- Vue + Boutons -----
    class QuickView(View):
        def __init__(self):
            super().__init__(timeout=10)
            self.success = False
            for n in nums:
                self.add_item(QuickButton(n))

        async def interaction_check(self, inter):
            return inter.user.id == get_user_id()

    class QuickButton(Button):
        def __init__(self, value):
            super().__init__(label=str(value), style=discord.ButtonStyle.primary)
            self.value = value

        async def callback(self, inter):
            if self.value == correct:
                view.success = True
                await inter.response.edit_message(
                    content=f"✅ Correct ! ({self.value})", view=None, embed=None
                )
            else:
                await inter.response.edit_message(
                    content=f"❌ Mauvaise réponse ({self.value})", view=None, embed=None
                )
            view.stop()

    view = QuickView()
    view_msg = await ctx.edit(embed=embed, view=view)

    await view.wait()
    return view.success


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
        value="Appuie sur le bouton **dès qu'il devient vert**.\nMais pas avant 👀",
        inline=False
    )
    await ctx.edit(embed=embed)
    await asyncio.sleep(prep_time)

    class ReflexeView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=7)
            self.clicked = False
            self.start_time = None
            self.reaction_time = None
            self.too_early = False

        @discord.ui.button(label="🔴 ATTENDS...", style=discord.ButtonStyle.danger)
        async def reflexe(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != get_user_id():
                await interaction.response.send_message("🚫 Ce n’est pas ton jeu.", ephemeral=True)
                return
            if button.style == discord.ButtonStyle.danger:
                self.too_early = True
                self.clicked = True
                self.stop()
                await interaction.response.send_message("❌ Trop tôt !", ephemeral=True)
            elif button.style == discord.ButtonStyle.success:
                self.reaction_time = round(asyncio.get_event_loop().time() - self.start_time, 3)
                self.clicked = True
                self.stop()
                await interaction.response.send_message(f"✅ Réflexe en {self.reaction_time}s !", ephemeral=True)

    view = ReflexeView()
    msg = await ctx.edit(view=view)

    await asyncio.sleep(random.uniform(2, 5))
    if view.is_finished():
        return False

    button = view.children[0]
    button.label = "🟢 CLIQUE !"
    button.style = discord.ButtonStyle.success
    await msg.edit(view=view)
    view.start_time = asyncio.get_event_loop().time()
    await view.wait()

    if view.too_early or not view.clicked or view.reaction_time is None:
        return False
    return view.reaction_time < 1.2

reflexe_couleur.title = "Réflexe couleur"
reflexe_couleur.emoji = "🟢"
reflexe_couleur.prep_time = 2

# ================================================================================
# 🔹 🧩 Séquence de symboles (version avec boutons)
# ================================================================================
async def sequence_symboles(ctx, embed, get_user_id, bot, msg_override=None):
    import random, asyncio
    from discord.ui import View, Button
    from discord import ButtonStyle

    symbols = ["⭐", "🍎", "🐍", "⚡", "🎲", "🍀", "🐱", "🔥"]
    seq = random.sample(symbols, 4)

    # Affichage initial
    embed.clear_fields()
    embed.add_field(
        name="🧩 Séquence de symboles",
        value="Observe bien la séquence suivante :",
        inline=False
    )
    embed.add_field(name="Séquence :", value=" ".join(seq), inline=False)
    await ctx.edit(embed=embed)
    await asyncio.sleep(sequence_symboles.prep_time)

    # On cache la séquence
    question_type = random.choice(["position", "complete"])
    embed.clear_fields()

    if question_type == "position":
        index = random.randint(0, len(seq) - 1)
        embed.add_field(
            name="🧩 Séquence de symboles",
            value=f"Quel était le **{index+1}ᵉ** emoji ?",
            inline=False
        )
        correct_answer = seq[index]
        multiple_clicks = False
    else:
        embed.add_field(
            name="🧩 Séquence de symboles",
            value="Clique sur les 4 emojis dans **le bon ordre** !",
            inline=False
        )
        correct_answer = seq
        multiple_clicks = True

    # ============== Création de la vue ==============
    class SequenceView(View):
        def __init__(self):
            super().__init__(timeout=TIMEOUT)
            self.result = False
            self.selected = []

    view = SequenceView()

    # ============== Création des boutons ==============
    for symbol in symbols:
        async def callback(interaction, s=symbol):
            if interaction.user.id != get_user_id():
                await interaction.response.send_message("🚫 Pas ton tour !", ephemeral=True)
                return

            if multiple_clicks:
                view.selected.append(s)
                # met à jour le bouton (désactivé après clic)
                for btn in view.children:
                    if btn.label == s:
                        btn.disabled = True
                        break
                await interaction.response.edit_message(view=view)

                # si 4 choix faits, on vérifie
                if len(view.selected) == len(correct_answer):
                    view.result = view.selected == correct_answer
                    view.stop()
            else:
                view.result = (s == correct_answer)
                view.stop()
                await interaction.response.defer()

        btn = Button(label=symbol, style=ButtonStyle.secondary)
        btn.callback = callback
        view.add_item(btn)

    await ctx.edit(embed=embed, view=view)
    await view.wait()

    # Nettoyage
    await ctx.edit(view=None)
    return view.result


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
    embed.add_field(
        name="🧩 Suite alphabétique",
        value=f"{', '.join(serie)} ... ?",
        inline=False
    )
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
    display_text = ", ".join(str(v) for v in display_serie)  # ex: "7, 13, ?, 25, 31" au lieu du repr brut de la liste
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
    except:
        return False

suite_logique.title = "Suite logique"
suite_logique.emoji = "➗"
suite_logique.prep_time = 2

# ================================================================================
# 🔹 🔎 Trouver la différence
# ================================================================================
async def trouver_difference(ctx, embed, get_user_id, bot, msg_override=None):
    import random, asyncio

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
trouver_difference.prep_time = 1

# ================================================================================
# 🔹 ✏️ Typographie erreur
# ================================================================================
async def typo_trap(ctx, embed, get_user_id, bot, msg_override=None):
    prep_time = 2  # Temps pour observer le mot avant de répondre

    mot = random.choice(["chien", "maison", "voiture", "ordinateur", "banane", "chocolat"])
    typo_index = random.randint(0, len(mot) - 1)
    mot_mod = list(mot)
    
    # Génère une lettre différente de la lettre originale
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
    await asyncio.sleep(prep_time)  # temps d'observation

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


#the end
