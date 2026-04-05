import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URI = "your_connection_string_here"

async def test_connection():
    try:
        client = AsyncIOMotorClient(MONGODB_URI)
        db = client["factshield"]

        # ping test
        result = await db.command("ping")
        print("✅ Connected to MongoDB:", result)

    except Exception as e:
        print("❌ Connection failed:", e)

asyncio.run(test_connection())