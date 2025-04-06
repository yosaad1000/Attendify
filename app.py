import os
import base64
import logging
import numpy as np
from io import BytesIO
from PIL import Image, ImageDraw
import face_recognition
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
from werkzeug.utils import secure_filename
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime, timedelta
import time
import uuid
import threading
from config import config
from pinecone import Pinecone, ServerlessSpec


app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Firebase
cred = credentials.Certificate(config.FIREBASE_CREDENTIALS)
firebase_admin.initialize_app(cred)
firestore_db = firestore.client()

# Initialize Pinecone
pc = Pinecone(api_key=config.PINECONE_API_KEY)
student_index = pc.Index(config.PINECONE_INDEX_NAME)

# Create Pinecone index if it doesn't exist
if config.PINECONE_INDEX_NAME not in pc.list_indexes().names():
    pc.create_index(
        name=config.PINECONE_INDEX_NAME,
        dimension=config.FACE_ENCODING_DIMENSION,
        metric=config.FACE_METRIC,
        spec=ServerlessSpec(
            cloud=config.PINECONE_ENV,
            region=config.PINECONE_REGION
        )
    )


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


# Create a global instance of the session manager
session_manager = SessionManager()

def log_attendance(student_id):
    """Log attendance in Firestore if not already logged today"""
    try:
        today = date.today().isoformat()
        attendance_ref = firestore_db.collection('attendance')
        
        query = (attendance_ref
                .where(filter=FieldFilter('student_id', '==', student_id))
                .where(filter=FieldFilter('attendance_date', '==', today))
                .limit(1))
        
        if not query.get():
            attendance_ref.add({
                'student_id': student_id,
                'timestamp': firestore.SERVER_TIMESTAMP,
                'attendance_date': today
            })
            return True
        return False
    except Exception as e:
        logger.error(f"Error logging attendance: {e}")
        return False

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS

def process_image_for_registration(image_data, student_id, name):
    """Process image for student registration"""
    np_image = face_recognition.load_image_file(BytesIO(image_data))
    face_locations = face_recognition.face_locations(np_image)
    
    if not face_locations:
        raise ValueError("No faces found in the image")
    
    face_encodings = face_recognition.face_encodings(np_image, face_locations)
    if not face_encodings:
        raise ValueError("No face encodings found")
    
    face_encoding = face_encodings[0]
    face_encoding_np = np.array(face_encoding, dtype=np.float32)

    student_index.upsert(vectors=[{
        "id": student_id,
        "values": face_encoding_np.tolist(),
        "metadata": {"name": name, "student_id": student_id}
    }])


# Route handlers
@app.route('/')
def attendify():
    return render_template('attendify.html')

@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/uploading')
def uploading():
    return render_template('upload.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        return redirect(url_for('index'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    try:
        # Get all unique attendance dates
        attendance_dates = {doc.to_dict()['attendance_date'] 
                          for doc in firestore_db.collection('attendance').stream()}
        total_days = len(attendance_dates)

        # Get all students with attendance data
        attendance_results = []
        for student in firestore_db.collection('students').stream():
            student_data = student.to_dict()
            student_id = student_data['student_id']
            
            present_dates = {att.to_dict()['attendance_date'] 
                           for att in firestore_db.collection('attendance')
                           .where(filter=FieldFilter('student_id', '==', student_id)).stream()}
            
            days_present = len(present_dates)
            percentage = round((days_present / total_days * 100), 2) if total_days > 0 else 0

            attendance_results.append({
                'student_id': student_id,
                'name': student_data['name'],
                'days_present': days_present,
                'total_days': total_days,
                'percentage': percentage
            })

        return render_template('dashboard.html', 
                           attendance_data=attendance_results, 
                           total_days=total_days)
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        return f"An error occurred: {e}", 500

@app.route('/register_student', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        name = request.form['name']
        student_id = request.form['student_id']
        
        if firestore_db.collection('students').document(student_id).get().exists:
            return "Student ID already registered", 400

        # Get image from either file upload or camera capture
        image_data = None
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                image_data = file.read()
        elif 'captured_image' in request.form:
            image_data = base64.b64decode(request.form['captured_image'].split(',')[1])

        if not image_data:
            return "No image provided", 400

        try:
            process_image_for_registration(image_data, student_id, name)
            firestore_db.collection('students').document(student_id).set({
                'student_id': student_id,
                'name': name
            })
            return redirect(url_for('index'))
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return f"Error processing registration: {str(e)}", 500

    return render_template('register.html')



@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file selected", 400
    
    file = request.files['file']
    if not file or not allowed_file(file.filename):
        return "Invalid file type", 400

    try:
        # Process the image and return a session ID
        session_id = start_processing_image(file.read())
        return render_template('processing.html', session_id=session_id)
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return f"Error processing image: {str(e)}", 500


def start_processing_image(image_data):
    """Start processing the image in the background and return a session ID"""
    # Load the image
    np_image = face_recognition.load_image_file(BytesIO(image_data))
    
    # Create a new session
    session_id = session_manager.create_session(np_image)
    
    # Start a background thread to process faces
    threading.Thread(target=process_faces_background, args=(session_id,)).start()
    
    return session_id


def process_faces_background(session_id):
    """Process faces in the background and update results progressively"""
    # Get the session data
    session_data = session_manager.get_session(session_id)
    if not session_data:
        return
    
    np_image = session_data['image']
    
    try:
        # Detect all face locations first
        face_locations = face_recognition.face_locations(np_image)
        
        if not face_locations:
            session_manager.update_session(session_id, {
                'status': 'completed',
                'error': 'No faces detected'
            })
            return
        
        # Create a copy of the image for drawing
        pil_image = Image.fromarray(np_image)
        draw = ImageDraw.Draw(pil_image)
        
        # Process each face one by one
        processed_faces = []
        for i, location in enumerate(face_locations):
            top, right, bottom, left = location
            
            # Get face encoding
            face_encoding = face_recognition.face_encodings(np_image, [location])[0]
            
            # Query student database
            results = student_index.query(
                vector=face_encoding.tolist(),
                top_k=1,
                include_metadata=True
            )
            
            # Process results
            if results['matches'] and results['matches'][0]['score'] < config.FACE_THRESHOLD:
                match = results['matches'][0]
                student_id = match['id']
                name = match['metadata'].get('name', 'Unknown')
                log_attendance(student_id)
                color = (0, 255, 0)  # Green
            else:
                student_id = None
                name = "Unknown"
                color = (255, 0, 0)  # Red
            
            # Draw rectangle and name on the image
            draw.rectangle(((left, top), (right, bottom)), outline=color, width=5)
            draw.text((left + 6, bottom + 6), name, fill=(0, 0, 0, 255))
            
            # Create a cropped image of just this face
            face_img = pil_image.crop((left, top, right, bottom))
            face_img_io = BytesIO()
            face_img.save(face_img_io, 'JPEG')
            face_img_io.seek(0)
            face_img_data = base64.b64encode(face_img_io.getvalue()).decode('ascii')
            
            # Save the processed face data
            face_data = {
                'id': i,
                'student_id': student_id,
                'name': name, 
                'face_img': face_img_data,
                'processed_at': datetime.now().isoformat()
            }
            
            # Add to our list of processed faces
            processed_faces.append(face_data)
            
            # Update the session with the new face
            session_manager.update_session(session_id, {
                'processed_faces': processed_faces
            })
        
        # Save the full processed image
        full_img_io = BytesIO()
        pil_image.save(full_img_io, 'JPEG')
        full_img_io.seek(0)
        full_image_data = base64.b64encode(full_img_io.getvalue()).decode('ascii')
        
        # Mark processing as completed
        session_manager.update_session(session_id, {
            'status': 'completed',
            'full_image': full_image_data
        })
        
    except Exception as e:
        # If an error occurs, mark the session as failed
        session_manager.update_session(session_id, {
            'status': 'error',
            'error': str(e)
        })


@app.route('/face_status/<session_id>')
def face_status(session_id):
    """API endpoint to get the current status of face processing"""
    session_data = session_manager.get_session(session_id)
    if not session_data:
        return jsonify({'error': 'Session not found'}), 404
    
    return jsonify({
        'status': session_data['status'],
        'processed_faces': session_data['processed_faces'],
        'error': session_data.get('error'),
        'full_image': session_data.get('full_image') if session_data['status'] == 'completed' else None,
        'total_faces': len(session_data.get('processed_faces', []))
    })

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('', filename)

@app.route('/capture')
def capture():
    return render_template('capture.html')

if __name__ == '__main__':
    app.run(debug=True)
