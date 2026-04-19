import discord
from discord.ext import commands
import datetime

import os
TOKEN = os.getenv("TOKEN")
LOG_CHANNEL_ID = 1227113471213043732  # ID канала для логов

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

async def get_log_channel(guild):
    return bot.get_channel(LOG_CHANNEL_ID)

def get_time():
    return datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")

# ─── ВХОД НА СЕРВЕР ───────────────────────────────────────────
import asyncio

@bot.event
async def on_member_join(member):
    channel = await get_log_channel(member.guild)
    if not channel:
        return

    # Ждём секунду чтобы Discord обновил данные
    await asyncio.sleep(1)

    invites_after = await member.guild.invites()
    used_invite = None

    for invite in invites_after:
        if invite.code in bot.invite_cache:
            if invite.uses > bot.invite_cache[invite.code]:
                used_invite = invite
                break

    bot.invite_cache = {inv.code: inv.uses for inv in invites_after}

    if used_invite:
        invite_info = f"`{used_invite.code}`"
        inviter_info = f"{used_invite.inviter.mention} (`{used_invite.inviter.name}`)"
    else:
        invite_info = "неизвестно"
        inviter_info = "неизвестно"

    embed = discord.Embed(
        title="📥 Участник вошёл",
        color=discord.Color.green(),
        timestamp=datetime.datetime.utcnow()
    )
    embed.add_field(name="Участник", value=f"{member.mention} (`{member.name}`)", inline=False)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Аккаунт создан", value=member.created_at.strftime("%d.%m.%Y"), inline=True)
    embed.add_field(name="Инвайт", value=invite_info, inline=True)
    embed.add_field(name="Пригласил", value=inviter_info, inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    await channel.send(embed=embed)
    

# ─── ВЫХОД С СЕРВЕРА ──────────────────────────────────────────
@bot.event
async def on_member_remove(member):
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

# ─── ИЗМЕНЕНИЕ УЧАСТНИКА (ник, роли, таймаут) ─────────────────
@bot.event
async def on_member_update(before, after):
    channel = await get_log_channel(after.guild)
    if not channel:
        return

    # Изменение ника
    if before.nick != after.nick:
        embed = discord.Embed(
            title="✏️ Изменён ник",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Участник", value=after.mention, inline=False)
        embed.add_field(name="Было", value=before.nick or before.name, inline=True)
        embed.add_field(name="Стало", value=after.nick or after.name, inline=True)
        await channel.send(embed=embed)

    # Изменение ролей
    added_roles = set(after.roles) - set(before.roles)
    removed_roles = set(before.roles) - set(after.roles)

    if added_roles or removed_roles:
        embed = discord.Embed(
            title="🎭 Изменены роли",
            color=discord.Color.blurple(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.add_field(name="Участник", value=after.mention, inline=False)
        if added_roles:
            embed.add_field(name="Добавлены", value=", ".join(r.mention for r in added_roles), inline=False)
        if removed_roles:
            embed.add_field(name="Убраны", value=", ".join(r.mention for r in removed_roles), inline=False)
        await channel.send(embed=embed)

    # Таймаут
    if before.timed_out_until != after.timed_out_until:
        if after.timed_out_until:
            embed = discord.Embed(
                title="🔇 Участник замьючен",
                color=discord.Color.orange(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="Участник", value=after.mention, inline=False)
            embed.add_field(name="До", value=after.timed_out_until.strftime("%d.%m.%Y %H:%M:%S"), inline=True)
        else:
            embed = discord.Embed(
                title="🔊 Мут снят",
                color=discord.Color.green(),
                timestamp=datetime.datetime.utcnow()
            )
            embed.add_field(name="Участник", value=after.mention, inline=False)
        await channel.send(embed=embed)

# ─── ИЗМЕНЕНИЕ АВАТАРКИ ───────────────────────────────────────
@bot.event
async def on_user_update(before, after):
    # Работает только если пользователь есть в кэше
    if before.avatar != after.avatar:
        for guild in bot.guilds:
            member = guild.get_member(after.id)
            if member:
                channel = await get_log_channel(guild)
                if channel:
                    embed = discord.Embed(
                        title="🖼️ Изменена аватарка",
                        color=discord.Color.blue(),
                        timestamp=datetime.datetime.utcnow()
                    )
                    embed.add_field(name="Участник", value=member.mention, inline=False)
                    embed.set_thumbnail(url=after.display_avatar.url)
                    await channel.send(embed=embed)

# ─── УДАЛЁННЫЕ СООБЩЕНИЯ ──────────────────────────────────────
@bot.event
async def on_message_delete(message):
    if message.author.bot:
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
    embed.add_field(name="Канал", value=message.channel.mention, inline=True)
    embed.add_field(name="Текст", value=message.content or "*(пусто/вложение)*", inline=False)

    if message.attachments:
        embed.add_field(name="Вложения", value="\n".join(a.url for a in message.attachments), inline=False)

    await channel.send(embed=embed)

# ─── ОТРЕДАКТИРОВАННЫЕ СООБЩЕНИЯ ──────────────────────────────
@bot.event
async def on_message_edit(before, after):
    if before.author.bot or before.content == after.content:
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
    embed.add_field(name="Канал", value=before.channel.mention, inline=True)
    embed.add_field(name="Было", value=before.content or "*(пусто)*", inline=False)
    embed.add_field(name="Стало", value=after.content or "*(пусто)*", inline=False)
    embed.add_field(name="Ссылка", value=f"[Перейти]({after.jump_url})", inline=False)
    await channel.send(embed=embed)

# ─── СОЗДАНИЕ ИНВАЙТА ─────────────────────────────────────────
@bot.event
async def on_invite_create(invite):
    channel = await get_log_channel(invite.guild)
    if not channel:
        return

    # Сохраняем в кэш
    bot.invite_cache[invite.code] = invite.uses

    embed = discord.Embed(
        title="🔗 Создана ссылка-приглашение",
        color=discord.Color.teal(),
        timestamp=datetime.datetime.utcnow()
    )
    embed.add_field(name="Создал", value=f"{invite.inviter.mention} (`{invite.inviter.name}`)", inline=False)
    embed.add_field(name="Код", value=f"`{invite.code}`", inline=True)
    embed.add_field(name="Ссылка", value=invite.url, inline=True)
    expires = invite.expires_at.strftime("%d.%m.%Y %H:%M") if invite.expires_at else "никогда"
    embed.add_field(name="Истекает", value=expires, inline=True)
    await channel.send(embed=embed)

# ─── УДАЛЕНИЕ ИНВАЙТА ─────────────────────────────────────────
@bot.event
async def on_invite_delete(invite):
    channel = await get_log_channel(invite.guild)
    if not channel:
        return

    bot.invite_cache.pop(invite.code, None)

    embed = discord.Embed(
        title="❌ Ссылка-приглашение удалена",
        color=discord.Color.dark_gray(),
        timestamp=datetime.datetime.utcnow()
    )
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
