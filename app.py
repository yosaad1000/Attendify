import os
import base64
import logging
import numpy as np
from io import BytesIO
from PIL import Image, ImageDraw
import face_recognition
from flask import Flask, render_template, request, redirect, url_for, Response, send_from_directory
from werkzeug.utils import secure_filename
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec







# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
########################################
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
        metric="euclidean",  # Changed from cosine
        spec=ServerlessSpec(
            cloud=PINECONE_CLOUD,
            region=PINECONE_REGION
        )
    )

# Connect to the Pinecone index
student_index = pc.Index(INDEX_NAME)
########################################
# # Pinecone configuration
# PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
# INDEX_NAME = os.getenv("PINEONE_INDEX_NAME", "student-face-encodings")
# pc = Pinecone(api_key=PINECONE_API_KEY)

# # Create or connect to Pinecone index
# if INDEX_NAME not in pc.list_indexes().names():
#     pc.create_index(
#         name=INDEX_NAME,
#         dimension=128,
#         metric="euclidean",
#         spec=ServerlessSpec(
#             cloud="aws",
#             region="us-east-1"
#         )
#     )
# index = pc.Index(INDEX_NAME)

# PostgreSQL configuration
DB_CONFIG = {
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT')
}

def get_db_connection():
    """Create a PostgreSQL database connection"""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        logger.error(f"Database connection error: {e}")
        return None

def init_database():
    """Initialize database tables"""
    commands = (
        """
        CREATE TABLE IF NOT EXISTS students (
            student_id VARCHAR(50) PRIMARY KEY,
            name VARCHAR(100) NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS attendance (
            id SERIAL PRIMARY KEY,
            student_id VARCHAR(50) REFERENCES students(student_id),
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            attendance_date DATE DEFAULT CURRENT_DATE
        )
        """)
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        for command in commands:
            cur.execute(command)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error initializing database: {e}")

init_database()

def log_attendance(student_id):
    """Log attendance in PostgreSQL"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO attendance (student_id)
            SELECT %s WHERE NOT EXISTS (
                SELECT 1 FROM attendance 
                WHERE student_id = %s 
                AND attendance_date = CURRENT_DATE
            )
        """, (student_id, student_id))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error logging attendance: {e}")
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
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        cur.execute("""
            SELECT s.student_id, s.name,
                COUNT(DISTINCT a.attendance_date) AS days_present,
                (SELECT COUNT(DISTINCT attendance_date) FROM attendance) AS total_days
            FROM students s
            LEFT JOIN attendance a ON s.student_id = a.student_id
            GROUP BY s.student_id, s.name
        """)
        attendance_data = cur.fetchall()
        
        total_days = attendance_data[0]['total_days'] if attendance_data else 0
        for student in attendance_data:
            student['percentage'] = round((student['days_present'] / total_days * 100), 2) if total_days > 0 else 0
        
        cur.close()
        conn.close()
        return render_template('dashboard.html', 
                             attendance_data=attendance_data, 
                             total_days=total_days)
    except Exception as e:
        return f"An error occurred: {e}", 500

@app.route('/register_student', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        name = request.form['name']
        student_id = request.form['student_id']
        image_data = None


        # Check if student already exists
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT student_id FROM students WHERE student_id = %s", (student_id,))
        if cur.fetchone():
            cur.close()
            conn.close()
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

            ############################



            # Detect faces in the image
            face_locations = face_recognition.face_locations    (np_image)
            if not face_locations:
                return "No faces found in the image", 400

            # Extract face encodings
            face_encodings = face_recognition.face_encodings    (np_image, face_locations)
            if not face_encodings:
                return "No face encodings found", 400

            # Get the first face encoding (assuming one     face per image)
            face_encoding = face_encodings[0]
            face_encoding_np = np.array(face_encoding,  dtype=np.float32)

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
#################################################
            # face_encodings = face_recognition.face_encodings(np_image)
            
            # if not face_encodings:
            #     return "No face detected", 400
            
            # # Store in Pinecone
            # index.upsert(
            #     vectors=[
            #         {
            #             "id": student_id,
            #             "values": face_encodings[0].tolist(),
            #             "metadata": {"name": name}
            #         }
            #     ]
            # )
            
            # Store in PostgreSQL
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO students (student_id, name)
                VALUES (%s, %s)
                ON CONFLICT (student_id) DO UPDATE
                SET name = EXCLUDED.name
            """, (student_id, name))
            conn.commit()
            cur.close()
            conn.close()
            
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

        # # Save annotated image to memory
        img_io = BytesIO()
        pil_image.save(img_io, 'JPEG')
        img_io.seek(0)
        
        # # Return results with in-memory image
        # return render_template('uploaded_file.html',
        #                      filename='processed_image.jpg',
        #                      recognition_results=recognized_students)

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
    init_database()
    app.run(debug=True)
