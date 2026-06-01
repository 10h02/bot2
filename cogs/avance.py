import discord
from discord.ext import commands
from datetime import datetime, timezone
import asyncio
import json
import os

def embed_success(titre, description):
    return discord.Embed(title=f"✅ {titre}", description=description, color=0x2ecc71, timestamp=datetime.now(timezone.utc))

def embed_error(titre, description):
    return discord.Embed(title=f"❌ {titre}", description=description, color=0xe74c3c, timestamp=datetime.now(timezone.utc))

def embed_info(titre, description):
    return discord.Embed(title=f"📋 {titre}", description=description, color=0x3498db, timestamp=datetime.now(timezone.utc))

def embed_warn(titre, description):
    return discord.Embed(title=f"⚠️ {titre}", description=description, color=0xf39c12, timestamp=datetime.now(timezone.utc))


# ─────────────────────────────────────────────
#  💾  PERSISTANCE — avance
# ─────────────────────────────────────────────
_AVANCE_FILE = "data/avance_config.json"

def _load_avance() -> dict:
    if os.path.exists(_AVANCE_FILE):
        try:
            with open(_AVANCE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}

def _save_avance(data: dict) -> None:
    try:
        os.makedirs(os.path.dirname(_AVANCE_FILE), exist_ok=True)
        with open(_AVANCE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"[Avance] Impossible de sauvegarder : {e}")

class Avance(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        _cfg = _load_avance()
        self.bot.LOGS_CHANNEL_ID    = _cfg.get("LOGS_CHANNEL_ID", None)
        self.bot.ANTI_RAID          = _cfg.get("ANTI_RAID", False)
        self.bot.ANTI_NUKE          = _cfg.get("ANTI_NUKE", False)
        self.bot.RAID_JOIN_COUNT    = {}
        self.bot.SNIPE_CACHE        = {}
        self.bot.EDIT_SNIPE_CACHE   = {}
        self.bot.NUKE_ACTION_TRACKER = {}
        print(f"[Avance] Config chargée — antiraid={self.bot.ANTI_RAID} antinuke={self.bot.ANTI_NUKE} logs={self.bot.LOGS_CHANNEL_ID}")

    def _save(self):
        _save_avance({
            "LOGS_CHANNEL_ID": self.bot.LOGS_CHANNEL_ID,
            "ANTI_RAID":       self.bot.ANTI_RAID,
            "ANTI_NUKE":       self.bot.ANTI_NUKE,
        })

    async def send_log(self, guild, embed):
        if self.bot.LOGS_CHANNEL_ID:
            channel = guild.get_channel(self.bot.LOGS_CHANNEL_ID)
            if channel:
                try:
                    await channel.send(embed=embed)
                except:
                    pass

    # ——— LOCKDOWN ———
    @commands.command()
    async def lockdown(self, ctx):
        if ctx.author.id not in self.bot.BOT_ADMINS:
            return await ctx.send(embed=embed_error("Permission refusée", "Tu n'as pas la permission."))
        msg = await ctx.send(embed=embed_warn("Lockdown", "Verrouillage de tous les salons en cours..."))
        count = 0
        for channel in ctx.guild.text_channels:
            try:
                await channel.set_permissions(ctx.guild.default_role, send_messages=False)
                count += 1
            except:
                pass
        await msg.edit(embed=embed_error("🔒 Lockdown activé", f"**{count}** salons ont été verrouillés."))

    @commands.command()
    async def unlockdown(self, ctx):
        if ctx.author.id not in self.bot.BOT_ADMINS:
            return await ctx.send(embed=embed_error("Permission refusée", "Tu n'as pas la permission."))
        msg = await ctx.send(embed=embed_warn("Unlockdown", "Déverrouillage de tous les salons en cours..."))
        count = 0
        for channel in ctx.guild.text_channels:
            try:
                await channel.set_permissions(ctx.guild.default_role, send_messages=True)
                count += 1
            except:
                pass
        await msg.edit(embed=embed_success("🔓 Lockdown désactivé", f"**{count}** salons ont été déverrouillés."))

    # ——— ANTI-RAID ———
    @commands.command()
    async def antiraid(self, ctx):
        if ctx.author.id not in self.bot.BOT_ADMINS:
            return await ctx.send(embed=embed_error("Permission refusée", "Tu n'as pas la permission."))
        self.bot.ANTI_RAID = not self.bot.ANTI_RAID
        self._save()
        status = "activé ✅" if self.bot.ANTI_RAID else "désactivé ❌"
        await ctx.send(embed=embed_success("Anti-raid", f"L'anti-raid est maintenant **{status}**.\nSi 5+ membres rejoignent en 10s, ils seront kickés et le serveur sera lockdown."))

    # ——— ANTI-NUKE ———
    @commands.command()
    async def antinuke(self, ctx):
        if ctx.author.id not in self.bot.BOT_ADMINS:
            return await ctx.send(embed=embed_error("Permission refusée", "Tu n'as pas la permission."))
        self.bot.ANTI_NUKE = not self.bot.ANTI_NUKE
        self._save()
        status = "activé ✅" if self.bot.ANTI_NUKE else "désactivé ❌"
        await ctx.send(embed=embed_success("Anti-nuke", f"L'anti-nuke est maintenant **{status}**.\nSi quelqu'un supprime 3+ salons en 10s, il sera banni."))

    # ——— ALT DETECTION ———
    @commands.command()
    async def altwarn(self, ctx, jours: int = 30):
        if ctx.author.id not in self.bot.BOT_ADMINS:
            return await ctx.send(embed=embed_error("Permission refusée", "Tu n'as pas la permission."))
        now = datetime.now(timezone.utc)
        msg = await ctx.send(embed=embed_warn("Détection alts", f"Recherche des comptes de moins de **{jours} jours**..."))
        count = 0
        kicked = []
        for membre in ctx.guild.members:
            age = (now - membre.created_at).days
            if age < jours and not membre.bot and membre.id != ctx.author.id:
                try:
                    await membre.kick(reason=f"Compte trop récent ({age} jours)")
                    kicked.append(f"`{membre.name}` — {age} jours")
                    count += 1
                except:
                    pass
        if count == 0:
            await msg.edit(embed=embed_success("Aucun alt détecté", f"Aucun compte de moins de **{jours} jours** trouvé."))
        else:
            e = embed_success("Alts kickés", f"**{count}** comptes récents ont été kickés.")
            e.add_field(name="Comptes", value="\n".join(kicked) if kicked else "Aucun", inline=False)
            await msg.edit(embed=e)

    # ——— LOGS ———
    @commands.command()
    async def setlogs(self, ctx, salon: discord.TextChannel = None):
        if ctx.author.id not in self.bot.BOT_ADMINS:
            return await ctx.send(embed=embed_error("Permission refusée", "Tu n'as pas la permission."))
        salon = salon or ctx.channel
        self.bot.LOGS_CHANNEL_ID = salon.id
        self._save()
        await ctx.send(embed=embed_success("Salon de logs", f"Les logs seront envoyés dans {salon.mention}."))

    # ——— SNIPE ———
    @commands.command()
    async def snipe(self, ctx):
        data = self.bot.SNIPE_CACHE.get(ctx.channel.id)
        if not data:
            return await ctx.send(embed=embed_error("Snipe", "Aucun message supprimé récemment dans ce salon."))
        e = discord.Embed(description=data["content"], color=0xe74c3c, timestamp=data["time"])
        e.set_author(name=data["author"], icon_url=data["avatar"])
        e.set_footer(text="🗑️ Message supprimé")
        await ctx.send(embed=e)

    @commands.command()
    async def editsnipe(self, ctx):
        data = self.bot.EDIT_SNIPE_CACHE.get(ctx.channel.id)
        if not data:
            return await ctx.send(embed=embed_error("Edit Snipe", "Aucun message édité récemment dans ce salon."))
        e = discord.Embed(color=0xf39c12, timestamp=data["time"])
        e.set_author(name=data["author"], icon_url=data["avatar"])
        e.add_field(name="Avant", value=data["before"], inline=False)
        e.add_field(name="Après", value=data["after"], inline=False)
        e.set_footer(text="✏️ Message édité")
        await ctx.send(embed=e)

    # ——— NUKE ———
    @commands.command()
    async def nuke(self, ctx):
        if ctx.author.id not in self.bot.BOT_ADMINS:
            return await ctx.send(embed=embed_error("Permission refusée", "Tu n'as pas la permission."))
        channel = ctx.channel
        new_channel = await channel.clone(reason=f"Nuke par {ctx.author}")
        await channel.delete()
        await new_channel.send(embed=embed_success("💥 Salon nuké", f"Ce salon a été nuké par {ctx.author.mention}."))

    # ——— CLONE ———
    @commands.command()
    async def clone(self, ctx, salon: discord.TextChannel = None):
        if ctx.author.id not in self.bot.BOT_ADMINS:
            return await ctx.send(embed=embed_error("Permission refusée", "Tu n'as pas la permission."))
        salon = salon or ctx.channel
        new = await salon.clone(reason=f"Clone par {ctx.author}")
        await ctx.send(embed=embed_success("Salon cloné", f"{salon.mention} a été cloné → {new.mention}"))

    # ——— HIDE / UNHIDE ———
    @commands.command()
    async def hide(self, ctx, salon: discord.TextChannel = None):
        if ctx.author.id not in self.bot.BOT_ADMINS:
            return await ctx.send(embed=embed_error("Permission refusée", "Tu n'as pas la permission."))
        salon = salon or ctx.channel
        await salon.set_permissions(ctx.guild.default_role, view_channel=False)
        await ctx.send(embed=embed_success("Salon caché", f"{salon.mention} est maintenant invisible pour tout le monde."))

    @commands.command()
    async def unhide(self, ctx, salon: discord.TextChannel = None):
        if ctx.author.id not in self.bot.BOT_ADMINS:
            return await ctx.send(embed=embed_error("Permission refusée", "Tu n'as pas la permission."))
        salon = salon or ctx.channel
        await salon.set_permissions(ctx.guild.default_role, view_channel=True)
        await ctx.send(embed=embed_success("Salon visible", f"{salon.mention} est maintenant visible pour tout le monde."))

    # ——— MASSROLE ———
    @commands.command()
    async def massrole(self, ctx, *roles: discord.Role):
        if ctx.author.id not in self.bot.BOT_ADMINS:
            return await ctx.send(embed=embed_error("Permission refusée", "Tu n'as pas la permission."))
        if not roles:
            return await ctx.send(embed=embed_error("Erreur", "Donne au moins un rôle. Ex: `!massrole @role1 @role2`"))
        msg = await ctx.send(embed=embed_warn("Massrole", f"Attribution des rôles à tous les membres..."))
        count = 0
        for membre in ctx.guild.members:
            try:
                await membre.add_roles(*roles)
                count += 1
            except:
                pass
        noms = ", ".join([r.mention for r in roles])
        await msg.edit(embed=embed_success("Massrole terminé", f"{noms} donnés à **{count}** membres."))

    # ——— TICKETS AVANCÉS ———
    @commands.command()
    async def adduser(self, ctx, membre: discord.Member):
        if ctx.channel.id not in self.bot.tickets:
            return await ctx.send(embed=embed_error("Erreur", "Ce salon n'est pas un ticket."))
        await ctx.channel.set_permissions(membre, read_messages=True, send_messages=True)
        e = embed_success("Utilisateur ajouté", f"{membre.mention} a été ajouté au ticket.")
        e.set_thumbnail(url=membre.display_avatar.url)
        await ctx.send(embed=e)

    @commands.command()
    async def renameticket(self, ctx, *, nom):
        if ctx.channel.id not in self.bot.tickets:
            return await ctx.send(embed=embed_error("Erreur", "Ce salon n'est pas un ticket."))
        await ctx.channel.edit(name=f"ticket-{nom}")
        await ctx.send(embed=embed_success("Ticket renommé", f"Ce ticket s'appelle maintenant **ticket-{nom}**."))

    @commands.command()
    async def saveticket(self, ctx):
        if ctx.channel.id not in self.bot.tickets:
            return await ctx.send(embed=embed_error("Erreur", "Ce salon n'est pas un ticket."))
        messages = []
        async for msg in ctx.channel.history(limit=500, oldest_first=True):
            messages.append(f"[{msg.created_at.strftime('%d/%m/%Y %H:%M')}] {msg.author}: {msg.content}")
        transcription = "\n".join(messages)
        if len(transcription) > 1900:
            transcription = transcription[:1900] + "\n... (tronqué)"
        e = discord.Embed(
            title=f"📄 Transcription — {ctx.channel.name}",
            description=f"```{transcription}```",
            color=0x7289da,
            timestamp=datetime.now(timezone.utc)
        )
        try:
            owner_id = self.bot.tickets.get(ctx.channel.id)
            owner = ctx.guild.get_member(owner_id)
            if owner:
                await owner.send(embed=e)
                await ctx.send(embed=embed_success("Transcription sauvegardée", f"La transcription a été envoyée en DM à {owner.mention}."))
            else:
                await ctx.send(embed=e)
        except:
            await ctx.send(embed=e)

    # ——— EVENTS ———
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.author.bot or not message.content:
            return
        self.bot.SNIPE_CACHE[message.channel.id] = {
            "content": message.content,
            "author": str(message.author),
            "avatar": message.author.display_avatar.url,
            "time": message.created_at
        }
        if self.bot.LOGS_CHANNEL_ID and message.guild:
            e = discord.Embed(title="🗑️ Message supprimé", description=message.content, color=0xe74c3c, timestamp=datetime.now(timezone.utc))
            e.set_author(name=str(message.author), icon_url=message.author.display_avatar.url)
            e.add_field(name="Salon", value=message.channel.mention)
            await self.send_log(message.guild, e)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author.bot or before.content == after.content:
            return
        self.bot.EDIT_SNIPE_CACHE[before.channel.id] = {
            "before": before.content,
            "after": after.content,
            "author": str(before.author),
            "avatar": before.author.display_avatar.url,
            "time": datetime.now(timezone.utc)
        }
        if self.bot.LOGS_CHANNEL_ID and before.guild:
            e = discord.Embed(title="✏️ Message édité", color=0xf39c12, timestamp=datetime.now(timezone.utc))
            e.set_author(name=str(before.author), icon_url=before.author.display_avatar.url)
            e.add_field(name="Avant", value=before.content or "vide", inline=False)
            e.add_field(name="Après", value=after.content or "vide", inline=False)
            e.add_field(name="Salon", value=before.channel.mention)
            await self.send_log(before.guild, e)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if self.bot.ANTI_RAID and member.guild:
            guild_id = member.guild.id
            now = datetime.now(timezone.utc).timestamp()
            if guild_id not in self.bot.RAID_JOIN_COUNT:
                self.bot.RAID_JOIN_COUNT[guild_id] = []
            self.bot.RAID_JOIN_COUNT[guild_id].append(now)
            self.bot.RAID_JOIN_COUNT[guild_id] = [t for t in self.bot.RAID_JOIN_COUNT[guild_id] if now - t <= 10]
            if len(self.bot.RAID_JOIN_COUNT[guild_id]) >= 5:
                try:
                    await member.kick(reason="Anti-raid")
                except:
                    pass
                for channel in member.guild.text_channels:
                    try:
                        await channel.set_permissions(member.guild.default_role, send_messages=False)
                    except:
                        pass
                if self.bot.LOGS_CHANNEL_ID:
                    e = discord.Embed(title="🚨 RAID DÉTECTÉ", description="5+ membres ont rejoint en moins de 10 secondes.\n**Lockdown automatique activé.**", color=0xe74c3c, timestamp=datetime.now(timezone.utc))
                    await self.send_log(member.guild, e)

        if self.bot.LOGS_CHANNEL_ID:
            e = discord.Embed(title="📥 Membre rejoint", description=f"{member.mention} a rejoint le serveur.", color=0x2ecc71, timestamp=datetime.now(timezone.utc))
            e.set_thumbnail(url=member.display_avatar.url)
            e.add_field(name="Compte créé le", value=member.created_at.strftime("%d/%m/%Y"))
            e.add_field(name="ID", value=f"`{member.id}`")
            await self.send_log(member.guild, e)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if self.bot.LOGS_CHANNEL_ID:
            e = discord.Embed(title="📤 Membre parti", description=f"**{member.name}** a quitté le serveur.", color=0xe74c3c, timestamp=datetime.now(timezone.utc))
            e.set_thumbnail(url=member.display_avatar.url)
            await self.send_log(member.guild, e)

    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        if self.bot.LOGS_CHANNEL_ID:
            e = discord.Embed(title="🔨 Membre banni", description=f"**{user.name}** a été banni.", color=0xe74c3c, timestamp=datetime.now(timezone.utc))
            e.set_thumbnail(url=user.display_avatar.url)
            await self.send_log(guild, e)

    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        if self.bot.LOGS_CHANNEL_ID:
            e = discord.Embed(title="✅ Membre débanni", description=f"**{user.name}** a été débanni.", color=0x2ecc71, timestamp=datetime.now(timezone.utc))
            e.set_thumbnail(url=user.display_avatar.url)
            await self.send_log(guild, e)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        if not self.bot.ANTI_NUKE:
            return
        guild = channel.guild
        async for entry in guild.audit_logs(action=discord.AuditLogAction.channel_delete, limit=1):
            if entry.user.id in self.bot.BOT_ADMINS:
                return
            user_id = entry.user.id
            now = datetime.now(timezone.utc).timestamp()
            if user_id not in self.bot.NUKE_ACTION_TRACKER:
                self.bot.NUKE_ACTION_TRACKER[user_id] = []
            self.bot.NUKE_ACTION_TRACKER[user_id].append(now)
            self.bot.NUKE_ACTION_TRACKER[user_id] = [t for t in self.bot.NUKE_ACTION_TRACKER[user_id] if now - t <= 10]
            if len(self.bot.NUKE_ACTION_TRACKER[user_id]) >= 3:
                try:
                    await guild.ban(entry.user, reason="Anti-nuke : suppression massive de salons")
                    if self.bot.LOGS_CHANNEL_ID:
                        e = discord.Embed(title="💣 NUKE DÉTECTÉ", description=f"**{entry.user}** banni pour suppression massive de salons.", color=0xe74c3c, timestamp=datetime.now(timezone.utc))
                        await self.send_log(guild, e)
                except:
                    pass

async def setup(bot):
    await bot.add_cog(Avance(bot))
