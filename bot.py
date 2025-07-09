import discord
from discord import app_commands
import asyncio
import json
import os
import feedparser
from keep_alive import keep_alive

# Load config
with open("config.json") as f:
    config = json.load(f)

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = discord.Object(id=int(config["guild_id"]))
WELCOME_CHANNEL_ID = int(config["welcome_channel_id"])
GOODBYE_CHANNEL_ID = int(config["goodbye_channel_id"])
NOTIFY_CHANNEL_ID = int(config["notification_channel_id"])
WELCOME_MSG = config["welcome_message"]
GOODBYE_MSG = config["goodbye_message"]
TIKTOK_USER = config["tiktok_username"]

intents = discord.Intents.default()
intents.members = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
last_video = None

@client.event
async def on_ready():
    await tree.sync(guild=GUILD_ID)
    print(f"✅ Logged in as {client.user}")

@client.event
async def on_member_join(member):
    if member.guild.id != GUILD_ID.id:
        return
    channel = client.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        await channel.send(WELCOME_MSG.format(member=member.mention))

@client.event
async def on_member_remove(member):
    if member.guild.id != GUILD_ID.id:
        return
    channel = client.get_channel(GOODBYE_CHANNEL_ID)
    if channel:
        await channel.send(GOODBYE_MSG.format(member=member.name))

@tree.command(name="ping", description="Check if the bot is online", guild=GUILD_ID)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("🏓 Pong!")

@tree.command(name="setwelcome", description="Update welcome message", guild=GUILD_ID)
@app_commands.describe(message="Message with {member}")
async def setwelcome(interaction: discord.Interaction, message: str):
    global WELCOME_MSG
    WELCOME_MSG = message
    config["welcome_message"] = message
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)
    await interaction.response.send_message("✅ Welcome message updated!")

@tree.command(name="setgoodbye", description="Update goodbye message", guild=GUILD_ID)
@app_commands.describe(message="Message with {member}")
async def setgoodbye(interaction: discord.Interaction, message: str):
    global GOODBYE_MSG
    GOODBYE_MSG = message
    config["goodbye_message"] = message
    with open("config.json", "w") as f:
        json.dump(config, f, indent=4)
    await interaction.response.send_message("✅ Goodbye message updated!")

@tree.command(name="admin-speak", description="Make the bot speak in a specific channel", guild=GUILD_ID)
@app_commands.describe(channel="Channel to speak in", message="Text to send")
async def admin_speak(
    interaction: discord.Interaction,
    channel: discord.TextChannel,
    message: str
):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message("🚫 You need **Manage Channels** permission to use this.", ephemeral=True)
        return

    try:
        await channel.send(message)
        await interaction.response.send_message(f"✅ Sent to {channel.mention}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

async def check_tiktok():
    global last_video
    await client.wait_until_ready()
    channel = client.get_channel(NOTIFY_CHANNEL_ID)
    feed_url = f"https://rsshub.app/tiktok/user/video/{TIKTOK_USER}"
    while not client.is_closed():
        try:
            feed = feedparser.parse(feed_url)
            if feed.entries:
                latest = feed.entries[0]
                if latest.link != last_video:
                    last_video = latest.link
                    embed = discord.Embed(
                        title=f"🎥 New TikTok from @{TIKTOK_USER}",
                        url=latest.link,
                        description=latest.title
                    )
                    if "media_thumbnail" in latest:
                        embed.set_thumbnail(url=latest.media_thumbnail[0]['url'])
                    await channel.send(embed=embed)
        except Exception as e:
            print(f"[ERROR] TikTok check failed: {e}")
        await asyncio.sleep(120)

keep_alive()
client.loop.create_task(check_tiktok())
client.run(TOKEN)