import discord
from discord.ext import commands
from datetime import datetime, timezone
import asyncio
import time
import re
import json
import os

def embed_success(titre, description):
    return discord.Embed(title=f"✅ {titre}", description=description, color=0x2ecc71, timestamp=datetime.now(timezone.utc))

def embed_error(titre, description):
    return discord.Embed(title=f"❌ {titre}", description=description, color=0xe74c3c, timestamp=datetime.now(timezone.utc))

def embed_info(titre, description):
    return discord.Embed(title=f"📋 {titre}", description=description, color=0x3498db, timestamp=datetime.now(timezone.utc))


# ─────────────────────────────────────────────
#  💾  PERSISTANCE — securite
# ─────────────────────────────────────────────
_SECU_FILE = "data/securite_config.json"

def _load_secu() -> dict:
    if os.path.exists(_SECU_FILE):
        try:
            with open(_SECU_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}

def _save_secu(data: dict) -> None:
    try:
        os.makedirs(os.path.dirname(_SECU_FILE), exist_ok=True)
        with open(_SECU_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"[Securite] Impossible de sauvegarder : {e}")

class Securite(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        _cfg = _load_secu()
        self.bot.ANTI_LIEN         = _cfg.get("ANTI_LIEN", False)
        self.bot.ANTI_PUB          = _cfg.get("ANTI_PUB", False)
        self.bot.ANTI_MAJUSCULES   = _cfg.get("ANTI_MAJUSCULES", False)
        self.bot.ANTI_EMOJI        = _cfg.get("ANTI_EMOJI", False)
        self.bot.MAX_MENTIONS      = _cfg.get("MAX_MENTIONS", 5)
        self.bot.MOTS_INTERDITS    = _cfg.get("MOTS_INTERDITS", [])
        self.bot.SALONS_EXCLUS_SECU = set(_cfg.get("SALONS_EXCLUS_SECU", []))
        print(f"[Securite] Config chargée — antilien={self.bot.ANTI_LIEN} antipub={self.bot.ANTI_PUB} mots={len(self.bot.MOTS_INTERDITS)}")

    def _save(self):
        _save_secu({
            "ANTI_LIEN":          self.bot.ANTI_LIEN,
            "ANTI_PUB":           self.bot.ANTI_PUB,
            "ANTI_MAJUSCULES":    self.bot.ANTI_MAJUSCULES,
            "ANTI_EMOJI":         self.bot.ANTI_EMOJI,
            "MAX_MENTIONS":       self.bot.MAX_MENTIONS,
            "MOTS_INTERDITS":     self.bot.MOTS_INTERDITS,
            "SALONS_EXCLUS_SECU": list(self.bot.SALONS_EXCLUS_SECU),
        })

    @commands.command()
    async def secu(self, ctx):
        e = discord.Embed(title="🔒 Configuration Sécurité", color=0x3498db, timestamp=datetime.now(timezone.utc))
        e.add_field(name="🔗 Anti-lien", value="✅ Activé" if self.bot.ANTI_LIEN else "❌ Désactivé", inline=True)
        e.add_field(name="📢 Anti-pub", value="✅ Activé" if self.bot.ANTI_PUB else "❌ Désactivé", inline=True)
        e.add_field(name="🔠 Anti-majuscules", value="✅ Activé" if self.bot.ANTI_MAJUSCULES else "❌ Désactivé", inline=True)
        e.add_field(name="😀 Anti-emoji spam", value="✅ Activé" if self.bot.ANTI_EMOJI else "❌ Désactivé", inline=True)
        e.add_field(name="👥 Max mentions", value=f"`{self.bot.MAX_MENTIONS}`", inline=True)
        e.add_field(name="🚫 Mots interdits", value=f"`{len(self.bot.MOTS_INTERDITS)}`", inline=True)
        e.set_footer(text=f"Demandé par {ctx.author.name}")
        await ctx.send(embed=e)

    @commands.command()
    async def antilien(self, ctx):
        self.bot.ANTI_LIEN = not self.bot.ANTI_LIEN
        self._save()
        status = "activé ✅" if self.bot.ANTI_LIEN else "désactivé ❌"
        await ctx.send(embed=embed_success("Anti-lien", f"L'anti-lien est maintenant **{status}**."))

    @commands.command()
    async def antipub(self, ctx):
        self.bot.ANTI_PUB = not self.bot.ANTI_PUB
        self._save()
        status = "activé ✅" if self.bot.ANTI_PUB else "désactivé ❌"
        await ctx.send(embed=embed_success("Anti-pub", f"L'anti-pub est maintenant **{status}**."))

    @commands.command()
    async def antimaj(self, ctx):
        self.bot.ANTI_MAJUSCULES = not self.bot.ANTI_MAJUSCULES
        self._save()
        status = "activé ✅" if self.bot.ANTI_MAJUSCULES else "désactivé ❌"
        await ctx.send(embed=embed_success("Anti-majuscules", f"L'anti-majuscules est maintenant **{status}**."))

    @commands.command()
    async def antiemoji(self, ctx):
        self.bot.ANTI_EMOJI = not self.bot.ANTI_EMOJI
        self._save()
        status = "activé ✅" if self.bot.ANTI_EMOJI else "désactivé ❌"
        await ctx.send(embed=embed_success("Anti-emoji spam", f"L'anti-emoji spam est maintenant **{status}**."))

    @commands.command()
    async def setmaxmentions(self, ctx, nombre: int):
        self.bot.MAX_MENTIONS = nombre
        self._save()
        await ctx.send(embed=embed_success("Max mentions", f"Le maximum de mentions par message est maintenant **{nombre}**."))

    @commands.command()
    async def addmot(self, ctx, *, mot):
        self.bot.MOTS_INTERDITS.append(mot.lower())
        self._save()
        await ctx.send(embed=embed_success("Mot interdit ajouté", f"Le mot **{mot}** a été ajouté à la liste."))

    @commands.command()
    async def removemot(self, ctx, *, mot):
        if mot.lower() in self.bot.MOTS_INTERDITS:
            self.bot.MOTS_INTERDITS.remove(mot.lower())
            self._save()
            await ctx.send(embed=embed_success("Mot retiré", f"Le mot **{mot}** a été retiré de la liste."))
        else:
            await ctx.send(embed=embed_error("Introuvable", f"Le mot **{mot}** n'est pas dans la liste."))

    @commands.command()
    async def listmots(self, ctx):
        if not self.bot.MOTS_INTERDITS:
            return await ctx.send(embed=embed_info("Mots interdits", "Aucun mot interdit configuré."))
        mots = "\n".join([f"• `{m}`" for m in self.bot.MOTS_INTERDITS])
        await ctx.send(embed=embed_info(f"🚫 Mots interdits ({len(self.bot.MOTS_INTERDITS)})", mots))

    @commands.command()
    async def excludesecu(self, ctx, salon: discord.TextChannel = None):
        salon = salon or ctx.channel
        if salon.id in self.bot.SALONS_EXCLUS_SECU:
            self.bot.SALONS_EXCLUS_SECU.discard(salon.id)
            self._save()
            await ctx.send(embed=embed_success("Sécurité réactivée", f"La sécurité est de nouveau active dans {salon.mention}."))
        else:
            self.bot.SALONS_EXCLUS_SECU.add(salon.id)
            self._save()
            await ctx.send(embed=embed_success("Salon exclu", f"La sécurité est désactivée dans {salon.mention}."))

    # ——— EVENTS ———
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.author.id in self.bot.PERSONNES_REPONSES:
            await message.channel.send(self.bot.PERSONNES_REPONSES[message.author.id])

        if self.bot.user in message.mentions and not message.mention_everyone:
            if message.author.id not in self.bot.BOT_ADMINS:
                await message.channel.send(embed=embed_info("Préfixe", "Mon préfixe est `!`"))

        if message.guild:
            admin_member = message.guild.get_member(self.bot.ADMIN_ID)
            if admin_member and admin_member in message.mentions and message.author.id != self.bot.ADMIN_ID:
                await message.channel.send(f"😤 Il n'a pas ton temps fdp !")

        for mention in message.mentions:
            if mention.id in self.bot.afk_users:
                afk_msg, afk_time = self.bot.afk_users[mention.id]
                e = discord.Embed(title="💤 Utilisateur AFK", color=0x95a5a6)
                e.add_field(name="Message", value=afk_msg)
                e.add_field(name="Depuis", value=afk_time.strftime("%H:%M"))
                e.set_thumbnail(url=mention.display_avatar.url)
                await message.channel.send(embed=e)

        if message.author.id in self.bot.afk_users:
            del self.bot.afk_users[message.author.id]
            await message.channel.send(embed=embed_success("Retour d'AFK", f"{message.author.mention} n'est plus AFK !"))

        if message.guild and message.channel.id not in self.bot.SALONS_EXCLUS_SECU:
            membre = message.author
            contenu = message.content
            if membre.id not in self.bot.BOT_ADMINS and membre.id not in self.bot.whitelist:
                if self.bot.ANTI_LIEN and ("http://" in contenu or "https://" in contenu or "www." in contenu):
                    await message.delete()
                    msg = await message.channel.send(embed=embed_error("Lien interdit", f"{membre.mention} les liens sont interdits ici !"))
                    await msg.delete(delay=3)
                    return
                if self.bot.ANTI_PUB and "discord.gg/" in contenu.lower():
                    await message.delete()
                    msg = await message.channel.send(embed=embed_error("Pub interdite", f"{membre.mention} la publicité Discord est interdite !"))
                    await msg.delete(delay=3)
                    return
                if self.bot.ANTI_MAJUSCULES and len(contenu) > 10:
                    nb_maj = sum(1 for c in contenu if c.isupper())
                    if nb_maj / len(contenu) > 0.7:
                        await message.delete()
                        msg = await message.channel.send(embed=embed_error("Majuscules", f"{membre.mention} arrête d'écrire en majuscules !"))
                        await msg.delete(delay=3)
                        return
                if self.bot.ANTI_EMOJI:
                    emojis = re.findall(r'[\U00010000-\U0010ffff]|<a?:\w+:\d+>', contenu)
                    if len(emojis) > 5:
                        await message.delete()
                        msg = await message.channel.send(embed=embed_error("Emoji spam", f"{membre.mention} trop d'emojis dans ton message !"))
                        await msg.delete(delay=3)
                        return
                if len(message.mentions) > self.bot.MAX_MENTIONS:
                    await message.delete()
                    role = discord.utils.get(message.guild.roles, name="Muted")
                    if not role:
                        role = await message.guild.create_role(name="Muted")
                        for channel in message.guild.channels:
                            await channel.set_permissions(role, send_messages=False, speak=False)
                    await membre.add_roles(role)
                    msg = await message.channel.send(embed=embed_error("Mention spam", f"{membre.mention} muté pour spam de mentions !"))
                    await msg.delete(delay=5)
                    await asyncio.sleep(300)
                    await membre.remove_roles(role)
                    return
                if self.bot.MOTS_INTERDITS and any(mot in contenu.lower() for mot in self.bot.MOTS_INTERDITS):
                    await message.delete()
                    msg = await message.channel.send(embed=embed_error("Mot interdit", f"{membre.mention} ce mot est interdit ici !"))
                    await msg.delete(delay=3)
                    return

        user_id = message.author.id
        if user_id not in self.bot.spam_muted and user_id not in self.bot.BOT_ADMINS and user_id not in self.bot.whitelist:
            now = time.time()
            self.bot.spam_tracker[user_id].append(now)
            self.bot.spam_tracker[user_id] = [t for t in self.bot.spam_tracker[user_id] if now - t <= 4]
            if len(self.bot.spam_tracker[user_id]) >= 5:
                self.bot.spam_muted.add(user_id)
                self.bot.spam_tracker[user_id] = []
                guild = message.guild
                membre = message.author
                role = discord.utils.get(guild.roles, name="Muted")
                if not role:
                    role = await guild.create_role(name="Muted")
                    for channel in guild.channels:
                        await channel.set_permissions(role, send_messages=False, speak=False, add_reactions=False)
                await membre.add_roles(role)
                await message.channel.send(embed=embed_error("Anti-spam", f"{membre.mention} muté **10 minutes** pour spam !"))
                try:
                    await membre.send(embed=embed_error("Tu as été muté", f"Tu as été muté **10 minutes** sur **{guild.name}** pour spam."))
                except:
                    pass
                await asyncio.sleep(600)
                await membre.remove_roles(role)
                self.bot.spam_muted.discard(user_id)
                await message.channel.send(embed=embed_success("Unmute automatique", f"{membre.mention} est de nouveau libre de parler."))

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.id in self.bot.blacklist:
            try:
                await member.ban(reason=f"Blacklist : {self.bot.blacklist[member.id]}")
            except:
                pass
            return

        if self.bot.WELCOME_CHANNEL_ID:
            channel = self.bot.get_channel(self.bot.WELCOME_CHANNEL_ID)
            if channel:
                e = discord.Embed(
                    title="👋 Bienvenue !",
                    description=f"Bienvenue sur **{member.guild.name}**, {member.mention} !\nNous sommes maintenant **{member.guild.member_count}** membres.",
                    color=0x2ecc71,
                    timestamp=datetime.now(timezone.utc)
                )
                e.set_thumbnail(url=member.display_avatar.url)
                e.set_footer(text=f"Compte créé le {member.created_at.strftime('%d/%m/%Y')}")
                await channel.send(embed=e)

        if self.bot.AUTO_ROLES:
            for role_id in self.bot.AUTO_ROLES:
                role = member.guild.get_role(role_id)
                if role:
                    try:
                        await member.add_roles(role)
                    except:
                        pass

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if self.bot.WELCOME_CHANNEL_ID:
            channel = self.bot.get_channel(self.bot.WELCOME_CHANNEL_ID)
            if channel:
                e = discord.Embed(
                    title="👋 Au revoir !",
                    description=f"**{member.name}** vient de quitter le serveur.\nIl reste **{member.guild.member_count}** membres.",
                    color=0xe74c3c,
                    timestamp=datetime.now(timezone.utc)
                )
                e.set_thumbnail(url=member.display_avatar.url)
                await channel.send(embed=e)

async def setup(bot):
    await bot.add_cog(Securite(bot))
