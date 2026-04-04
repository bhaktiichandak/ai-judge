import motor.motor_asyncio
import os
from dotenv import load_dotenv
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb+srv://<user>:<pass>@cluster.mongodb.net/factshield?retryWrites=true&w=majority")
DB_NAME = "factshield"

client = None
db = None

async def connect_db():
    global client, db
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]
    await _create_indexes()
    print(f"[DB] Connected to MongoDB Atlas: {DB_NAME}")

async def close_db():
    if client:
        client.close()
        print("[DB] MongoDB connection closed")

async def _create_indexes():
    # claims collection
    await db.claims.create_indexes([
        IndexModel([("created_at", DESCENDING)]),
        IndexModel([("verdict", ASCENDING)]),
        IndexModel([("claim_text", TEXT)]),
        IndexModel([("session_id", ASCENDING)]),
        IndexModel([("credibility_score", DESCENDING)]),
    ])
    # evidence collection
    await db.evidence.create_indexes([
        IndexModel([("claim_id", ASCENDING)]),
        IndexModel([("source_type", ASCENDING)]),
        IndexModel([("credibility_score", DESCENDING)]),
        IndexModel([("retrieved_at", DESCENDING)]),
    ])
    # sources collection (trusted source registry)
    await db.sources.create_indexes([
        IndexModel([("domain", ASCENDING)], unique=True),
        IndexModel([("trust_score", DESCENDING)]),
        IndexModel([("category", ASCENDING)]),
    ])
    # sessions collection
    await db.sessions.create_indexes([
        IndexModel([("created_at", DESCENDING)]),
        IndexModel([("session_id", ASCENDING)], unique=True),
    ])
    print("[DB] Indexes created/verified")

def get_db():
    return db