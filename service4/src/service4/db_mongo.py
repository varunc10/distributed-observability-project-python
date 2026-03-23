from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["tracing_python"]
orders_collection = db["orders"]
user_collection = db["users"]