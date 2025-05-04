import os
import json
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
# import face_recognition
from PIL import Image, ImageDraw
import pickle
import cv2
# import dlib
from flask import Response
from base64 import b64decode
from io import BytesIO
import time

import csv
from datetime import datetime
import pandas as pd
from flask import render_template







# # Flask app setup
app = Flask(__name__)

# # Paths to store uploaded images and student images
# UPLOAD_FOLDER = 'uploads'   # For uploaded attendance images
# STUDENT_FOLDER = 'students' # For registered student images
# STUDENT_DATA_FILE = 'students_data.json'  # File to store student data
# ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
# app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# app.config['STUDENT_FOLDER'] = STUDENT_FOLDER


# ATTENDANCE_FILE = 'attendance.csv'  # Path to your attendance file
# # Function to log attendance
# def log_attendance(student_id):
#     # Check if the file exists; if not, create it with headers
#     if not os.path.exists(ATTENDANCE_FILE):
#         with open(ATTENDANCE_FILE, mode='w', newline='') as file:
#             writer = csv.writer(file)
#             writer.writerow(['Student ID', 'Timestamp'])

#     # Append the attendance log
#     with open(ATTENDANCE_FILE, mode='a', newline='') as file:
#         writer = csv.writer(file)
#         timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
#         writer.writerow([student_id, timestamp])


# # Function to initialize student data file if it doesn't exist
# def init_student_data():
#     if not os.path.exists(STUDENT_DATA_FILE):
#         with open(STUDENT_DATA_FILE, 'w') as f:
#             json.dump([], f)

# # Function to read student data from JSON file
# def get_student_data():
#     try:
#         with open(STUDENT_DATA_FILE, 'r') as f:
#             return json.load(f)
#     except (FileNotFoundError, json.JSONDecodeError):
#         return []  # Return an empty list if the file is missing or corrupted

# # Function to save student data to JSON file
# def save_student_data(student_data):
#     try:
#         with open(STUDENT_DATA_FILE, 'w') as f:
#             json.dump(student_data, f)
#     except IOError as e:
#         print(f"Error saving student data: {e}")

# # Function to add a new student or update an existing student
# def add_student_to_file(name, student_id, face_encoding):
#     try:
#         student_data = get_student_data()

#         # Check if the student already exists
#         student_exists = False
#         for student in student_data:
#             if student['student_id'] == student_id:
#                 # Update the existing student's data
#                 student['name'] = name
#                 student['face_encoding'] = pickle.dumps(face_encoding).decode('latin1')  # Update face encoding
#                 student_exists = True
#                 break

#         # If the student does not exist, add a new record
#         if not student_exists:
#             student_data.append({
#                 'name': name,
#                 'student_id': student_id,
#                 'face_encoding': pickle.dumps(face_encoding).decode('latin1')
#             })

#         # Save updated student data
#         save_student_data(student_data)
#     except Exception as e:
#         print(f"Error adding or updating student: {e}")


# # Function to check allowed file extensions
# def allowed_file(filename):
#     return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



# # Global variable to store the last captured frame
# captured_frame = None

# def generate_camera_feed():
#     global captured_frame
#     detector = dlib.get_frontal_face_detector()
#     predictor = dlib.shape_predictor('shape_predictor_68_face_landmarks.dat')  # Ensure this file is downloaded and in the same directory

#     # Access the camera
#     video_capture = cv2.VideoCapture(0)
#     while True:
#         ret, frame = video_capture.read()
#         if not ret:
#             break
        
#         # Convert frame to grayscale
#         gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
#         # Detect faces in the frame
#         faces = detector(gray)
#         for face in faces:
#             # Predict facial landmarks
#             landmarks = predictor(gray, face)
            
#             # Draw facial landmarks on the frame
#             for n in range(0, 68):
#                 x = landmarks.part(n).x
#                 y = landmarks.part(n).y
#                 cv2.circle(frame, (x, y), 2, (0, 255, 0), -1)
            
#             # Draw a rectangle around the face
#             x1, y1, x2, y2 = face.left(), face.top(), face.right(), face.bottom()
#             cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
        
#         # Save the last processed frame
#         captured_frame = frame.copy()
        
#         # Encode the frame as JPEG
#         _, buffer = cv2.imencode('.jpg', frame)
#         frame_data = buffer.tobytes()
        
#         yield (b'--frame\r\n'
#                b'Content-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n')
    
#     video_capture.release()

# def update_total_days():
#     """Update the total days column in attendance.csv."""
#     csv_file_path = 'attendance.csv'
    
#     # Ensure the file exists
#     if not os.path.exists(csv_file_path):
#         with open(csv_file_path, 'w') as f:
#             writer = csv.writer(f)
#             writer.writerow(['student_id', 'name', 'timestamp', 'total_days'])  # Add headers

#     # Read the file into a DataFrame
#     df = pd.read_csv(csv_file_path)

#     if df.empty:
#         return 0  # No records yet

#     # Extract unique dates from the timestamp column
#     df['date'] = pd.to_datetime(df['timestamp']).dt.date
#     unique_days = df['date'].nunique()

#     # Update the total_days column
#     df['total_days'] = unique_days

#     # Drop the temporary 'date' column
#     df.drop(columns=['date'], inplace=True)

#     # Write the updated DataFrame back to the CSV
#     df.to_csv(csv_file_path, index=False)

#     return unique_days





# Route for Attendify page
@app.route('/')
def attendify():
    return render_template('attendify.html')

# Route to render the home page
@app.route('/index')
def index():

    return render_template('index.html')

# Route to upload
@app.route('/uploading')
def uploading():
    return render_template('upload.html')


# Route for Sign-Up page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    # if request.method == 'POST':
    #     # You can process the sign-up form data here if needed
    #     return redirect(url_for('index'))
    return render_template('signup.html')

# Route for Log-In page
@app.route('/login', methods=['GET', 'POST'])
def login():
    # if request.method == 'POST':
    #     # You can process the log-in form data here if needed
    #     return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    # try:
    #     # Load attendance data
    #     csv_file_path = 'attendance.csv'  # Path to your attendance file
    #     if not os.path.exists(csv_file_path):
    #         return "Attendance file not found.", 404

    #     # Read attendance CSV into a DataFrame
    #     df = pd.read_csv(csv_file_path, header=None, names=['student_id', 'timestamp'])

    #     # Add a placeholder for 'name' if student names are unavailable
    #     df['name'] = df['student_id']  # Temporarily use student IDs as names

    #     # Calculate attendance counts and percentages
    #     attendance_summary = df.groupby(['student_id', 'name']).size().reset_index(name='days_present')
    #     total_days = df['timestamp'].apply(lambda x: x.split()[0]).nunique()  # Unique days based on timestamp
    #     attendance_summary['percentage'] = (attendance_summary['days_present'] / total_days * 100).round(2)

    #     # Convert to dictionary for passing to template
    #     attendance_data = attendance_summary.to_dict(orient='records')

        # return render_template('dashboard.html', attendance_data=attendance_data, total_days=total_days)
    return render_template('dashboard.html')
    # except Exception as e:
    #     return f"An error occurred: {e}", 500



@app.route('/register_student', methods=['GET', 'POST'])
def register_student():
    # if request.method == 'POST':
    #     # Get student details
    #     name = request.form['name']
    #     student_id = request.form['student_id']

    #     # Check if the student already exists
    #     student_data = get_student_data()
    #     existing_student = next((s for s in student_data if s['student_id'] == student_id), None)

    #     # Handle image data (manual upload or camera capture)
    #     if 'file' in request.files:  # Manual upload
    #         file = request.files['file']
    #         if file and allowed_file(file.filename):
    #             filename = secure_filename(file.filename)
    #             filepath = os.path.join(app.config['STUDENT_FOLDER'], filename)
    #             file.save(filepath)

    #             # Process the uploaded image for face encoding
    #             image = face_recognition.load_image_file(filepath)
    #     elif 'captured_image' in request.form:  # Real-time camera capture

    #         captured_image_data = request.form['captured_image']
    #         if captured_image_data:
    #             # Decode Base64 image data
    #             image_data = b64decode(captured_image_data.split(',')[1])
    #             image = Image.open(BytesIO(image_data))
    #             filepath = os.path.join(app.config['STUDENT_FOLDER'], f"{name}_{student_id}.png")
    #             image.save(filepath)
    #         else:
    #             return "No image captured. Please try again.", 400
    #     else:
    #         return "No image provided. Please upload or capture an image.", 400

    #     # Extract face encodings from the image
    #     face_encodings = face_recognition.face_encodings(face_recognition.load_image_file(filepath))
    #     if not face_encodings:
    #         return "No face detected in the image. Please try again with a different image.", 400

    #     face_encoding = face_encodings[0]

    #     if existing_student:
    #         # Update existing student's face encoding
    #         existing_student['face_encoding'] = pickle.dumps(face_encoding).decode('latin1')
    #         save_student_data(student_data)
    #         # return f"Student {name} (ID: {student_id}) updated successfully!"
    #         return redirect(url_for('index'))
    #     else:
    #         # Add new student
    #         add_student_to_file(name, student_id, face_encoding)
    #         # return f"Student {name} (ID: {student_id}) registered successfully!"
    #         return redirect(url_for('index'))


    return render_template('register.html')

    

@app.route('/capture', methods=['GET', 'POST'])
def capture():
    # if request.method == 'POST':
    #     # When the user clicks "Capture" in the template, save the captured frame
    #     filename = "captured_student.jpg"
    #     filepath = os.path.join(app.config['STUDENT_FOLDER'], filename)
        
    #     # Save the last frame as the captured image
    #     global captured_frame
    #     if captured_frame is not None:
    #         cv2.imwrite(filepath, captured_frame)
    #         return redirect(url_for('register_student'))  # Redirect to registration form with the captured image
        
    #     return "No frame captured. Please try again.", 400
    
    return render_template('capture.html')


@app.route('/save_captured_image', methods=['POST'])
def save_captured_image():
    # Get the captured image data
    image_data = request.form['image_data']
    if not image_data:
        return "No image data received.", 400

    # Decode the Base64 image
    image_data = b64decode(image_data.split(',')[1])
    filename = f"captured_{int(time.time())}.png"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # Save the image
    with open(filepath, 'wb') as f:
        f.write(image_data)

    # Redirect to register with the filename
    return redirect(url_for('register_student', captured_image=filename))


# @app.route('/video_feed')
# def video_feed():
    # return Response(generate_camera_feed(), mimetype='multipart/x-mixed-replace; boundary=frame')



# @app.route('/upload', methods=['POST'])
# def upload_file():
#     # try:
    #     if 'file' not in request.files or request.files['file'].filename == '':
    #         return "No file selected for upload.", 400

    #     file = request.files['file']

    #     if file and allowed_file(file.filename):
    #         filename = secure_filename(file.filename)
    #         filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    #         file.save(filepath)

    #         # Load the uploaded image and extract face encodings and locations
    #         uploaded_image = face_recognition.load_image_file(filepath)
    #         face_locations = face_recognition.face_locations(uploaded_image)
    #         uploaded_face_encodings = face_recognition.face_encodings(uploaded_image)

    #         if not face_locations:
    #             return "No faces detected in the uploaded image.", 400

    #         # Load known students' face encodings from JSON
    #         student_data = get_student_data()
    #         known_face_encodings = []
    #         known_face_names = []

    #         for student in student_data:
    #             known_face_encodings.append(pickle.loads(student['face_encoding'].encode('latin1')))
    #             known_face_names.append(student['student_id'])

    #         # Create PIL Image object for drawing
    #         pil_image = Image.fromarray(uploaded_image)
    #         draw = ImageDraw.Draw(pil_image)

    #         # Initialize a list to store recognition results
    #         recognition_results = []

    #         # Compare each detected face with known faces
    #         for face_encoding, face_location in zip(uploaded_face_encodings, face_locations):
    #             # Calculate distances to known faces
    #             distances = face_recognition.face_distance(known_face_encodings, face_encoding)
    #             best_match_index = distances.argmin() if len(distances) > 0 else -1

    #             # Default recognition result
    #             name = "Unknown"
    #             color = (255, 0, 0)  # Red for unrecognized
    #             top, right, bottom, left = face_location

    #             # Check if the best match is within the threshold
    #             if best_match_index != -1 and distances[best_match_index] < 0.5:
    #                 student_id = known_face_names[best_match_index]
    #                 name = student_id
    #                 color = (0, 255, 0)  # Green for recognized

    #                 # Log the recognized student's attendance
    #                 log_attendance(student_id)

    #             # Draw a rectangle around the face and add a label
    #             draw.rectangle(((left, top), (right, bottom)), outline=color, width=5)
    #             draw.text((left + 6, bottom + 6), name, fill=(0, 0, 0, 255))

    #             # Append the result for this face
    #             recognition_results.append((face_location, name))

    #         # Save the output image
    #         output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'output_' + filename)
    #         pil_image.save(output_path)

    #         return redirect(url_for('uploaded_file', filename='output_' + filename))

    #     return "Invalid file type.", 400
    # except Exception as e:
    #     return f"An error occurred: {e}", 500





# Serve the output images
# @app.route('/uploads/<filename>')
# def uploaded_file(filename):
#     try:
#         return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
#     except Exception as e:
#         return f"An error occurred: {e}", 500

# # Ensure required folders and JSON file exist
# if __name__ == '__main__':
#     try:
#         os.makedirs(UPLOAD_FOLDER, exist_ok=True)
#         os.makedirs(STUDENT_FOLDER, exist_ok=True)
#         init_student_data()
#         app.run(debug=True)
#     except Exception as e:
#         print(f"Failed to start the application: {e}")

