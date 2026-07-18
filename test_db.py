import sys
from config import Config
import pymongo

print("Connecting to MongoDB Atlas...")
print("URI:", Config.MONGODB_URI)

try:
    client = pymongo.MongoClient(Config.MONGODB_URI, serverSelectionTimeoutMS=8000)
    res = client.admin.command('ping')
    print("PING SUCCESSFUL:", res)
    
    db = client[Config.DATABASE_NAME]
    collections = db.list_collection_names()
    print("Collections in database:", collections)
    
    users_count = db.users.count_documents({})
    items_count = db.items.count_documents({})
    print(f"Users in DB: {users_count}")
    print(f"Items in DB: {items_count}")
    print("\nSUCCESS: Connected to MongoDB Atlas successfully!")
except Exception as e:
    print("\nERROR connecting to MongoDB Atlas:")
    print(e)
