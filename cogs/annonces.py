# cogs/annonces.py
"""
====================================================
  SYSTEME D'ANNONCES — Cog discord.py
  Fichier a placer dans : cogs/annonces.py

  COMMANDES :
    !annoncepanel   -> Ouvre le panel de gestion des templates
    !apost          -> Poste un template dans un salon
                       Usage : !apost <nom_template> #salon

  FONCTIONNEMENT :
    1. !annoncepanel  → boutons pour créer / voir / supprimer des templates
    2. Clic "Créer"   → formulaire Discord (modal) avec :
         - Titre
         - Emoji de titre
         - Corps du texte (multiligne, markdown Discord supporté)
         - Couleur hex de l'embed
         - Footer (optionnel)
    3. !apost mon_template #general  → poste l'embed dans #general
====================================================
"""

import discord
from discord.ext import commands
import json
import os
from datetime import datetime, timezone

# ─────────────────────────────────────────────
#  ⚙️  CONFIG
# ─────────────────────────────────────────────
CONFIG = {
    "staff_role_ids": [123456789012345678],  # IDs rôles autorisés à gérer les annonces
}

TEMPLATES_FILE = "data/annonce_templates.json"


# ─────────────────────────────────────────────
#  💾  PERSISTANCE
# ─────────────────────────────────────────────
def _load_templates() -> dict:
    if os.path.exists(TEMPLATES_FILE):
        try:
            with open(TEMPLATES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f"[Annonces] {len(data)} template(s) chargé(s)")
                return data
        except (json.JSONDecodeError, OSError) as e:
            print(f"[Annonces] Erreur lecture templates : {e}")
    return {}

def _save_templates() -> None:
    try:
        os.makedirs(os.path.dirname(TEMPLATES_FILE), exist_ok=True)
        with open(TEMPLATES_FILE, "w", encoding="utf-8") as f:
            json.dump(TEMPLATES, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"[Annonces] Impossible de sauvegarder : {e}")

TEMPLATES: dict = _load_templates()


# ─────────────────────────────────────────────
#  🎨  HELPERS
# ─────────────────────────────────────────────
def _is_staff(ctx: commands.Context) -> bool:
    if hasattr(ctx.bot, "BOT_ADMINS") and ctx.author.id in ctx.bot.BOT_ADMINS:
        return True
    staff_roles = [ctx.guild.get_role(rid) for rid in CONFIG["staff_role_ids"]]
    return any(r in ctx.author.roles for r in staff_roles if r)

def _is_staff_interaction(interaction: discord.Interaction) -> bool:
    if hasattr(interaction.client, "BOT_ADMINS") and interaction.user.id in interaction.client.BOT_ADMINS:
        return True
    staff_roles = [interaction.guild.get_role(rid) for rid in CONFIG["staff_role_ids"]]
    return any(r in interaction.user.roles for r in staff_roles if r)

def _build_embed(tpl: dict) -> discord.Embed:
    """Construit l'embed Discord depuis un template."""
    color = discord.Color.blurple()
    if tpl.get("color"):
        try:
            color = discord.Color(int(tpl["color"].lstrip("#"), 16))
        except ValueError:
            pass

    title = f"{tpl['emoji']} {tpl['title']}" if tpl.get("emoji") else tpl["title"]

    embed = discord.Embed(
        title=title,
        description=tpl.get("body", ""),
        color=color,
        timestamp=datetime.now(timezone.utc),
    )
    if tpl.get("footer"):
        embed.set_footer(text=tpl["footer"])
    return embed

def _slug(name: str) -> str:
    return name.lower().strip().replace(" ", "_")


# ══════════════════════════════════════════════
#  MODALS
# ══════════════════════════════════════════════

class AnnonceCreateModal(discord.ui.Modal, title="Créer un template d'annonce"):
    nom = discord.ui.TextInput(
        label="Nom du template (identifiant)",
        placeholder="ex: ventes_photos, promo_vip, reglement...",
        max_length=40,
        required=True,
    )
    titre = discord.ui.TextInput(
        label="Titre de l'annonce",
        placeholder="ex: PHOTOS · NUDES",
        max_length=100,
        required=True,
    )
    emoji = discord.ui.TextInput(
        label="Emoji titre (optionnel)",
        placeholder="ex: 🎀  ou  ✨  (laisse vide si aucun)",
        max_length=10,
        required=False,
    )
    body = discord.ui.TextInput(
        label="Contenu (markdown Discord supporté)",
        placeholder="ex:\n🔴 Lingerie Sexy → **3 €**\n🔴 Photos Seins → **7 €**\n\n✂️ Paiement **avant** la prestation",
        style=discord.TextStyle.paragraph,
        max_length=3000,
        required=True,
    )
    options = discord.ui.TextInput(
        label="Couleur hex | Footer (séparés par |)",
        placeholder="ex: #E74C3C | Paiement avant toute prestation",
        max_length=200,
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        slug = _slug(self.nom.value)

        if slug in TEMPLATES:
            return await interaction.response.send_message(
                f"❌ Un template **{slug}** existe déjà. Supprime-le d'abord avec le panel.",
                ephemeral=True,
            )

        # Parse couleur et footer depuis le champ combiné
        color  = None
        footer = None
        if self.options.value.strip():
            parts = self.options.value.split("|", 1)
            raw_color = parts[0].strip()
            if raw_color:
                hex_val = raw_color.lstrip("#")
                if len(hex_val) == 6:
                    try:
                        int(hex_val, 16)
                        color = f"#{hex_val.upper()}"
                    except ValueError:
                        pass
            if len(parts) > 1 and parts[1].strip():
                footer = parts[1].strip()

        TEMPLATES[slug] = {
            "name":   slug,
            "title":  self.titre.value.strip(),
            "emoji":  self.emoji.value.strip(),
            "body":   self.body.value,
            "color":  color,
            "footer": footer,
        }
        _save_templates()

        preview = _build_embed(TEMPLATES[slug])
        await interaction.response.send_message(
            content=f"✅ Template **{slug}** créé ! Aperçu :",
            embed=preview,
            ephemeral=True,
        )


class AnnonceEditModal(discord.ui.Modal, title="Modifier un template"):
    def __init__(self, slug: str):
        super().__init__()
        self.slug = slug
        tpl = TEMPLATES[slug]

        self.titre = discord.ui.TextInput(label="Titre", default=tpl["title"], max_length=100)
        self.emoji = discord.ui.TextInput(label="Emoji titre", default=tpl.get("emoji", ""), max_length=10, required=False)
        self.body  = discord.ui.TextInput(label="Contenu", default=tpl.get("body", ""), style=discord.TextStyle.paragraph, max_length=3000)
        self.opts  = discord.ui.TextInput(
            label="Couleur hex | Footer",
            default=f"{tpl.get('color') or ''} | {tpl.get('footer') or ''}".strip(" |"),
            max_length=200, required=False,
        )
        self.add_item(self.titre)
        self.add_item(self.emoji)
        self.add_item(self.body)
        self.add_item(self.opts)

    async def on_submit(self, interaction: discord.Interaction):
        color  = TEMPLATES[self.slug].get("color")
        footer = TEMPLATES[self.slug].get("footer")
        if self.opts.value.strip():
            parts = self.opts.value.split("|", 1)
            raw_color = parts[0].strip()
            if raw_color:
                hex_val = raw_color.lstrip("#")
                if len(hex_val) == 6:
                    try:
                        int(hex_val, 16)
                        color = f"#{hex_val.upper()}"
                    except ValueError:
                        pass
                else:
                    color = None
            else:
                color = None
            footer = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None

        TEMPLATES[self.slug].update({
            "title":  self.titre.value.strip(),
            "emoji":  self.emoji.value.strip(),
            "body":   self.body.value,
            "color":  color,
            "footer": footer,
        })
        _save_templates()

        preview = _build_embed(TEMPLATES[self.slug])
        await interaction.response.send_message(
            content=f"✅ Template **{self.slug}** modifié ! Aperçu :",
            embed=preview,
            ephemeral=True,
        )


# ══════════════════════════════════════════════
#  SELECT — choisir un template
# ══════════════════════════════════════════════

class TemplateSelect(discord.ui.Select):
    def __init__(self, action: str):
        self.action = action
        options = [
            discord.SelectOption(label=slug, description=tpl["title"][:80])
            for slug, tpl in TEMPLATES.items()
        ] or [discord.SelectOption(label="(aucun template)", value="__none__")]
        super().__init__(placeholder="Choisis un template...", options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        slug = self.values[0]
        if slug == "__none__":
            return await interaction.response.send_message("Aucun template disponible.", ephemeral=True)

        if self.action == "preview":
            if slug not in TEMPLATES:
                return await interaction.response.send_message("Template introuvable.", ephemeral=True)
            embed = _build_embed(TEMPLATES[slug])
            await interaction.response.send_message(content=f"Aperçu de **{slug}** :", embed=embed, ephemeral=True)

        elif self.action == "edit":
            if not _is_staff_interaction(interaction):
                return await interaction.response.send_message("Réservé au staff.", ephemeral=True)
            if slug not in TEMPLATES:
                return await interaction.response.send_message("Template introuvable.", ephemeral=True)
            await interaction.response.send_modal(AnnonceEditModal(slug))

        elif self.action == "delete":
            if not _is_staff_interaction(interaction):
                return await interaction.response.send_message("Réservé au staff.", ephemeral=True)
            if slug not in TEMPLATES:
                return await interaction.response.send_message("Template introuvable.", ephemeral=True)
            del TEMPLATES[slug]
            _save_templates()
            await interaction.response.send_message(f"🗑️ Template **{slug}** supprimé.", ephemeral=True)


class TemplateSelectView(discord.ui.View):
    def __init__(self, action: str):
        super().__init__(timeout=60)
        self.add_item(TemplateSelect(action))


# ══════════════════════════════════════════════
#  PANEL PRINCIPAL
# ══════════════════════════════════════════════

class AnnoncePanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="Créer", style=discord.ButtonStyle.success, emoji="➕", row=0)
    async def btn_create(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not _is_staff_interaction(interaction):
            return await interaction.response.send_message("Réservé au staff.", ephemeral=True)
        await interaction.response.send_modal(AnnonceCreateModal())

    @discord.ui.button(label="Modifier", style=discord.ButtonStyle.primary, emoji="✏️", row=0)
    async def btn_edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not _is_staff_interaction(interaction):
            return await interaction.response.send_message("Réservé au staff.", ephemeral=True)
        if not TEMPLATES:
            return await interaction.response.send_message("Aucun template existant.", ephemeral=True)
        await interaction.response.send_message("Quel template modifier ?", view=TemplateSelectView("edit"), ephemeral=True)

    @discord.ui.button(label="Aperçu", style=discord.ButtonStyle.secondary, emoji="👁️", row=0)
    async def btn_preview(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not TEMPLATES:
            return await interaction.response.send_message("Aucun template existant.", ephemeral=True)
        await interaction.response.send_message("Quel template voir ?", view=TemplateSelectView("preview"), ephemeral=True)

    @discord.ui.button(label="Supprimer", style=discord.ButtonStyle.danger, emoji="🗑️", row=1)
    async def btn_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not _is_staff_interaction(interaction):
            return await interaction.response.send_message("Réservé au staff.", ephemeral=True)
        if not TEMPLATES:
            return await interaction.response.send_message("Aucun template existant.", ephemeral=True)
        await interaction.response.send_message("Quel template supprimer ?", view=TemplateSelectView("delete"), ephemeral=True)

    @discord.ui.button(label="Liste", style=discord.ButtonStyle.secondary, emoji="📋", row=1)
    async def btn_list(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not TEMPLATES:
            return await interaction.response.send_message("Aucun template pour l'instant. Crée-en un avec **Créer** !", ephemeral=True)
        embed = discord.Embed(title="📋 Templates d'annonces", color=discord.Color.blurple())
        for slug, tpl in TEMPLATES.items():
            color_info = tpl["color"] if tpl.get("color") else "défaut"
            embed.add_field(
                name=f"`{slug}`",
                value=f"**{tpl.get('emoji','')} {tpl['title']}**\nCouleur : `{color_info}`\nPoster : `!apost {slug} #salon`",
                inline=False,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ══════════════════════════════════════════════
#  COG
# ══════════════════════════════════════════════

class Annonces(commands.Cog, name="Annonces"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ──────────────────────────────────────────
    #  !annoncepanel
    # ──────────────────────────────────────────
    @commands.command(name="annoncepanel", aliases=["apanel"])
    async def annonce_panel(self, ctx: commands.Context):
        """Ouvre le panel de gestion des templates d'annonces."""
        if not _is_staff(ctx):
            return await ctx.reply("❌ Réservé au staff.", delete_after=5)
        embed = discord.Embed(
            title="📢 Gestion des annonces",
            description=(
                "**➕ Créer** — Nouveau template via formulaire\n"
                "**✏️ Modifier** — Editer un template existant\n"
                "**👁️ Aperçu** — Voir le rendu d'un template\n"
                "**🗑️ Supprimer** — Supprimer un template\n"
                "**📋 Liste** — Voir tous les templates\n\n"
                "Pour poster : `!apost <nom_template> #salon`"
            ),
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=f"{len(TEMPLATES)} template(s) enregistré(s)")
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        await ctx.send(embed=embed, view=AnnoncePanelView())

    # ──────────────────────────────────────────
    #  !apost <template> #salon
    # ──────────────────────────────────────────
    @commands.command(name="apost")
    async def annonce_post(self, ctx: commands.Context, nom: str, channel: discord.TextChannel = None):
        """
        Poste un template dans un salon.
        Usage : !apost <nom_template> #salon
        """
        if not _is_staff(ctx):
            return await ctx.reply("❌ Réservé au staff.", delete_after=5)

        slug = _slug(nom)
        if slug not in TEMPLATES:
            noms = ", ".join(f"`{k}`" for k in TEMPLATES) or "*(aucun)*"
            return await ctx.reply(
                f"❌ Template **{slug}** introuvable.\nTemplates disponibles : {noms}",
                delete_after=10,
            )

        dest = channel or ctx.channel
        embed = _build_embed(TEMPLATES[slug])
        await dest.send(embed=embed)
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass

    @annonce_post.error
    async def annonce_post_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(
                "❌ Usage : `!apost <nom_template> #salon`\nExemple : `!apost ventes_photos #annonces`",
                delete_after=10,
            )
        elif isinstance(error, commands.ChannelNotFound):
            await ctx.reply("❌ Salon introuvable. Mentionne bien le salon avec #.", delete_after=8)


async def setup(bot: commands.Bot):
    await bot.add_cog(Annonces(bot))
