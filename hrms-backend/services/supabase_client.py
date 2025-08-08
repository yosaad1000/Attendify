from supabase import create_client, Client
from config import settings
import logging

logger = logging.getLogger(__name__)

class SupabaseClient:
    _instance = None
    _client = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SupabaseClient, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            try:
                self._client: Client = create_client(
                    settings.SUPABASE_URL,
                    settings.SUPABASE_KEY
                )
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                raise
    
    @property
    def client(self) -> Client:
        return self._client
    
    def get_service_client(self) -> Client:
        """Get client with service role key for admin operations"""
        try:
            return create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY
            )
        except Exception as e:
            logger.error(f"Failed to create service client: {e}")
            raise

# Global instance
supabase_client = SupabaseClient()