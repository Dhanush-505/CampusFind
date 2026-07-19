import pymongo
from pymongo import MongoClient
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash
import datetime
from config import Config

class Database:
    def __init__(self):
        self.uri = Config.MONGODB_URI
        self.db_name = Config.DATABASE_NAME
        self.client = None
        self.db = None
        self.connect()

    def connect(self):
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            self.db = self.client[self.db_name]
            # Quick server check
            self.client.admin.command('ping')
            print(f"Successfully connected to MongoDB database '{self.db_name}'")
            self._init_db()
        except Exception as e:
            print(f"MongoDB Connection Warning: {e}")

    def get_db(self):
        if self.db is None:
            self.connect()
        return self.db

    def _init_db(self):
        db = self.db
        if db is None:
            return

        # Create unique indexes for users collection
        try:
            db.users.create_index([("email", pymongo.ASCENDING)], unique=True)
            db.users.create_index([("roll_number", pymongo.ASCENDING)], unique=True, sparse=True)
            db.lost_items.create_index([("owner_id", pymongo.ASCENDING)])
            db.found_items.create_index([("owner_id", pymongo.ASCENDING)])
            db.items.create_index([("owner_id", pymongo.ASCENDING)])
            db.items.create_index([("created_at", pymongo.DESCENDING)])
            db.items.create_index([("status", pymongo.ASCENDING)])
            db.items.create_index([("category", pymongo.ASCENDING)])
            db.items.create_index([("responses.responder_id", pymongo.ASCENDING)])
            db.items.create_index([("responses.owner_id", pymongo.ASCENDING)])
            db.items.create_index([("responses.item_id", pymongo.ASCENDING)])
        except Exception as e:
            print(f"Index creation notice: {e}")

        # Seed initial default accounts if users collection is empty
        if db.users.count_documents({}) == 0:
            today = datetime.date.today().strftime("%Y-%m-%d")
            default_users = [
                {
                    "full_name": "Admin User",
                    "name": "Admin User",
                    "roll_number": "CF-ADMIN-01",
                    "email": "admin@campusfind.com",
                    "phone": "1234567890",
                    "password_hash": generate_password_hash("AdminPassword123"),
                    "role": "admin",
                    "profile_image": None,
                    "created_at": datetime.datetime.utcnow(),
                    "updated_at": datetime.datetime.utcnow(),
                    "joined_date": today
                },
                {
                    "full_name": "Alice Student",
                    "name": "Alice Student",
                    "roll_number": "STUDENT-01",
                    "email": "alice@student.com",
                    "phone": "9876543210",
                    "password_hash": generate_password_hash("StudentPassword123"),
                    "role": "student",
                    "profile_image": None,
                    "created_at": datetime.datetime.utcnow(),
                    "updated_at": datetime.datetime.utcnow(),
                    "joined_date": today
                },
                {
                    "full_name": "Bob Security",
                    "name": "Bob Security",
                    "roll_number": "STAFF-01",
                    "email": "bob@security.com",
                    "phone": "9998887776",
                    "password_hash": generate_password_hash("SecurityPassword123"),
                    "role": "security",
                    "profile_image": None,
                    "created_at": datetime.datetime.utcnow(),
                    "updated_at": datetime.datetime.utcnow(),
                    "joined_date": today
                }
            ]
            db.users.insert_many(default_users)
            print("Seeded default users (Admin, Alice Student, Bob Security) into MongoDB.")

db_instance = Database()
