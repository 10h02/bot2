import discord
from discord.ext import commands
from datetime import datetime, timezone
import asyncio
import random
import yt_dlp

def embed_success(titre, description):
    return discord.Embed(title=f"✅ {titre}", description=description, color=0x2ecc71, timestamp=datetime.now(timezone.utc))

def embed_error(titre, description):
    return discord.Embed(title=f"❌ {titre}", description=description, color=0xe74c3c, timestamp=datetime.now(timezone.utc))

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queues = {}

    # ——— FUN ———
    @commands.command()
    async def ping(self, ctx):
        latence = round(self.bot.latency * 1000)
        couleur = 0x2ecc71 if latence < 100 else 0xf39c12 if latence < 200 else 0xe74c3c
        e = discord.Embed(title="🏓 Pong !", color=couleur, timestamp=datetime.now(timezone.utc))
        e.add_field(name="Latence", value=f"`{latence}ms`")
        await ctx.send(embed=e)

    @commands.command()
    async def say(self, ctx, *, message):
        await ctx.message.delete()
        await ctx.send(message)

    @commands.command()
    async def embed(self, ctx, titre, *, description):
        e = discord.Embed(title=titre, description=description, color=0x7289da, timestamp=datetime.now(timezone.utc))
        e.set_footer(text=f"Demandé par {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=e)

    @commands.command()
    async def userinfo(self, ctx, membre: discord.Member = None):
        membre = membre or ctx.author
        roles = [r.mention for r in membre.roles[1:]]
        e = discord.Embed(title=f"👤 {membre.name}", color=membre.color, timestamp=datetime.now(timezone.utc))
        e.add_field(name="ID", value=f"`{membre.id}`", inline=True)
        e.add_field(name="Surnom", value=membre.nick or "Aucun", inline=True)
        e.add_field(name="Bot", value="Oui" if membre.bot else "Non", inline=True)
        e.add_field(name="Compte créé le", value=membre.created_at.strftime("%d/%m/%Y"), inline=True)
        e.add_field(name="A rejoint le", value=membre.joined_at.strftime("%d/%m/%Y"), inline=True)
        e.add_field(name=f"Rôles ({len(roles)})", value=", ".join(roles) if roles else "Aucun", inline=False)
        e.set_thumbnail(url=membre.display_avatar.url)
        e.set_footer(text=f"Demandé par {ctx.author.name}")
        await ctx.send(embed=e)

    @commands.command()
    async def serverinfo(self, ctx):
        guild = ctx.guild
        e = discord.Embed(title=f"🏠 {guild.name}", color=0x7289da, timestamp=datetime.now(timezone.utc))
        e.add_field(name="Membres", value=f"`{guild.member_count}`", inline=True)
        e.add_field(name="Salons", value=f"`{len(guild.channels)}`", inline=True)
        e.add_field(name="Rôles", value=f"`{len(guild.roles)}`", inline=True)
        e.add_field(name="Créé le", value=guild.created_at.strftime("%d/%m/%Y"), inline=True)
        e.add_field(name="Propriétaire", value=guild.owner.mention if guild.owner else "Inconnu", inline=True)
        e.add_field(name="Boosts", value=f"`{guild.premium_subscription_count}`", inline=True)
        if guild.icon:
            e.set_thumbnail(url=guild.icon.url)
        e.set_footer(text=f"ID : {guild.id}")
        await ctx.send(embed=e)

    @commands.command()
    async def roll(self, ctx, maximum: int = 100):
        resultat = random.randint(1, maximum)
        e = discord.Embed(title="🎲 Lancer de dé", color=0x9b59b6, timestamp=datetime.now(timezone.utc))
        e.add_field(name="Résultat", value=f"**{resultat}** / {maximum}")
        e.set_footer(text=f"Lancé par {ctx.author.name}")
        await ctx.send(embed=e)

    @commands.command()
    async def flip(self, ctx):
        resultat = random.choice(["Pile", "Face"])
        emoji = "🌕" if resultat == "Pile" else "🌑"
        e = discord.Embed(title=f"{emoji} Pile ou Face", description=f"Résultat : **{resultat}**", color=0xf1c40f, timestamp=datetime.now(timezone.utc))
        e.set_footer(text=f"Lancé par {ctx.author.name}")
        await ctx.send(embed=e)

    @commands.command()
    async def afk(self, ctx, *, message="AFK"):
        self.bot.afk_users[ctx.author.id] = (message, datetime.now(timezone.utc))
        e = discord.Embed(title="💤 Mode AFK activé", description=f"{ctx.author.mention} est maintenant AFK.", color=0x95a5a6, timestamp=datetime.now(timezone.utc))
        e.add_field(name="Message", value=message)
        e.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=e)

    @commands.command()
    async def avatar(self, ctx, membre: discord.Member = None):
        membre = membre or ctx.author
        e = discord.Embed(title=f"🖼️ Avatar de {membre.name}", color=membre.color, timestamp=datetime.now(timezone.utc))
        e.set_image(url=membre.display_avatar.url)
        e.set_footer(text=f"Demandé par {ctx.author.name}")
        await ctx.send(embed=e)

    @commands.command()
    async def quit(self, ctx):
        await ctx.send(embed=embed_success("Au revoir !", f"Le bot quitte **{ctx.guild.name}**..."))
        await asyncio.sleep(1)
        await ctx.guild.leave()

    # ——— MUSIQUE ———
    @commands.command()
    async def join(self, ctx):
        if not ctx.author.voice:
            return await ctx.send(embed=embed_error("Erreur", "Tu dois être dans un salon vocal."))
        channel = ctx.author.voice.channel
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()
        await ctx.send(embed=embed_success("Connecté", f"Connecté à **{channel.name}**."))

    @commands.command()
    async def leave(self, ctx):
        if not ctx.voice_client:
            return await ctx.send(embed=embed_error("Erreur", "Je ne suis pas dans un salon vocal."))
        await ctx.voice_client.disconnect()
        await ctx.send(embed=embed_success("Déconnecté", "Déconnecté du salon vocal."))

    @commands.command()
    async def play(self, ctx, *, recherche):
        if not ctx.author.voice:
            return await ctx.send(embed=embed_error("Erreur", "Tu dois être dans un salon vocal."))
        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()
        guild_id = ctx.guild.id
        if guild_id not in self.queues:
            self.queues[guild_id] = []
        msg = await ctx.send(embed=discord.Embed(title="🔍 Recherche en cours...", description=f"Recherche de **{recherche}**...", color=0x3498db))
        try:
            with yt_dlp.YoutubeDL(self.bot.YDL_OPTIONS) as ydl:
                info = ydl.extract_info(recherche, download=False)
                if 'entries' in info:
                    info = info['entries'][0]
                url = info['url']
                titre = info.get('title', 'Inconnu')
                duree = info.get('duration', 0)
                mins, secs = divmod(duree, 60)
        except Exception as ex:
            return await msg.edit(embed=embed_error("Erreur", f"{ex}"))
        if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
            self.queues[guild_id].append((url, titre))
            e = discord.Embed(title="➕ Ajouté à la file", description=f"**{titre}**", color=0x3498db, timestamp=datetime.now(timezone.utc))
            e.add_field(name="Durée", value=f"`{mins}:{secs:02d}`")
            e.add_field(name="Position", value=f"`#{len(self.queues[guild_id])}`")
            await msg.edit(embed=e)
        else:
            e = discord.Embed(title="🎵 Lecture en cours", description=f"**{titre}**", color=0x1db954, timestamp=datetime.now(timezone.utc))
            e.add_field(name="Durée", value=f"`{mins}:{secs:02d}`")
            e.set_footer(text=f"Demandé par {ctx.author.name}")
            await msg.edit(embed=e)
            self._play_next(ctx, guild_id, url, titre)

    def _play_next(self, ctx, guild_id, url=None, titre=None):
        if url is None:
            if self.queues.get(guild_id):
                url, titre = self.queues[guild_id].pop(0)
            else:
                return
        source = discord.FFmpegPCMAudio(url, **self.bot.FFMPEG_OPTIONS)
        def after_play(error):
            if error:
                print(f"Erreur lecture : {error}")
            self._play_next(ctx, guild_id)
        ctx.voice_client.play(source, after=after_play)

    @commands.command()
    async def pause(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send(embed=discord.Embed(title="⏸️ Musique en pause", color=0xf39c12, timestamp=datetime.now(timezone.utc)))
        else:
            await ctx.send(embed=embed_error("Erreur", "Aucune musique en lecture."))

    @commands.command()
    async def resume(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send(embed=discord.Embed(title="▶️ Musique reprise", color=0x2ecc71, timestamp=datetime.now(timezone.utc)))
        else:
            await ctx.send(embed=embed_error("Erreur", "La musique n'est pas en pause."))

    @commands.command()
    async def stop(self, ctx):
        if ctx.voice_client:
            self.queues[ctx.guild.id] = []
            ctx.voice_client.stop()
            await ctx.send(embed=discord.Embed(title="⏹️ Musique stoppée", description="La file d'attente a été vidée.", color=0xe74c3c, timestamp=datetime.now(timezone.utc)))
        else:
            await ctx.send(embed=embed_error("Erreur", "Je ne suis pas dans un salon vocal."))

    @commands.command()
    async def skip(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send(embed=discord.Embed(title="⏭️ Musique skippée", color=0x3498db, timestamp=datetime.now(timezone.utc)))
        else:
            await ctx.send(embed=embed_error("Erreur", "Aucune musique en lecture."))

    @commands.command()
    async def queue(self, ctx):
        guild_id = ctx.guild.id
        if not self.queues.get(guild_id):
            return await ctx.send(embed=embed_error("File vide", "La file d'attente est vide."))
        e = discord.Embed(title="🎵 File d'attente", color=0x1db954, timestamp=datetime.now(timezone.utc))
        for i, (_, titre) in enumerate(self.queues[guild_id]):
            e.add_field(name=f"#{i+1}", value=titre, inline=False)
        await ctx.send(embed=e)

    @commands.command()
    async def volume(self, ctx, vol: int):
        if ctx.voice_client and ctx.voice_client.source:
            ctx.voice_client.source = discord.PCMVolumeTransformer(ctx.voice_client.source, volume=vol / 100)
            e = discord.Embed(title="🔊 Volume", description=f"Volume réglé à **{vol}%**", color=0x3498db, timestamp=datetime.now(timezone.utc))
            await ctx.send(embed=e)
        else:
            await ctx.send(embed=embed_error("Erreur", "Aucune musique en lecture."))

async def setup(bot):
    await bot.add_cog(Fun(bot))
