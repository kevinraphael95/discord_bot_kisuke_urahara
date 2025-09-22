# ────────────────────────────────────────────────────────────────────────────────
# 📌 fixtables.py — Commande interactive /fixtables et !fixtables
# Objectif : Vérifier les tables et colonnes utilisées par le bot, comparer avec Supabase
#            et générer des suggestions SQL par table avec navigation par page.
# Catégorie : Admin
# Accès : Administrateurs uniquement
# Cooldown : 30 secondes par serveur
# ────────────────────────────────────────────────────────────────────────────────

# ────────────────────────────────────────────────────────────────────────────────
# 📦 Imports nécessaires
# ────────────────────────────────────────────────────────────────────────────────
import os
import re
import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, Button
from typing import Dict, List, Tuple, Set

from utils.supabase_client import supabase
from utils.discord_utils import safe_send, safe_edit

# ────────────────────────────────────────────────────────────────────────────────
# 🔧 Config
# ────────────────────────────────────────────────────────────────────────────────
CODE_SCAN_DIRS = ["commands", "tasks"]
WINDOW_CHARS = 2500

# ────────────────────────────────────────────────────────────────────────────────
# 🔎 Helpers — Détection tables/colonnes dans le code
# ────────────────────────────────────────────────────────────────────────────────
_table_re = re.compile(r'supabase\.table\(\s*["\']([\w\d_]+)["\']\s*\)')
_select_re = re.compile(r'\.select\(\s*["\']([^"\']+)["\']\s*\)')
_eq_re = re.compile(r'\.eq\(\s*["\']([\w\d_]+)["\']\s*,')
_update_dict_re = re.compile(r'\.(?:update|insert)\s*\(\s*\{([^}]+)\}', re.S)
_key_in_dict_re = re.compile(r'["\']([\w\d_]+)["\']\s*:')

def _infer_sql_type(c: str) -> str:
    """Détecte un type SQL probable pour une colonne donnée."""
    c = c.lower()
    if c.endswith("_id") or c in {"user_id", "guild_id", "channel_id"}:
        return "text"
    if c.endswith("_at") or c.startswith("last_"):
        return "timestamp with time zone"
    if c in {"points", "spawn_delay", "quantity"}:
        return "integer"
    if c.startswith("is_") or c.startswith("has_"):
        return "boolean"
    return "text"

def discover_expected_tables(dirs: List[str] = CODE_SCAN_DIRS) -> Dict[str, Dict]:
    """Analyse le code et retourne un mapping table -> colonnes (dans l'ordre d'apparition)."""
    results: Dict[str, Dict] = {}
    for base_dir in dirs:
        for root, _, files in os.walk(base_dir):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                path = os.path.join(root, fn)
                try:
                    code = open(path, "r", encoding="utf-8").read()
                except Exception:
                    continue

                for match in _table_re.finditer(code):
                    table = match.group(1)
                    line_no = code[:match.start()].count("\n") + 1
                    t_info = results.setdefault(table, {"columns": {}, "locations": []})
                    t_info["locations"].append((path, line_no))
                    window = code[match.end():match.end() + WINDOW_CHARS]

                    # select(...)
                    for s in _select_re.finditer(window):
                        for c in [col.strip() for col in s.group(1).split(",") if col.strip() != "*"]:
                            t_info["columns"].setdefault(c, []).append((path, line_no))

                    # eq(...)
                    for e in _eq_re.finditer(window):
                        c = e.group(1)
                        t_info["columns"].setdefault(c, []).append((path, line_no))

                    # update/insert dict
                    for block in _update_dict_re.finditer(window):
                        for k in _key_in_dict_re.findall(block.group(1)):
                            t_info["columns"].setdefault(k, []).append((path, line_no))
    return results

# ────────────────────────────────────────────────────────────────────────────────
# 🗄️ Récupération structure Supabase
# ────────────────────────────────────────────────────────────────────────────────
def fetch_actual_columns(table: str) -> Tuple[Dict[str, str], bool]:
    """Retourne (colonnes:types, existe:bool) depuis Supabase."""
    try:
        res = supabase.table(table).select("*").limit(1).execute()
        if not res or not getattr(res, "data", None):
            return {}, True  # table existe mais peut-être vide
        row = res.data[0]
        return {k: str(type(v)) for k, v in row.items()}, True
    except Exception:
        return {}, False  # table n'existe pas

# ────────────────────────────────────────────────────────────────────────────────
# 🎛️ UI — Pagination par table
# ────────────────────────────────────────────────────────────────────────────────
class TablePaginator(View):
    def __init__(self, pages: List[discord.Embed], sql_per_table: Dict[str, Tuple[str, str]]):
        super().__init__(timeout=180)
        self.pages = pages
        self.sql_per_table = sql_per_table
        self.index = 0
        self.message = None

    async def update_message(self, interaction=None):
        if interaction:
            await interaction.response.edit_message(embed=self.pages[self.index], view=self)
        elif self.message:
            await safe_edit(self.message, embed=self.pages[self.index], view=self)

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary)
    async def prev_page(self, interaction: discord.Interaction, button: Button):
        self.index = (self.index - 1) % len(self.pages)
        await self.update_message(interaction)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: Button):
        self.index = (self.index + 1) % len(self.pages)
        await self.update_message(interaction)

    @discord.ui.button(label="Créer table", style=discord.ButtonStyle.success)
    async def create_table(self, interaction: discord.Interaction, button: Button):
        table = self.pages[self.index].title.split("`")[1]
        sql = self.sql_per_table.get(table, ("", ""))[0] or "-- Rien à créer"
        await interaction.response.send_message(f"```sql\n{sql}\n```", ephemeral=True)

    @discord.ui.button(label="Modifier table", style=discord.ButtonStyle.primary)
    async def alter_table(self, interaction: discord.Interaction, button: Button):
        table = self.pages[self.index].title.split("`")[1]
        sql = self.sql_per_table.get(table, ("", ""))[1] or "-- Rien à modifier"
        await interaction.response.send_message(f"```sql\n{sql}\n```", ephemeral=True)

# ────────────────────────────────────────────────────────────────────────────────
# 🧠 Cog principal
# ────────────────────────────────────────────────────────────────────────────────
class FixTables(commands.Cog):
    """
    /fixtables et !fixtables — Vérifie les tables Supabase et génère un rapport interactif paginé
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _scan_and_report(self, channel: discord.abc.Messageable):
        expected = discover_expected_tables()
        pages = []
        sql_per_table = {}

        for table, info in expected.items():
            # Respecter l'ordre d'apparition des colonnes
            expected_cols = {c: _infer_sql_type(c) for c in info["columns"].keys()}
            actual_cols, exists = fetch_actual_columns(table)

            embed = discord.Embed(
                title=f"📄 Table `{table}`",
                color=discord.Color.blurple()
            )

            exp_str = "\n".join(f"`{c}` → `{t}`" for c, t in expected_cols.items()) or "Aucune colonne détectée"
            embed.add_field(name="📌 Colonnes attendues (code)", value=exp_str, inline=False)

            if exists:
                act_str = "\n".join(f"`{c}` → `{t}`" for c, t in actual_cols.items()) or "Table vide"
                embed.add_field(name="🗄️ Colonnes réelles (Supabase)", value=act_str, inline=False)
            else:
                embed.add_field(name="🗄️ Colonnes réelles (Supabase)", value="❌ Table inexistante", inline=False)

            missing = [c for c in expected_cols if c not in actual_cols]
            extra = [c for c in actual_cols if c not in expected_cols]

            diff_lines = []
            if missing:
                diff_lines.append(f"⚠️ Colonnes manquantes : {', '.join(missing)}")
            if extra:
                diff_lines.append(f"ℹ️ Colonnes supplémentaires : {', '.join(extra)}")

            embed.add_field(name="🔎 Différences", value="\n".join(diff_lines) or "✅ Structure conforme", inline=False)

            locations = "\n".join(f"- `{os.path.relpath(f)}`:{ln}" for f, ln in info["locations"]) or "Non trouvé"
            embed.add_field(name="📂 Fichiers utilisant cette table", value=locations, inline=False)

            # SQL généré dans le bon ordre
            create_sql = "CREATE TABLE {t} (\n  {cols}\n);".format(
                t=table,
                cols=",\n  ".join(f"{c} {t}" for c, t in expected_cols.items())
            )
            alter_sql = "\n".join(f"ALTER TABLE {table} ADD COLUMN {c} {_infer_sql_type(c)};" for c in missing)

            sql_per_table[table] = (create_sql, alter_sql)
            pages.append(embed)

        view = TablePaginator(pages, sql_per_table)
        view.message = await safe_send(channel, embed=pages[0], view=view)

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande SLASH
    # ────────────────────────────────────────────────────────────────────────────
    @app_commands.command(name="fixtables", description="Vérifie les tables Supabase et génère des suggestions SQL (par page).")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.checks.cooldown(1, 30.0, key=lambda i: i.guild_id or i.user.id)
    async def slash_fixtables(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._scan_and_report(interaction.channel)
        await interaction.delete_original_response()

    # ────────────────────────────────────────────────────────────────────────────
    # 🔹 Commande PREFIX
    # ────────────────────────────────────────────────────────────────────────────
    @commands.command(name="fixtables")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 30.0, commands.BucketType.guild)
    async def prefix_fixtables(self, ctx: commands.Context):
        await self._scan_and_report(ctx.channel)

# ────────────────────────────────────────────────────────────────────────────────
# 🔌 Setup du Cog
# ────────────────────────────────────────────────────────────────────────────────
async def setup(bot: commands.Bot):
    cog = FixTables(bot)
    for command in cog.get_commands():
        if not hasattr(command, "category"):
            command.category = "Admin"
    await bot.add_cog(cog)
