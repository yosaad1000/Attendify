import os
import base64
import logging
import numpy as np
from io import BytesIO
from PIL import Image, ImageDraw
import face_recognition
from flask import Flask, render_template, request, redirect, url_for, Response, send_from_directory
from werkzeug.utils import secure_filename
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec
from datetime import date

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env file when running locally
if not os.getenv("DOCKER_ENV"):  # Check if running inside Docker
    load_dotenv()

# Get environment variables
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("PINEONE_INDEX_NAME", "student-face-encodings")
PINECONE_CLOUD = os.getenv("PINEONE_CLOUD", "aws")
PINECONE_REGION = os.getenv("PINEONE_REGION", "us-east-1")

# Initialize Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)

# Create Pinecone index if it doesn't exist
if INDEX_NAME not in pc.list_indexes().names():
    pc.create_index(
        name=INDEX_NAME,
        dimension=128,
        metric="euclidean",
        spec=ServerlessSpec(
            cloud=PINECONE_CLOUD,
            region=PINECONE_REGION
        )
    )

# Connect to the Pinecone index
student_index = pc.Index(INDEX_NAME)

# Configure database
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT')
DB_NAME = os.getenv('DB_NAME')

# SQLAlchemy configuration
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Define models
class Student(db.Model):
    __tablename__ = 'students'
    student_id = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    attendances = db.relationship('Attendance', backref='student', lazy=True)

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), db.ForeignKey('students.student_id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=func.now())
    attendance_date = db.Column(db.Date, default=date.today)

# Initialize database
with app.app_context():
    db.create_all()

def log_attendance(student_id):
    """Log attendance using SQLAlchemy"""
    try:
        # Check if attendance for today already exists
        existing_attendance = Attendance.query.filter_by(
            student_id=student_id, 
            attendance_date=date.today()
        ).first()
        
        # If no attendance record for today, create one
        if not existing_attendance:
            new_attendance = Attendance(student_id=student_id)
            db.session.add(new_attendance)
            db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Error logging attendance: {e}")
        db.session.rollback()
        return False

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg'}

# Routes
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
        # Using SQLAlchemy for queries
        from sqlalchemy import func, distinct

        # Count total days (distinct attendance dates)
        total_days_query = db.session.query(
            func.count(distinct(Attendance.attendance_date))
        ).scalar()
        total_days = total_days_query or 0

        # Query for student attendance data
        attendance_data = db.session.query(
            Student.student_id,
            Student.name,
            func.count(distinct(Attendance.attendance_date)).label('days_present')
        ).outerjoin(
            Attendance, Student.student_id == Attendance.student_id
        ).group_by(
            Student.student_id, Student.name
        ).all()

        # Format the results
        attendance_results = []
        for student in attendance_data:
            percentage = round((student.days_present / total_days * 100), 2) if total_days > 0 else 0
            attendance_results.append({
                'student_id': student.student_id,
                'name': student.name,
                'days_present': student.days_present,
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
        image_data = None

        # Check if student already exists
        existing_student = Student.query.filter_by(student_id=student_id).first()
        if existing_student:
            return "Student ID already registered", 400

        # Handle image input
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                image_data = file.read()
        elif 'captured_image' in request.form:
            image_data = base64.b64decode(request.form['captured_image'].split(',')[1])

        if not image_data:
            return "No image provided", 400

        try:
            # Process image and store embeddings
            np_image = face_recognition.load_image_file(BytesIO(image_data))

            # Detect faces in the image
            face_locations = face_recognition.face_locations(np_image)
            if not face_locations:
                return "No faces found in the image", 400

            # Extract face encodings
            face_encodings = face_recognition.face_encodings(np_image, face_locations)
            if not face_encodings:
                return "No face encodings found", 400

            # Get the first face encoding (assuming one face per image)
            face_encoding = face_encodings[0]
            face_encoding_np = np.array(face_encoding, dtype=np.float32)

            # Store face encoding and metadata in Pinecone
            student_index.upsert(
                vectors=[{
                    "id": student_id,
                    "values": face_encoding_np.tolist(),
                    "metadata": {
                        "name": name,
                        "student_id": student_id
                    }
                }]
            )
            
            # Store in SQLAlchemy
            new_student = Student(student_id=student_id, name=name)
            db.session.add(new_student)
            db.session.commit()
            
            return redirect(url_for('index'))
        
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            db.session.rollback()
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
        # Process image in memory
        image_data = file.read()
        np_image = face_recognition.load_image_file(BytesIO(image_data))
        
        # Detect faces
        face_locations = face_recognition.face_locations(np_image)
        face_encodings = face_recognition.face_encodings(np_image, face_locations)
        
        if not face_encodings:
            return "No faces detected", 400
        
        # Annotate image
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

        # Save annotated image to memory
        img_io = BytesIO()
        pil_image.save(img_io, 'JPEG')
        img_io.seek(0)
        
        img_data = base64.b64encode(img_io.getvalue()).decode('ascii')
    
        # Return results with embedded image
        return render_template('uploaded_file.html',
                             img_data=img_data,
                             recognition_results=recognized_students)
    
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