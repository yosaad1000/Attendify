import os
import json
from dotenv import load_dotenv

# Load environment variables from .env if not in production
if not os.getenv("DOCKER_ENV"):
    load_dotenv()

class Config:
    # Flask Configuration
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecretkey")
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    
    # Face Recognition Settings
    FACE_THRESHOLD = 0.25
    FACE_ENCODING_DIMENSION = 128
    FACE_METRIC = "euclidean"
    
    # Pinecone Configuration
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_ENV = os.getenv("PINEONE_CLOUD", "aws")
    PINECONE_REGION = os.getenv("PINEONE_REGION", "us-east-1")
    PINECONE_INDEX_NAME = os.getenv("PINEONE_INDEX_NAME", "student-face-encodings")
    
    # Firebase Configuration
    FIREBASE_CREDENTIALS = json.loads(os.getenv("FIREBASE_CREDENTIALS"))
    
    # Session Management
    SESSION_CLEANUP_INTERVAL = 300  # 5 minutes
    SESSION_PENDING_TTL = 900  # 15 minutes
    SESSION_MAX_VIEWS = 3
    
    # Server Settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

config = Config()