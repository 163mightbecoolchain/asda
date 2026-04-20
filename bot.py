import discord
from discord.ext import commands
import datetime
import asyncio
import os
import json
import gspread
from google.oauth2.service_account import Credentials

# ─── КОНФИГ ───────────────────────────────────────────────────
TOKEN = os.getenv("TOKEN")
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))
SHEET_ID = os.getenv("SHEET_ID")
GOOGLE_CREDENTIALS = os.getenv("GOOGLE_CREDENTIALS")
OWNER_IDS = [474658252840370176]

# ─── НАСТРОЙКИ ЛОГИРОВАНИЯ ────────────────────────────────────
log_settings = {
    # ВКЛЮЧЕНО по умолчанию
    "joins":          {"enabled": True,  "name": "Входы на сервер"},
    "leaves":         {"enabled": True,  "name": "Выходы с сервера"},
    "bans":           {"enabled": True,  "name": "Баны/разбаны"},
    "timeouts":       {"enabled": True,  "name": "Таймауты"},
    "msg_delete":     {"enabled": True,  "name": "Удалённые сообщения"},
    "msg_edit":       {"enabled": True,  "name": "Отредактированные сообщения"},
    "invites":        {"enabled": True,  "name": "Инвайты"},
    "suspicious":     {"enabled": True,  "name": "Подозрительные аккаунты"},
    # ВЫКЛЮЧЕНО по умолчанию
    "nick_change":    {"enabled": False, "name": "Смена ника"},
    "role_change":    {"enabled": False, "name": "Смена ролей"},
    "avatar_change":  {"enabled": False, "name": "Смена аватарки"},
    "voice":          {"enabled": False, "name": "Голосовые каналы"},
    "channels":       {"enabled": False, "name": "Создание/удаление каналов"},
    "roles":          {"enabled": False, "name": "Создание/удаление ролей"},
    "server_edit":    {"enabled": False, "name": "Изменение настроек сервера"},
    "reactions":      {"enabled": False, "name": "Реакции"},
    "threads":        {"enabled": False, "name": "Создание/удаление тредов"},
    "slash_commands": {"enabled": False, "name": "Слэш-команды"},
}

# ─── GOOGLE SHEETS ────────────────────────────────────────────
def get_sheets_client():
    if not GOOGLE_CREDENTIALS or not SHEET_ID:
        return None, None
    try:
        creds_dict = json.loads(GOOGLE_CREDENTIALS)
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(SHEET_ID)
        return client, sheet
    except Exception as e:
        print(f"Ошибка подключения к Google Sheets: {e}")
        return None, None

def get_or_create_worksheet(sheet, title, headers):
    try:
        ws = sheet.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = sheet.add_worksheet(title=title, rows=1000, cols=20)
        ws.append_row(headers)
    return ws

def sheets_add_invite(code, creator_name, creator_id, member_name, member_id, date):
    try:
        _, sheet = get_sheets_client()
        if not sheet:
            return
        ws = get_or_create_worksheet(sheet, "Инвайты", [
            "Код", "Создатель", "UID создателя", "Вошедший", "UID вошедшего", "Дата"
        ])
        ws.append_row([code, creator_name, str(creator_id), member_name, str(member_id), date])
    except Exception as e:
        print(f"Ошибка записи в Инвайты: {e}")

def sheets_add_suspicious(member_name, member_id, created_at, joined_at, invite_code):
    try:
        _, sheet = get_sheets_client()
        if not sheet:
            return
        ws = get_or_create_worksheet(sheet, "Подозрительные", [
            "Ник", "UID", "Дата создания аккаунта", "Дата входа", "Код инвайта"
        ])
        ws.append_row([member_name, str(member_id), created_at, joined_at, invite_code])
    except Exception as e:
        print(f"Ошибка записи в Подозрительные: {e}")

def sheets_add_creator(creator_name, creator_id, code, created_at):
    try:
        _, sheet = get_sheets_client()
        if not sheet:
            return
        ws = get_or_create_worksheet(sheet, "Создатели инвайтов", [
            "Ник создателя", "UID создателя", "Код инвайта", "Дата создания", "Использований"
        ])
        ws.append_row([creator_name, str(creator_id), code, created_at, 0])
    except Exception as e:
        print(f"Ошибка записи в Создатели инвайтов: {e}")

def sheets_update_invite_uses(code, uses):
    try:
        _, sheet = get_sheets_client()
        if not sheet:
            return
        ws = get_or_create_worksheet(sheet, "Создатели инвайтов", [
            "Ник создателя", "UID создателя", "Код инвайта", "Дата создания", "Использований"
        ])
        cell = ws.find(code)
        if cell:
            ws.update_cell(cell.row, 5, uses)
    except Exception as e:
        print(f"Ошибка обновления использований: {e}")

# ─── БОТ ──────────────────────────────────────────────────────
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

async def get_log_channel(guild):
    return bot.get_channel(LOG_CHANNEL_ID)

def is_owner(ctx):
    return ctx.author.id in OWNER_IDS

def is_enabled(key):
    return log_settings.get(key, {}).get("enabled", False)

def account_age_days(member):
    return (datetime.datetime.utcnow() - member.created_at.replace(tzinfo=None)).days

# ─── КОМАНДЫ ──────────────────────────────────────────────────
@bot.command(name="status")
async def status(ctx):
    if not is_owner(ctx):
        return

    enabled = []
    disabled = []

    for key, val in log_settings.items():
        if val["enabled"]:
            enabled.append(f"✅ `{key}` — {val['name']}")
        else:
            disabled.append(f"❌ `{key}` — {val['name']}")

    embed = discord.Embed(
        title="⚙️ Статус функций логирования",
        color=discord.Color.blurple(),
        timestamp=datetime.datetime.utcnow()
    )
    embed.add_field(name="Включено", value="\n".join(enabled) or "нет", inline=False)
    embed.add_field(name="Выключено", value="\n".join(disabled) or "нет", inline=False)
    await ctx.send(embed=embed)

@bot.command(name="toggle")
async def toggle(ctx, key: str = None):
    if not is_owner(ctx):
        return

    if not key or key not in log_settings:
        keys = ", ".join(f"`{k}`" for k in log_settings.keys())
        await ctx.send(f"❌ Укажи правильный ключ. Доступные: {keys}")
        return

    log_settings[key]["enabled"] = not log_settings[key]["enabled"]
    state = "✅ включена" if log_settings[key]["enabled"] else "❌ выключена"
    await ctx.send(f"Функция **{log_settings[key]['name']}** {state}")

@bot.command(name="invcheck")
async def invcheck(ctx, code: str = None):
    if not is_owner(ctx):
        return

    if not code:
        await ctx.send("❌ Укажи код инвайта: `!invcheck (код)`")
        return

    try:
        _, sheet = get_sheets_client()
        if not sheet:
            await ctx.send("❌ Google Sheets не подключён")
            return

        ws_invites = get_or_create_worksheet(sheet, "Инвайты", [
            "Код", "Создатель", "UID создателя", "Вошедший", "UID вошедшего", "Дата"
        ])
        ws_creators = get_or_create_worksheet(sheet, "Создатели инвайтов", [
            "Ник создателя", "UID создателя", "Код инвайта", "Дата создания", "Использований"
        ])

        all_invites = ws_invites.get_all_records()
        rows = [r for r in all_invites if str(r.get("Код")) == code]

        creator_name = "неизвестно"
        creator_id = "неизвестно"
        created_at = "неизвестно"

        all_creators = ws_creators.get_all_records()
        for r in all_creators:
            if str(r.get("Код инвайта")) == code:
                creator_name = r.get("Ник создателя", "неизвестно")
                creator_id = r.get("UID создателя", "неизвестно")
                created_at = r.get("Дата создания", "неизвестно")
                break

        embed = discord.Embed(
            title=f"🔗 Инвайт: {code}",
            color=discord.Color.teal(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Создал", value=f"{creator_name} (`{creator_id}`)", inline=True)
        embed.add_field(name="Дата создания", value=created_at, inline=True)
        embed.add_field(name="Всего зашло", value=len(rows), inline=True)

        if rows:
            members_list = "\n".join(
                f"{i+1}. {r['Вошедший']} | `{r['UID вошедшего']}` | {r['Дата']}"
                for i, r in enumerate(rows)
            )
            embed.add_field(
                name="━━━━━━━━━━━━━━━━\nКто зашёл",
                value=members_list[:1024] or "никто",
                inline=False
            )
        else:
            embed.add_field(name="Кто зашёл", value="никто", inline=False)

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Ошибка: {e}")

@bot.command(name="invuser")
async def invuser(ctx, *, username: str = None):
    if not is_owner(ctx):
        return

    if not username:
        await ctx.send("❌ Укажи ник: `!invuser (ник)`")
        return

    try:
        _, sheet = get_sheets_client()
        if not sheet:
            await ctx.send("❌ Google Sheets не подключён")
            return

        ws = get_or_create_worksheet(sheet, "Создатели инвайтов", [
            "Ник создателя", "UID создателя", "Код инвайта", "Дата создания", "Использований"
        ])

        all_rows = ws.get_all_records()
        rows = [r for r in all_rows if r.get("Ник создателя", "").lower() == username.lower()]

        if not rows:
            await ctx.send(f"❌ Инвайты для `{username}` не найдены")
            return

        embed = discord.Embed(
            title=f"👤 Инвайты пользователя: {username}",
            color=discord.Color.blurple(),
            timestamp=datetime.datetime.utcnow()
        )

        codes_list = "\n".join(
            f"`{r['Код инвайта']}` — создан {r['Дата создания']} — использований: {r['Использований']}"
            for r in rows
        )
        embed.add_field(name="Созданные ссылки", value=codes_list[:1024], inline=False)
        embed.add_field(name="Всего ссылок", value=len(rows), inline=True)

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"❌ Ошибка: {e}")

@bot.command(name="invdel")
async def invdel(ctx, code: str = None):
    if not is_owner(ctx):
        return

    if not code:
        await ctx.send("❌ Укажи код: `!invdel (код)`")
        return

    try:
        invite = await ctx.guild.fetch_invite(code)
        await invite.delete()
        await ctx.send(f"✅ Инвайт `{code}` удалён")
    except discord.NotFound:
        await ctx.send(f"❌ Инвайт `{code}` не найден")
    except Exception as e:
        await ctx.send(f"❌ Ошибка: {e}")

# ─── ВХОД НА СЕРВЕР ───────────────────────────────────────────
@bot.event
async def on_member_join(member):
    channel = await get_log_channel(member.guild)
    if not channel:
        return

    old_cache = bot.invite_cache.copy()
    await asyncio.sleep(3)

    invites_after = await member.guild.invites()
    bot.invite_cache = {inv.code: inv.uses for inv in invites_after}

    used_invite = None
    for invite in invites_after:
        if invite.code in old_cache:
            if invite.uses > old_cache[invite.code]:
                used_invite = invite
                break

    invite_info = "неизвестно"
    inviter_info = "неизвестно"
    inviter_id = "неизвестно"

    if used_invite:
        invite_info = f"`{used_invite.code}`"
        inviter_info = used_invite.inviter.name
        inviter_id = used_invite.inviter.id
        sheets_add_invite(
            used_invite.code,
            used_invite.inviter.name,
            used_invite.inviter.id,
            member.name,
            member.id,
            datetime.datetime.utcnow().strftime("%d.%m.%Y %H:%M")
        )
        sheets_update_invite_uses(used_invite.code, used_invite.uses)
    else:
        deleted_codes = set(old_cache.keys()) - set(bot.invite_cache.keys())
        for code in deleted_codes:
            if old_cache[code] == 0:
                invite_info = f"`{code}`"
                inviter_info = "неизвестно (одноразовая)"
                break

    # Проверка возраста аккаунта
    age_days = account_age_days(member)
    if age_days < 7:
        suspicion = "🔴 Подозрительный (младше 7 дней)"
    elif age_days < 30:
        suspicion = "🟡 Новый аккаунт (младше 30 дней)"
    else:
        suspicion = "🟢 Обычный"

    if is_enabled("joins"):
        embed = discord.Embed(
            title="📥 Участник вошёл",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Участник", value=f"{member.mention} (`{member.name}`)", inline=False)
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Аккаунт создан", value=member.created_at.strftime("%d.%m.%Y"), inline=True)
        embed.add_field(name="Возраст аккаунта", value=f"{age_days} дней — {suspicion}", inline=False)
        embed.add_field(name="Инвайт", value=invite_info, inline=True)
        embed.add_field(name="Пригласил", value=f"{inviter_info} (`{inviter_id}`)", inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)

    if is_enabled("suspicious") and age_days < 7:
        susp_embed = discord.Embed(
            title="🚨 Подозрительный аккаунт",
            color=discord.Color.red(),
            timestamp=datetime.datetime.utcnow()
        )
        susp_embed.add_field(name="Участник", value=f"{member.mention} (`{member.name}`)", inline=False)
        susp_embed.add_field(name="ID", value=member.id, inline=True)
        susp_embed.add_field(name="Аккаунт создан", value=member.created_at.strftime("%d.%m.%Y"), inline=True)
        susp_embed.add_field(name="Возраст", value=f"{age_days} дней", inline=True)
        susp_embed.add_field(name="Инвайт", value=invite_info, inline=True)
        susp_embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=susp_embed)
        sheets_add_suspicious(
            member.name,
            member.id,
            member.created_at.strftime("%d.%m.%Y"),
            datetime.datetime.utcnow().strftime("%d.%m.%Y %H:%M"),
            invite_info
        )

# ─── ВЫХОД С СЕРВЕРА ──────────────────────────────────────────
@bot.event
async def on_member_remove(member):
    if not is_enabled("leaves"):
        return

    channel = await get_log_channel(member.guild)
    if not channel:
        return

    roles = [role.mention for role in member.roles if role.name != "@everyone"]

    embed = discord.Embed(
        title="📤 Участник вышел",
        color=discord.Color.red(),
        timestamp=datetime.datetime.utcnow()
    )
    embed.add_field(name="Участник", value=f"{member.mention} (`{member.name}`)", inline=False)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Роли", value=", ".join(roles) if roles else "нет", inline=False)
    embed.set_thumbnail(url=member.display_avatar.url)
    await channel.send(embed=embed)

# ─── БАН ──────────────────────────────────────────────────────
@bot.event
async def on_member_ban(guild, user):
    if not is_enabled("bans"):
        return

    channel = await get_log_channel(guild)
    if not channel:
        return

    embed = discord.Embed(
        title="🔨 Участник забанен",
        color=discord.Color.dark_red(),
        timestamp=datetime.datetime.utcnow()
    )
    embed.add_field(name="Участник", value=f"{user.mention} (`{user.name}`)", inline=False)
    embed.add_field(name="ID", value=user.id, inline=True)
    await channel.send(embed=embed)

# ─── РАЗБАН ───────────────────────────────────────────────────
@bot.event
async def on_member_unban(guild, user):
    if not is_enabled("bans"):
        return

    channel = await get_log_channel(guild)
    if not channel:
        return

    embed = discord.Embed(
        title="✅ Участник разбанен",
        color=discord.Color.green(),
        timestamp=datetime.datetime.utcnow()
    )
    embed.add_field(name="Участник", value=f"{user.mention} (`{user.name}`)", inline=False)
    embed.add_field(name="ID", value=user.id, inline=True)
    await channel.send(embed=embed)

# ─── ИЗМЕНЕНИЯ УЧАСТНИКА ──────────────────────────────────────
@bot.event
async def on_member_update(before, after):
    channel = await get_log_channel(after.guild)
    if not channel:
        return

    # Ник
    if is_enabled("nick_change") and before.nick != after.nick:
        embed = discord.Embed(title="✏️ Изменён ник", color=discord.Color.blue(), timestamp=datetime.datetime.utcnow())
        embed.add_field(name="Участник", value=after.mention, inline=False)
        embed.add_field(name="Было", value=before.nick or before.name, inline=True)
        embed.add_field(name="Стало", value=after.nick or after.name, inline=True)
        await channel.send(embed=embed)

    # Роли
    if is_enabled("role_change"):
        added_roles = set(after.roles) - set(before.roles)
        removed_roles = set(before.roles) - set(after.roles)
        if added_roles or removed_roles:
            embed = discord.Embed(title="🎭 Изменены роли", color=discord.Color.blurple(), timestamp=datetime.datetime.utcnow())
            embed.add_field(name="Участник", value=after.mention, inline=False)
            if added_roles:
                embed.add_field(name="Добавлены", value=", ".join(r.mention for r in added_roles), inline=False)
            if removed_roles:
                embed.add_field(name="Убраны", value=", ".join(r.mention for r in removed_roles), inline=False)
            await channel.send(embed=embed)

    # Таймаут
    if is_enabled("timeouts") and before.timed_out_until != after.timed_out_until:
        if after.timed_out_until:
            embed = discord.Embed(title="🔇 Участник замьючен", color=discord.Color.orange(), timestamp=datetime.datetime.utcnow())
            embed.add_field(name="Участник", value=after.mention, inline=False)
            embed.add_field(name="До", value=after.timed_out_until.strftime("%d.%m.%Y %H:%M:%S"), inline=True)
        else:
            embed = discord.Embed(title="🔊 Мут снят", color=discord.Color.green(), timestamp=datetime.datetime.utcnow())
            embed.add_field(name="Участник", value=after.mention, inline=False)
        await channel.send(embed=embed)

# ─── АВАТАРКА ─────────────────────────────────────────────────
@bot.event
async def on_user_update(before, after):
    if not is_enabled("avatar_change"):
        return
    if before.avatar != after.avatar:
        for guild in bot.guilds:
            member = guild.get_member(after.id)
            if member:
                channel = await get_log_channel(guild)
                if channel:
                    embed = discord.Embed(title="🖼️ Изменена аватарка", color=discord.Color.blue(), timestamp=datetime.datetime.utcnow())
                    embed.add_field(name="Участник", value=member.mention, inline=False)
                    embed.set_thumbnail(url=after.display_avatar.url)
                    await channel.send(embed=embed)

# ─── УДАЛЁННЫЕ СООБЩЕНИЯ ──────────────────────────────────────
@bot.event
async def on_message_delete(message):
    if not is_enabled("msg_delete") or message.author.bot:
        return

    channel = await get_log_channel(message.guild)
    if not channel:
        return

    embed = discord.Embed(
        title="🗑️ Сообщение удалено",
        color=discord.Color.red(),
        timestamp=datetime.datetime.utcnow()
    )
    embed.add_field(name="Автор", value=f"{message.author.mention} (`{message.author.name}`)", inline=False)

    # Определяем тред или обычный канал
    if isinstance(message.channel, discord.Thread):
        embed.add_field(name="Тред", value=f"{message.channel.mention} (в {message.channel.parent.mention})", inline=True)
    else:
        embed.add_field(name="Канал", value=message.channel.mention, inline=True)

    embed.add_field(name="Текст", value=message.content or "*(пусто/вложение)*", inline=False)

    if message.attachments:
        embed.add_field(name="Вложения", value="\n".join(a.url for a in message.attachments), inline=False)

    await channel.send(embed=embed)

# ─── ОТРЕДАКТИРОВАННЫЕ СООБЩЕНИЯ ──────────────────────────────
@bot.event
async def on_message_edit(before, after):
    if not is_enabled("msg_edit") or before.author.bot or before.content == after.content:
        return

    channel = await get_log_channel(before.guild)
    if not channel:
        return

    embed = discord.Embed(
        title="✏️ Сообщение отредактировано",
        color=discord.Color.yellow(),
        timestamp=datetime.datetime.utcnow()
    )
    embed.add_field(name="Автор", value=f"{before.author.mention} (`{before.author.name}`)", inline=False)

    if isinstance(before.channel, discord.Thread):
        embed.add_field(name="Тред", value=f"{before.channel.mention} (в {before.channel.parent.mention})", inline=True)
    else:
        embed.add_field(name="Канал", value=before.channel.mention, inline=True)

    embed.add_field(name="Было", value=before.content or "*(пусто)*", inline=False)
    embed.add_field(name="Стало", value=after.content or "*(пусто)*", inline=False)
    embed.add_field(name="Ссылка", value=f"[Перейти]({after.jump_url})", inline=False)
    await channel.send(embed=embed)

# ─── ГОЛОСОВЫЕ КАНАЛЫ ─────────────────────────────────────────
@bot.event
async def on_voice_state_update(member, before, after):
    if not is_enabled("voice"):
        return

    channel = await get_log_channel(member.guild)
    if not channel:
        return

    if before.channel is None and after.channel is not None:
        desc = f"вошёл в **{after.channel.name}**"
        color = discord.Color.green()
    elif before.channel is not None and after.channel is None:
        desc = f"вышел из **{before.channel.name}**"
        color = discord.Color.red()
    elif before.channel != after.channel:
        desc = f"перешёл из **{before.channel.name}** в **{after.channel.name}**"
        color = discord.Color.blue()
    else:
        return

    embed = discord.Embed(title="🔊 Голосовой канал", color=color, timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Участник", value=f"{member.mention} (`{member.name}`)", inline=False)
    embed.add_field(name="Действие", value=desc, inline=False)
    await channel.send(embed=embed)

# ─── КАНАЛЫ ───────────────────────────────────────────────────
@bot.event
async def on_guild_channel_create(channel_created):
    if not is_enabled("channels"):
        return
    channel = await get_log_channel(channel_created.guild)
    if not channel:
        return
    embed = discord.Embed(title="📁 Канал создан", color=discord.Color.green(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Канал", value=channel_created.mention, inline=True)
    embed.add_field(name="Тип", value=str(channel_created.type), inline=True)
    await channel.send(embed=embed)

@bot.event
async def on_guild_channel_delete(channel_deleted):
    if not is_enabled("channels"):
        return
    channel = await get_log_channel(channel_deleted.guild)
    if not channel:
        return
    embed = discord.Embed(title="🗑️ Канал удалён", color=discord.Color.red(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Канал", value=channel_deleted.name, inline=True)
    embed.add_field(name="Тип", value=str(channel_deleted.type), inline=True)
    await channel.send(embed=embed)

# ─── РОЛИ ─────────────────────────────────────────────────────
@bot.event
async def on_guild_role_create(role):
    if not is_enabled("roles"):
        return
    channel = await get_log_channel(role.guild)
    if not channel:
        return
    embed = discord.Embed(title="🎭 Роль создана", color=discord.Color.green(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Роль", value=role.mention, inline=True)
    await channel.send(embed=embed)

@bot.event
async def on_guild_role_delete(role):
    if not is_enabled("roles"):
        return
    channel = await get_log_channel(role.guild)
    if not channel:
        return
    embed = discord.Embed(title="🗑️ Роль удалена", color=discord.Color.red(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Роль", value=role.name, inline=True)
    await channel.send(embed=embed)

# ─── НАСТРОЙКИ СЕРВЕРА ────────────────────────────────────────
@bot.event
async def on_guild_update(before, after):
    if not is_enabled("server_edit"):
        return
    channel = await get_log_channel(after)
    if not channel:
        return
    if before.name != after.name:
        embed = discord.Embed(title="⚙️ Изменено название сервера", color=discord.Color.blue(), timestamp=datetime.datetime.utcnow())
        embed.add_field(name="Было", value=before.name, inline=True)
        embed.add_field(name="Стало", value=after.name, inline=True)
        await channel.send(embed=embed)

# ─── РЕАКЦИИ ──────────────────────────────────────────────────
@bot.event
async def on_reaction_add(reaction, user):
    if not is_enabled("reactions") or user.bot:
        return
    channel = await get_log_channel(reaction.message.guild)
    if not channel:
        return
    embed = discord.Embed(title="😀 Реакция добавлена", color=discord.Color.green(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Пользователь", value=f"{user.mention}", inline=True)
    embed.add_field(name="Реакция", value=str(reaction.emoji), inline=True)
    embed.add_field(name="Сообщение", value=f"[Перейти]({reaction.message.jump_url})", inline=True)
    await channel.send(embed=embed)

@bot.event
async def on_reaction_remove(reaction, user):
    if not is_enabled("reactions") or user.bot:
        return
    channel = await get_log_channel(reaction.message.guild)
    if not channel:
        return
    embed = discord.Embed(title="😀 Реакция убрана", color=discord.Color.red(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Пользователь", value=f"{user.mention}", inline=True)
    embed.add_field(name="Реакция", value=str(reaction.emoji), inline=True)
    embed.add_field(name="Сообщение", value=f"[Перейти]({reaction.message.jump_url})", inline=True)
    await channel.send(embed=embed)

# ─── ТРЕДЫ ────────────────────────────────────────────────────
@bot.event
async def on_thread_create(thread):
    if not is_enabled("threads"):
        return
    channel = await get_log_channel(thread.guild)
    if not channel:
        return
    embed = discord.Embed(title="🧵 Тред создан", color=discord.Color.green(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Тред", value=thread.mention, inline=True)
    embed.add_field(name="Канал", value=thread.parent.mention, inline=True)
    await channel.send(embed=embed)

@bot.event
async def on_thread_delete(thread):
    if not is_enabled("threads"):
        return
    channel = await get_log_channel(thread.guild)
    if not channel:
        return
    embed = discord.Embed(title="🗑️ Тред удалён", color=discord.Color.red(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Тред", value=thread.name, inline=True)
    embed.add_field(name="Канал", value=thread.parent.mention if thread.parent else "неизвестно", inline=True)
    await channel.send(embed=embed)

# ─── СЛЭШ-КОМАНДЫ ─────────────────────────────────────────────
@bot.event
async def on_interaction(interaction):
    if not is_enabled("slash_commands"):
        return
    if interaction.type != discord.InteractionType.application_command:
        return
    channel = await get_log_channel(interaction.guild)
    if not channel:
        return
    embed = discord.Embed(title="⚡ Слэш-команда", color=discord.Color.blurple(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Пользователь", value=f"{interaction.user.mention}", inline=True)
    embed.add_field(name="Команда", value=f"`/{interaction.data.get('name', 'неизвестно')}`", inline=True)
    embed.add_field(name="Канал", value=interaction.channel.mention if interaction.channel else "неизвестно", inline=True)
    await channel.send(embed=embed)

# ─── ИНВАЙТЫ ──────────────────────────────────────────────────
@bot.event
async def on_invite_create(invite):
    bot.invite_cache[invite.code] = invite.uses
    sheets_add_creator(
        invite.inviter.name,
        invite.inviter.id,
        invite.code,
        datetime.datetime.utcnow().strftime("%d.%m.%Y %H:%M")
    )

    if not is_enabled("invites"):
        return

    channel = await get_log_channel(invite.guild)
    if not channel:
        return

    embed = discord.Embed(title="🔗 Создана ссылка-приглашение", color=discord.Color.teal(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Создал", value=f"{invite.inviter.mention} (`{invite.inviter.name}`)", inline=False)
    embed.add_field(name="Код", value=f"`{invite.code}`", inline=True)
    embed.add_field(name="Ссылка", value=invite.url, inline=True)
    expires = invite.expires_at.strftime("%d.%m.%Y %H:%M") if invite.expires_at else "никогда"
    embed.add_field(name="Истекает", value=expires, inline=True)
    await channel.send(embed=embed)

@bot.event
async def on_invite_delete(invite):
    bot.invite_cache.pop(invite.code, None)

    if not is_enabled("invites"):
        return

    channel = await get_log_channel(invite.guild)
    if not channel:
        return

    embed = discord.Embed(title="❌ Ссылка-приглашение удалена", color=discord.Color.dark_gray(), timestamp=datetime.datetime.utcnow())
    embed.add_field(name="Код", value=f"`{invite.code}`", inline=True)
    await channel.send(embed=embed)

# ─── ЗАПУСК ───────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"Бот запущен: {bot.user}")
    bot.invite_cache = {}
    for guild in bot.guilds:
        try:
            invites = await guild.invites()
            bot.invite_cache = {inv.code: inv.uses for inv in invites}
            print(f"Кэш инвайтов загружен: {len(bot.invite_cache)} инвайтов")
        except Exception as e:
            print(f"Ошибка загрузки инвайтов: {e}")

bot.run(TOKEN)
