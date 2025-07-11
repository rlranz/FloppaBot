import json
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

with open("config.json") as f:
    config = json.load(f)

client = MongoClient(config["mongo_uri"])
db = client["floppabot"]

try:
    client.admin.command("ping")
    print("✅ MongoDB connected")
except ConnectionFailure as e:
    print(f"❌ MongoDB connection failed: {e}")

users_col = db["users"]
warnings_col = db["warnings"]
birthdays_col = db["birthdays"]
reports_col = db["reports"]
settings_col = db["settings"]

def set_guild_channel(guild_id, key, channel_id):
    settings_col.update_one({"_id": str(guild_id)}, {"$set": {f"channels.{key}": str(channel_id)}}, upsert=True)

def get_guild_channel(guild_id, key):
    doc = settings_col.find_one({"_id": str(guild_id)})
    return int(doc["channels"].get(key)) if doc and "channels" in doc and key in doc["channels"] else None

def set_guild_message(guild_id, key, message):
    settings_col.update_one({"_id": str(guild_id)}, {"$set": {f"messages.{key}": message}}, upsert=True)

def get_guild_message(guild_id, key):
    doc = settings_col.find_one({"_id": str(guild_id)})
    return doc["messages"].get(key) if doc and "messages" in doc and key in doc["messages"] else None

def set_tiktok(guild_id, username):
    settings_col.update_one({"_id": str(guild_id)}, {"$set": {"tiktok": username}}, upsert=True)

def get_tiktok(guild_id):
    doc = settings_col.find_one({"_id": str(guild_id)})
    return doc.get("tiktok") if doc else None

def add_user(user_id, name):
    users_col.update_one({"_id": user_id}, {"$set": {"name": name}}, upsert=True)

def add_warning(user_id, reason, mod):
    warnings_col.update_one(
        {"_id": user_id},
        {"$inc": {"count": 1}, "$push": {"reasons": {"reason": reason, "mod": mod}}},
        upsert=True
    )

def get_warnings(user_id):
    return warnings_col.find_one({"_id": user_id})

def add_report(report_id, reporter_id, reported_id, reason):
    reports_col.insert_one({
        "_id": report_id,
        "reporter": reporter_id,
        "reported": reported_id,
        "reason": reason
    })
