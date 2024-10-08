import os
import cv2
import face_recognition
import mediapipe as mp
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw

# Flask app setup
app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
STUDENT_FOLDER = 'students'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['STUDENT_FOLDER'] = STUDENT_FOLDER

# Ensure upload and student directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STUDENT_FOLDER, exist_ok=True)

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

# Upload image to check for students' presence
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

        # Perform face detection on the uploaded image
        uploaded_image = face_recognition.load_image_file(filepath)
        uploaded_face_encodings = face_recognition.face_encodings(uploaded_image)

        # Load student images and check for matches
        students_present = []
        for student_image_name in os.listdir(STUDENT_FOLDER):
            student_image_path = os.path.join(STUDENT_FOLDER, student_image_name)
            student_image = face_recognition.load_image_file(student_image_path)
            student_face_encoding = face_recognition.face_encodings(student_image)[0]

            # Check if student face is present in uploaded image
            matches = face_recognition.compare_faces(uploaded_face_encodings, student_face_encoding)
            if True in matches:
                students_present.append(student_image_name)

        return render_template('check_result.html', students_present=students_present)

    return redirect(request.url)

# Page to capture students' photos using MediaPipe
@app.route('/capture')
def capture():
    return render_template('capture.html')

@app.route('/save_student', methods=['POST'])
def save_student():
    student_name = request.form['student_name']
    
    # Check if a file was submitted
    if 'student_image' not in request.files:
        return "No file part", 400

    file = request.files['student_image']

    # If no file is selected, return an error
    if file.filename == '':
        return "No selected file", 400

    # Check if the file is allowed (by extension)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        
        # Save the file to the upload folder
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        print(f"Student name: {student_name}")
        print(f"Uploaded file: {filename}")

        return redirect(url_for('index'))
    else:
        return "File not allowed", 400


if __name__ == '__main__':
    app.run(debug=True)
