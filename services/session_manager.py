from config import config
import time
from datetime import datetime, timedelta
import uuid
import threading

class SessionManager:
    def __init__(self, cleanup_interval=300, pending_ttl=900):
        self.sessions = {}
        self.lock = threading.RLock()  # Reentrant lock for thread safety
        self.cleanup_interval = config.SESSION_CLEANUP_INTERVAL  # Cleanup every 5 minutes
        self.pending_ttl = config.SESSION_PENDING_TTL  # Pending/incomplete sessions expire after 15 minutes
        
        # Start the cleanup thread for abandoned sessions
        self.cleanup_thread = threading.Thread(target=self._cleanup_abandoned_sessions, daemon=True)
        self.cleanup_thread.start()
    
    def create_session(self, image_data):
        """Create a new processing session"""
        print("Creating new session")
        with self.lock:
            session_id = str(uuid.uuid4())
            self.sessions[session_id] = {
                'image': image_data,
                'processed_faces': [],
                'status': 'processing',
                'created_at': datetime.now(),
                'last_accessed': datetime.now(),
                'viewed_count': 0  # Track how many times the completed result has been viewed
            }
            return session_id
    
    def get_session(self, session_id):
        """Get session data and update last accessed time"""
        print("Getting session data")
        with self.lock:
            if session_id not in self.sessions:
                return None
            
            # Update last accessed time
            session_data = self.sessions[session_id]
            session_data['last_accessed'] = datetime.now()
            
            # If session is completed, increment the viewed counter
            if session_data['status'] == 'completed':
                session_data['viewed_count'] += 1
                
                # If it's been viewed 3 times after completion, mark for cleanup
                # This gives the frontend enough time to get the final result
                if session_data['viewed_count'] >= config.SESSION_MAX_VIEWS:
                    self._mark_for_cleanup(session_id)
                    
            return session_data
    
    def update_session(self, session_id, updates):
        """Update session with new data"""
        print("Updating session data")
        with self.lock:
            if session_id not in self.sessions:
                return False
            
            # Update the session data
            session_data = self.sessions[session_id]
            for key, value in updates.items():
                if key != 'created_at':  # Don't allow changing creation time
                    session_data[key] = value
            
            # Update last accessed time
            session_data['last_accessed'] = datetime.now()
            
            # If status is being set to completed, handle completion
            if updates.get('status') == 'completed':
                # Reset viewed count when marking complete
                session_data['viewed_count'] = 0
            
            return True
    
    def _mark_for_cleanup(self, session_id):
        """Mark a session for cleanup or remove it immediately"""
        print("Marking session for cleanup")
        # Remove immediately
        if session_id in self.sessions:
            del self.sessions[session_id]
            print(f"Session {session_id} has been removed after completion")
    
    def _cleanup_abandoned_sessions(self):
        """Background thread to clean up abandoned sessions"""
        print("Starting session cleanup thread")
        while True:
            time.sleep(self.cleanup_interval)
            try:
                now = datetime.now()
                expired_sessions = []
                
                with self.lock:
                    # Find abandoned sessions (started but never completed)
                    for session_id, data in self.sessions.items():
                        # Only clean up sessions that are still processing but haven't been
                        # accessed in a while (likely abandoned uploads)
                        if (data['status'] == 'processing' and 
                            now - data['last_accessed'] > timedelta(seconds=self.pending_ttl)):
                            expired_sessions.append(session_id)
                    
                    # Delete expired sessions
                    for session_id in expired_sessions:
                        del self.sessions[session_id]
                
                if expired_sessions:
                    print(f"Cleaned up {len(expired_sessions)} abandoned sessions")
            except Exception as e:
                print(f"Error in session cleanup: {str(e)}")