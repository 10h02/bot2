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

  # ——— BACKUP ———
    @commands.command()
    @commands.has_permissions(administrator=True)
    async def backup(self, ctx):
        await ctx.send("⏳ Création du backup en cours...")
        guild = ctx.guild
        data = {
            "nom": guild.name,
            "description": guild.description or "",
            "roles": [],
            "categories": [],
            "salons": []
        }

        # Sauvegarder les rôles
        for role in guild.roles:
            if role.name == "@everyone":
                continue
            data["roles"].append({
                "nom": role.name,
                "couleur": role.color.value,
                "hoist": role.hoist,
                "mentionable": role.mentionable,
                "permissions": role.permissions.value,
                "position": role.position
            })

        # Sauvegarder les catégories
        for category in guild.categories:
            cat_data = {
                "nom": category.name,
                "position": category.position,
                "permissions": []
            }
            for target, overwrite in category.overwrites.items():
                if isinstance(target, discord.Role):
                    cat_data["permissions"].append({
                        "type": "role",
                        "nom": target.name,
                        "allow": overwrite.pair()[0].value,
                        "deny": overwrite.pair()[1].value
                    })
            data["categories"].append(cat_data)

        # Sauvegarder les salons
        for channel in guild.channels:
            if isinstance(channel, discord.CategoryChannel):
                continue
            salon_data = {
                "nom": channel.name,
                "type": str(channel.type),
                "position": channel.position,
                "categorie": channel.category.name if channel.category else None,
                "permissions": []
            }
            if isinstance(channel, discord.TextChannel):
                salon_data["slowmode"] = channel.slowmode_delay
                salon_data["nsfw"] = channel.is_nsfw()
                salon_data["topic"] = channel.topic or ""
            if isinstance(channel, discord.VoiceChannel):
                salon_data["bitrate"] = channel.bitrate
                salon_data["user_limit"] = channel.user_limit
            for target, overwrite in channel.overwrites.items():
                if isinstance(target, discord.Role):
                    salon_data["permissions"].append({
                        "type": "role",
                        "nom": target.name,
                        "allow": overwrite.pair()[0].value,
                        "deny": overwrite.pair()[1].value
                    })
            data["salons"].append(salon_data)

        # Sauvegarder dans un fichier JSON
        nom_fichier = f"backup_{guild.name}_{ctx.message.created_at.strftime('%d-%m-%Y_%H-%M')}.json"
        with open(nom_fichier, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        await ctx.send(f"✅ Backup créé avec **{len(data['roles'])}** rôles, **{len(data['categories'])}** catégories et **{len(data['salons'])}** salons !", file=discord.File(nom_fichier))
        os.remove(nom_fichier)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def loadbackup(self, ctx):
        if not ctx.message.attachments:
            await ctx.send("❌ Attache un fichier backup `.json` à ton message !")
            return

        attachment = ctx.message.attachments[0]
        if not attachment.filename.endswith(".json"):
            await ctx.send("❌ Le fichier doit être un `.json` !")
            return

        await ctx.send("⏳ Chargement du backup en cours... ça peut prendre du temps !")
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                content = await resp.text()
        data = json.loads(content)
        guild = ctx.guild

        # Supprimer les anciens rôles
        for role in guild.roles:
            if role.name != "@everyone" and role < guild.me.top_role:
                try:
                    await role.delete()
                    await asyncio.sleep(0.5)
                except:
                    pass

        # Supprimer les anciens salons
        for channel in guild.channels:
            try:
                await channel.delete()
                await asyncio.sleep(0.3)
            except:
                pass

        # Recréer les rôles
        roles_map = {}
        for role_data in sorted(data["roles"], key=lambda r: r["position"]):
            try:
                new_role = await guild.create_role(
                    name=role_data["nom"],
                    color=discord.Color(role_data["couleur"]),
                    hoist=role_data["hoist"],
                    mentionable=role_data["mentionable"],
                    permissions=discord.Permissions(role_data["permissions"])
                )
                roles_map[role_data["nom"]] = new_role
                await asyncio.sleep(0.5)
            except:
                pass

        # Recréer les catégories
        categories_map = {}
        for cat_data in sorted(data["categories"], key=lambda c: c["position"]):
            try:
                overwrites = {}
                for perm in cat_data["permissions"]:
                    if perm["type"] == "role" and perm["nom"] in roles_map:
                        role = roles_map[perm["nom"]]
                        overwrites[role] = discord.PermissionOverwrite.from_pair(
                            discord.Permissions(perm["allow"]),
                            discord.Permissions(perm["deny"])
                        )
                new_cat = await guild.create_category(cat_data["nom"], overwrites=overwrites)
                categories_map[cat_data["nom"]] = new_cat
                await asyncio.sleep(0.5)
            except:
                pass

        # Recréer les salons
        for salon_data in sorted(data["salons"], key=lambda s: s["position"]):
            try:
                overwrites = {}
                for perm in salon_data["permissions"]:
                    if perm["type"] == "role" and perm["nom"] in roles_map:
                        role = roles_map[perm["nom"]]
                        overwrites[role] = discord.PermissionOverwrite.from_pair(
                            discord.Permissions(perm["allow"]),
                            discord.Permissions(perm["deny"])
                        )
                categorie = categories_map.get(salon_data["categorie"]) if salon_data["categorie"] else None

                if salon_data["type"] == "text":
                    await guild.create_text_channel(
                        salon_data["nom"],
                        category=categorie,
                        slowmode_delay=salon_data.get("slowmode", 0),
                        nsfw=salon_data.get("nsfw", False),
                        topic=salon_data.get("topic", ""),
                        overwrites=overwrites
                    )
                elif salon_data["type"] == "voice":
                    await guild.create_voice_channel(
                        salon_data["nom"],
                        category=categorie,
                        bitrate=salon_data.get("bitrate", 64000),
                        user_limit=salon_data.get("user_limit", 0),
                        overwrites=overwrites
                    )
                await asyncio.sleep(0.3)
            except:
                pass

        # Trouver un salon pour envoyer la confirmation
        for channel in guild.text_channels:
            try:
                await channel.send(f"✅ Backup chargé ! **{len(data['roles'])}** rôles, **{len(data['categories'])}** catégories et **{len(data['salons'])}** salons recréés !")
                break
            except:
                pass

async def setup(bot):
    await bot.add_cog(Gestion(bot))
