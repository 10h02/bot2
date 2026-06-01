import discord
from discord.ext import commands
from datetime import datetime, timezone
import asyncio

def embed_success(titre, description):
    return discord.Embed(title=f"✅ {titre}", description=description, color=0x2ecc71, timestamp=datetime.now(timezone.utc))

def embed_error(titre, description):
    return discord.Embed(title=f"❌ {titre}", description=description, color=0xe74c3c, timestamp=datetime.now(timezone.utc))

def embed_info(titre, description):
    return discord.Embed(title=f"📋 {titre}", description=description, color=0x3498db, timestamp=datetime.now(timezone.utc))

def embed_warn(titre, description):
    return discord.Embed(title=f"⚠️ {titre}", description=description, color=0xf39c12, timestamp=datetime.now(timezone.utc))

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ——— WHITELIST ———
    @commands.command()
    async def wl(self, ctx, membre: discord.Member):
        if ctx.author.id not in self.bot.BOT_ADMINS:
            return await ctx.send(embed=embed_error("Permission refusée", "Tu n'as pas la permission de faire ça."))
        self.bot.whitelist.add(membre.id)
        e = embed_success("Whitelist", f"{membre.mention} a été ajouté à la whitelist.")
        e.set_thumbnail(url=membre.display_avatar.url)
        await ctx.send(embed=e)

    @commands.command()
    async def unwl(self, ctx, membre: discord.Member):
        if ctx.author.id not in self.bot.BOT_ADMINS:
            return await ctx.send(embed=embed_error("Permission refusée", "Tu n'as pas la permission de faire ça."))
        self.bot.whitelist.discard(membre.id)
        e = embed_success("Whitelist", f"{membre.mention} a été retiré de la whitelist.")
        e.set_thumbnail(url=membre.display_avatar.url)
        await ctx.send(embed=e)

    @commands.command()
    async def wllist(self, ctx):
        if not self.bot.whitelist:
            return await ctx.send(embed=embed_info("Whitelist", "La whitelist est vide."))
        membres = "\n".join([f"• <@{uid}>" for uid in self.bot.whitelist])
        await ctx.send(embed=embed_info("Whitelist", membres))

    # ——— ADMINS DU BOT ———
    @commands.command()
    async def addadmin(self, ctx, membre: discord.Member):
        if ctx.author.id not in self.bot.BOT_ADMINS:
            return await ctx.send(embed=embed_error("Permission refusée", "Tu n'as pas la permission de faire ça."))
        self.bot.BOT_ADMINS.add(membre.id)
        e = embed_success("Admin ajouté", f"{membre.mention} est maintenant admin du bot.")
        e.set_thumbnail(url=membre.display_avatar.url)
        await ctx.send(embed=e)

    @commands.command()
    async def removeadmin(self, ctx, membre: discord.Member):
        if ctx.author.id not in self.bot.BOT_ADMINS:
            return await ctx.send(embed=embed_error("Permission refusée", "Tu n'as pas la permission de faire ça."))
        if membre.id == self.bot.ADMIN_ID:
            return await ctx.send(embed=embed_error("Impossible", "Tu ne peux pas retirer l'admin principal."))
        self.bot.BOT_ADMINS.discard(membre.id)
        e = embed_success("Admin retiré", f"{membre.mention} n'est plus admin du bot.")
        e.set_thumbnail(url=membre.display_avatar.url)
        await ctx.send(embed=e)

    @commands.command()
    async def adminlist(self, ctx):
        membres = "\n".join([f"• <@{uid}>" for uid in self.bot.BOT_ADMINS])
        await ctx.send(embed=embed_info("👑 Admins du bot", membres))

    # ——— BLACKLIST ———
    @commands.command()
    async def bl(self, ctx, membre: discord.Member, *, raison="Aucune raison"):
        if ctx.author.id not in self.bot.BOT_ADMINS:
            return await ctx.send(embed=embed_error("Permission refusée", "Tu n'as pas la permission de faire ça."))
        self.bot.blacklist[membre.id] = raison
        for guild in self.bot.guilds:
            try:
                await guild.ban(membre, reason=f"Blacklist : {raison}")
            except:
                pass
        e = embed_error("🚫 Blacklist", f"{membre.mention} a été blacklisté et banni de tous les serveurs.")
        e.add_field(name="Raison", value=raison)
        e.set_thumbnail(url=membre.display_avatar.url)
        await ctx.send(embed=e)

    @commands.command()
    async def unbl(self, ctx, user_id: int):
        if ctx.author.id not in self.bot.BOT_ADMINS:
            return await ctx.send(embed=embed_error("Permission refusée", "Tu n'as pas la permission de faire ça."))
        if user_id not in self.bot.blacklist:
            return await ctx.send(embed=embed_error("Introuvable", "Cet utilisateur n'est pas blacklisté."))
        del self.bot.blacklist[user_id]
        for guild in self.bot.guilds:
            try:
                user = await self.bot.fetch_user(user_id)
                await guild.unban(user)
            except:
                pass
        await ctx.send(embed=embed_success("Blacklist", f"<@{user_id}> retiré de la blacklist et débanni partout."))

    @commands.command()
    async def bllist(self, ctx):
        if ctx.author.id not in self.bot.BOT_ADMINS:
            return await ctx.send(embed=embed_error("Permission refusée", "Tu n'as pas la permission de faire ça."))
        if not self.bot.blacklist:
            return await ctx.send(embed=embed_info("🚫 Blacklist", "La blacklist est vide."))
        e = discord.Embed(title="🚫 Blacklist", color=0xe74c3c, timestamp=datetime.now(timezone.utc))
        for uid, raison in self.bot.blacklist.items():
            e.add_field(name=f"<@{uid}>", value=f"```{raison}```", inline=False)
        await ctx.send(embed=e)

    # ——— BANALL ———
    @commands.command()
    async def banall(self, ctx):
        if ctx.author.id not in self.bot.BOT_ADMINS:
            return await ctx.send(embed=embed_error("Permission refusée", "Tu n'as pas la permission de faire ça."))
        msg = await ctx.send(embed=embed_warn("BanAll", "Ban de tous les membres en cours..."))
        count = 0
        for membre in ctx.guild.members:
            if membre.id != ctx.author.id and membre.id != self.bot.user.id and not membre.bot:
                try:
                    await membre.ban(reason="BanAll")
                    count += 1
                except:
                    pass
        await msg.edit(embed=embed_success("BanAll terminé", f"**{count}** membres bannis."))

    # ——— KICK / BAN / UNBAN ———
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, membre: discord.Member, *, raison="Aucune raison"):
        await membre.kick(reason=raison)
        e = embed_warn("Membre kické", f"{membre.mention} a été expulsé du serveur.")
        e.add_field(name="Raison", value=raison)
        e.add_field(name="Modérateur", value=ctx.author.mention)
        e.set_thumbnail(url=membre.display_avatar.url)
        await ctx.send(embed=e)

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, membre: discord.Member, *, raison="Aucune raison"):
        await membre.ban(reason=raison)
        e = embed_error("Membre banni", f"{membre.mention} a été banni du serveur.")
        e.add_field(name="Raison", value=raison)
        e.add_field(name="Modérateur", value=ctx.author.mention)
        e.set_thumbnail(url=membre.display_avatar.url)
        await ctx.send(embed=e)

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def unban(self, ctx, *, nom):
        bans = [entry async for entry in ctx.guild.bans()]
        for ban in bans:
            if ban.user.name == nom:
                await ctx.guild.unban(ban.user)
                return await ctx.send(embed=embed_success("Membre débanni", f"**{ban.user.name}** a été débanni."))
        await ctx.send(embed=embed_error("Introuvable", f"Aucun banni avec le nom **{nom}**."))

    # ——— MUTE / UNMUTE ———
    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def mute(self, ctx, membre: discord.Member, *, raison="Aucune raison"):
        role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not role:
            role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(role, send_messages=False, speak=False, add_reactions=False)
        await membre.add_roles(role)
        e = embed_warn("Membre muté", f"{membre.mention} a été réduit au silence.")
        e.add_field(name="Raison", value=raison)
        e.add_field(name="Modérateur", value=ctx.author.mention)
        e.set_thumbnail(url=membre.display_avatar.url)
        await ctx.send(embed=e)
        try:
            await membre.send(embed=embed_warn("Tu as été muté", f"Sur **{ctx.guild.name}**\nRaison : {raison}"))
        except:
            pass

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def unmute(self, ctx, membre: discord.Member):
        role = discord.utils.get(ctx.guild.roles, name="Muted")
        if role:
            await membre.remove_roles(role)
        e = embed_success("Membre unmuté", f"{membre.mention} peut de nouveau parler.")
        e.set_thumbnail(url=membre.display_avatar.url)
        await ctx.send(embed=e)

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def tempmute(self, ctx, membre: discord.Member, duree: str, *, raison="Aucune raison"):
        role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not role:
            role = await ctx.guild.create_role(name="Muted")
        for channel in ctx.guild.channels:
            await channel.set_permissions(role, send_messages=False, speak=False, add_reactions=False)
        unite = duree[-1]
        try:
            valeur = int(duree[:-1])
        except:
            return await ctx.send(embed=embed_error("Format invalide", "Utilise : `10m`, `1h`, `2d`"))
        if unite == "m": secondes = valeur * 60
        elif unite == "h": secondes = valeur * 3600
        elif unite == "d": secondes = valeur * 86400
        else:
            return await ctx.send(embed=embed_error("Unité invalide", "Utilise `m`, `h` ou `d`."))
        await membre.add_roles(role)
        e = embed_warn("Mute temporaire", f"{membre.mention} est muté pour **{duree}**.")
        e.add_field(name="Raison", value=raison)
        e.add_field(name="Modérateur", value=ctx.author.mention)
        e.set_thumbnail(url=membre.display_avatar.url)
        await ctx.send(embed=e)
        try:
            await membre.send(embed=embed_warn("Tu as été muté temporairement", f"Sur **{ctx.guild.name}** pendant **{duree}**\nRaison : {raison}"))
        except:
            pass
        await asyncio.sleep(secondes)
        await membre.remove_roles(role)
        await ctx.send(embed=embed_success("Unmute automatique", f"{membre.mention} est de nouveau libre de parler."))

    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def tempban(self, ctx, membre: discord.Member, duree: str, *, raison="Aucune raison"):
        unite = duree[-1]
        try:
            valeur = int(duree[:-1])
        except:
            return await ctx.send(embed=embed_error("Format invalide", "Utilise : `10m`, `1h`, `2d`"))
        if unite == "m": secondes = valeur * 60
        elif unite == "h": secondes = valeur * 3600
        elif unite == "d": secondes = valeur * 86400
        else:
            return await ctx.send(embed=embed_error("Unité invalide", "Utilise `m`, `h` ou `d`."))
        await membre.ban(reason=raison)
        e = embed_error("Ban temporaire", f"{membre.mention} est banni pour **{duree}**.")
        e.add_field(name="Raison", value=raison)
        e.add_field(name="Modérateur", value=ctx.author.mention)
        e.set_thumbnail(url=membre.display_avatar.url)
        await ctx.send(embed=e)
        await asyncio.sleep(secondes)
        await ctx.guild.unban(membre)
        await ctx.send(embed=embed_success("Unban automatique", f"{membre.mention} a été débanni automatiquement."))

    # ——— WARNS ———
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def warn(self, ctx, membre: discord.Member, *, raison="Aucune raison"):
        if membre.id not in self.bot.warnings:
            self.bot.warnings[membre.id] = []
        self.bot.warnings[membre.id].append({
            "raison": raison,
            "moderateur": ctx.author.id,
            "date": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        })
        nb = len(self.bot.warnings[membre.id])
        e = embed_warn("Avertissement", f"{membre.mention} a reçu un avertissement. (**{nb}** au total)")
        e.add_field(name="Raison", value=raison)
        e.add_field(name="Modérateur", value=ctx.author.mention)
        e.set_thumbnail(url=membre.display_avatar.url)
        await ctx.send(embed=e)
        try:
            await membre.send(embed=embed_warn("Tu as reçu un avertissement", f"Sur **{ctx.guild.name}**\nRaison : {raison} ({nb} au total)"))
        except:
            pass

    @commands.command()
    async def warns(self, ctx, membre: discord.Member):
        if membre.id not in self.bot.warnings or not self.bot.warnings[membre.id]:
            return await ctx.send(embed=embed_success("Aucun warn", f"{membre.mention} n'a aucun avertissement."))
        e = discord.Embed(title=f"⚠️ Warns de {membre.name}", color=0xf39c12, timestamp=datetime.now(timezone.utc))
        for i, w in enumerate(self.bot.warnings[membre.id]):
            e.add_field(name=f"Warn #{i+1}", value=f"```{w['raison']}```", inline=False)
        e.set_thumbnail(url=membre.display_avatar.url)
        await ctx.send(embed=e)

    @commands.command()
    async def warninfo(self, ctx, membre: discord.Member):
        if membre.id not in self.bot.warnings or not self.bot.warnings[membre.id]:
            return await ctx.send(embed=embed_success("Aucun warn", f"{membre.mention} n'a aucun avertissement."))
        e = discord.Embed(title=f"⚠️ Détails des warns de {membre.name}", color=0xf39c12, timestamp=datetime.now(timezone.utc))
        for i, w in enumerate(self.bot.warnings[membre.id]):
            e.add_field(name=f"Warn #{i+1}", value=f"📝 {w['raison']}\n👮 <@{w['moderateur']}>\n📅 {w['date']}", inline=False)
        e.set_thumbnail(url=membre.display_avatar.url)
        await ctx.send(embed=e)

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def unwarn(self, ctx, membre: discord.Member, numero: int):
        if membre.id not in self.bot.warnings or not self.bot.warnings[membre.id]:
            return await ctx.send(embed=embed_success("Aucun warn", f"{membre.mention} n'a aucun avertissement."))
        if numero < 1 or numero > len(self.bot.warnings[membre.id]):
            return await ctx.send(embed=embed_error("Numéro invalide", f"Ce warn n'existe pas."))
        self.bot.warnings[membre.id].pop(numero - 1)
        await ctx.send(embed=embed_success("Warn supprimé", f"Avertissement **#{numero}** de {membre.mention} supprimé."))

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clearwarns(self, ctx, membre: discord.Member):
        self.bot.warnings[membre.id] = []
        e = embed_success("Warns effacés", f"Tous les avertissements de {membre.mention} ont été supprimés.")
        e.set_thumbnail(url=membre.display_avatar.url)
        await ctx.send(embed=e)

    # ——— DERANK ———
    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def derank(self, ctx, membre: discord.Member):
        roles_to_remove = [r for r in membre.roles if r != ctx.guild.default_role and r < ctx.guild.me.top_role]
        if not roles_to_remove:
            return await ctx.send(embed=embed_error("Aucun rôle", f"{membre.mention} n'a aucun rôle à retirer."))
        await membre.remove_roles(*roles_to_remove)
        e = embed_success("Derank", f"Tous les rôles de {membre.mention} ont été retirés.")
        e.set_thumbnail(url=membre.display_avatar.url)
        await ctx.send(embed=e)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
