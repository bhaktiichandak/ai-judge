import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")

async def test_connection():
    try:
        client = AsyncIOMotorClient(MONGODB_URI)
        db = client["factshield"]

        # simple test
        result = await db.command("ping")
        print("✅ Connected to MongoDB!", result)

    except Exception as e:
        print("❌ Connection failed:", e)

asyncio.run(test_connection())