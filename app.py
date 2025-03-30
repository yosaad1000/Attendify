import os
import json
import base64
import logging
import numpy as np
from io import BytesIO
from PIL import Image, ImageDraw
import face_recognition
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from datetime import date
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
if not os.getenv("DOCKER_ENV"):
    load_dotenv()

# Initialize Firebase
firebase_config = json.loads(os.getenv("FIREBASE_CREDENTIALS"))
cred = credentials.Certificate(firebase_config)
firebase_admin.initialize_app(cred)
firestore_db = firestore.client()

# Initialize Pinecone
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
INDEX_NAME = os.getenv("PINEONE_INDEX_NAME", "student-face-encodings")

# Create Pinecone index if it doesn't exist
if INDEX_NAME not in pc.list_indexes().names():
    pc.create_index(
        name=INDEX_NAME,
        dimension=128,
        metric="euclidean",
        spec=ServerlessSpec(
            cloud=os.getenv("PINEONE_CLOUD", "aws"),
            region=os.getenv("PINEONE_REGION", "us-east-1")
        )
    )

student_index = pc.Index(INDEX_NAME)

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
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}

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

def process_image_for_attendance(image_data):
    """Process image for attendance marking"""
    np_image = face_recognition.load_image_file(BytesIO(image_data))
    face_locations = face_recognition.face_locations(np_image)
    face_encodings = face_recognition.face_encodings(np_image, face_locations)
    
    if not face_encodings:
        raise ValueError("No faces detected")
    
    pil_image = Image.fromarray(np_image)
    draw = ImageDraw.Draw(pil_image)
    recognized_students = []

    for face_encoding, location in zip(face_encodings, face_locations):
        results = student_index.query(
            vector=face_encoding.tolist(),
            top_k=1,
            include_metadata=True
        )

        if results['matches'] and results['matches'][0]['score'] < 0.25:
            match = results['matches'][0]
            student_id = match['id']
            name = match['metadata'].get('name', 'Unknown')
            log_attendance(student_id)
            recognized_students.append({'student_id': student_id, 'name': name})
            color = (0, 255, 0)  # Green
        else:
            name = "Unknown"
            color = (255, 0, 0)  # Red

        top, right, bottom, left = location
        draw.rectangle(((left, top), (right, bottom)), outline=color, width=5)
        draw.text((left + 6, bottom + 6), name, fill=(0, 0, 0, 255))

    img_io = BytesIO()
    pil_image.save(img_io, 'JPEG')
    img_io.seek(0)
    
    return base64.b64encode(img_io.getvalue()).decode('ascii'), recognized_students

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
        img_data, results = process_image_for_attendance(file.read())
        return render_template('uploaded_file.html',
                             img_data=img_data,
                             recognition_results=results)
    except ValueError as e:
        return str(e), 400
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return f"Error processing image: {str(e)}", 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('', filename)

@app.route('/capture')
def capture():
    return render_template('capture.html')

if __name__ == '__main__':
    app.run(debug=True)