# main.py
import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import yaml
import os
import aiohttp
from io import BytesIO

class DiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        self._ensure_files()
        self.config = self._load_yaml("config.yml")
        self.data = self._load_yaml("data.yml")
        
    def _ensure_files(self):
        if not os.path.exists("config.yml"):
            default_config = {"token": "YOUR_BOT_TOKEN_HERE"}
            with open("config.yml", 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, allow_unicode=True)
            print("config.yml created. Please add your bot token.")
        
        if not os.path.exists("data.yml"):
            with open("data.yml", 'w', encoding='utf-8') as f:
                yaml.dump({}, f, allow_unicode=True)
            print("data.yml created.")
    
    def _load_yaml(self, filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    
    def _save_data(self):
        with open("data.yml", 'w', encoding='utf-8') as f:
            yaml.dump(self.data, f, allow_unicode=True)
    
    def _get_user_setting(self, user_id, key, default=True):
        return self.data.get(str(user_id), {}).get(key, default)
    
    def _set_user_setting(self, user_id, key, value):
        user_id = str(user_id)
        if user_id not in self.data:
            self.data[user_id] = {}
        self.data[user_id][key] = value
        self._save_data()

    async def setup_hook(self):
        await self.tree.sync()

bot = DiscordBot()

async def download_avatar(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.read()
                return Image.open(BytesIO(data)).convert('RGBA')
    return None

def create_circular_avatar(avatar_img, size):
    avatar_img = avatar_img.resize((size, size), Image.Resampling.LANCZOS)
    mask = Image.new('L', (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)
    
    output = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    output.paste(avatar_img, (0, 0))
    output.putalpha(mask)
    return output

async def create_card(user):
    width, height = 900, 400
    img = Image.new('RGB', (width, height), color='#2c2f33')
    draw = ImageDraw.Draw(img)
    
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 42)
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
    except:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    avatar_url = user.display_avatar.url
    avatar_img = await download_avatar(avatar_url)
    
    if avatar_img:
        avatar_size = 150
        circular_avatar = create_circular_avatar(avatar_img, avatar_size)
        avatar_x = 80
        avatar_y = (height - avatar_size) // 2
        img.paste(circular_avatar, (avatar_x, avatar_y), circular_avatar)
    
    text_x = 280
    
    draw.text((text_x, 80), user.name, fill='#ffffff', font=font_large)
    draw.text((text_x, 140), f"UID: {user.id}", fill='#99aab5', font=font_medium)
    
    created_date = user.created_at.strftime("%Y-%m-%d")
    draw.text((text_x, 200), f"Created: {created_date}", fill='#99aab5', font=font_small)
    
    age = (datetime.now(user.created_at.tzinfo) - user.created_at).days
    years = age // 365
    months = (age % 365) // 30
    days = (age % 365) % 30
    
    age_text = f"Age: {years}y {months}m {days}d"
    draw.text((text_x, 250), age_text, fill='#99aab5', font=font_small)
    
    output_path = f"temp_{user.id}.png"
    img.save(output_path)
    return output_path

@bot.tree.command(name="uid", description="Display user info by UID")
@app_commands.describe(uid="User ID")
async def uid_command(interaction: discord.Interaction, uid: str):
    try:
        user = await bot.fetch_user(int(uid))
    except:
        await interaction.response.send_message("User not found", ephemeral=True)
        return
    
    show_output = bot._get_user_setting(interaction.user.id, "show_output", True)
    
    if show_output:
        card_path = await create_card(user)
        await interaction.response.send_message(file=discord.File(card_path))
        os.remove(card_path)
    else:
        created_date = user.created_at.strftime("%Y-%m-%d")
        age = (datetime.now(user.created_at.tzinfo) - user.created_at).days
        years = age // 365
        months = (age % 365) // 30
        days = (age % 365) % 30
        
        message = f"**{user.name}**\nUID: {user.id}\nCreated: {created_date}\nAge: {years}y {months}m {days}d"
        await interaction.response.send_message(message)

@bot.tree.command(name="name", description="Display user info by name")
@app_commands.describe(name="Username")
async def name_command(interaction: discord.Interaction, name: str):
    guild = interaction.guild
    if not guild:
        await interaction.response.send_message("This command only works in servers", ephemeral=True)
        return
    
    member = discord.utils.get(guild.members, name=name)
    if not member:
        member = discord.utils.get(guild.members, display_name=name)
    
    if not member:
        await interaction.response.send_message("User not found", ephemeral=True)
        return
    
    show_output = bot._get_user_setting(interaction.user.id, "show_output", True)
    
    if show_output:
        card_path = await create_card(member)
        await interaction.response.send_message(file=discord.File(card_path))
        os.remove(card_path)
    else:
        created_date = member.created_at.strftime("%Y-%m-%d")
        age = (datetime.now(member.created_at.tzinfo) - member.created_at).days
        years = age // 365
        months = (age % 365) // 30
        days = (age % 365) % 30
        
        message = f"**{member.name}**\nUID: {member.id}\nCreated: {created_date}\nAge: {years}y {months}m {days}d"
        await interaction.response.send_message(message)

@bot.tree.command(name="settings", description="Configure output settings")
@app_commands.describe(out="Show canvas output")
@app_commands.choices(out=[
    app_commands.Choice(name="true", value=1),
    app_commands.Choice(name="false", value=0)
])
async def settings_command(interaction: discord.Interaction, out: app_commands.Choice[int]):
    bot._set_user_setting(interaction.user.id, "show_output", bool(out.value))
    status = "enabled" if out.value else "disabled"
    await interaction.response.send_message(f"Canvas output {status}", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

if __name__ == "__main__":
    token = bot.config.get("token")
    if not token or token == "YOUR_BOT_TOKEN_HERE":
        print("Please set your bot token in config.yml")
        exit(1)
    bot.run(token)
