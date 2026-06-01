import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
from collections import defaultdict

load_dotenv(".env")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix=["!"], intents=intents, help_command=None)

bot.ADMIN_ID = 1463705858541097063
bot.BOT_ADMINS = {1463705858541097063}
bot.whitelist = set()
bot.warnings = {}
bot.afk_users = {}
bot.tickets = {}
bot.TICKET_CATEGORY_NAME = "TICKETS"
bot.blacklist = {}
bot.AUTO_ROLES = []
bot.WELCOME_CHANNEL_ID = None
bot.spam_tracker = defaultdict(list)
bot.spam_muted = set()

bot.ANTI_LIEN = False
bot.ANTI_PUB = False
bot.ANTI_MAJUSCULES = False
bot.ANTI_EMOJI = False
bot.MAX_MENTIONS = 5
bot.MOTS_INTERDITS = []
bot.SALONS_EXCLUS_SECU = set()

bot.YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch',
    'extract_flat': False,
}
bot.FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

@bot.check
async def verif_globale(ctx):
    if ctx.author.id in bot.BOT_ADMINS or ctx.author.id in bot.whitelist:
        return True
    await ctx.send("❌ Tu n'as pas accès aux commandes du bot.")
    return False

@bot.event
async def on_ready():
    print(f"✅ Bot connecté en tant que {bot.user}")
    print(f"📦 Cogs chargés : {[c for c in bot.cogs]}")

@bot.event
async def on_guild_join(guild):
    async for entry in guild.audit_logs(action=discord.AuditLogAction.bot_add, limit=1):
        if entry.user.id in bot.BOT_ADMINS:
            return
    await guild.leave()
    print(f"Serveur quitté : {guild.name} (pas invité par un bot admin)")

async def main():
    async with bot:
        cogs = [
            "cogs.moderation",
            "cogs.gestion",
            "cogs.fun",
            "cogs.securite",
            "cogs.avance",
            "cogs.tickets",
            "cogs.annonces",
            "cogs.extras",
        ]
        for cog in cogs:
            try:
                await bot.load_extension(cog)
                print(f"✅ {cog} chargé")
            except Exception as e:
                print(f"❌ Erreur chargement {cog} : {e}")
        await bot.start(os.getenv("DISCORD_TOKEN"))

asyncio.run(main())
