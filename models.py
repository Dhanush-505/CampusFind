import datetime
from bson.objectid import ObjectId
from database import db_instance

class User:
    def __init__(self, id, name, roll_number, email, phone, password_hash, role, joined_date=None, profile_image=None):
        self.id = str(id)
        self.name = name
        self.roll_number = roll_number
        self.email = email
        self.phone = phone
        self.password_hash = password_hash
        self.role = role  # 'student', 'security', 'admin'
        self.joined_date = joined_date or datetime.date.today().strftime("%Y-%m-%d")
        self.profile_image = profile_image

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'roll_number': self.roll_number,
            'email': self.email,
            'phone': self.phone,
            'role': self.role,
            'joined_date': self.joined_date,
            'profile_image': self.profile_image
        }

    @staticmethod
    def from_mongo(doc):
        if not doc:
            return None
        return User(
            id=str(doc['_id']),
            name=doc.get('full_name') or doc.get('name', ''),
            roll_number=doc.get('roll_number', ''),
            email=doc.get('email', ''),
            phone=doc.get('phone', ''),
            password_hash=doc.get('password_hash', ''),
            role=doc.get('role', 'student'),
            joined_date=doc.get('joined_date') or (doc.get('created_at').strftime("%Y-%m-%d") if isinstance(doc.get('created_at'), datetime.datetime) else None),
            profile_image=doc.get('profile_image')
        )


class MongoDB:
    @property
    def db(self):
        return db_instance.get_db()

    # User Management
    def create_user(self, name, roll_number, email, phone, password_hash, role):
        now = datetime.datetime.utcnow()
        today = datetime.date.today().strftime("%Y-%m-%d")
        doc = {
            "full_name": name,
            "name": name,
            "roll_number": roll_number,
            "email": email.lower().strip(),
            "phone": phone,
            "password_hash": password_hash,
            "role": role,
            "profile_image": None,
            "created_at": now,
            "updated_at": now,
            "joined_date": today
        }
        res = self.db.users.insert_one(doc)
        doc['_id'] = res.inserted_id
        return User.from_mongo(doc)

    def get_user_by_id(self, user_id):
        if not user_id:
            return None
        try:
            query = {"_id": ObjectId(user_id)} if ObjectId.is_valid(user_id) else {"_id": user_id}
            doc = self.db.users.find_one(query)
            return User.from_mongo(doc)
        except Exception:
            return None

    def get_user_by_email(self, email):
        if not email:
            return None
        doc = self.db.users.find_one({"email": email.lower().strip()})
        return User.from_mongo(doc)

    def check_duplicate_email(self, email):
        if not email:
            return False
        return self.db.users.find_one({"email": email.lower().strip()}) is not None

    def check_duplicate_roll(self, roll_number):
        if not roll_number:
            return False
        return self.db.users.find_one({"roll_number": roll_number.strip()}) is not None

    def update_user_password(self, user_id, new_password_hash):
        try:
            query = {"_id": ObjectId(user_id)} if ObjectId.is_valid(user_id) else {"_id": user_id}
            self.db.users.update_one(
                query,
                {"$set": {"password_hash": new_password_hash, "updated_at": datetime.datetime.utcnow()}}
            )
            return True
        except Exception:
            return False

    # Items Management
    def add_item(self, creator_id, creator_name, creator_roll, creator_phone, item_name, description, filename, item_type='Lost', category=None, location=None, date=None, creator_email=None):
        now = datetime.datetime.utcnow()
        is_found = (item_type == 'Found')
        
        doc = {
            "title": item_name,
            "item": item_name,  # compatibility field
            "description": description,
            "category": category,
            "image": filename,
            "location": location,
            "location_found": location if is_found else None,
            "date": date,
            "date_lost": date if not is_found else None,
            "date_found": date if is_found else None,
            "type": item_type,
            "status": "Found" if is_found else "Active",
            "found": is_found,  # boolean status indicator
            "owner_id": str(creator_id),
            "creator_id": str(creator_id),  # compatibility field
            "owner_name": creator_name,
            "name": creator_name,  # compatibility field
            "roll": creator_roll,
            "phone": creator_phone,
            "owner_email": creator_email or "",
            "responses": [],
            "Responses": [],  # compatibility field
            "marked_found": is_found,
            "found_by": None,
            "created_at": now,
            "updated_at": now
        }

        # Store in main items collection as well as lost_items / found_items collections
        res = self.db.items.insert_one(doc)
        doc['_id'] = res.inserted_id

        if is_found:
            self.db.found_items.insert_one(doc.copy())
        else:
            self.db.lost_items.insert_one(doc.copy())

        return self.format_item(doc)

    def format_item(self, doc):
        if not doc:
            return None
        item_id = str(doc['_id'])
        owner_id = str(doc.get('owner_id') or doc.get('creator_id', ''))
        responses = doc.get('Responses') or doc.get('responses') or []
        
        # Normalize responses format
        normalized_responses = []
        for r in responses:
            normalized_responses.append({
                'name': r.get('name') or r.get('responder_name', ''),
                'roll': r.get('roll') or r.get('responder_roll', ''),
                'phone': r.get('phone') or r.get('responder_phone', ''),
                'Response': r.get('Response') or r.get('response_text') or r.get('response', '')
            })

        return {
            'id': item_id,
            '_id': item_id,
            'creator_id': owner_id,
            'owner_id': owner_id,
            'name': doc.get('name') or doc.get('owner_name', ''),
            'roll': doc.get('roll', ''),
            'phone': doc.get('phone', ''),
            'item': doc.get('item') or doc.get('title', ''),
            'title': doc.get('title') or doc.get('item', ''),
            'description': doc.get('description', ''),
            'image': doc.get('image'),
            'type': doc.get('type', 'Lost'),
            'found': bool(doc.get('found', False) or doc.get('status') == 'Found'),
            'category': doc.get('category'),
            'location': doc.get('location') or doc.get('location_found'),
            'date': doc.get('date') or doc.get('date_lost') or doc.get('date_found'),
            'Responses': normalized_responses,
            'responses': normalized_responses,
            'marked_found': bool(doc.get('marked_found', False)),
            'status': doc.get('status', 'Active')
        }

    def get_all_items(self):
        docs = list(self.db.items.find().sort("created_at", -1))
        return [self.format_item(doc) for doc in docs]

    def get_item_by_id(self, item_id):
        if not item_id:
            return None
        try:
            query = {"_id": ObjectId(item_id)} if ObjectId.is_valid(str(item_id)) else {"_id": str(item_id)}
            doc = self.db.items.find_one(query)
            return self.format_item(doc)
        except Exception:
            return None

    def mark_item_found(self, item_id):
        if not item_id:
            return False
        try:
            query = {"_id": ObjectId(item_id)} if ObjectId.is_valid(str(item_id)) else {"_id": str(item_id)}
            res = self.db.items.update_one(
                query,
                {"$set": {"found": True, "marked_found": True, "status": "Found", "type": "Found", "updated_at": datetime.datetime.utcnow()}}
            )
            if ObjectId.is_valid(str(item_id)):
                self.db.lost_items.update_one({"_id": ObjectId(item_id)}, {"$set": {"found": True, "marked_found": True, "status": "Found", "type": "Found"}})
            return res.modified_count > 0 or res.matched_count > 0
        except Exception as e:
            print(f"Error marking item found: {e}")
            return False

    def delete_item(self, item_id):
        if not item_id:
            return False
        try:
            query = {"_id": ObjectId(item_id)} if ObjectId.is_valid(str(item_id)) else {"_id": str(item_id)}
            res = self.db.items.delete_one(query)
            if ObjectId.is_valid(str(item_id)):
                self.db.lost_items.delete_one({"_id": ObjectId(item_id)})
                self.db.found_items.delete_one({"_id": ObjectId(item_id)})
            return res.deleted_count > 0
        except Exception as e:
            print(f"Error deleting item: {e}")
            return False

    def add_response(self, item_id, responder_name, responder_roll, responder_phone, response_text):
        if not item_id:
            return False
        try:
            response_obj = {
                "name": responder_name,
                "roll": responder_roll,
                "phone": responder_phone,
                "Response": response_text
            }
            query = {"_id": ObjectId(item_id)} if ObjectId.is_valid(str(item_id)) else {"_id": str(item_id)}
            res = self.db.items.update_one(
                query,
                {
                    "$push": {"Responses": response_obj, "responses": response_obj},
                    "$set": {"updated_at": datetime.datetime.utcnow()}
                }
            )
            return res.modified_count > 0
        except Exception as e:
            print(f"Error adding response: {e}")
            return False

db = MongoDB()
