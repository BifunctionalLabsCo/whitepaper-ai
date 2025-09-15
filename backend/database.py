import os

from firebase_admin import firestore
from backend.firebase_config import initialize_firebase


class Database:
    client = None
    database = None


# Global database instance
db_instance = Database()


class FirestoreDatabase:
    def __init__(self, client):
        self.courses = FirestoreCollection(client.collection("courses"))
        self.user_progress = FirestoreCollection(client.collection("user_progress"))
        self.modules = FirestoreCollection(client.collection("modules"))

    async def update_quiz(self, module_id: str, quiz_data: dict):
        doc_ref = self.modules.collection_ref.document(module_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise ValueError("Module not found")

        doc_ref.update({"quiz": quiz_data})

    async def update_flashcards(self, module_id: str, flashcards: list):
        doc_ref = self.modules.collection_ref.document(module_id)
        doc = doc_ref.get()
        if not doc.exists:
            raise ValueError("Module not found")

        doc_ref.update({"flashcards": flashcards})


class FirestoreCollection:
    def __init__(self, collection_ref):
        self.collection_ref = collection_ref

    async def insert_one(self, document):
        doc_ref = self.collection_ref.document(document["id"])
        doc_ref.set(document)
        return {"inserted_id": document["id"]}

    async def find_one(self, filter_dict):
        query = self.collection_ref
        for key, value in filter_dict.items():
            query = query.where(key, "==", value)
        docs = query.limit(1).stream()
        docs = list(docs)
        return docs[0].to_dict() if docs else None

    def find(self, filter_dict):
        query = self.collection_ref
        for key, value in filter_dict.items():
            query = query.where(key, "==", value)
        return FirestoreCursor(query)

    async def update_one(self, filter_dict, update_dict):
        doc = await self.find_one(filter_dict)
        if not doc:
            return {"matched_count": 0, "modified_count": 0}
        doc_ref = self.collection_ref.document(doc["id"])
        if "$set" in update_dict:
            doc_ref.update(update_dict["$set"])
        return {"matched_count": 1, "modified_count": 1}

    async def create_index(self, index_spec):
        pass  # Firestore auto-indexes


class FirestoreCursor:
    def __init__(self, query):
        self.query = query

    async def to_list(self, length=None):
        docs = self.query.limit(length or 100).stream()
        return [doc.to_dict() for doc in docs]


def connect_to_db():
    # Ensure Firebase is initialized first
    initialize_firebase()
    print("✅ Connecting to Firestore")
    client = firestore.client()
    db_instance.client = client
    db_instance.database = FirestoreDatabase(client)
    return db_instance.database


async def startup_db():
    return connect_to_db()


async def shutdown_db():
    """Cleanup on shutdown"""
    pass
