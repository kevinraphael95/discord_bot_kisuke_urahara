# ────────────────────────────────────────────────────────────────────────────────
# 📌 kawashima_games.py — Mini-jeux Professeur Kawashima
# Objectif : Contient tous les mini-jeux cérébraux
# ────────────────────────────────────────────────────────────────────────────────
import random
import asyncio

# ────────────────────────────────────────────────────────────────────────────────
# 🔹 Mini-jeux
# ────────────────────────────────────────────────────────────────────────────────
async def calcul_rapide(ctx, embed, get_user_id, bot):
    a = random.randint(20, 80)
    b = random.randint(20, 80)
    op = random.choice(["+", "-", "*"])
    question = f"{a} {op} {b} = ?"
    answer = eval(f"{a}{op}{b}")
    embed.add_field(name="🧮 Calcul rapide", value=question, inline=False)
    msg_embed = await ctx.send(embed=embed)
    try:
        msg = await bot.wait_for(
            "message",
            check=lambda m: m.author.id == get_user_id(),
            timeout=12
        )
        if int(msg.content) == answer:
            return 1
        else:
            return 0
    except:
        return 0

async def memoire_numerique(ctx, embed, get_user_id, bot):
    sequence = [random.randint(0, 9) for _ in range(6)]
    embed.add_field(name="🔢 Mémoire numérique", value=str(sequence), inline=False)
    msg_embed = await ctx.send(embed=embed)
    await asyncio.sleep(5)
    await msg_embed.delete()
    embed.set_field_at(0, name="🔢 Mémoire numérique", value="🕵️‍♂️ Séquence disparue, retapez-la !", inline=False)
    msg_embed = await ctx.send(embed=embed)
    try:
        msg = await bot.wait_for(
            "message",
            check=lambda m: m.author.id == get_user_id(),
            timeout=15
        )
        if msg.content == "".join(map(str, sequence)):
            return 1
        else:
            return 0
    except:
        return 0

async def trouver_intrus(ctx, embed, get_user_id, bot):
    mots = ["pomme", "banane", "orange", "voiture", "stylo", "livre"]
    intrus = random.choice(mots)
    shuffle = random.sample(mots, len(mots))
    embed.add_field(name="🔍 Trouver l’intrus", value=str(shuffle), inline=False)
    await ctx.send(embed=embed)
    try:
        msg = await bot.wait_for(
            "message",
            check=lambda m: m.author.id == get_user_id(),
            timeout=12
        )
        if msg.content.lower() == intrus:
            return 1
        else:
            return 0
    except:
        return 0

async def trouver_difference(ctx, embed, get_user_id, bot):
    liste1 = [random.randint(1, 9) for _ in range(5)]
    liste2 = liste1.copy()
    index = random.randint(0, 4)
    liste2[index] = random.randint(10, 20)
    embed.add_field(name="🔎 Trouver la différence", value=str(liste2), inline=False)
    await ctx.send(embed=embed)
    try:
        msg = await bot.wait_for(
            "message",
            check=lambda m: m.author.id == get_user_id(),
            timeout=12
        )
        if int(msg.content) == index + 1:
            return 1
        else:
            return 0
    except:
        return 0

async def suite_logique(ctx, embed, get_user_id, bot):
    start = random.randint(1, 5)
    step = random.randint(2, 7)
    serie = [start + i * step for i in range(4)]
    answer = serie[-1] + step
    embed.add_field(name="➗ Suite logique", value=str(serie) + " ... ?", inline=False)
    await ctx.send(embed=embed)
    try:
        msg = await bot.wait_for(
            "message",
            check=lambda m: m.author.id == get_user_id(),
            timeout=12
        )
        if int(msg.content) == answer:
            return 1
        else:
            return 0
    except:
        return 0

async def typo_trap(ctx, embed, get_user_id, bot):
    mot = random.choice(["chien", "maison", "voiture", "ordinateur"])
    typo_index = random.randint(0, len(mot)-1)
    mot_mod = list(mot)
    mot_mod[typo_index] = chr(random.randint(97, 122))
    mot_mod = "".join(mot_mod)
    embed.add_field(name="✏️ Typo trap", value=mot_mod, inline=False)
    await ctx.send(embed=embed)
    try:
        msg = await bot.wait_for(
            "message",
            check=lambda m: m.author.id == get_user_id(),
            timeout=12
        )
        if int(msg.content) == typo_index + 1:
            return 1
        else:
            return 0
    except:
        return 0
