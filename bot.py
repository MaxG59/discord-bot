from keep_alive import keep_alive

keep_alive()

import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", help_command=None, intents=intents, case_insensitive=True)

user_data = {}

# Seviyeye göre verilecek roller
level_roles = {
    2: 11372940201378185417,   # 2. seviye rol ID
    3: 1372940171359555697,
    4: 1372940107769712681,
    5: 1372940049578065932,
    6: 1372939928077602816
}

@bot.event
async def on_ready():
    print(f'Bot {bot.user} olarak giriş yaptı.')

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = str(message.author.id)
    if user_id not in user_data:
        user_data[user_id] = {"xp": 0, "level": 1}

    user_data[user_id]["xp"] += 10
    xp = user_data[user_id]["xp"]
    level = user_data[user_id]["level"]
    xp_needed = 100 + (level - 1) * 150

    if xp >= xp_needed:
        user_data[user_id]["level"] += 1
        user_data[user_id]["xp"] = xp - xp_needed
        new_level = user_data[user_id]["level"]

        guild = message.guild
        member = guild.get_member(message.author.id)

        if member:
            # Yeni rolü ver
            if new_level in level_roles:
                new_role = guild.get_role(level_roles[new_level])
                if new_role and new_role not in member.roles:
                    await member.add_roles(new_role)

            # Önceki seviyedeki rolü al
            previous_level = new_level - 1
            if previous_level in level_roles:
                old_role = guild.get_role(level_roles[previous_level])
                if old_role and old_role in member.roles:
                    await member.remove_roles(old_role)

        await message.channel.send(f"{message.author.mention}, Seviye atladın! Yeni seviyen: **{new_level}** 🎉")

    await bot.process_commands(message)

# KOMUTLAR

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📘 Komut Listesi", color=discord.Color.green())
    embed.add_field(name="Genel Komutlar", value="`!sa`, `!bb`, `!dc`, `!profil`, `!rank`, `!levels`", inline=False)
    embed.add_field(name="Moderasyon Komutları", value="`!temizle`, `!kick`, `!ban`, `!unban`", inline=False)
    embed.add_field(name="Eğlence Komutları", value="`!zar`, `!yazıtura`, `!espri`, `!8ball`", inline=False)
    embed.set_footer(text="🔹 Daha fazla özellik yakında!")
    await ctx.send(embed=embed)

@bot.command()
async def sa(ctx):
    await ctx.send(f'{ctx.author.mention} Aleyküm selam, hoş geldin!')

@bot.command()
async def bb(ctx):
    await ctx.send(f'Hoşçakal {ctx.author.mention}, yine bekleriz!')

@bot.command()
async def dc(ctx):
    await ctx.send('Sunucu Davet Linki: https://discord.gg/6cuBvGVJxu')

@bot.command()
@commands.has_permissions(manage_messages=True)
async def temizle(ctx, miktar: int):
    await ctx.channel.purge(limit=miktar + 1)
    await ctx.send(f"{miktar} mesaj silindi.", delete_after=3)

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f"{member.mention} sunucudan atıldı.")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"{member.mention} sunucudan yasaklandı.")

@bot.command()
@commands.has_permissions(ban_members=True)
async def unban(ctx, *, user_name):
    banned_users = await ctx.guild.bans()
    for ban_entry in banned_users:
        user = ban_entry.user
        if user.name == user_name:
            await ctx.guild.unban(user)
            await ctx.send(f"{user.name} adlı kişinin yasağı kaldırıldı.")
            return
    await ctx.send("Bu kullanıcı yasaklı değil.")

@bot.command()
async def sunucu(ctx):
    guild = ctx.guild
    embed = discord.Embed(title="📊 Sunucu Bilgileri", color=discord.Color.orange())
    embed.set_thumbnail(url=guild.icon.url if guild.icon else "")
    embed.add_field(name="• Sunucu Adı", value=guild.name, inline=True)
    embed.add_field(name="• Üye Sayısı", value=guild.member_count, inline=True)
    embed.add_field(name="• Oluşturulma Tarihi", value=guild.created_at.strftime("%d.%m.%Y %H:%M"), inline=True)
    embed.add_field(name="• Sahip", value=guild.owner, inline=True)
    embed.set_footer(text=f"ID: {guild.id}")
    await ctx.send(embed=embed)

@bot.command()
async def kullanıcı(ctx, member: discord.Member = None):
    member = member or ctx.author
    embed = discord.Embed(title=f"👤 Kullanıcı Bilgisi: {member}", color=discord.Color.green())
    embed.set_thumbnail(url=member.avatar.url if member.avatar else "")
    embed.add_field(name="• Ad", value=member.name, inline=True)
    embed.add_field(name="• Takma Ad", value=member.display_name, inline=True)
    embed.add_field(name="• Katılım Tarihi", value=member.joined_at.strftime("%d.%m.%Y"), inline=True)
    embed.add_field(name="• Rol Sayısı", value=len(member.roles) - 1, inline=True)
    embed.set_footer(text=f"ID: {member.id}")
    await ctx.send(embed=embed)

@bot.command()
async def rolsay(ctx):
    msg = "**🎭 Rol Bazlı Üye Sayısı:**\n\n"
    for role in ctx.guild.roles[::-1]:
        if role.name != "@everyone":
            count = len(role.members)
            if count > 0:
                msg += f"{role.name}: `{count}`\n"
    await ctx.send(msg)

@bot.command()
async def rank(ctx):
    user_id = str(ctx.author.id)
    if user_id not in user_data:
        user_data[user_id] = {"xp": 0, "level": 1}

    level = user_data[user_id]["level"]
    xp = user_data[user_id]["xp"]
    xp_needed = 100 + (level - 1) * 150

    sorted_users = sorted(user_data.items(), key=lambda x: (x[1]["level"], x[1]["xp"]), reverse=True)
    rank = next((i + 1 for i, (uid, _) in enumerate(sorted_users) if uid == user_id), None)

    width, height = 750, 220
    img = Image.new("RGB", (width, height), color=(30, 30, 30))
    draw = ImageDraw.Draw(img)
    progress = int((xp / xp_needed) * 500)

    draw.rounded_rectangle([150, 130, 670, 160], 10, fill=(50, 50, 50))
    draw.rounded_rectangle([150, 130, 150 + progress, 160], 10, fill=(0, 200, 0))

    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except IOError:
        font = ImageFont.load_default()

    draw.text((150, 90), f"{ctx.author.name}", font=font, fill=(255, 255, 255))
    draw.text((500, 30), f"RÜTBE #{rank} | SEVİYE {level}", font=font, fill=(255, 255, 255))
    draw.text((550, 100), f"{xp}/{xp_needed} XP", font=font, fill=(200, 200, 200))

    avatar_bytes = await ctx.author.avatar.read()
    avatar = Image.open(BytesIO(avatar_bytes)).resize((120, 120)).convert("RGBA")

    mask = Image.new("L", (120, 120), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, 120, 120), fill=255)
    avatar.putalpha(mask)

    img.paste(avatar, (20, 50), avatar)

    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    await ctx.send(file=discord.File(fp=buffer, filename="rank.png"))

@bot.command()
async def levels(ctx):
    if not user_data:
        await ctx.send("Henüz kayıtlı kullanıcı yok.")
        return

    sorted_users = sorted(user_data.items(), key=lambda x: (x[1]["level"], x[1]["xp"]), reverse=True)
    top_users = sorted_users[:10]

    leaderboard = ""
    for i, (user_id, data) in enumerate(top_users, start=1):
        member = ctx.guild.get_member(int(user_id))
        if member:
            leaderboard += f"**#{i}** | {member.mention} XP: **{data['xp']}**\n"

    embed = discord.Embed(
        title="Lonca Puan Liderlik Tabloları",
        description=f":speech_balloon: **TEXT SCORE [1/1]**\n\n{leaderboard}",
        color=discord.Color.purple()
    )
    if ctx.guild.icon:
        embed.set_author(name="Lonca Puan Liderlik Tabloları", icon_url=ctx.guild.icon.url)
    else:
        embed.set_author(name="Lonca Puan Liderlik Tabloları")

    embed.set_footer(text="🔹 En aktif kullanıcılar burada listelenir.")
    await ctx.send(embed=embed)
