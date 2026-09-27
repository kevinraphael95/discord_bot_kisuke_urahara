# ================================================================================
# 📌 kawashima_games.py — Mini-jeux Kawashima
# 4 boutons de choix (1 bonne réponse + 3 leurres)
# Retour : (success: bool, clicker_id: int | None)
# ================================================================================

# ================================================================================
# 📦 Imports nécessaires
# ================================================================================
import random
import asyncio
import time
import discord
from discord.ui import View, Button

TIMEOUT = 60


# ================================================================================
# 🛠️ Helpers
# ================================================================================
async def _ask_choice(ctx, embed, choices, correct, get_user_id, timeout=TIMEOUT):
    """Affiche les 4 boutons de choix. Retourne (success, clicker_id)."""
    shuffled = choices.copy()
    random.shuffle(shuffled)

    class ChoiceView(View):
        def __init__(self):
            super().__init__(timeout=timeout)
            self.result = False
            self.clicker_id = None

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            expected = get_user_id()
            if expected is not None and interaction.user.id != expected:
                await interaction.response.send_message(
                    "🚫 Ce n'est pas ton tour.", ephemeral=True
                )
                return False
            return True

    view = ChoiceView()

    for choice in shuffled:
        btn = Button(label=str(choice), style=discord.ButtonStyle.primary)

        async def callback(interaction, c=choice):
            view.result = (c == correct)
            view.clicker_id = interaction.user.id
            for child in view.children:
                child.disabled = True
            try:
                await interaction.response.edit_message(view=view)
            except Exception:
                try:
                    await interaction.response.defer()
                except Exception:
                    pass
            view.stop()

        btn.callback = callback
        view.add_item(btn)

    # ⚠️ Délai AVANT la 1ère tentative pour laisser respirer Discord
    await asyncio.sleep(0.3)

    # Retry anti-rate-limit (5 tentatives)
    for tentative in range(5):
        try:
            await ctx.edit(embed=embed, view=view)
            break
        except Exception as e:
            print(f"[kawashima] edit raté (essai {tentative+1}) : {e}")
            await asyncio.sleep(1.5)
    else:
        print("[kawashima] impossible d'afficher les boutons")
        return False, None

    await view.wait()

    try:
        await ctx.edit(view=None)
    except Exception:
        pass

    return view.result, view.clicker_id


def _numeric_distractors(correct: int, n=3, min_val=None, max_val=None):
    """Génère n leurres numériques proches de `correct`."""
    distractors = set()
    attempts = 0
    while len(distractors) < n and attempts < 100:
        attempts += 1
        if abs(correct) < 20:
            delta = random.choice([-3, -2, -1, 1, 2, 3])
        elif abs(correct) < 100:
            delta = random.choice([-10, -5, -3, -2, -1, 1, 2, 3, 5, 10])
        else:
            delta = random.choice([-50, -20, -10, -5, 5, 10, 20, 50])
        candidate = correct + delta
        if min_val is not None and candidate < min_val:
            continue
        if max_val is not None and candidate > max_val:
            continue
        if candidate != correct:
            distractors.add(candidate)
    while len(distractors) < n:
        candidate = correct + random.choice([-1, 1, -2, 2, -3, 3, -4, 4, -5, 5])
        if min_val is not None and candidate < min_val:
            continue
        if max_val is not None and candidate > max_val:
            continue
        if candidate != correct:
            distractors.add(candidate)
    return list(distractors)


def _clean_embed(embed):
    """Nettoie complètement un embed avant chaque jeu."""
    embed.clear_fields()
    embed.title = None
    embed.description = None
    embed.color = discord.Color.blurple()


# ================================================================================
# 🔹 ⚡ Réflexe couleur
# ================================================================================
async def reflexe_couleur(ctx, embed, get_user_id, bot, msg_override=None):
    _clean_embed(embed)
    embed.add_field(name="⚡ Réflexe couleur", value="🔴 **Attends que le bouton devienne vert...**", inline=False)

    class ReflexeView(View):
        def __init__(self):
            super().__init__(timeout=15)
            self.result = False
            self.clicker_id = None
            self.too_early = False
            self.started = False

        @discord.ui.button(label="🔴 ATTENDS...", style=discord.ButtonStyle.danger)
        async def reflexe(self, interaction: discord.Interaction, button: discord.ui.Button):
            expected = get_user_id()
            if expected is not None and interaction.user.id != expected:
                await interaction.response.send_message("🚫 Ce n'est pas ton tour.", ephemeral=True)
                return

            if not self.started:
                self.too_early = True
                self.clicker_id = interaction.user.id
                button.disabled = True
                button.label = "❌ Trop tôt !"
            else:
                self.result = True
                self.clicker_id = interaction.user.id
                button.disabled = True
                button.label = "✅ Bien joué !"

            try:
                await interaction.response.edit_message(view=self)
            except Exception:
                pass
            self.stop()

    view = ReflexeView()
    await ctx.edit(embed=embed, view=view)

    await asyncio.sleep(random.uniform(2, 5))
    if view.is_finished():
        return False, view.clicker_id

    button = view.children[0]
    button.label = "🟢 CLIQUE !"
    button.style = discord.ButtonStyle.success
    view.started = True
    try:
        await ctx.edit(view=view)
    except Exception:
        pass

    await view.wait()
    try:
        await ctx.edit(view=None)
    except Exception:
        pass

    if view.too_early:
        return False, view.clicker_id
    return view.result, view.clicker_id

reflexe_couleur.title = "Réflexe couleur"
reflexe_couleur.emoji = "🟢"
reflexe_couleur.prep_time = 2


# ================================================================================
# 🔹 🧮 Addition à la suite
# ================================================================================
async def addition_cachee(ctx, embed, get_user_id, bot, msg_override=None):
    additions = [random.randint(-9, 9) for _ in range(6)]
    total = sum(additions)

    _clean_embed(embed)
    embed.add_field(name="🧮 Addition à la suite", value="Observe bien...", inline=False)
    await ctx.edit(embed=embed)
    await asyncio.sleep(3)

    for add in additions:
        _clean_embed(embed)
        embed.add_field(name="🧮 Addition à la suite", value=f"{add:+d}", inline=False)
        await ctx.edit(embed=embed)
        await asyncio.sleep(1.8)

    _clean_embed(embed)
    embed.add_field(name="🧮 Addition à la suite", value="Quel est le total final ?", inline=False)
    await ctx.edit(embed=embed)

    choices = [total] + _numeric_distractors(total)
    return await _ask_choice(ctx, embed, choices, total, get_user_id)

addition_cachee.title = "Addition à la suite"
addition_cachee.emoji = "➕"
addition_cachee.prep_time = 3 + 1.8 * 6


# ================================================================================
# 🔹 🧮 Calcul rapide
# ================================================================================
async def calcul_rapide(ctx, embed, get_user_id, bot, msg_override=None):
    op = random.choice(["+", "-", "*", "/"])
    if op == "*":
        a, b = random.randint(2, 9), random.randint(2, 9)
        answer = a * b
    elif op == "/":
        b = random.randint(2, 9)
        answer = random.randint(2, 9)
        a = b * answer
    else:
        a, b = random.randint(10, 50), random.randint(10, 50)
        answer = a + b if op == "+" else a - b

    _clean_embed(embed)
    embed.add_field(name="🧮 Calcul rapide", value=f"{a} {op} {b} = ?", inline=False)
    await ctx.edit(embed=embed)

    choices = [answer] + _numeric_distractors(answer)
    return await _ask_choice(ctx, embed, choices, answer, get_user_id)

calcul_rapide.title = "Calcul rapide"
calcul_rapide.emoji = "🧮"
calcul_rapide.prep_time = 0


# ================================================================================
# 🔹 🔢 Carré magique
# ================================================================================
async def carre_magique_fiable_emoji(ctx, embed, get_user_id, bot, msg_override=None):
    base = [[8, 1, 6], [3, 5, 7], [4, 9, 2]]

    def rotate(s):
        return [list(x) for x in zip(*s[::-1])]

    def flip(s):
        return [row[::-1] for row in s]

    for _ in range(random.randint(0, 3)):
        base = rotate(base)
    if random.choice([True, False]):
        base = flip(base)

    row, col = random.randint(0, 2), random.randint(0, 2)
    answer = base[row][col]
    base[row][col] = "❓"

    num_to_emoji = {i: f"{i}\ufe0f\u20e3" for i in range(1, 10)}
    display = "\n".join("|".join(num_to_emoji.get(x, x) for x in r) for r in base)

    _clean_embed(embed)
    embed.add_field(
        name="🔢 Carré magique",
        value=f"Toutes les lignes/colonnes/diagonales font 15 :\n{display}\n\nQuel chiffre manque ?",
        inline=False
    )
    await ctx.edit(embed=embed)

    choices = random.sample([n for n in range(1, 10) if n != answer], 3) + [answer]
    return await _ask_choice(ctx, embed, choices, answer, get_user_id)

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
    texte_grille = "\n".join("".join(l) for l in grille)
    total = sum(l.count(cible) for l in grille)

    _clean_embed(embed)
    embed.add_field(
        name="👀 Compter les emojis",
        value=f"{texte_grille}\n\nCombien de {cible} ?",
        inline=False
    )
    await ctx.edit(embed=embed)

    choices = [total] + _numeric_distractors(total, min_val=0, max_val=16)
    return await _ask_choice(ctx, embed, choices, total, get_user_id)

compter_emojis.title = "Compter les emojis"
compter_emojis.emoji = "👀"
compter_emojis.prep_time = 1.5


# ================================================================================
# 🔹 🎨 Couleurs
# ================================================================================
async def couleurs(ctx, embed, get_user_id, bot, msg_override=None):
    couleurs_list = ["bleu", "vert", "rouge", "gris"]
    mots = couleurs_list.copy()
    random.shuffle(mots)
    cible = random.choice(mots)

    _clean_embed(embed)
    embed.add_field(
        name="🎨 Couleurs",
        value=f"Mots : **{', '.join(m.upper() for m in mots)}**\n\nQuel mot est écrit en **{cible.upper()}** ?",
        inline=False
    )
    await ctx.edit(embed=embed)

    choices = couleurs_list.copy()
    return await _ask_choice(ctx, embed, choices, cible, get_user_id)

couleurs.title = "Couleurs"
couleurs.emoji = "🎨"
couleurs.prep_time = 0.5


# ================================================================================
# 🔹 📅 Datation
# ================================================================================
async def datation(msg, embed, get_user_id, bot, msg_override=None):
    import datetime
    today = datetime.date.today()
    date = today + datetime.timedelta(days=random.randint(-7, 7))
    jours = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    correct = jours[date.weekday()]

    _clean_embed(embed)
    embed.title = "📅 Datation"
    embed.description = f"Quel jour était le **{date.day}/{date.month}/{date.year}** ?"
    await msg.edit(embed=embed)

    choices = random.sample([j for j in jours if j != correct], 3) + [correct]
    return await _ask_choice(msg, embed, choices, correct, get_user_id)

datation.title = "Datation"
datation.emoji = "📅"
datation.prep_time = 0


# ================================================================================
# 🔹 🧭 Directions opposées
# ================================================================================
async def directions_opposees(ctx, embed, get_user_id, bot, msg_override=None):
    arrows_map = {"⬆️": "⬇️", "⬇️": "⬆️", "⬅️": "➡️", "➡️": "⬅️"}
    arrow = random.choice(list(arrows_map.keys()))
    correct = arrows_map[arrow]

    _clean_embed(embed)
    embed.add_field(
        name="🧭 Directions opposées",
        value=f"Flèche : **{arrow}**\n\nQuelle est la direction opposée ?",
        inline=False
    )
    await ctx.edit(embed=embed)

    choices = list(arrows_map.keys())
    return await _ask_choice(ctx, embed, choices, correct, get_user_id)

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
        a, b = random.randint(2, 9), random.randint(2, 9)
        answer = random.choice([a, b])
        question = f"? × {b} = {a * b}" if answer == a else f"{a} × ? = {a * b}"

    _clean_embed(embed)
    embed.add_field(name="➗ Équation à trou", value=question, inline=False)
    await ctx.edit(embed=embed)

    choices = [answer] + _numeric_distractors(answer, min_val=0)
    return await _ask_choice(ctx, embed, choices, answer, get_user_id)

equation_trou.title = "Equation à trou"
equation_trou.emoji = "➗"
equation_trou.prep_time = 0


# ================================================================================
# 🔹 🕒 Heures
# ================================================================================
async def heures(ctx, embed, get_user_id, bot, msg_override=None):
    h1, m1 = random.randint(0, 23), random.choice([0, 15, 30, 45])
    h2, m2 = random.randint(0, 23), random.choice([0, 15, 30, 45])
    if (h1, m1) == (h2, m2):
        h2 = (h2 + 1) % 24
    diff = abs((h1 * 60 + m1) - (h2 * 60 + m2))
    hours, mins = divmod(diff, 60)
    correct_str = f"{hours}h{mins:02d}" if mins else f"{hours}h"

    _clean_embed(embed)
    embed.add_field(
        name="🕒 Heures",
        value=f"Différence entre **{h1:02d}:{m1:02d}** et **{h2:02d}:{m2:02d}** ?",
        inline=False
    )
    await ctx.edit(embed=embed)

    distractors = set()
    for delta in [-60, -45, -30, -15, 15, 30, 45, 60]:
        total = diff + delta
        if total < 0:
            continue
        h, m = divmod(total, 60)
        s = f"{h}h{m:02d}" if m else f"{h}h"
        if s != correct_str:
            distractors.add(s)
    distractors = list(distractors)
    random.shuffle(distractors)
    choices = distractors[:3] + [correct_str]

    return await _ask_choice(ctx, embed, choices, correct_str, get_user_id)

heures.title = "Heures"
heures.emoji = "🕒"
heures.prep_time = 0


# ================================================================================
# 🔹 🔢 Mémoire numérique
# ================================================================================
async def memoire_numerique(ctx, embed, get_user_id, bot, msg_override=None):
    sequence = [random.randint(0, 9) for _ in range(5)]

    _clean_embed(embed)
    embed.add_field(name="🔢 Mémoire numérique", value=f"Mémorise : **{''.join(map(str, sequence))}**", inline=False)
    await ctx.edit(embed=embed)
    await asyncio.sleep(5)

    _clean_embed(embed)
    embed.add_field(name="🔢 Mémoire numérique", value="Quelle était la séquence ?", inline=False)
    await ctx.edit(embed=embed)

    seq_str = "".join(map(str, sequence))
    distractors = set()
    while len(distractors) < 3:
        mod = list(seq_str)
        idx = random.randint(0, len(mod) - 1)
        mod[idx] = str(random.randint(0, 9))
        cand = "".join(mod)
        if cand != seq_str:
            distractors.add(cand)

    choices = list(distractors) + [seq_str]
    return await _ask_choice(ctx, embed, choices, seq_str, get_user_id)

memoire_numerique.title = "Mémoire numérique"
memoire_numerique.emoji = "🔢"
memoire_numerique.prep_time = 5


# ================================================================================
# 🔹 👁️ Mémoire visuelle
# ================================================================================
async def memoire_visuelle(ctx, embed, get_user_id, bot, msg_override=None):
    base_emojis = ["🍎", "🚗", "🐶", "🌟", "⚽", "🎲", "💎", "🎵", "🍕", "🐱", "🚀", "🎁"]
    shown = random.sample(base_emojis, 4)

    _clean_embed(embed)
    embed.add_field(name="👁️ Mémoire visuelle", value=f"Mémorise : {' '.join(shown)}", inline=False)
    await ctx.edit(embed=embed)
    await asyncio.sleep(4)

    _clean_embed(embed)
    embed.add_field(name="👁️ Mémoire visuelle", value="Lequel n'était **PAS** dans la liste ?", inline=False)
    await ctx.edit(embed=embed)

    intrus = random.choice([e for e in base_emojis if e not in shown])
    choices = shown[:] + [intrus]
    random.shuffle(choices)
    return await _ask_choice(ctx, embed, choices, intrus, get_user_id)

memoire_visuelle.title = "Mémoire visuelle"
memoire_visuelle.emoji = "👁️"
memoire_visuelle.prep_time = 4


# ================================================================================
# 🔹 💰 Monnaie
# ================================================================================
async def monnaie(ctx, embed, get_user_id, bot, msg_override=None):
    prix = round(random.uniform(1, 20), 2)
    donne = round(prix + random.choice([0.5, 1.0, 2.0]), 2)
    rendu = round(donne - prix, 2)

    _clean_embed(embed)
    embed.add_field(
        name="💰 Monnaie",
        value=f"Prix : **{prix:.2f} €**\nPayé : **{donne:.2f} €**\n\nQuelle monnaie rends-tu ?",
        inline=False
    )
    await ctx.edit(embed=embed)

    correct_c = round(rendu * 100)
    distractors = set()
    while len(distractors) < 3:
        delta = random.choice([-50, -20, -10, -5, 5, 10, 20, 50])
        cand = correct_c + delta
        if cand > 0 and cand != correct_c:
            distractors.add(cand)

    choices = [f"{c/100:.2f} €" for c in distractors]
    correct_str = f"{rendu:.2f} €"
    choices.append(correct_str)
    return await _ask_choice(ctx, embed, choices, correct_str, get_user_id)

monnaie.title = "Monnaie"
monnaie.emoji = "💰"
monnaie.prep_time = 2


# ================================================================================
# 🔹 🔁 Mot miroir
# ================================================================================
async def mot_miroir(ctx, embed, get_user_id, bot, msg_override=None):
    mots = ["maison", "cerveau", "banane", "voiture", "jardin", "chocolat"]
    mot = random.choice(mots)
    correct = mot[::-1]

    _clean_embed(embed)
    embed.add_field(name="🔁 Mot miroir", value=f"**{mot}** à l'envers ?", inline=False)
    await ctx.edit(embed=embed)

    autres = [m for m in mots if m != mot]
    distractors = random.sample([m[::-1] for m in autres], 3)
    choices = distractors + [correct]
    return await _ask_choice(ctx, embed, choices, correct, get_user_id)

mot_miroir.title = "Mot miroir"
mot_miroir.emoji = "🔁"
mot_miroir.prep_time = 2


# ================================================================================
# 🔹 🔤 Pagaille
# ================================================================================
async def pagaille(ctx, embed, get_user_id, bot, msg_override=None):
    mots = ["amour", "cerveau", "maison", "voiture", "banane", "jardin"]
    mot = random.choice(mots)
    melange = mot
    while melange == mot:
        melange = "".join(random.sample(mot, len(mot)))

    _clean_embed(embed)
    embed.add_field(name="🔤 Pagaille", value=f"**{melange}**\n\nQuel mot se cache ici ?", inline=False)
    await ctx.edit(embed=embed)

    autres = [m for m in mots if m != mot]
    distractors = random.sample(autres, 3)
    choices = distractors + [mot]
    return await _ask_choice(ctx, embed, choices, mot, get_user_id)

pagaille.title = "Pagaille"
pagaille.emoji = "🔤"
pagaille.prep_time = 2


# ================================================================================
# 🔹 ⚖️ Pair ou impair
# ================================================================================
async def pair_ou_impair(msg, embed, get_user_id, bot, msg_override=None):
    number = random.randint(1, 100)
    correct = "Pair" if number % 2 == 0 else "Impair"

    _clean_embed(embed)
    embed.title = "⚖️ Pair ou impair ?"
    embed.description = f"Le nombre est : **{number}**"
    await msg.edit(embed=embed)

    choices = ["Pair", "Impair"]
    return await _ask_choice(msg, embed, choices, correct, get_user_id)

pair_ou_impair.title = "Pair ou impair"
pair_ou_impair.emoji = "⚖️"
pair_ou_impair.prep_time = 1.5


# ================================================================================
# 🔹 ⚡ Rapidité
# ================================================================================
async def rapidite(ctx, embed, get_user_id, bot, msg_override=None):
    nums = random.sample(range(10, 99), 5)
    mode = random.choice(["grand", "petit"])

    _clean_embed(embed)
    embed.add_field(
        name="⚡ Rapidité",
        value=f"Le plus **{mode}** :\n{', '.join(map(str, nums))}",
        inline=False
    )
    await ctx.edit(embed=embed)

    correct = max(nums) if mode == "grand" else min(nums)
    autres = [n for n in nums if n != correct]
    choices = random.sample(autres, 3) + [correct]
    return await _ask_choice(ctx, embed, choices, correct, get_user_id)

rapidite.title = "Rapidité"
rapidite.emoji = "⚡"
rapidite.prep_time = 2


# ================================================================================
# 🔹 🧩 Séquence de symboles
# ================================================================================
async def sequence_symboles(ctx, embed, get_user_id, bot, msg_override=None):
    symbols = ["⭐", "🍎", "🐍", "⚡", "🎲", "🍀", "🐱", "🔥"]
    seq = random.sample(symbols, 4)

    _clean_embed(embed)
    embed.add_field(name="🧩 Séquence de symboles", value="Observe :", inline=False)
    embed.add_field(name="Séquence :", value=" ".join(seq), inline=False)
    await ctx.edit(embed=embed)
    await asyncio.sleep(8)

    index = random.randint(0, 3)
    _clean_embed(embed)
    embed.add_field(name="🧩 Séquence de symboles", value=f"Le **{index+1}ᵉ** emoji ?", inline=False)
    await ctx.edit(embed=embed)

    correct = seq[index]
    autres = [s for s in symbols if s != correct]
    choices = random.sample(autres, 3) + [correct]
    return await _ask_choice(ctx, embed, choices, correct, get_user_id)

sequence_symboles.title = "Séquence de symboles"
sequence_symboles.emoji = "🧩"
sequence_symboles.prep_time = 8


# ================================================================================
# 🔹 🧩 Suite alphabétique
# ================================================================================
async def suite_alpha(ctx, embed, get_user_id, bot, msg_override=None):
    sens_normal = random.choice([True, False])
    if sens_normal:
        start = random.randint(65, 70)
        step = random.randint(1, 2)
        serie = [chr(start + i * step) for i in range(4)]
        correct = chr(start + 4 * step)
    else:
        start = random.randint(85, 90)
        step = random.randint(1, 2)
        serie = [chr(start - i * step) for i in range(4)]
        correct = chr(start - 4 * step)

    _clean_embed(embed)
    embed.add_field(name="🧩 Suite alphabétique", value=f"{', '.join(serie)} ... ?", inline=False)
    await ctx.edit(embed=embed)

    idx = ord(correct)
    distractors = set()
    for delta in [-3, -2, -1, 1, 2, 3]:
        c = chr(idx + delta)
        if c != correct and c.isalpha():
            distractors.add(c.upper())
    distractors = list(distractors)[:3]
    while len(distractors) < 3:
        c = chr(random.randint(65, 90))
        if c != correct and c not in distractors:
            distractors.append(c)

    choices = distractors + [correct]
    return await _ask_choice(ctx, embed, choices, correct, get_user_id)

suite_alpha.title = "Suite alphabétique"
suite_alpha.emoji = "🧩"
suite_alpha.prep_time = 1


# ================================================================================
# 🔹 ➗ Suite logique
# ================================================================================
async def suite_logique(ctx, embed, get_user_id, bot, msg_override=None):
    type_suite = random.choice(["arithmétique", "géométrique", "carrés", "fibonacci"])
    if type_suite == "arithmétique":
        start = random.randint(1, 10)
        step = random.randint(2, 6)
        serie = [start + i * step for i in range(5)]
    elif type_suite == "géométrique":
        start = random.randint(1, 3)
        ratio = random.choice([2, 3])
        serie = [start * (ratio ** i) for i in range(5)]
    elif type_suite == "carrés":
        start = random.randint(1, 5)
        serie = [i ** 2 for i in range(start, start + 5)]
    else:
        a, b = random.randint(1, 5), random.randint(1, 5)
        serie = [a, b]
        for _ in range(3):
            serie.append(serie[-1] + serie[-2])

    answer_index = random.randint(0, 4)
    answer = serie[answer_index]
    display = serie.copy()
    display[answer_index] = "?"

    _clean_embed(embed)
    embed.add_field(name="➗ Suite logique", value=f"{', '.join(str(v) for v in display)} ...\n\nQuelle valeur remplace **?** ?", inline=False)
    await ctx.edit(embed=embed)

    choices = [answer] + _numeric_distractors(answer, min_val=0)
    return await _ask_choice(ctx, embed, choices, answer, get_user_id)

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

    _clean_embed(embed)
    embed.add_field(
        name="🔎 Trouver la différence",
        value=f"**1️⃣** {', '.join(map(str, liste1))}\n**2️⃣** {', '.join(map(str, liste2))}\n\nQuelle **position** diffère ?",
        inline=False
    )
    await ctx.edit(embed=embed)

    correct = diff_index + 1
    autres = [i for i in range(1, 7) if i != correct]
    choices = random.sample(autres, 3) + [correct]
    return await _ask_choice(ctx, embed, choices, correct, get_user_id)

trouver_difference.title = "Trouver la différence"
trouver_difference.emoji = "🔎"
trouver_difference.prep_time = 1


# ================================================================================
# 🔹 ✏️ Typographie erreur
# ================================================================================
async def typo_trap(ctx, embed, get_user_id, bot, msg_override=None):
    mot = random.choice(["chien", "maison", "voiture", "ordinateur", "banane", "chocolat"])
    typo_index = random.randint(0, len(mot) - 1)
    mot_mod = list(mot)
    original = mot_mod[typo_index]
    nouvelle = random.choice([chr(i) for i in range(97, 123) if chr(i) != original])
    mot_mod[typo_index] = nouvelle
    mot_mod = "".join(mot_mod)

    _clean_embed(embed)
    embed.add_field(name="✏️ Typographie erreur", value=f"**{mot_mod}**\n\nQuelle lettre est incorrecte ?", inline=False)
    await ctx.edit(embed=embed)

    autres_lettres = list(set(mot) - {nouvelle})
    distractors = random.sample(autres_lettres, min(3, len(autres_lettres)))
    while len(distractors) < 3:
        c = random.choice("abcdefghijklmnopqrstuvwxyz")
        if c != nouvelle and c not in distractors:
            distractors.append(c)

    choices = distractors[:3] + [nouvelle]
    return await _ask_choice(ctx, embed, choices, nouvelle, get_user_id)

typo_trap.title = "Typographie erreur"
typo_trap.emoji = "✏️"
typo_trap.prep_time = 2


# ================================================================================
# 🔖 Marqueurs
# ================================================================================
for _f in [
    addition_cachee, calcul_rapide, carre_magique_fiable_emoji,
    compter_emojis, couleurs, datation, directions_opposees,
    equation_trou, heures, memoire_numerique, memoire_visuelle,
    monnaie, mot_miroir, pagaille, pair_ou_impair, rapidite,
    reflexe_couleur, sequence_symboles, suite_alpha, suite_logique,
    trouver_difference, typo_trap,
]:
    _f.uses_buttons = True

# the end
