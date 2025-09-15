import os
import json
import firebase_admin
from firebase_admin import credentials, auth
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


# Initialize Firebase Admin SDK
def initialize_firebase():
    """Initialize Firebase Admin SDK with service account credentials"""
    if not firebase_admin._apps:
        try:
            # Method 1: Using service account file (recommended for development)
            service_account_path = "whitepaper-ai-clone-firebase.creds.json"
            if os.path.exists(service_account_path):
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
                print("✅ Firebase Admin SDK initialized with service account file")
                return firebase_admin.get_app()

            # Method 2: Using environment variable (recommended for production)
            firebase_config = os.getenv("FIREBASE_CONFIG")
            if firebase_config:
                cred_dict = json.loads(firebase_config)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                print("✅ Firebase Admin SDK initialized with environment variable")
                return firebase_admin.get_app()

            # Method 3: Using individual environment variables
            if all(
                [
                    os.getenv("FIREBASE_PROJECT_ID"),
                    os.getenv("FIREBASE_PRIVATE_KEY"),
                    os.getenv("FIREBASE_CLIENT_EMAIL"),
                ]
            ):
                cred_dict = {
                    "type": "service_account",
                    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
                    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
                    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),
                    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
                    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{os.getenv('FIREBASE_CLIENT_EMAIL')}",
                }
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                print("✅ Firebase Admin SDK initialized with environment variables")
                return firebase_admin.get_app()

            # No credentials found
            raise Exception(
                "No Firebase credentials found. Please provide firebase-service-account.json or set environment variables."
            )

        except Exception as e:
            print(f"❌ Firebase initialization failed: {e}")
            raise e

    return firebase_admin.get_app()


# Security scheme
security = HTTPBearer()


async def verify_firebase_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify Firebase ID token - production only"""
    try:
        # Ensure Firebase is initialized
        if not firebase_admin._apps:
            raise HTTPException(
                status_code=500,
                detail="Firebase not initialized. Please check server configuration.",
            )

        # Verify the ID token
        decoded_token = auth.verify_id_token(credentials.credentials)
        return {
            "uid": decoded_token["uid"],
            "email": decoded_token.get("email"),
            "name": decoded_token.get("name"),
            "email_verified": decoded_token.get("email_verified", False),
        }
    except auth.InvalidIdTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")
    except auth.ExpiredIdTokenError:
        raise HTTPException(status_code=401, detail="Authentication token has expired")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


async def get_current_user(token_data: dict = Depends(verify_firebase_token)):
    """Get current user from verified Firebase token"""
    return token_data


# Initialize Firebase on import
try:
    initialize_firebase()
except Exception as e:
    print(f"⚠️  Firebase initialization failed on startup: {e}")
    print("Please ensure Firebase credentials are properly configured.")
