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

    def format_item(self, doc, current_user_id=None):
        if not doc:
            return None
        item_id = str(doc['_id'])
        owner_id = str(doc.get('owner_id') or doc.get('creator_id', ''))
        responses = doc.get('Responses') or doc.get('responses') or []
        
        current_user_id_str = str(current_user_id) if current_user_id else None
        
        normalized_responses = []
        for r in responses:
            responder_id_str = str(r.get('responder_id', ''))
            r_owner_id = str(r.get('owner_id', owner_id))
            
            # THE FIX: Removed the privacy block that was hiding responses from other users.
            # Everyone can now see all responses appended to this item.

            resp_id = str(r.get('response_id') or r.get('_id', ''))
            r_name = r.get('responder_name') or r.get('name', '')
            r_role = r.get('responder_role', 'student')
            r_roll = r.get('responder_roll') or r.get('roll', '')
            r_phone = r.get('responder_phone') or r.get('phone', '')
            msg = r.get('message') or r.get('Response') or r.get('response_text', '')
            created_at = r.get('created_at')
            if isinstance(created_at, datetime.datetime):
                created_at = created_at.isoformat()

            normalized_responses.append({
                'response_id': resp_id,
                'item_id': item_id,
                'responder_id': responder_id_str,
                'responder_name': r_name,
                'responder_role': r_role,
                'responder_roll': r_roll,
                'responder_phone': r_phone,
                'message': msg,
                'created_at': created_at or '',
                'is_read': bool(r.get('is_read', False)),
                'owner_id': r_owner_id,
                'name': r_name,
                'roll': r_roll,
                'phone': r_phone,
                'Response': msg
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

    def get_all_items(self, current_user_id=None):
        docs = list(self.db.items.find().sort("created_at", -1))
        return [self.format_item(doc, current_user_id=current_user_id) for doc in docs]

    def get_item_by_id(self, item_id, current_user_id=None):
        if not item_id:
            return None
        try:
            query = {"_id": ObjectId(item_id)} if ObjectId.is_valid(str(item_id)) else {"_id": str(item_id)}
            doc = self.db.items.find_one(query)
            return self.format_item(doc, current_user_id=current_user_id)
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

    def delete_item(self, item_id, current_user_id=None):
        if not item_id:
            return False

        try:
            # Fetch the item first and verify ownership if current_user_id is provided
            item = self.get_item_by_id(item_id)
            if not item:
                return False

            if current_user_id and str(item.get('owner_id')) != str(current_user_id):
                print("Unauthorized delete attempt.")
                return False

            # Proceed with deletion if ownership matches or bypass is granted
            query = {"_id": ObjectId(item_id)} if ObjectId.is_valid(str(item_id)) else {"_id": str(item_id)}
            res = self.db.items.delete_one(query)

            if ObjectId.is_valid(str(item_id)):
                self.db.lost_items.delete_one({"_id": ObjectId(item_id)})
                self.db.found_items.delete_one({"_id": ObjectId(item_id)})

            return res.deleted_count > 0
        except Exception as e:
            print(f"Error deleting item: {e}")
            return False

    def update_item(self, item_id, item_name=None, description=None, location=None, category=None, filename=None):
        if not item_id:
            return False
        try:
            update_data = {"updated_at": datetime.datetime.utcnow()}
            if item_name:
                update_data["title"] = item_name
                update_data["item"] = item_name
            if description is not None:
                update_data["description"] = description
            if location is not None:
                update_data["location"] = location
                update_data["location_found"] = location
            if category is not None:
                update_data["category"] = category
            if filename:
                update_data["image"] = filename

            query = {"_id": ObjectId(item_id)} if ObjectId.is_valid(str(item_id)) else {"_id": str(item_id)}
            res = self.db.items.update_one(query, {"$set": update_data})
            if ObjectId.is_valid(str(item_id)):
                self.db.lost_items.update_one({"_id": ObjectId(item_id)}, {"$set": update_data})
                self.db.found_items.update_one({"_id": ObjectId(item_id)}, {"$set": update_data})

            return res.modified_count > 0 or res.matched_count > 0
        except Exception as e:
            print(f"Error updating item: {e}")
            return False

    def add_response(self, item_id, responder_id, responder_name, responder_role, responder_roll, responder_phone, message):
        if not item_id:
            return False
        try:
            item = self.get_item_by_id(item_id)
            if not item:
                return False
            owner_id = str(item.get('owner_id') or item.get('creator_id', ''))
            
            response_id = str(ObjectId())
            now = datetime.datetime.utcnow().isoformat()
            
            response_obj = {
                "response_id": response_id,
                "item_id": str(item_id),
                "responder_id": str(responder_id),
                "responder_name": responder_name,
                "responder_role": responder_role,
                "responder_roll": responder_roll,
                "responder_phone": responder_phone,
                "message": message,
                "created_at": now,
                "is_read": False,
                "owner_id": owner_id,
                "name": responder_name,
                "roll": responder_roll,
                "phone": responder_phone,
                "Response": message
            }
            
            query = {"_id": ObjectId(item_id)} if ObjectId.is_valid(str(item_id)) else {"_id": str(item_id)}
            res = self.db.items.update_one(
                query,
                {
                    "$push": {"responses": response_obj, "Responses": response_obj},
                    "$set": {"updated_at": datetime.datetime.utcnow()}
                }
            )
            if ObjectId.is_valid(str(item_id)):
                self.db.lost_items.update_one({"_id": ObjectId(item_id)}, {"$push": {"responses": response_obj, "Responses": response_obj}})
                self.db.found_items.update_one({"_id": ObjectId(item_id)}, {"$push": {"responses": response_obj, "Responses": response_obj}})

            return res.modified_count > 0
        except Exception as e:
            print(f"Error adding response: {e}")
            return False

db = MongoDB()
