import discord
from discord import app_commands
from discord.ui import Button, View, Modal, TextInput
from discord.ext import tasks
from typing import Literal
import asyncio

# Подключаем Flask для создания веб-страницы-"будильника"
from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Монки-бот активен и работает 24/7!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_flask)
    t.start()

# === НАСТРОЙКИ БОТА ===
import os
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
FORUM_CHANNEL_ID = 1536815402724630539
ADMIN_CHANNEL_ID = 1536824673084379156  
CONTENT_ROLE_ID = 1536011600392228864   
MY_ADMIN_ID = 1340727420591800421       

class Bot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True     
        intents.presences = True   
        intents.message_content = True 
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        bot.add_view(StartPanelView())
        await self.tree.sync()

bot = Bot()

# === МОДАЛЬНОЕ ОКНО ДЛЯ ИГРОКА ===
class ApplicationModal(Modal, title="Заявка на Контент-Мейкера"):
    link_input = TextInput(
        label="Ссылка на ваш канал (YouTube/TikTok)",
        placeholder="https://youtube.com@...",
        required=True,
        max_length=200
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("Ваша заявка успешно отправлена на рассмотрение!", ephemeral=True)
        
        admin_chan = bot.get_channel(ADMIN_CHANNEL_ID)
        if admin_chan:
            embed = discord.Embed(
                title="🎥 Новая заявка на роль!",
                description=f"Пользователь {interaction.user.mention} хочет получить роль контент-мейкера!\n\n"
                            f"🔗 **Его ссылки:**\n{self.link_input.value}",
                color=discord.Color.purple()
            )
            await admin_chan.send(
                content=f"<@{MY_ADMIN_ID}>, {interaction.user.mention} хочет получить роль контент мейкера!",
                embed=embed,
                view=AdminDecisionView(user_id=interaction.user.id)
            )

# === ОКНО ДЛЯ ПРИЧИНЫ ОТКАЗА ===
class RejectReasonModal(Modal, title="Причина отказа"):
    reason_input = TextInput(
        label="Укажите причину отказа",
        placeholder="Например: Нет видео по Gorilla Tag",
        required=True,
        style=discord.TextStyle.paragraph
    )

    def __init__(self, member: discord.Member, message: discord.Message):
        super().__init__()
        self.member = member
        self.message = message

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            await self.member.send(f"❌ Ваша заявка на роль Контент-Мейкера была отклонена.\n**Причина:** {self.reason_input.value}")
        except discord.Forbidden:
            pass
            
        await self.message.edit(content=f"❌ Заявка пользователя {self.member.mention} отклонена.", view=None)

# === КНОПКИ ДЛЯ АДМИНОВ ===
class AdminDecisionView(View):
    def __init__(self, user_id: int):
        super().__init__(timeout=None)
        self.user_id = user_id

    @discord.ui.button(label="Одобрить ✅", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        
        member = guild.get_member(self.user_id)
        if not member:
            try: member = await guild.fetch_member(self.user_id)
            except: member = None
                
        role = guild.get_role(CONTENT_ROLE_ID)
        if not member or not role:
            await interaction.followup.send("❌ Ошибка: Не удалось найти пользователя или роль.", ephemeral=True)
            return
            
        try:
            await member.add_roles(role)
            await interaction.message.edit(content=f"✅ Роль успешно выдана пользователю {member.mention}!", view=None)
            try: await member.send(f"🎉 Поздравляем! Ваша заявка одобрена, вам выдана роль **{role.name}** на сервере Gorilla Tag! 🎬")
            except discord.Forbidden: pass
        except discord.Forbidden:
            await interaction.followup.send("❌ Ошибка иерархии ролей!", ephemeral=True)

    @discord.ui.button(label="Отказать ❌", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        member = guild.get_member(self.user_id) or await guild.fetch_member(self.user_id)
        if not member:
            await interaction.response.send_message("Пользователь покинул сервер.", ephemeral=True)
            return
        await interaction.response.send_modal(RejectReasonModal(member=member, message=interaction.message))

# === СТАРТОВАЯ ПАНЕЛЬ С КНОПКОЙ ===
class StartPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Отправить заявку 🚀", style=discord.ButtonStyle.blurple, custom_id="submit_content_app")
    async def submit_app(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(ApplicationModal())

# === СТАНДАРТНЫЙ ФУНКЦИОНАЛ И СОБЫТИЯ ===
currentpeople_group = app_commands.Group(name="currentpeople", description="Управление статистикой сервера")
bot.tree.add_command(currentpeople_group)

@tasks.loop(minutes=10)
async def update_stats():
    for guild in bot.guilds:
        category = discord.utils.get(guild.categories, name="CurrentPeople")
        if category:
            total_members = guild.member_count
            online_members = sum(1 for m in guild.members if m.status != discord.Status.offline and not m.bot)
            for channel in category.voice_channels:
                if "Всего:" in channel.name:
                    await channel.edit(name=f"📊 Всего: {total_members}")
                elif "В сети:" in channel.name:
                    await channel.edit(name=f"🟢 В сети: {online_members}")

@bot.event
async def on_ready():
    print("=========================================")
    print(f"Бот {bot.user} успешно запущен и работает!")
    print("=========================================")
    if not update_stats.is_running():
        update_stats.start()

@bot.event
async def on_message(message: discord.Message):
    if isinstance(message.channel, discord.Thread):
        if message.channel.parent_id == FORUM_CHANNEL_ID:
            if message.id == message.channel.id:
                await asyncio.sleep(1)
                embed = discord.Embed(
                    title="💡 Новое предложение!",
                    description="Обезьянки, вам нравится эта идея?\nГолосуйте реакциями ниже! 👇",
                    color=discord.Color.gold()
                )
                msg = await message.channel.send(embed=embed)
                await msg.add_reaction("👍")
                await msg.add_reaction("👎")

@currentpeople_group.command(name="setup", description="Создать каналы статистики")
@app_commands.checks.has_permissions(manage_channels=True)
async def setup(interaction: discord.Interaction):
    guild = interaction.guild
    existing_category = discord.utils.get(guild.categories, name="CurrentPeople")
    if existing_category:
        await interaction.response.send_message("Категория CurrentPeople уже создана!", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    category = await guild.create_category(name="CurrentPeople")
    total_members = guild.member_count
    online_members = sum(1 for m in guild.members if m.status != discord.Status.offline and not m.bot)
    overwrites = {guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=True)}
    await guild.create_voice_channel(name=f"📊 Всего: {total_members}", category=category, overwrites=overwrites)
    await guild.create_voice_channel(name=f"🟢 В сети: {online_members}", category=category, overwrites=overwrites)
    await interaction.followup.send("Категория и каналы статистики успешно созданы!")

@bot.tree.command(name="zov", description="Позвать игроков в Gorilla Tag")
@app_commands.describe(код_комнаты="Напиши код приватной комнаты", кого_позвать="Выбери кого пингануть")
async def zov(interaction: discord.Interaction, код_комнаты: str, кого_позвать: Literal["@here", "@everyone"]):
    if interaction.user.id != MY_ADMIN_ID:
        await interaction.response.send_message("❌ У вас нет прав на использование этой команды!", ephemeral=True)
        return
    mention = "@here" if кого_позвать == "@here" else "@everyone"
    embed = discord.Embed(
        title="🦍 Сбор в Gorilla Tag!",
        description=f"Собираемся в Gorilla Tag! \n**Код комнаты:** `{код_комнаты}`\nЖдём вас!",
        color=discord.Color.from_rgb(112, 66, 20) 
    )
    embed.set_footer(text=f"Организатор: {interaction.user.display_name}")
    await interaction.response.send_message(content=mention, embed=embed)

@bot.tree.command(name="send_panel", description="Отправить панель подачи заявок для контент-мейкеров")
@app_commands.checks.has_permissions(administrator=True)
async def send_panel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎥 Стань Контент-Мейкером сервера!",
        description="Привет! Если ты контент-мейкер по Горилла Таг, прошу, нажми кнопку ниже и вставь ссылку на свой канал (YouTube/TikTok), вашу заявку рассмотрят и выдадут роль!",
        color=discord.Color.purple()
    )
    await interaction.channel.send(embed=embed, view=StartPanelView())
    await interaction.response.send_message("Панель успешно отправлена!", ephemeral=True)

