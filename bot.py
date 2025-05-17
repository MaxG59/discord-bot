import discord
from discord.ext import commands
import re
import asyncio
from collections import defaultdict
from discord.ui import Select, View
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

#----------------------- BOT INTENTLERI --------------------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

#----------------------- BOT TOKENI VE SUNUCU ID -----------------------

#----------------------- BOT NESNESI OLUŞTURMA --------------------------
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

#----------------------- GLOBAL DEĞİŞKENLER ----------------------------
user_warn_count = {}
user_warnings = {}
MUTE_DURATION_SECONDS = 2 * 60 * 60  # 2 saat
MUTE_ROLE_NAME = "Susturuldu"

forbidden_words = ["amk", "sg", "oc", "skm", "amcık", "oç", "siktir", "yarrak", "am", "piç", "amcı", "pipi", "orospu", "göt", "kahpe", "şerefsiz", "ananı", "mal", "gerizekalı", "aptal", "pezevenk", "puşt", "sikik", "oe", "porno", "gay", "lezbiyen", "travesti", "sikerim", "aq", "aw", "sikik"]
invite_pattern = re.compile(r"(discord\.gg/|discord\.com/invite/)")

FLOOD_LIMIT = 5
FLOOD_MSG_COUNT = 3
user_message_times = {}

warnings = defaultdict(list)

LOG_CHANNEL_ID = 1372936287488573480

#----------------------- BOT HAZIR OLAYI --------------------------------
@bot.event
async def on_ready():
    print(f"{bot.user} başarıyla giriş yaptı!")

#----------------------- ÜYE SUNUCUDA KATILDIĞINDA ---------------------
@bot.event
async def on_member_join(member):
    rol = discord.utils.get(member.guild.roles, name="Üye")
    if rol:
        await member.add_roles(rol)

#----------------------- ÜYE SUNUCUDAN AYRILDIĞINDA --------------------
@bot.event
async def on_member_remove(member):
    kanal = discord.utils.get(member.guild.text_channels, name="gideni-görme")
    if kanal:
        await kanal.send(f"**{member.name}** ayrıldı **S2GEsports** Bye Bye **{member.name}**...")

#----------------------- UYARI VE XP & LEVEL SISTEMI --------------------

level_roles = {
    2: 1372940201378185417,
    15: 820231840921157642,
    25: 820234560137592853,
    40: 820232958996381697,
    50: 820234739247349780
}

user_data = {}  # global veri saklama


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = message.author.id
    guild = message.guild
    if guild is None:
        return  # DM'de işlem yapma

    member = guild.get_member(user_id)
    if member is None:
        return

    content = message.content.lower()

    # --- Yasaklı kelime filtresi ---
    for word in forbidden_words:
        if word.strip() != "":
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, content, re.IGNORECASE):
                await message.delete()
                await user_warn(message, "Yasaklı kelime kullanımı")
                await log_warn(message, bot.user, "Yasaklı kelime kullanımı")
                return

    # --- Büyük harf spam engelleme ---
    if len(content) >= 10:
        uppercase_count = sum(1 for c in message.content if c.isupper())
        uppercase_ratio = uppercase_count / len(message.content)
        if uppercase_ratio > 0.7:
            await message.delete()
            await user_warn(message, "Büyük harf kullanımı")
            await log_warn(message, bot.user, "Büyük harf kullanımı")
            return

    # --- Emoji spam engelleme ---
    emoji_count = len(re.findall(r"<a?:\w+:\d+>|[\U0001F600-\U0001F64F]|[\U0001F300-\U0001F5FF]", message.content))
    if emoji_count > 7:
        await message.delete()
        await user_warn(message, "Emoji spam")
        await log_warn(message, bot.user, "Emoji spam")
        return

    # --- Flood engelleme ---
    now = asyncio.get_running_loop().time()
    times = user_message_times.get(user_id, [])
    times = [t for t in times if now - t < FLOOD_LIMIT]
    times.append(now)
    user_message_times[user_id] = times

    if len(times) > FLOOD_MSG_COUNT:
        await message.delete()
        await user_warn(message, "Tekrarlanan yazı")
        await log_warn(message, bot.user, "Tekrarlanan yazı")
        return

    # --- Davet linki engelleme ---
    if invite_pattern.search(content):
        await message.delete()
        await user_warn(message, "Link paylaşım")
        await log_warn(message, bot.user, "Link paylaşım")
        return

    # --- XP ve seviye sistemi ---
    if user_id not in user_data:
        user_data[user_id] = {"xp": 0, "level": 1}

    user_data[user_id]["xp"] += 10

    level = user_data[user_id]["level"]
    xp = user_data[user_id]["xp"]
    xp_needed = 100 + (level - 1) * 300

    leveled_up = False

    while xp >= xp_needed:
        xp -= xp_needed
        level += 1
        xp_needed = 100 + (level - 1) * 300
        leveled_up = True

        # Rol değişimleri
        previous_role_id = None
        previous_level = -1
        for lvl, rid in level_roles.items():
            if lvl < level and rid in [r.id for r in member.roles]:
                if lvl > previous_level:
                    previous_level = lvl
                    previous_role_id = rid

        new_role_id = level_roles.get(level)

        if new_role_id:
            if previous_role_id and previous_role_id != new_role_id:
                role_to_remove = guild.get_role(previous_role_id)
                if role_to_remove and role_to_remove in member.roles:
                    await member.remove_roles(role_to_remove)
            new_role = guild.get_role(new_role_id)
            if new_role and new_role not in member.roles:
                await member.add_roles(new_role)

    if leveled_up:
        user_data[user_id]["level"] = level
        user_data[user_id]["xp"] = xp

        try:
            await message.channel.send(f"Çenesi düşük {message.author.mention},  seviye atladı. **seviye {level}**!")
        except Exception as e:
            print(f"Seviye mesajı gönderilemedi: {e}")
    else:
        user_data[user_id]["xp"] = xp

    await bot.process_commands(message)
    
    
# -------------------- YARDIMCI FONKSİYONLAR --------------------

from datetime import datetime

LOG_CHANNEL_ID = 1372936287488573480  # Log kanal ID
MUTE_ROLE_NAME = "Susturuldu"          # Susturma rol adı
MUTE_DURATION_SECONDS = 7200            # 2 saat = 7200 saniye

async def log_warn(message, moderator, reason):
    kanal = bot.get_channel(LOG_CHANNEL_ID)
    if kanal is None:
        print("Log kanalı bulunamadı!")
        return

    embed = discord.Embed(color=0xFF0000)
    embed.set_author(name=f"[WARN] {message.author.name}", icon_url=message.author.display_avatar.url)
    embed.add_field(name="Kullanıcı", value=message.author.mention, inline=True)
    embed.add_field(name="Moderatör", value=moderator.mention if hasattr(moderator, 'mention') else str(moderator), inline=True)
    embed.add_field(name="Neden", value=reason, inline=True)
    embed.add_field(name="Kanal", value=message.channel.mention, inline=True)
    embed.add_field(name="Mesaj", value=message.content or "*boş mesaj*", inline=False)
    await kanal.send(embed=embed)

async def user_warn(message, reason, moderator=None):
    kanal = bot.get_channel(LOG_CHANNEL_ID)
    user_id = message.author.id
    user_warnings[user_id] = user_warnings.get(user_id, 0) + 1

    # Uyarı mesajı kanal içine gönderilir
    embed = discord.Embed(color=0xFF0000)
    embed.set_author(name=f"{message.author.name} uyarıldı", icon_url=message.author.display_avatar.url)
    embed.description = f"**Sebep:** {reason}"
    await message.channel.send(embed=embed)


    # DM mesajı gönder
    dm_message = None
    reason_lower = reason.lower()
    if "yasaklı kelime" in reason_lower:
        dm_message = f"{message.author.mention}, burda o kelimeyi kullanamazsın! 😡"
    elif "tekrarlanan yazı" in reason_lower:
        dm_message = f"{message.author.mention}, aynı mesajı tekrar tekrar gönderme! 😡"
    elif "büyük harf" in reason_lower:
        dm_message = f"{message.author.mention}, MESAJINIZDA çok sayıda BÜYÜK HARF KULLANIYORSUNUZ! 😡"
    elif "link paylaşım" in reason_lower or "link" in reason_lower:
        dm_message = f"{message.author.mention}, o sayfaya ait bağlantıları paylaşman yasaktır! 😡"
    elif "emoji" in reason_lower:
        dm_message = f"{message.author.mention}, çok fazla emoji kullanıyorsun, lütfen azalt! 😡"
    else:
        dm_message = f"{message.author.mention}, lütfen kurallara uy!"

    try:
        await message.author.send(dm_message)
    except Exception as e:
        print(f"Kullanıcıya DM gönderilemedi: {e}")

    # 3 veya üzeri uyarıysa önce uyarı logu at, sonra mute işlemi yap
    if user_warnings[user_id] >= 3:
        # Önce uyarı logu
        if moderator:
            await log_warn(message, moderator, reason)

        guild = message.guild
        mute_role = discord.utils.get(guild.roles, name=MUTE_ROLE_NAME)
        if not mute_role:
            mute_role = await guild.create_role(name=MUTE_ROLE_NAME, reason="Susturma rolü oluşturuldu.")
            for channel in guild.channels:
                await channel.set_permissions(mute_role, send_messages=False)

        await message.author.add_roles(mute_role, reason="3 uyarı sonrası susturuldu.")

        # MUTE log embedi
        if kanal:
            mute_embed = discord.Embed(color=0xFF0000)
            mute_embed.set_author(name=f"[MUTE] {message.author.name}", icon_url=message.author.display_avatar.url)
            mute_embed.add_field(name="Kullanıcı", value=message.author.mention, inline=True)
            mute_embed.add_field(name="Moderatör", value=bot.user.mention, inline=True)
            mute_embed.add_field(name="Neden", value="Aşırı kural ihlali", inline=True)
            mute_embed.add_field(name="Süre", value="2 saat", inline=False)
            await kanal.send(embed=mute_embed)

        # Mute kaldırma işlemi için görev oluştur
        asyncio.create_task(remove_mute(message, mute_role, kanal))

    else:
        # 3 uyarıdan azsa normal uyarı logu gönder
        if moderator:
            await log_warn(message, moderator, reason)


async def remove_mute(message, mute_role, kanal):
    await asyncio.sleep(MUTE_DURATION_SECONDS)
    await message.author.remove_roles(mute_role, reason="Susturma süresi doldu.")

    if kanal:
        unmute_embed = discord.Embed(color=0x00FF00)
        unmute_embed.set_author(name=f"[UNMUTE] {message.author.name}", icon_url=message.author.display_avatar.url)
        unmute_embed.add_field(name="Kullanıcı", value=message.author.mention, inline=True)
        unmute_embed.add_field(name="Moderatör", value=bot.user.mention, inline=True)
        await kanal.send(embed=unmute_embed)


        asyncio.create_task(remove_mute(message, mute_role, kanal))

    # Eğer moderatör belirtilmişse uyarı logunu gönder
    if moderator:
        await log_warn(message, moderator, reason)


async def remove_mute(message, mute_role, kanal):
    await asyncio.sleep(MUTE_DURATION_SECONDS)
    await message.author.remove_roles(mute_role, reason="Susturma süresi doldu.")

    if kanal:
        unmute_embed = discord.Embed(color=0x00FF00)
        unmute_embed.set_author(name=f"[UNMUTE] {message.author.name}", icon_url=message.author.display_avatar.url)
        unmute_embed.add_field(name="Kullanıcı", value=message.author.mention, inline=True)
        unmute_embed.add_field(name="Moderatör", value=bot.user.mention, inline=True)
        await kanal.send(embed=unmute_embed)

        asyncio.create_task(remove_mute())

    # Moderatör bilgisi varsa log gönder
    if moderator:
        await log_warn(message, moderator, reason)


# -------------------- KOMUTLAR --------------------

help_data = {
    "commands": {
        "title": "📜 Komutlar",
        "description": "Belirli roller ve cevaplar veren kendi özel komutlarınızı oluşturun",
        "fields": [
            ("!adam (optional text)", "Harika bir komut!"),
            ("!bb (optional text)", "Harika bir komut!"),
            ("!dc (optional text)", "Discord Linki"),
            ("!gacaman (optional text)", "Harika bir komut!"),
            ("!insta (optional text)", "S2G İnstagram Hesabı"),
            ("!sa (optional text)", "Harika bir komut!"),
        ]
    },
    "levels": {
        "title": "📈 Seviye Sistemi",
        "description": "Seviye, XP ve rütbe sistemi hakkında bilgiler.",
        "fields": [
            ("XP Kazanma", "Mesaj atarak veya belirli aktivitelerle XP kazanırsınız."),
            ("Seviye Atlama", "Belirli XP topladığınızda seviye atlayabilirsiniz."),
            ("Rütbeler", "Seviyenize göre rütbeler kazanırsınız."),
        ]
    },
    "moderator": {
        "title": "🔧 Moderatör Komutları",
        "description": "Uyarı, yasaklama, susturma gibi moderasyon araçları.",
        "fields": [
            ("!uyar [kullanıcı] [sebep]", "Bir kullanıcıyı uyarır."),
            ("!yasakla [kullanıcı] [sebep]", "Kullanıcıyı sunucudan yasaklar."),
            ("!sustur [kullanıcı] [süre]", "Belirli süre susturur."),
            ("!temizle [miktar]", "Mesajları toplu siler."),
        ]
    },
    "record": {
        "title": "📝 Kayıt Komutları",
        "description": "Kullanıcı kayıt ve profil yönetim komutları.",
        "fields": [
            ("!kayıt [kullanıcı] [isim] [yaş]", "Kullanıcıyı kaydeder."),
            ("!profil [kullanıcı]", "Kullanıcı profilini gösterir."),
            ("!kayıtlar", "Tüm kayıtları listeler."),
        ]
    },
    "search": {
        "title": "🔍 Arama Komutları",
        "description": "Sunucuda veya internette arama yapmanızı sağlar.",
        "fields": [
            ("!ara [kelime]", "Sunucuda mesaj arar."),
            ("!google [kelime]", "Google’da arama yapar."),
            ("!youtube [kelime]", "Youtube’da arama yapar."),
        ]
    },
    "emojis": {
        "title": "😄 Emojiler",
        "description": "Emoji ekleme, silme ve gösterme komutları.",
        "fields": [
            ("!emoji-ekle [url] [isim]", "Yeni emoji ekler."),
            ("!emoji-sil [isim]", "Emoji siler."),
            ("!emoji-liste", "Sunucudaki emojileri listeler."),
        ]
    }
}

class HelpSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=help_data[key]["title"], description=help_data[key]["description"][:50]+"...", value=key)
            for key in help_data
        ]
        super().__init__(placeholder="Select the plugin for which you need help", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        key = self.values[0]
        data = help_data[key]

        embed = discord.Embed(title=data["title"], description=data["description"], color=discord.Color.blue())

        for name, value in data["fields"]:
            embed.add_field(name=name, value=value, inline=False)

        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(View):
    def __init__(self):
        super().__init__()
        self.add_item(HelpSelect())

@bot.command()
async def help(ctx):
    embed = discord.Embed(color=discord.Color.blue())

    embed.set_author(name=f"{ctx.bot.user.name} Komutları", icon_url=ctx.bot.user.display_avatar.url)

    embed.add_field(name=" Commands", value="!help commands", inline=True)
    embed.add_field(name=" Levels", value="!help levels", inline=True)
    embed.add_field(name=" Moderator", value="!help moderator", inline=True)
    embed.add_field(name=" Record", value="!help record", inline=True)
    embed.add_field(name=" Search", value="!help search", inline=True)
    embed.add_field(name=" Emojis", value="!help emojis", inline=True)

    await ctx.send(embed=embed, view=HelpView())


# ÜYE KOMUTLARI --------------------------------------------------------------------

@bot.command()
async def sa(ctx):
    await ctx.send(f'{ctx.author.mention} Aleyküm selam, hoş geldin!')

@bot.command()
async def bb(ctx):
    await ctx.send(f'Hoşçakal {ctx.author.mention},')
    
@bot.command()
async def gacaman(ctx):
    await ctx.send(f'Gurtulaman Gıbrıs Polisindennn')

@bot.command()
async def dc(ctx):
    await ctx.send('https://discord.gg/s2gespor')
    
@bot.command()
async def insta(ctx):
    await ctx.send('https://instagram.com/s2gespor')
    
@bot.command()
async def yt(ctx):
    await ctx.send('https://youtube.com/@s2gesports')

#------------------------------------------------------------------------------------------

@bot.command()
async def sunucu(ctx):
    guild = ctx.guild

    embed = discord.Embed(
        title=f" {guild.name} Sunucu Bilgileri",
        color=0xFFA500,  # Turuncu renk
        timestamp=ctx.message.created_at
    )
    embed.set_thumbnail(url=guild.icon.url if guild.icon else "")
    
    embed.add_field(name=" Sunucu Sahibi", value=f"{guild.owner.mention}", inline=False)
    embed.add_field(name=" Üye Sayısı", value=f"{guild.member_count} kişi", inline=True)
    embed.add_field(name=" Oluşturulma Tarihi", value=guild.created_at.strftime("%d %B %Y\n%H:%M"), inline=True)
    embed.add_field(name=" Sunucu ID", value=guild.id, inline=False)
    
    embed.set_footer(text=f"{ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)

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
    
    
infractions = {}

@bot.command()
async def infractions(ctx, member: discord.Member = None):
    member = member or ctx.author  # Eğer üye belirtilmezse, kendini gösterir
    key = f"{ctx.guild.id}-{member.id}"
    
    if key in infractions and infractions[key]:
        embed = discord.Embed(title=f"{member} Ceza Geçmişi", color=discord.Color.red())
        for i, inf in enumerate(infractions[key], 1):
            mod = bot.get_user(inf["mod"])
            mod_name = mod.name if mod else "Bilinmiyor"
            embed.add_field(
                name=f"Ceza {i}",
                value=f"Eylem: {inf['action']}\nSebep: {inf['reason']}\nModeratör: {mod_name}",
                inline=False
            )
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"{member} kullanıcısının ceza geçmişi yok.")




@bot.command()
async def profil(ctx, member: discord.Member = None):
    member = member or ctx.author
    user_id = str(member.id)
    level = user_data.get(user_id, {}).get("level", 1)
    xp = user_data.get(user_id, {}).get("xp", 0)
    warn_count = len(warnings.get(member.id, []))

    embed = discord.Embed(title=f"📊 {member.name} Profili", color=discord.Color.purple())
    embed.set_thumbnail(url=member.avatar.url if member.avatar else "")
    embed.add_field(name="Seviye", value=str(level))
    embed.add_field(name="XP", value=str(xp))
    embed.add_field(name="Uyarı Sayısı", value=str(warn_count))
    if warn_count > 0:
        embed.add_field(name="Uyarılar", value="\n".join(warnings[member.id]), inline=False)
    await ctx.send(embed=embed)


#----------------------------------------------LEVELS-------------------------------------------------

@bot.command()
async def rank(ctx):
    user_id = ctx.author.id  # INT olarak kalmalı
    if user_id not in user_data:
        user_data[user_id] = {"xp": 0, "level": 1}

    level = user_data[user_id]["level"]
    xp = user_data[user_id]["xp"]
    xp_needed = 100 + (level - 1) * 150

    # Sıralama
    sorted_users = sorted(user_data.items(), key=lambda x: (x[1]["level"], x[1]["xp"]), reverse=True)
    rank = next((i + 1 for i, (uid, _) in enumerate(sorted_users) if uid == user_id), None)

    # Görsel
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
