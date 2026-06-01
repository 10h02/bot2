# cogs/tickets.py
"""
====================================================
  SYSTEME DE TICKETS - Cog discord.py
  Fichier a placer dans : cogs/tickets.py

  COMMANDES :
    !ticketpanel          -> Envoie le panel de tickets
    !tcatlist             -> Liste toutes les categories
    !tcatadd              -> Ajoute une categorie
    !tcatremove           -> Supprime une categorie
    !tcatedit             -> Modifie une categorie
    !tcatconfig           -> Configure salon/roles/couleur/message
    !tcatinfo             -> Voir la config d'une categorie

  CONFIG PAR CATEGORIE avec !tcatconfig :
    !tcatconfig <cat> channel #salon
    !tcatconfig <cat> roles @role1 @role2
    !tcatconfig <cat> color #FF0000
    !tcatconfig <cat> message Bonjour {user} !
    !tcatconfig <cat> reset
====================================================
"""

import discord
from discord.ext import commands
import asyncio
import json
import os
from datetime import datetime, timezone

CONFIG = {
    "ticket_category_id": 123456789012345678,
    "log_channel_id":     123456789012345678,
    "staff_role_ids":     [123456789012345678],
    "max_per_user":       1,
    "channel_prefix":     "ticket",
    "autoban_48h":        True,
    "dm_on_open":         True,
}

CATEGORIES_FILE = "data/ticket_categories.json"

_DEFAULT_CATEGORIES = [
    {"id": "renseignement", "emoji": "\u2139\ufe0f", "label": "Renseignement", "description": "Pour toute question generale", "channel_id": None, "role_ids": [], "color": None, "message": None},
    {"id": "achat_vip",     "emoji": "\U0001f48e",   "label": "Achat VIP",      "description": "Pour acheter un grade VIP",   "channel_id": None, "role_ids": [], "color": None, "message": None},
    {"id": "achat_pack",    "emoji": "\U0001f4e6",   "label": "Achat de pack",  "description": "Pour acheter un pack du serveur", "channel_id": None, "role_ids": [], "color": None, "message": None},
]

def _load_categories() -> list:
    if os.path.exists(CATEGORIES_FILE):
        try:
            with open(CATEGORIES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for cat in data:
                    cat.setdefault("channel_id", None)
                    cat.setdefault("role_ids",   [])
                    cat.setdefault("color",      None)
                    cat.setdefault("message",    None)
                print(f"[Tickets] {len(data)} categorie(s) chargee(s) depuis {CATEGORIES_FILE}")
                return data
        except (json.JSONDecodeError, OSError) as e:
            print(f"[Tickets] Erreur lecture {CATEGORIES_FILE} : {e}")
    return [dict(c) for c in _DEFAULT_CATEGORIES]

def _save_categories() -> None:
    try:
        os.makedirs(os.path.dirname(CATEGORIES_FILE), exist_ok=True)
        with open(CATEGORIES_FILE, "w", encoding="utf-8") as f:
            json.dump(CATEGORIES, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"[Tickets] Impossible de sauvegarder : {e}")

CATEGORIES: list = _load_categories()


def _get_color(cat: dict) -> discord.Color:
    if cat.get("color"):
        try:
            return discord.Color(int(cat["color"].lstrip("#"), 16))
        except ValueError:
            pass
    return discord.Color.blurple()

def _get_role_ids(cat: dict) -> list:
    return cat["role_ids"] if cat.get("role_ids") else CONFIG["staff_role_ids"]

def _get_channel(guild: discord.Guild, cat: dict):
    if cat.get("channel_id"):
        return guild.get_channel(cat["channel_id"])
    return guild.get_channel(CONFIG["ticket_category_id"])

def _find_cat(target: str):
    if target.isdigit():
        idx = int(target)
        if 0 <= idx < len(CATEGORIES):
            return CATEGORIES[idx]
    found = next((c for c in CATEGORIES if c["label"].lower() == target.lower()), None)
    if not found:
        found = next((c for c in CATEGORIES if c["id"].lower() == target.lower().replace(" ", "_")), None)
    return found


class TicketSelectMenu(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=cat["label"], value=cat["id"], emoji=cat["emoji"], description=cat["description"])
            for cat in CATEGORIES
        ]
        super().__init__(placeholder="Fais un choix", min_values=1, max_values=1, options=options, custom_id="ticket_select")

    async def callback(self, interaction: discord.Interaction):
        cat = next((c for c in CATEGORIES if c["id"] == self.values[0]), None)
        if not cat:
            return await interaction.response.send_message("Categorie introuvable.", ephemeral=True)
        await interaction.response.defer(ephemeral=True)
        await _open_ticket(interaction, cat)


class TicketSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelectMenu())


class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Fermer", style=discord.ButtonStyle.danger, emoji="\U0001f512", custom_id="ticket_close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="Fermer ce ticket ?", description="Le salon sera supprime definitivement.", color=discord.Color.orange())
        await interaction.response.send_message(embed=embed, view=ConfirmCloseView(), ephemeral=True)

    @discord.ui.button(label="Reclamer", style=discord.ButtonStyle.secondary, emoji="\U0001f64b", custom_id="ticket_claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        staff_roles = [interaction.guild.get_role(rid) for rid in CONFIG["staff_role_ids"]]
        if not any(r in interaction.user.roles for r in staff_roles if r):
            return await interaction.response.send_message("Reserve au staff.", ephemeral=True)
        embed = discord.Embed(description=f"Ticket reclame par {interaction.user.mention}", color=discord.Color.green())
        await interaction.response.send_message(embed=embed)
        await _send_log(interaction.guild, f"{interaction.user.mention} a reclame **{interaction.channel.name}**")


class ConfirmCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=30)

    @discord.ui.button(label="Confirmer", style=discord.ButtonStyle.danger, emoji="\u2705")
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.send_message("Fermeture dans 5 secondes...")
        await _send_log(interaction.guild, f"Ticket **{interaction.channel.name}** ferme par {interaction.user.mention}")
        await asyncio.sleep(5)
        await interaction.channel.delete(reason=f"Ferme par {interaction.user}")

    @discord.ui.button(label="Annuler", style=discord.ButtonStyle.secondary, emoji="\u2716\ufe0f")
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.stop()
        await interaction.response.send_message("Annule.", ephemeral=True)


async def _open_ticket(interaction: discord.Interaction, cat: dict):
    guild  = interaction.guild
    member = interaction.user

    if CONFIG["max_per_user"] > 0:
        existing = discord.utils.get(guild.text_channels, name=f"{CONFIG['channel_prefix']}-{member.name.lower()}")
        if existing:
            return await interaction.followup.send(f"Tu as deja un ticket ouvert : {existing.mention}", ephemeral=True)

    category = _get_channel(guild, cat)
    role_ids = _get_role_ids(cat)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
    }
    for rid in role_ids:
        role = guild.get_role(rid)
        if role:
            overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, manage_messages=True)

    channel = await guild.create_text_channel(
        name=f"{CONFIG['channel_prefix']}-{member.name.lower()}",
        category=category,
        overwrites=overwrites,
        topic=f"{cat['label']} - {member} ({member.id})",
    )

    if cat.get("message"):
        welcome_text = cat["message"].replace("{user}", member.mention)
    else:
        welcome_text = (
            f"Bienvenue {member.mention} !\n\n"
            f"**Categorie :** {cat['emoji']} {cat['label']}\n"
            f"*{cat['description']}*\n\n"
            f"Explique ta demande, le staff te repondra des que possible.\n\n"
            f"Toute personne ne repondant pas apres 48h sera bannie."
        )

    embed = discord.Embed(title=f"{cat['emoji']} {cat['label']}", description=welcome_text, color=_get_color(cat), timestamp=datetime.now(timezone.utc))
    embed.set_footer(text=f"Ticket de {member}", icon_url=member.display_avatar.url)

    staff_ping = " ".join(f"<@&{rid}>" for rid in role_ids)
    await channel.send(content=f"{member.mention} {staff_ping}", embed=embed, view=TicketControlView())

    if CONFIG["dm_on_open"]:
        try:
            dm = discord.Embed(title="Ticket ouvert !", description=f"Ton ticket **{cat['label']}** a ete cree sur **{guild.name}**.\nSalon : {channel.mention}", color=discord.Color.green())
            await member.send(embed=dm)
        except discord.Forbidden:
            pass

    await _send_log(guild, f"Ticket ouvert par {member.mention} - **{cat['label']}** -> {channel.mention}")
    await interaction.followup.send(f"Ticket cree : {channel.mention}", ephemeral=True)


async def _send_log(guild: discord.Guild, message: str):
    ch = guild.get_channel(CONFIG["log_channel_id"])
    if ch:
        embed = discord.Embed(description=message, color=discord.Color.blurple(), timestamp=datetime.now(timezone.utc))
        try:
            await ch.send(embed=embed)
        except discord.Forbidden:
            pass


def _is_staff(ctx: commands.Context) -> bool:
    if ctx.author.id in ctx.bot.BOT_ADMINS:
        return True
    staff_roles = [ctx.guild.get_role(rid) for rid in CONFIG["staff_role_ids"]]
    return any(r in ctx.author.roles for r in staff_roles if r)


class Tickets(commands.Cog, name="Tickets"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(TicketSelectView())
        self.bot.add_view(TicketControlView())
        print("[Tickets] Cog charge et vues persistantes enregistrees.")

    @commands.command(name="ticketpanel", aliases=["tpanel"])
    @commands.has_permissions(manage_channels=True)
    async def ticket_panel(self, ctx: commands.Context):
        if not CATEGORIES:
            return await ctx.reply("Aucune categorie configuree. Utilise `!tcatadd` pour en creer.", delete_after=8)
        lines = "\n\n".join(f"{c['emoji']} **{c['label']}**\n>> {c['description']}" for c in CATEGORIES)
        embed = discord.Embed(title="Tickets", description=f"Choisis le ticket correspondant a ta demande :\n\n{lines}", color=discord.Color.blurple())
        embed.set_footer(text="Tu auras une reponse des que possible, merci de patienter.")
        try:
            await ctx.message.delete()
        except discord.Forbidden:
            pass
        await ctx.send(embed=embed, view=TicketSelectView())

    @ticket_panel.error
    async def ticket_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.reply("Il te faut la permission Gerer les salons.", delete_after=5)

    @commands.command(name="tcatlist", aliases=["tcats"])
    async def cat_list(self, ctx: commands.Context):
        if not _is_staff(ctx):
            return await ctx.reply("Reserve au staff.", delete_after=5)
        if not CATEGORIES:
            return await ctx.reply("Aucune categorie pour l'instant. Utilise `!tcatadd` pour en creer.")
        embed = discord.Embed(title="Categories de tickets", color=discord.Color.blurple())
        for i, c in enumerate(CATEGORIES):
            channel_info = f"<#{c['channel_id']}>" if c.get("channel_id") else "*(config globale)*"
            roles_info   = " ".join(f"<@&{r}>" for r in c["role_ids"]) if c.get("role_ids") else "*(config globale)*"
            color_info   = c["color"] if c.get("color") else "*(defaut)*"
            embed.add_field(
                name=f"`[{i}]` {c['emoji']} {c['label']}",
                value=f">> {c['description']}\nSalon : {channel_info} | Roles : {roles_info} | Couleur : `{color_info}`",
                inline=False,
            )
        embed.set_footer(text=f"{len(CATEGORIES)} categorie(s) - !tcatadd | !tcatremove | !tcatedit | !tcatconfig | !tcatinfo")
        await ctx.reply(embed=embed)

    @commands.command(name="tcatadd")
    async def cat_add(self, ctx: commands.Context, *, args: str):
        if not _is_staff(ctx):
            return await ctx.reply("Reserve au staff.", delete_after=5)
        if "|" not in args:
            return await ctx.reply("Format : `!tcatadd <emoji> <nom> | <description>`\nExemple : `!tcatadd 🎮 Gaming | Pour le gaming`", delete_after=10)
        if len(CATEGORIES) >= 25:
            return await ctx.reply("Maximum 25 categories (limite Discord).", delete_after=8)
        left, description = args.split("|", 1)
        left = left.strip(); description = description.strip()
        parts = left.split(" ", 1)
        if len(parts) < 2:
            return await ctx.reply("Format : `!tcatadd <emoji> <nom> | <description>`", delete_after=10)
        emoji, label = parts[0].strip(), parts[1].strip()
        cat_id = label.lower().replace(" ", "_")
        if any(c["id"] == cat_id or c["label"].lower() == label.lower() for c in CATEGORIES):
            return await ctx.reply(f"Une categorie **{label}** existe deja.", delete_after=8)
        CATEGORIES.append({"id": cat_id, "emoji": emoji, "label": label, "description": description, "channel_id": None, "role_ids": [], "color": None, "message": None})
        _save_categories()
        embed = discord.Embed(title="Categorie ajoutee !", description=f"{emoji} **{label}**\n>> {description}\n\nConfigurer : `!tcatconfig {label} ...`", color=discord.Color.green())
        embed.set_footer(text=f"Total : {len(CATEGORIES)} categorie(s) - Relance !ticketpanel pour mettre a jour")
        await ctx.reply(embed=embed)
        await _send_log(ctx.guild, f"Categorie **{label}** ajoutee par {ctx.author.mention}")

    @cat_add.error
    async def cat_add_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply("Usage : `!tcatadd <emoji> <nom> | <description>`", delete_after=10)

    @commands.command(name="tcatremove", aliases=["tcatdel", "tcatsup"])
    async def cat_remove(self, ctx: commands.Context, *, target: str):
        if not _is_staff(ctx):
            return await ctx.reply("Reserve au staff.", delete_after=5)
        cat = _find_cat(target)
        if not cat:
            return await ctx.reply(f"Categorie **{target}** introuvable. Utilise `!tcatlist`.", delete_after=8)
        CATEGORIES.remove(cat)
        _save_categories()
        embed = discord.Embed(title="Categorie supprimee", description=f"{cat['emoji']} **{cat['label']}** a ete retiree.", color=discord.Color.red())
        embed.set_footer(text=f"Total : {len(CATEGORIES)} categorie(s) - Relance !ticketpanel pour mettre a jour")
        await ctx.reply(embed=embed)
        await _send_log(ctx.guild, f"Categorie **{cat['label']}** supprimee par {ctx.author.mention}")

    @cat_remove.error
    async def cat_remove_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply("Indique l'index ou le nom : `!tcatremove 0` ou `!tcatremove Achat VIP`", delete_after=8)

    @commands.command(name="tcatedit", aliases=["tcatmodif"])
    async def cat_edit(self, ctx: commands.Context, *, args: str):
        if not _is_staff(ctx):
            return await ctx.reply("Reserve au staff.", delete_after=5)
        if ">>" not in args:
            return await ctx.reply("Usage : `!tcatedit <index ou nom> >> <emoji> <nouveau nom> | <description>`", delete_after=10)
        target_part, new_part = args.split(">>", 1)
        target = target_part.strip(); new_part = new_part.strip()
        if "|" not in new_part:
            return await ctx.reply("Separateur `|` manquant entre le nom et la description.", delete_after=10)
        left, description = new_part.split("|", 1)
        left = left.strip(); description = description.strip()
        parts = left.split(" ", 1)
        if len(parts) < 2:
            return await ctx.reply("L'emoji et le nouveau nom doivent etre separes par un espace.", delete_after=8)
        new_emoji, new_label = parts[0].strip(), parts[1].strip()
        cat = _find_cat(target)
        if not cat:
            return await ctx.reply(f"Categorie **{target}** introuvable. Utilise `!tcatlist`.", delete_after=8)
        old_label = cat["label"]
        cat["emoji"] = new_emoji; cat["label"] = new_label; cat["id"] = new_label.lower().replace(" ", "_"); cat["description"] = description
        _save_categories()
        embed = discord.Embed(title="Categorie modifiee !", color=discord.Color.orange())
        embed.add_field(name="Avant", value=f"**{old_label}**", inline=True)
        embed.add_field(name="Apres", value=f"{new_emoji} **{new_label}**\n>> {description}", inline=True)
        embed.set_footer(text="Relance !ticketpanel pour mettre a jour le panel")
        await ctx.reply(embed=embed)
        await _send_log(ctx.guild, f"Categorie **{old_label}** -> **{new_label}** modifiee par {ctx.author.mention}")

    @cat_edit.error
    async def cat_edit_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply("Usage : `!tcatedit <index ou nom> >> <emoji> <nouveau nom> | <description>`", delete_after=10)

    @commands.command(name="tcatconfig", aliases=["tcatset"])
    async def cat_config(self, ctx: commands.Context, target: str, option: str, *, value: str = ""):
        if not _is_staff(ctx):
            return await ctx.reply("Reserve au staff.", delete_after=5)
        cat = _find_cat(target)
        if not cat:
            return await ctx.reply(f"Categorie **{target}** introuvable. Utilise `!tcatlist`.", delete_after=8)
        option = option.lower()

        if option == "channel":
            if not ctx.message.channel_mentions:
                return await ctx.reply("Mentionne un salon. Exemple : `!tcatconfig Gaming channel #tickets-gaming`", delete_after=8)
            ch = ctx.message.channel_mentions[0]
            cat["channel_id"] = ch.id
            _save_categories()
            await ctx.reply(embed=discord.Embed(description=f"Les tickets **{cat['label']}** arriveront dans {ch.mention}", color=discord.Color.green()))

        elif option in ("roles", "role"):
            if not ctx.message.role_mentions:
                return await ctx.reply("Mentionne au moins un role. Exemple : `!tcatconfig Gaming roles @Support @Admin`", delete_after=8)
            cat["role_ids"] = [r.id for r in ctx.message.role_mentions]
            _save_categories()
            roles_txt = " ".join(r.mention for r in ctx.message.role_mentions)
            await ctx.reply(embed=discord.Embed(description=f"Roles pour **{cat['label']}** : {roles_txt}", color=discord.Color.green()))

        elif option in ("color", "couleur"):
            hex_val = value.strip().lstrip("#")
            if len(hex_val) != 6:
                return await ctx.reply("Couleur invalide. Format hex attendu. Exemple : `!tcatconfig Gaming color #FF0000`", delete_after=8)
            try:
                int(hex_val, 16)
            except ValueError:
                return await ctx.reply("Couleur invalide.", delete_after=8)
            cat["color"] = f"#{hex_val.upper()}"
            _save_categories()
            await ctx.reply(embed=discord.Embed(description=f"Couleur pour **{cat['label']}** : `#{hex_val.upper()}`", color=discord.Color(int(hex_val, 16))))

        elif option in ("message", "msg", "accueil"):
            if not value:
                return await ctx.reply("Indique un message. Exemple : `!tcatconfig Gaming message Bienvenue {user} !`\n`{user}` sera remplace par la mention.", delete_after=10)
            cat["message"] = value
            _save_categories()
            preview = value.replace("{user}", ctx.author.mention)
            embed = discord.Embed(title="Message d'accueil mis a jour", description=f"**Apercu :**\n{preview}", color=discord.Color.green())
            embed.set_footer(text="{user} sera remplace par la mention du membre qui ouvre le ticket")
            await ctx.reply(embed=embed)

        elif option == "reset":
            cat["channel_id"] = None; cat["role_ids"] = []; cat["color"] = None; cat["message"] = None
            _save_categories()
            await ctx.reply(embed=discord.Embed(description=f"Config de **{cat['label']}** remise a zero (config globale utilisee).", color=discord.Color.orange()))

        else:
            await ctx.reply(
                "Option inconnue. Options disponibles : `channel` | `roles` | `color` | `message` | `reset`\n\n"
                "Exemples :\n"
                "`!tcatconfig Gaming channel #tickets-gaming`\n"
                "`!tcatconfig Gaming roles @Support @Admin`\n"
                "`!tcatconfig Gaming color #FF0000`\n"
                "`!tcatconfig Gaming message Bienvenue {user} !`\n"
                "`!tcatconfig Gaming reset`",
                delete_after=15,
            )

    @cat_config.error
    async def cat_config_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply(
                "Usage : `!tcatconfig <categorie> <option> <valeur>`\n"
                "Options : `channel` | `roles` | `color` | `message` | `reset`\n\n"
                "Exemples :\n"
                "`!tcatconfig Gaming channel #tickets-gaming`\n"
                "`!tcatconfig Gaming roles @Support @Admin`\n"
                "`!tcatconfig Gaming color #FF0000`\n"
                "`!tcatconfig Gaming message Bienvenue {user} !`",
                delete_after=15,
            )

    @commands.command(name="tcatinfo")
    async def cat_info(self, ctx: commands.Context, *, target: str):
        if not _is_staff(ctx):
            return await ctx.reply("Reserve au staff.", delete_after=5)
        cat = _find_cat(target)
        if not cat:
            return await ctx.reply(f"Categorie **{target}** introuvable. Utilise `!tcatlist`.", delete_after=8)
        channel_info = f"<#{cat['channel_id']}>" if cat.get("channel_id") else "*(config globale)*"
        roles_info   = " ".join(f"<@&{r}>" for r in cat["role_ids"]) if cat.get("role_ids") else "*(config globale)*"
        color_info   = cat["color"] if cat.get("color") else "*(blurple par defaut)*"
        message_info = cat["message"] if cat.get("message") else "*(message par defaut)*"
        embed = discord.Embed(title=f"{cat['emoji']} Config - {cat['label']}", color=_get_color(cat))
        embed.add_field(name="Salon d'arrivee",  value=channel_info, inline=False)
        embed.add_field(name="Roles avec acces",  value=roles_info,   inline=False)
        embed.add_field(name="Couleur embed",     value=f"`{color_info}`", inline=True)
        embed.add_field(name="ID interne",        value=f"`{cat['id']}`",  inline=True)
        embed.add_field(name="Message d'accueil", value=message_info, inline=False)
        embed.set_footer(text="Modifier avec !tcatconfig - {user} = mention du membre")
        await ctx.reply(embed=embed)

    @cat_info.error
    async def cat_info_error(self, ctx: commands.Context, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.reply("Indique la categorie : `!tcatinfo Gaming` ou `!tcatinfo 0`", delete_after=8)


async def setup(bot: commands.Bot):
    await bot.add_cog(Tickets(bot))
