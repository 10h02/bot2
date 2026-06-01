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

class Gestion(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ——— SALONS ———
    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def lock(self, ctx, salon: discord.TextChannel = None):
        salon = salon or ctx.channel
        await salon.set_permissions(ctx.guild.default_role, send_messages=False)
        await ctx.send(embed=embed_success("Salon verrouillé", f"{salon.mention} est maintenant verrouillé."))

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def unlock(self, ctx, salon: discord.TextChannel = None):
        salon = salon or ctx.channel
        await salon.set_permissions(ctx.guild.default_role, send_messages=True)
        await ctx.send(embed=embed_success("Salon déverrouillé", f"{salon.mention} est maintenant ouvert."))

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def slowmode(self, ctx, secondes: int):
        await ctx.channel.edit(slowmode_delay=secondes)
        await ctx.send(embed=embed_success("Slowmode", f"Slowmode réglé à **{secondes} secondes** dans {ctx.channel.mention}."))

    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, nombre: int = 10):
        await ctx.channel.purge(limit=nombre + 1)
        msg = await ctx.send(embed=embed_success("Messages supprimés", f"**{nombre}** messages ont été supprimés."))
        await msg.delete(delay=3)

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def setsalon(self, ctx, salon: discord.TextChannel = None):
        salon = salon or ctx.channel
        self.bot.WELCOME_CHANNEL_ID = salon.id
        await ctx.send(embed=embed_success("Salon de bienvenue", f"Salon défini sur {salon.mention}."))

    # ——— RÔLES ———
    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def addrole(self, ctx, membre: discord.Member, role: discord.Role):
        await membre.add_roles(role)
        e = embed_success("Rôle ajouté", f"{role.mention} a été donné à {membre.mention}.")
        e.set_thumbnail(url=membre.display_avatar.url)
        await ctx.send(embed=e)

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def removerole(self, ctx, membre: discord.Member, role: discord.Role):
        await membre.remove_roles(role)
        e = embed_success("Rôle retiré", f"{role.mention} a été retiré de {membre.mention}.")
        e.set_thumbnail(url=membre.display_avatar.url)
        await ctx.send(embed=e)

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def createrole(self, ctx, *, nom):
        role = await ctx.guild.create_role(name=nom)
        await ctx.send(embed=embed_success("Rôle créé", f"Le rôle {role.mention} a été créé avec succès."))

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def delrole(self, ctx, role: discord.Role):
        nom = role.name
        await role.delete()
        await ctx.send(embed=embed_success("Rôle supprimé", f"Le rôle **{nom}** a été supprimé."))

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def autorole(self, ctx, role: discord.Role):
        if role.id in self.bot.AUTO_ROLES:
            self.bot.AUTO_ROLES.remove(role.id)
            await ctx.send(embed=embed_success("Auto-rôle retiré", f"{role.mention} ne sera plus attribué automatiquement."))
        else:
            self.bot.AUTO_ROLES.append(role.id)
            await ctx.send(embed=embed_success("Auto-rôle ajouté", f"{role.mention} sera attribué automatiquement aux nouveaux membres."))

    # ——— TICKETS ———
    @commands.command()
    async def ticket(self, ctx, *, sujet="Support"):
        category = discord.utils.get(ctx.guild.categories, name=self.bot.TICKET_CATEGORY_NAME)
        if not category:
            category = await ctx.guild.create_category(self.bot.TICKET_CATEGORY_NAME)
        overwrites = {
            ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            ctx.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        channel = await ctx.guild.create_text_channel(f"ticket-{ctx.author.name}", category=category, overwrites=overwrites)
        self.bot.tickets[channel.id] = ctx.author.id
        e = discord.Embed(
            title=f"🎫 Ticket ouvert — {sujet}",
            description=f"Bonjour {ctx.author.mention}, l'équipe va te répondre rapidement.\nUtilise `!closeticket` pour fermer ce ticket.",
            color=0x2ecc71,
            timestamp=datetime.now(timezone.utc)
        )
        e.set_footer(text=f"Ticket créé par {ctx.author.name}")
        e.set_thumbnail(url=ctx.author.display_avatar.url)
        await channel.send(embed=e)
        await ctx.send(embed=embed_success("Ticket créé", f"Ton ticket est disponible ici : {channel.mention}"))

    @commands.command()
    async def closeticket(self, ctx):
        if ctx.channel.id not in self.bot.tickets:
            return await ctx.send(embed=embed_error("Erreur", "Ce salon n'est pas un ticket."))
        e = embed_info("Fermeture du ticket", "Ce ticket sera fermé dans **5 secondes**...")
        await ctx.send(embed=e)
        await asyncio.sleep(5)
        await ctx.channel.delete()

    # ——— ANNONCE ———
    @commands.command()
    async def annonce(self, ctx, salon: discord.TextChannel, *, message):
        e = discord.Embed(
            description=message,
            color=0xf1c40f,
            timestamp=datetime.now(timezone.utc)
        )
        e.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        e.set_footer(text=ctx.guild.name, icon_url=ctx.guild.icon.url if ctx.guild.icon else discord.Embed.Empty)
        await salon.send(embed=e)
        await ctx.send(embed=embed_success("Annonce envoyée", f"L'annonce a été publiée dans {salon.mention}."))

    # ——— SONDAGE ———
    @commands.command()
    async def sondage(self, ctx, *, question):
        e = discord.Embed(
            title="📊 Sondage",
            description=question,
            color=0x9b59b6,
            timestamp=datetime.now(timezone.utc)
        )
        e.set_footer(text=f"Sondage créé par {ctx.author.name}", icon_url=ctx.author.display_avatar.url)
        msg = await ctx.send(embed=e)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

    # ——— GIVE ROLE ALL ———
    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def giveroleall(self, ctx, role: discord.Role):
        msg = await ctx.send(embed=embed_info("En cours...", f"Attribution de {role.mention} à tous les membres..."))
        count = 0
        for membre in ctx.guild.members:
            try:
                await membre.add_roles(role)
                count += 1
            except:
                pass
        await msg.edit(embed=embed_success("Rôle distribué", f"{role.mention} donné à **{count}** membres."))

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def removeroleall(self, ctx, role: discord.Role):
        msg = await ctx.send(embed=embed_info("En cours...", f"Retrait de {role.mention} à tous les membres..."))
        count = 0
        for membre in ctx.guild.members:
            try:
                await membre.remove_roles(role)
                count += 1
            except:
                pass
        await msg.edit(embed=embed_success("Rôle retiré", f"{role.mention} retiré de **{count}** membres."))

async def setup(bot):
    await bot.add_cog(Gestion(bot))
