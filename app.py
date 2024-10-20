import os
import json
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
import face_recognition
from PIL import Image, ImageDraw
import pickle

# Flask app setup
app = Flask(__name__)

# Paths to store uploaded images and student images
UPLOAD_FOLDER = 'uploads'   # For uploaded attendance images
STUDENT_FOLDER = 'students' # For registered student images
STUDENT_DATA_FILE = 'students_data.json'  # File to store student data
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['STUDENT_FOLDER'] = STUDENT_FOLDER

# Function to initialize student data file if it doesn't exist
def init_student_data():
    if not os.path.exists(STUDENT_DATA_FILE):
        with open(STUDENT_DATA_FILE, 'w') as f:
            json.dump([], f)

# Function to read student data from JSON file
def get_student_data():
    with open(STUDENT_DATA_FILE, 'r') as f:
        return json.load(f)

# Function to save student data to JSON file
def save_student_data(student_data):
    with open(STUDENT_DATA_FILE, 'w') as f:
        json.dump(student_data, f)

# Function to add a new student to the JSON file
def add_student_to_file(name, student_id, face_encoding):
    student_data = get_student_data()
    student_data.append({
        'name': name,
        'student_id': student_id,
        'face_encoding': pickle.dumps(face_encoding).decode('latin1')  # Convert encoding to storable format
    })
    save_student_data(student_data)

# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route to render the home page
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register_student', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        # Get student details from the form
        name = request.form['name']
        student_id = request.form['student_id']
        
        # Handle file upload
        if 'file' not in request.files:
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['STUDENT_FOLDER'], filename)
            file.save(filepath)

            # Perform face encoding
            image = face_recognition.load_image_file(filepath)
            face_encodings = face_recognition.face_encodings(image)

            if len(face_encodings) > 0:
                face_encoding = face_encodings[0]

                # Save student data and face encoding to JSON file
                add_student_to_file(name, student_id, face_encoding)

                return redirect(url_for('index'))
            else:
                return "No face detected in the uploaded image. Please try again."

    return render_template('register.html')

# Upload an image for attendance check
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        # Load the uploaded image and extract face encodings
        uploaded_image = face_recognition.load_image_file(filepath)
        uploaded_face_encodings = face_recognition.face_encodings(uploaded_image)
        face_locations = face_recognition.face_locations(uploaded_image)

        # Load known students' face encodings from JSON
        student_data = get_student_data()
        known_face_encodings = []
        known_face_names = []

        for student in student_data:
            known_face_encodings.append(pickle.loads(student['face_encoding'].encode('latin1')))  # Convert back from storable format
            known_face_names.append(student['student_id'])  # Student ID or name

        # Compare faces in the uploaded image to the known faces
        matches = []
        for uploaded_face_encoding in uploaded_face_encodings:
            # Check for matches against known faces
            results = face_recognition.compare_faces(known_face_encodings, uploaded_face_encoding)
            if True in results:
                match_index = results.index(True)
                matches.append(known_face_names[match_index])  # Matched student name or ID
            else:
                matches.append("Unknown")  # No match found, label as "Unknown"

        # Draw rectangles around all detected faces and label them
        pil_image = Image.fromarray(uploaded_image)
        draw = ImageDraw.Draw(pil_image)

        for (top, right, bottom, left), match in zip(face_locations, matches):
            # Draw a rectangle around the face
            draw.rectangle(((left, top), (right, bottom)), outline=(0, 255, 0), width=5)
            
            # Label the face
            draw.text((left + 6, bottom + 6), match, fill=(255, 255, 255, 255))

        # Save the output image
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'output_' + filename)
        pil_image.save(output_path)

        return redirect(url_for('uploaded_file', filename='output_' + filename))

    return redirect(request.url)

# Serve the output images
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Ensure required folders and JSON file exist
if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(STUDENT_FOLDER, exist_ok=True)
    init_student_data()
    app.run(debug=True)
