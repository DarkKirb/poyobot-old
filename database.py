import motor.motor_asyncio
import json

with open("config.json") as f:
    config = json.load(f)
client = motor.motor_asyncio.AsyncIOMotorClient()
db = client[config["database"]]


