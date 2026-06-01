# cogs/extras.py
"""
====================================================
  EXTRAS — Bienvenue/Bye + MassRole + React=Role
  Fichier a placer dans : cogs/extras.py

  COMMANDES :
  ─────────────────────────────────────────────────
  BIENVENUE / BYE
    !welcomepanel         -> Panel config bienvenue/bye
    !testwelcome          -> Simuler un message de bienvenue
    !testbye              -> Simuler un message de bye

  MASSROLE
    !massifrole @role     -> Donne le role a tout le serveur

  REACT = ROLE
    !reactpanel           -> Panel pour creer/gerer les react-roles
    !reactpost            -> Poste le message react-role dans le salon configure
  ─────────────────────────────────────────────────
"""

import discord
from discord.ext import commands
import json
import os
from datetime import datetime, timezone

# ─────────────────────────────────────────────
#  PERSISTANCE
# ─────────────────────────────────────────────
_EXTRAS_FILE = "data/extras_config.json"

def _load() -> dict:
    if os.path.exists(_EXTRAS_FILE):
        try:
            with open(_EXTRAS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}

def _save(data: dict) -> None:
    try:
        os.makedirs(os.path.dirname(_EXTRAS_FILE), exist_ok=True)
        with open(_EXTRAS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"[Extras] Impossible de sauvegarder : {e}")

CFG: dict = _load()

def _cfg_save():
    _save(CFG)

# ─────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────
def _is_admin(ctx):
    if hasattr(ctx.bot, "BOT_ADMINS") and ctx.author.id in ctx.bot.BOT_ADMINS:
        return True
    return ctx.author.guild_permissions.administrator

def _is_admin_i(interaction):
    if hasattr(interaction.client, "BOT_ADMINS") and interaction.user.id in interaction.client.BOT_ADMINS:
        return True
    return interaction.user.guild_permissions.administrator

def _build_welcome_embed(member: discord.Member, kind: str) -> discord.Embed:
    section = CFG.get(kind, {})
    color = discord.Color.blurple()
    if section.get("color"):
        try:
            color = discord.Color(int(section["color"].lstrip("#"), 16))
        except ValueError:
            pass
    msg = section.get("message", "")
    msg = msg.replace("{user}", member.mention).replace("{name}", member.display_name).replace("{server}", member.guild.name).replace("{count}", str(member.guild.member_count))
    embed = discord.Embed(description=msg, color=color, timestamp=datetime.now(timezone.utc))
    if kind == "welcome":
        embed.set_author(name=f"Bienvenue sur {member.guild.name} !", icon_url=member.guild.icon.url if member.guild.icon else None)
    else:
        embed.set_author(name=f"Au revoir !", icon_url=member.guild.icon.url if member.guild.icon else None)
    embed.set_thumbnail(url=member.display_avatar.url)
    if section.get("image"):
        embed.set_image(url=section["image"])
    embed.set_footer(text=f"Membre #{member.guild.member_count}")
    return embed


# ══════════════════════════════════════════════
#  BIENVENUE / BYE — MODALS
# ══════════════════════════════════════════════

class WelcomeModal(discord.ui.Modal):
    def __init__(self, kind: str):
        label = "Bienvenue" if kind == "welcome" else "Au revoir"
        super().__init__(title=f"Configurer le message {label}")
        self.kind = kind
        section = CFG.get(kind, {})

        self.msg = discord.ui.TextInput(
            label="Message ({user} {name} {server} {count})",
            placeholder="ex: Bienvenue {user} sur {server} ! Tu es le membre #{count} !",
            default=section.get("message", ""),
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True,
        )
        self.color = discord.ui.TextInput(
            label="Couleur hex (ex: #2ECC71)",
            default=section.get("color", ""),
            max_length=7,
            required=False,
        )
        self.image = discord.ui.TextInput(
            label="URL image/banniere (optionnel)",
            default=section.get("image", ""),
            placeholder="https://exemple.com/image.png",
            max_length=300,
            required=False,
        )
        self.add_item(self.msg)
        self.add_item(self.color)
        self.add_item(self.image)

    async def on_submit(self, interaction: discord.Interaction):
        section = CFG.setdefault(self.kind, {})
        section["message"] = self.msg.value
        if self.color.value.strip():
            hex_val = self.color.value.strip().lstrip("#")
            if len(hex_val) == 6:
                try:
                    int(hex_val, 16)
                    section["color"] = f"#{hex_val.upper()}"
                except ValueError:
                    pass
        if self.image.value.strip():
            section["image"] = self.image.value.strip()
        else:
            section.pop("image", None)
        _cfg_save()

        fake = interaction.user
        embed = _build_welcome_embed(fake, self.kind)
        await interaction.response.send_message(
            content=f"Apercu du message {'bienvenue' if self.kind == 'welcome' else 'bye'} :",
            embed=embed,
            ephemeral=True,
        )


class WelcomeChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, kind: str):
        self.kind = kind
        super().__init__(placeholder="Choisis le salon...", channel_types=[discord.ChannelType.text])

    async def callback(self, interaction: discord.Interaction):
        ch = self.values[0]
        CFG.setdefault(self.kind, {})["channel_id"] = ch.id
        _cfg_save()
        label = "bienvenue" if self.kind == "welcome" else "bye"
        await interaction.response.send_message(f"Salon {label} defini sur {ch.mention}", ephemeral=True)


class WelcomeChannelView(discord.ui.View):
    def __init__(self, kind: str):
        super().__init__(timeout=60)
        self.add_item(WelcomeChannelSelect(kind))


# ── Panel principal bienvenue/bye ──────────────
class WelcomePanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    def _status(self, kind: str) -> str:
        section = CFG.get(kind, {})
        ch_id = section.get("channel_id")
        ch = f"<#{ch_id}>" if ch_id else "*(non defini)*"
        color = section.get("color") or "defaut"
        has_img = "Oui" if section.get("image") else "Non"
        has_msg = "Oui" if section.get("message") else "Non"
        return f"Salon : {ch}\nCouleur : `{color}` | Image : {has_img} | Message : {has_msg}"

    @discord.ui.button(label="Config Bienvenue", style=discord.ButtonStyle.success, emoji="👋", row=0)
    async def btn_welcome_msg(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not _is_admin_i(interaction):
            return await interaction.response.send_message("Reserve aux admins.", ephemeral=True)
        await interaction.response.send_modal(WelcomeModal("welcome"))

    @discord.ui.button(label="Salon Bienvenue", style=discord.ButtonStyle.primary, emoji="📁", row=0)
    async def btn_welcome_ch(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not _is_admin_i(interaction):
            return await interaction.response.send_message("Reserve aux admins.", ephemeral=True)
        await interaction.response.send_message("Choisis le salon bienvenue :", view=WelcomeChannelView("welcome"), ephemeral=True)

    @discord.ui.button(label="Config Bye", style=discord.ButtonStyle.danger, emoji="🚪", row=1)
    async def btn_bye_msg(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not _is_admin_i(interaction):
            return await interaction.response.send_message("Reserve aux admins.", ephemeral=True)
        await interaction.response.send_modal(WelcomeModal("bye"))

    @discord.ui.button(label="Salon Bye", style=discord.ButtonStyle.primary, emoji="📁", row=1)
    async def btn_bye_ch(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not _is_admin_i(interaction):
            return await interaction.response.send_message("Reserve aux admins.", ephemeral=True)
        await interaction.response.send_message("Choisis le salon bye :", view=WelcomeChannelView("bye"), ephemeral=True)

    @discord.ui.button(label="Statut", style=discord.ButtonStyle.secondary, emoji="📋", row=2)
    async def btn_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(title="Config Bienvenue/Bye", color=discord.Color.blurple())
        embed.add_field(name="👋 Bienvenue", value=self._status("welcome"), inline=False)
        embed.add_field(name="🚪 Bye",       value=self._status("bye"),     inline=False)
        embed.set_footer(text="Variables : {user} {name} {server} {count}")
        await interaction.response.send_message(embed=embed, ephemeral=True)


# ══════════════════════════════════════════════
#  REACT = ROLE — MODALS + VIEWS
# ══════════════════════════════════════════════

class ReactRoleCreateModal(discord.ui.Modal, title="Ajouter un React-Role"):
    emoji_input = discord.ui.TextInput(
        label="Emoji",
        placeholder="ex: 🎮",
        max_length=50,
        required=True,
    )
    role_input = discord.ui.TextInput(
        label="ID du role",
        placeholder="ex: 123456789012345678",
        max_length=20,
        required=True,
    )
    label_input = discord.ui.TextInput(
        label="Label (nom affiche sur le bouton)",
        placeholder="ex: Gaming",
        max_length=50,
        required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        role_id_str = self.role_input.value.strip()
        if not role_id_str.isdigit():
            return await interaction.response.send_message("ID de role invalide.", ephemeral=True)
        role = interaction.guild.get_role(int(role_id_str))
        if not role:
            return await interaction.response.send_message(f"Role `{role_id_str}` introuvable sur ce serveur.", ephemeral=True)

        entries = CFG.setdefault("react_roles", [])
        if any(e["role_id"] == int(role_id_str) for e in entries):
            return await interaction.response.send_message(f"Le role **{role.name}** est deja dans la liste.", ephemeral=True)
        if len(entries) >= 25:
            return await interaction.response.send_message("Maximum 25 react-roles.", ephemeral=True)

        entries.append({
            "emoji":   self.emoji_input.value.strip(),
            "role_id": int(role_id_str),
            "label":   self.label_input.value.strip(),
        })
        _cfg_save()
        await interaction.response.send_message(
            f"React-role ajoute : {self.emoji_input.value.strip()} **{self.label_input.value.strip()}** → {role.mention}",
            ephemeral=True,
        )


class ReactRoleSelect(discord.ui.Select):
    def __init__(self):
        entries = CFG.get("react_roles", [])
        options = [
            discord.SelectOption(label=e["label"], value=str(e["role_id"]), emoji=e["emoji"])
            for e in entries
        ] or [discord.SelectOption(label="(aucun)", value="__none__")]
        super().__init__(placeholder="Choisis un react-role a supprimer...", options=options[:25])

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "__none__":
            return await interaction.response.send_message("Aucun react-role.", ephemeral=True)
        role_id = int(self.values[0])
        entries = CFG.get("react_roles", [])
        entry = next((e for e in entries if e["role_id"] == role_id), None)
        if entry:
            entries.remove(entry)
            _cfg_save()
            await interaction.response.send_message(f"React-role **{entry['label']}** supprime.", ephemeral=True)
        else:
            await interaction.response.send_message("Introuvable.", ephemeral=True)


class ReactRoleDeleteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(ReactRoleSelect())


class ReactRoleChannelSelect(discord.ui.ChannelSelect):
    def __init__(self):
        super().__init__(placeholder="Choisis le salon pour le panel react-role...", channel_types=[discord.ChannelType.text])

    async def callback(self, interaction: discord.Interaction):
        ch = self.values[0]
        CFG["react_role_channel_id"] = ch.id
        _cfg_save()
        await interaction.response.send_message(f"Salon react-role defini sur {ch.mention}.\nUtilise `!reactpost` pour poster le message.", ephemeral=True)


class ReactRoleChannelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(ReactRoleChannelSelect())


# ── Boutons react-role (message poste dans le salon) ──
class ReactRoleButtonView(discord.ui.View):
    def __init__(self, entries: list):
        super().__init__(timeout=None)
        for entry in entries:
            btn = discord.ui.Button(
                label=entry["label"],
                emoji=entry["emoji"],
                custom_id=f"rr_{entry['role_id']}",
                style=discord.ButtonStyle.secondary,
            )
            btn.callback = self._make_callback(entry["role_id"])
            self.add_item(btn)

    def _make_callback(self, role_id: int):
        async def callback(interaction: discord.Interaction):
            role = interaction.guild.get_role(role_id)
            if not role:
                return await interaction.response.send_message("Role introuvable.", ephemeral=True)
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(f"Role **{role.name}** retire.", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"Role **{role.name}** donne !", ephemeral=True)
        return callback


# ── Panel react-role ──────────────────────────
class ReactPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.button(label="Ajouter", style=discord.ButtonStyle.success, emoji="➕", row=0)
    async def btn_add(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not _is_admin_i(interaction):
            return await interaction.response.send_message("Reserve aux admins.", ephemeral=True)
        await interaction.response.send_modal(ReactRoleCreateModal())

    @discord.ui.button(label="Supprimer", style=discord.ButtonStyle.danger, emoji="🗑️", row=0)
    async def btn_del(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not _is_admin_i(interaction):
            return await interaction.response.send_message("Reserve aux admins.", ephemeral=True)
        if not CFG.get("react_roles"):
            return await interaction.response.send_message("Aucun react-role configure.", ephemeral=True)
        await interaction.response.send_message("Quel react-role supprimer ?", view=ReactRoleDeleteView(), ephemeral=True)

    @discord.ui.button(label="Salon", style=discord.ButtonStyle.primary, emoji="📁", row=0)
    async def btn_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not _is_admin_i(interaction):
            return await interaction.response.send_message("Reserve aux admins.", ephemeral=True)
        await interaction.response.send_message("Choisis le salon pour le panel :", view=ReactRoleChannelView(), ephemeral=True)

    @discord.ui.button(label="Liste", style=discord.ButtonStyle.secondary, emoji="📋", row=1)
    async def btn_list(self, interaction: discord.Interaction, button: discord.ui.Button):
        entries = CFG.get("react_roles", [])
        if not entries:
            return await interaction.response.send_message("Aucun react-role pour l\'instant.", ephemeral=True)
        embed = discord.Embed(title="React-Roles configures", color=discord.Color.blurple())
        for e in entries:
            embed.add_field(name=f"{e['emoji']} {e['label']}", value=f"Role : <@&{e['role_id']}>", inline=True)
        ch_id = CFG.get("react_role_channel_id")
        embed.set_footer(text=f"Salon : {'<#' + str(ch_id) + '>' if ch_id else 'non defini'} • !reactpost pour poster")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Apercu", style=discord.ButtonStyle.secondary, emoji="👁️", row=1)
    async def btn_preview(self, interaction: discord.Interaction, button: discord.ui.Button):
        entries = CFG.get("react_roles", [])
        if not entries:
            return await interaction.response.send_message("Aucun react-role configure.", ephemeral=True)
        embed = discord.Embed(
            title=CFG.get("react_role_title", "Choisis tes roles !"),
            description=CFG.get("react_role_desc", "Clique sur un bouton pour obtenir ou retirer un role."),
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message("Apercu :", embed=embed, view=ReactRoleButtonView(entries), ephemeral=True)

    @discord.ui.button(label="Titre/Description", style=discord.ButtonStyle.primary, emoji="✏️", row=2)
    async def btn_edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not _is_admin_i(interaction):
            return await interaction.response.send_message("Reserve aux admins.", ephemeral=True)
        await interaction.response.send_modal(ReactRoleTitleModal())


class ReactRoleTitleModal(discord.ui.Modal, title="Titre et description du panel"):
    titre = discord.ui.TextInput(
        label="Titre",
        default="Choisis tes roles !",
        max_length=100,
        required=True,
    )
    desc = discord.ui.TextInput(
        label="Description",
        default="Clique sur un bouton pour obtenir ou retirer un role.",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=False,
    )

    async def on_submit(self, interaction: discord.Interaction):
        CFG["react_role_title"] = self.titre.value
        CFG["react_role_desc"]  = self.desc.value
        _cfg_save()
        await interaction.response.send_message("Titre et description mis a jour.", ephemeral=True)


# ══════════════════════════════════════════════
#  COG
# ══════════════════════════════════════════════

class Extras(commands.Cog, name="Extras"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ──────────────────────────────────────────
    #  BIENVENUE / BYE
    # ──────────────────────────────────────────
    @commands.command(name="welcomepanel", aliases=["wpanel"])
    async def welcome_panel(self, ctx: commands.Context):
        if not _is_admin(ctx):
            return await ctx.reply("Reserve aux admins.", delete_after=5)
        w = CFG.get("welcome", {})
        b = CFG.get("bye", {})
        embed = discord.Embed(title="👋 Config Bienvenue / Bye", color=discord.Color.blurple())
        embed.add_field(
            name="Bienvenue",
            value=f"Salon : {'<#' + str(w.get('channel_id')) + '>' if w.get('channel_id') else 'non defini'}\nMessage : {'Oui' if w.get('message') else 'Non'} | Image : {'Oui' if w.get('image') else 'Non'}",
            inline=False,
        )
        embed.add_field(
            name="Bye",
            value=f"Salon : {'<#' + str(b.get('channel_id')) + '>' if b.get('channel_id') else 'non defini'}\nMessage : {'Oui' if b.get('message') else 'Non'} | Image : {'Oui' if b.get('image') else 'Non'}",
            inline=False,
        )
        embed.set_footer(text="Variables disponibles : {user} {name} {server} {count}")
        try: await ctx.message.delete()
        except: pass
        await ctx.send(embed=embed, view=WelcomePanelView())

    @commands.command(name="testwelcome")
    async def test_welcome(self, ctx: commands.Context):
        if not _is_admin(ctx):
            return await ctx.reply("Reserve aux admins.", delete_after=5)
        embed = _build_welcome_embed(ctx.author, "welcome")
        await ctx.reply(embed=embed)

    @commands.command(name="testbye")
    async def test_bye(self, ctx: commands.Context):
        if not _is_admin(ctx):
            return await ctx.reply("Reserve aux admins.", delete_after=5)
        embed = _build_welcome_embed(ctx.author, "bye")
        await ctx.reply(embed=embed)

    # ──────────────────────────────────────────
    #  MASSROLE
    # ──────────────────────────────────────────
    @commands.command(name="massifrole")
    async def massif_role(self, ctx: commands.Context, *roles: discord.Role):
        if not _is_admin(ctx):
            return await ctx.reply("Reserve aux admins.", delete_after=5)
        if not roles:
            return await ctx.reply("Mentionne au moins un role.\nExemple : `!massifrole @Membre @Verified`", delete_after=8)

        members = [m for m in ctx.guild.members if not m.bot]
        msg = await ctx.reply(f"Ajout de {', '.join(r.mention for r in roles)} a **{len(members)}** membres... (peut prendre du temps)")

        count = 0
        errors = 0
        for member in members:
            try:
                await member.add_roles(*roles, reason=f"Massifrole par {ctx.author}")
                count += 1
            except:
                errors += 1

        embed = discord.Embed(
            title="Massifrole termine",
            description=f"Role(s) {', '.join(r.mention for r in roles)} donnes a **{count}** membres.\n" + (f"Echecs : {errors}" if errors else ""),
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc),
        )
        await msg.edit(content=None, embed=embed)

    @massif_role.error
    async def massif_role_error(self, ctx, error):
        if isinstance(error, commands.RoleNotFound):
            await ctx.reply("Role introuvable. Mentionne bien le role avec @.", delete_after=8)

    # ──────────────────────────────────────────
    #  REACT = ROLE
    # ──────────────────────────────────────────
    @commands.command(name="reactpanel")
    async def react_panel(self, ctx: commands.Context):
        if not _is_admin(ctx):
            return await ctx.reply("Reserve aux admins.", delete_after=5)
        entries = CFG.get("react_roles", [])
        ch_id   = CFG.get("react_role_channel_id")
        embed = discord.Embed(title="React = Role", color=discord.Color.blurple())
        embed.add_field(name="Salon", value=f"<#{ch_id}>" if ch_id else "Non defini", inline=True)
        embed.add_field(name="Roles configures", value=str(len(entries)), inline=True)
        embed.set_footer(text="Ajoute des roles, configure le salon, puis !reactpost")
        try: await ctx.message.delete()
        except: pass
        await ctx.send(embed=embed, view=ReactPanelView())

    @commands.command(name="reactpost")
    async def react_post(self, ctx: commands.Context):
        if not _is_admin(ctx):
            return await ctx.reply("Reserve aux admins.", delete_after=5)
        entries = CFG.get("react_roles", [])
        if not entries:
            return await ctx.reply("Aucun react-role configure. Utilise `!reactpanel` pour en ajouter.", delete_after=8)
        ch_id = CFG.get("react_role_channel_id")
        if not ch_id:
            return await ctx.reply("Aucun salon configure. Utilise `!reactpanel` → bouton **Salon**.", delete_after=8)
        channel = ctx.guild.get_channel(ch_id)
        if not channel:
            return await ctx.reply("Salon introuvable. Reconfigure-le avec `!reactpanel`.", delete_after=8)
        embed = discord.Embed(
            title=CFG.get("react_role_title", "Choisis tes roles !"),
            description=CFG.get("react_role_desc", "Clique sur un bouton pour obtenir ou retirer un role."),
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc),
        )
        await channel.send(embed=embed, view=ReactRoleButtonView(entries))
        try: await ctx.message.delete()
        except: pass
        await ctx.reply(f"Panel react-role poste dans {channel.mention} !", delete_after=5)

    # ──────────────────────────────────────────
    #  EVENTS
    # ──────────────────────────────────────────
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        section = CFG.get("welcome", {})
        ch_id = section.get("channel_id")
        if not ch_id or not section.get("message"):
            return
        channel = member.guild.get_channel(ch_id)
        if channel:
            try:
                await channel.send(embed=_build_welcome_embed(member, "welcome"))
            except discord.Forbidden:
                pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        section = CFG.get("bye", {})
        ch_id = section.get("channel_id")
        if not ch_id or not section.get("message"):
            return
        channel = member.guild.get_channel(ch_id)
        if channel:
            try:
                await channel.send(embed=_build_welcome_embed(member, "bye"))
            except discord.Forbidden:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(Extras(bot))
