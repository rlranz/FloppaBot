import discord
from discord import app_commands
import asyncio
import json
import os
import feedparser
import database
from dotenv import load_dotenv
import datetime

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

class FloppaClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.members = True
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self.last_video_links = {}

    async def setup_hook(self):
        await self.tree.sync()
        self.loop.create_task(self.check_tiktok())
        self.loop.create_task(self.check_birthdays())
        print(f"✅ Logged in as {self.user}")

    async def check_tiktok(self):
        await self.wait_until_ready()
        while not self.is_closed():
            for guild in self.guilds:
                tiktok = database.get_tiktok(guild.id)
                channel_id = database.get_guild_channel(guild.id, "notify")
                channel = self.get_channel(channel_id) if channel_id else None
                if tiktok and channel:
                    feed_url = f"https://rsshub.app/tiktok/user/video/{tiktok}"
                    feed = feedparser.parse(feed_url)
                    if feed.entries:
                        link = feed.entries[0].link
                        if guild.id not in self.last_video_links or self.last_video_links[guild.id] != link:
                            self.last_video_links[guild.id] = link
                            embed = discord.Embed(title=f"🎥 New TikTok by @{tiktok}", url=link)
                            await channel.send(embed=embed)
            await asyncio.sleep(120)

    async def check_birthdays(self):
        await self.wait_until_ready()
        while not self.is_closed():
            today = datetime.datetime.utcnow().strftime("%m-%d")
            for guild in self.guilds:
                bchan_id = database.get_guild_channel(guild.id, "birthday")
                if not bchan_id:
                    continue
                bchan = self.get_channel(bchan_id)
                for member in guild.members:
                    bdata = database.get_birthday(str(member.id))
                    if bdata and bdata.get("birthday") == today:
                        await bchan.send(f"🎉 Happy Birthday {member.mention}!")
            await asyncio.sleep(86400)

client = FloppaClient()
tree = client.tree

@client.event
async def on_member_join(member):
    channel_id = database.get_guild_channel(member.guild.id, "welcome")
    message = database.get_guild_message(member.guild.id, "welcome") or f"Welcome {member.mention}!"
    if channel_id:
        channel = client.get_channel(channel_id)
        if channel:
            await channel.send(message.format(member=member.mention))
    database.add_user(str(member.id), member.name)

@client.event
async def on_member_remove(member):
    channel_id = database.get_guild_channel(member.guild.id, "goodbye")
    message = database.get_guild_message(member.guild.id, "goodbye") or f"Goodbye {member.name}."
    if channel_id:
        channel = client.get_channel(channel_id)
        if channel:
            await channel.send(message.format(member=member.name))

# --------- Slash Commands ---------

@tree.command(name="ping", description="Check if bot is alive")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!", ephemeral=True)

@tree.command(name="setchannel", description="Set a bot channel (per server)")
@app_commands.choices(type=[
    app_commands.Choice(name="Welcome", value="welcome"),
    app_commands.Choice(name="Goodbye", value="goodbye"),
    app_commands.Choice(name="Notify", value="notify"),
    app_commands.Choice(name="Report", value="report"),
    app_commands.Choice(name="Birthday", value="birthday")
])
@app_commands.describe(type="Channel type", channel="Channel to use")
async def setchannel(interaction: discord.Interaction, type: app_commands.Choice[str], channel: discord.TextChannel):
    database.set_guild_channel(interaction.guild.id, type.value, channel.id)
    await interaction.response.send_message(f"✅ Set {type.name} channel to {channel.mention}", ephemeral=True)

@tree.command(name="setmessage", description="Set welcome/goodbye/warn message")
@app_commands.choices(type=[
    app_commands.Choice(name="Welcome", value="welcome"),
    app_commands.Choice(name="Goodbye", value="goodbye"),
    app_commands.Choice(name="Warn", value="warn")
])
@app_commands.describe(type="Message type", message="Message content with {member} or {reason}")
async def setmessage(interaction: discord.Interaction, type: app_commands.Choice[str], message: str):
    database.set_guild_message(interaction.guild.id, type.value, message)
    await interaction.response.send_message(f"✅ Updated {type.name} message.", ephemeral=True)

@tree.command(name="settiktok", description="Set TikTok username")
@app_commands.describe(username="TikTok username")
async def settiktok(interaction: discord.Interaction, username: str):
    database.set_tiktok(interaction.guild.id, username)
    await interaction.response.send_message(f"✅ TikTok username set to @{username}", ephemeral=True)

@tree.command(name="warn", description="Warn a user and DM them")
@app_commands.describe(user="User to warn", reason="Reason for warning")
async def warn(interaction: discord.Interaction, user: discord.Member, reason: str):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("🚫 You don't have permission to warn.", ephemeral=True)
        return

    database.add_warning(str(user.id), reason, interaction.user.name)
    warn_msg = database.get_guild_message(interaction.guild.id, "warn")
    if not warn_msg:
        warn_msg = "You have been warned for: {reason}"

    try:
        await user.send(warn_msg.format(reason=reason))
    except:
        pass

    await interaction.response.send_message(f"⚠️ Warned {user.mention} for: {reason}", ephemeral=True)

@tree.command(name="report", description="Report a user")
@app_commands.describe(user="User to report", reason="Reason")
async def report(interaction: discord.Interaction, user: discord.Member, reason: str):
    channel_id = database.get_guild_channel(interaction.guild.id, "report")
    channel = client.get_channel(channel_id) if channel_id else None
    if not channel:
        await interaction.response.send_message("⚠️ Report channel not set.", ephemeral=True)
        return

    report_id = f"{interaction.user.id}-{user.id}-{int(datetime.datetime.utcnow().timestamp())}"
    database.add_report(report_id, interaction.user.id, user.id, reason)
    embed = discord.Embed(title="🚨 New Report", color=discord.Color.red())
    embed.add_field(name="Reporter", value=interaction.user.mention)
    embed.add_field(name="Reported", value=user.mention)
    embed.add_field(name="Reason", value=reason)
    await channel.send(embed=embed)
    await interaction.response.send_message("✅ Report sent.", ephemeral=True)

@tree.command(name="kick", description="Kick a user")
@app_commands.describe(user="User to kick", reason="Reason")
async def kick(interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("🚫 You don't have permission to kick.", ephemeral=True)
        return
    try:
        await user.kick(reason=reason)
        await interaction.response.send_message(f"✅ Kicked {user.mention} for: {reason}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to kick: {e}", ephemeral=True)

@tree.command(name="ban", description="Ban a user")
@app_commands.describe(user="User to ban", reason="Reason")
async def ban(interaction: discord.Interaction, user: discord.Member, reason: str = "No reason provided"):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("🚫 You don't have permission to ban.", ephemeral=True)
        return
    try:
        await user.ban(reason=reason)
        await interaction.response.send_message(f"✅ Banned {user.mention} for: {reason}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed to ban: {e}", ephemeral=True)

client.run(TOKEN)
