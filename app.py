import base64
import logging
import uuid
import threading
from datetime import datetime, date
from io import BytesIO
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify,flash
from werkzeug.utils import secure_filename
from PIL import Image, ImageDraw
from config import config
from services.face_service import FaceService
from services.storage_service import StorageService
from services.attendance_service import AttendanceService
from services.session_manager import SessionManager
from models.student import Student
from models.department import Department
from models.faculty import Faculty
from models.subject import Subject
from models.student_subject import StudentSubject
from models.attendance import Attendance
from models.admin import Admin

# Initialize Flask app
app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = config.MAX_CONTENT_LENGTH

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize services
storage_service = StorageService()
face_service = FaceService()
attendance_service = AttendanceService()
session_manager = SessionManager()

# Helper functions
def allowed_file(filename):
    """Check if file has allowed extension"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS

def process_image_for_registration(image_data, student_id, name):
    """Process image for student registration"""
    try:
        # Detect faces in the image
        np_image, face_locations = face_service.detect_faces(image_data)
        
        if not face_locations:
            raise ValueError("No faces found in the image")
        

        if len(face_locations) > 1:
            raise ValueError("Multiple faces found in the image. Please upload an image with only one face.")
        # Use the first face
        face_encoding = face_service.encode_face(np_image, face_locations[0])
        
        # Store face encoding in Pinecone
        storage_service.store_student_face(student_id, name, face_encoding)
        
        return True
    except Exception as e:
        logger.error(f"Error processing image for registration: {e}")
        raise
































#######################################################################################################################################
def start_processing_image(image_data):
    """Start processing image in background and return session ID"""
    try:
        # Create a new session with binary image data
        # Note: SessionManager.create_session only takes image_data as argument
        session_id = session_manager.create_session(image_data)
        
        # Start a background thread to process faces
        threading.Thread(target=process_faces_background, args=(session_id,)).start()
        
        return session_id
    except Exception as e:
        logger.error(f"Error starting image processing: {e}")
        raise

def process_faces_background(session_id):
    """Process faces in background and update session progressively"""
    session_data = session_manager.get_session(session_id)
    if not session_data:
        logger.error(f"Session {session_id} not found")
        return
    
    try:
        # Get the image data from the session
        image_data = session_data['image']
        
        # Detect faces in the image using FaceService
        np_image, face_locations = face_service.detect_faces(image_data)
        
        if not face_locations:
            session_manager.update_session(session_id, {
                'status': 'completed',
                'error': 'No faces detected in the image'
            })
            logger.warning(f"No faces detected in session {session_id}")
            return
        
        # Process each face
        processed_faces = []
        
        # Get metadata from session
        metadata = session_data.get('metadata', {})
        subject_id = metadata.get('subject_id', 'default_subject')
        faculty_id = metadata.get('faculty_id')
        
        # Track names and student_ids for later drawing all faces at once
        all_names = []
        all_student_ids = []
        
        for i, face_location in enumerate(face_locations):
            try:
                # Get face encoding using FaceService
                face_encoding = face_service.encode_face(np_image, face_location)
                
                # Find matching face using StorageService
                student_id, name, score = storage_service.find_matching_face(face_encoding)
                
                # Add to tracking lists
                all_names.append(name)
                all_student_ids.append(student_id)
                
                # Crop face image
                top, right, bottom, left = face_location
                face_crop = face_service.crop_face(Image.fromarray(np_image), face_location)
                
                # Add to processed faces
                processed_faces.append({
                    'id': i,
                    'student_id': student_id,
                    'name': name,
                    'face_img': face_crop,
                    'processed_at': datetime.now().isoformat()
                })
                
                # Update session with new face - important for real-time updates
                session_manager.update_session(session_id, {
                    'processed_faces': processed_faces,
                    'status': 'processing'  # Ensure status is set
                })
                
                # Add a small delay to make updates visible in UI
                time.sleep(0.2)
                
            except Exception as e:
                logger.error(f"Error processing face {i}: {str(e)}")
                # Continue with next face
        
        # Draw all face rectangles at once using FaceService
        pil_image_with_faces = face_service.draw_face_rectangles(np_image, face_locations, all_names, all_student_ids)
        
        # Convert processed image to base64
        full_image_data = face_service.image_to_base64(pil_image_with_faces)
        
        # Mark processing as completed
        session_manager.update_session(session_id, {
            'status': 'completed',
            'full_image': full_image_data,
            'total_faces': len(processed_faces)
        })
        logger.info(f"Completed processing session {session_id} with {len(processed_faces)} faces")
        
    except Exception as e:
        logger.error(f"Error in face processing for session {session_id}: {str(e)}")
        session_manager.update_session(session_id, {
            'status': 'error',
            'error': str(e)
        })
#######################################################################################################################################


















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
        # In a real app, you would validate and store user credentials
        return redirect(url_for('index'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # In a real app, you would validate credentials
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    try:
        # Get all departments
        departments = storage_service.get_all_departments()
        
        # Get all students
        students = storage_service.get_all_students()
        
        # Get all subjects
        subjects = storage_service.get_all_subjects()
        
        # Get attendance summaries for all students
        attendance_results = []
        for student in students:
            summary = attendance_service.get_student_attendance_summary(student.student_id)
            attendance_results.append({
                'student_id': student.student_id,
                'name': student.name,
                'department': next((d.name for d in departments if d.dept_id == student.department_id), 'Unknown'),
                'days_present': summary['present_count'],
                'total_days': summary['total_classes'],
                'percentage': summary['attendance_percentage']
            })
        
        # Calculate total number of attendance days
        attendance_dates = set()
        for att in storage_service.db.collection('attendance').stream():
            att_data = att.to_dict()
            if 'date' in att_data:
                attendance_dates.add(att_data['date'])
        
        total_days = len(attendance_dates)
        
        return render_template('dashboard.html', 
                             attendance_data=attendance_results,
                             total_days=total_days,
                             departments=departments,
                             subjects=subjects)
    except Exception as e:
        logger.error(f"Dashboard error: {str(e)}")
        return f"An error occurred: {e}", 500

@app.route('/register_student', methods=['GET', 'POST'])
def register_student():
    if request.method == 'POST':
        name = request.form['name']
        student_id = request.form['student_id']
        email = request.form.get('email', '')
        department_id = request.form.get('department_id', '')
        batch_year = request.form.get('batch_year', datetime.now().year)
        
        if storage_service.student_exists(student_id):
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
            # Process face for recognition
            process_image_for_registration(image_data, student_id, name)
            
            # Create and store student record
            student = Student(
                student_id=student_id,
                name=name,
                email=email,
                department_id=department_id,
                batch_year=batch_year
            )
            storage_service.add_student(student)
            
            return redirect(url_for('index'))
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return f"Error processing registration: {str(e)}", 500
    
    # GET request: show registration form
    departments = storage_service.get_all_departments()
    return render_template('register.html', departments=departments)
















#################################################################################################################################
@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return "No file selected", 400
    
    file = request.files['file']
    if not file or not allowed_file(file.filename):
        return "Invalid file type", 400
    
    subject_id = request.form.get('subject_id', 'default_subject')
    faculty_id = request.form.get('faculty_id')
    
    try:
        # Read the file data
        image_data = file.read()
        
        # Start processing and get session ID
        session_id = start_processing_image(image_data)
        
        # Store subject and faculty info in session metadata
        session_manager.update_session(session_id, {
            'metadata': {
                'subject_id': subject_id,
                'faculty_id': faculty_id
            }
        })
        
        # Add debug log
        logger.info(f"Created session {session_id} and started processing")
        
        return render_template('processing.html', session_id=session_id)
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return f"Error processing image: {str(e)}", 500

@app.route('/process-captured-image', methods=['POST'])
def process_captured_image():
    # Get the base64 image data from the form
    captured_image_data = request.form.get('captured_image')
    subject_id = request.form.get('subject_id', 'default_subject')
    faculty_id = request.form.get('faculty_id')
    
    if not captured_image_data:
        return "No image data received", 400
    
    try:
        # Remove the data URL prefix if present
        if 'base64,' in captured_image_data:
            image_data = captured_image_data.split('base64,')[1]
        else:
            image_data = captured_image_data
            
        # Convert base64 to binary
        binary_image = base64.b64decode(image_data)
        
        # Start processing and get session ID
        session_id = start_processing_image(binary_image)
        
        # Store subject and faculty info in session metadata
        session_manager.update_session(session_id, {
            'metadata': {
                'subject_id': subject_id,
                'faculty_id': faculty_id
            }
        })
        
        return render_template('processing.html', session_id=session_id)
    except Exception as e:
        logger.error(f"Capture processing error: {str(e)}")
        return f"Error processing captured image: {str(e)}", 500


@app.route('/face_status/<session_id>')
def face_status(session_id):
    """API endpoint to get current status of face processing"""
    session_data = session_manager.get_session(session_id)
    if not session_data:
        return jsonify({'error': 'Session not found'}), 404
    
    response = {
        'status': session_data.get('status', 'unknown'),
        'processed_faces': session_data.get('processed_faces', []),
        'error': session_data.get('error'),
        'full_image': session_data.get('full_image') if session_data.get('status') == 'completed' else None,
        'total_faces': len(session_data.get('processed_faces', []))
    }
    
    logger.debug(f"Status response for session {session_id}: status={response['status']}, faces={response['total_faces']}")
    
    return jsonify(response)

#######################################################################################################################################



















@app.route('/capture')
def capture():
    subjects = storage_service.get_all_subjects()
    return render_template('capture.html', subjects=subjects)

# Admin routes
@app.route('/admin/departments', methods=['GET', 'POST'])
def admin_departments():
    if request.method == 'POST':
        dept_id = request.form['dept_id']
        name = request.form['name']
        
        # HOD is optional during creation
        hod = request.form.get('hod', None)
        
        department = Department(dept_id=dept_id, name=name, hod=hod)
        storage_service.add_department(department)
        
        return redirect(url_for('admin_departments'))
    
    departments = storage_service.get_all_departments()
    faculty = storage_service.db.collection('faculty').stream()
    faculty_list = [Faculty.from_dict(doc.to_dict()) for doc in faculty]
    
    return render_template('admin/departments.html', departments=departments, faculty=faculty_list)

@app.route('/admin/departments/set_hod', methods=['POST'])
def set_hod():
    dept_id = request.form['dept_id']
    hod_id = request.form['hod_id']
    
    # Update the department with the new HOD
    storage_service.db.collection('departments').document(dept_id).update({'hod': hod_id})
    
    return redirect(url_for('admin_departments'))

@app.route('/admin/faculty', methods=['GET', 'POST'])
def admin_faculty():
    if request.method == 'POST':
        if 'edit_subjects' in request.form:
            # Handle subject editing
            faculty_id = request.form['faculty_id']
            subjects = request.form.getlist('subjects')
            
            # Update faculty subjects in database
            faculty_ref = storage_service.db.collection('faculty').where('faculty_id', '==', faculty_id).get()
            if faculty_ref:
                doc = faculty_ref[0]
                doc.reference.update({'subjects': subjects})
            
            return redirect(url_for('admin_faculty'))
        else:
            # Handle new faculty creation
            department = request.form['department']
            name = request.form['name']
            email = request.form['email']
            manual_id = request.form.get('faculty_id', '').strip()
            
            # Generate faculty ID if not manually provided
            if manual_id:
                faculty_id = manual_id
            else:
                faculty_count = len([doc for doc in storage_service.db.collection('faculty')
                                   .where('departments', 'array_contains', department).stream()])
                faculty_id = f"TE00{department}{faculty_count + 1}"
            
            # Check if ID already exists
            existing_faculty = storage_service.db.collection('faculty') \
                .where('faculty_id', '==', faculty_id).get()
            if existing_faculty:
                flash('Faculty ID already exists!', 'error')
                return redirect(url_for('admin_faculty'))
            
            # Get default subjects for the department - USING department_id NOW
            default_subjects = [subj.subject_id for subj in storage_service.get_all_subjects() 
                               if subj.department_id == department]
            
            faculty = Faculty(
                faculty_id=faculty_id,
                name=name, 
                email=email,
                departments=department,
                subjects=default_subjects
            )
            storage_service.add_faculty(faculty)
            
            return redirect(url_for('admin_faculty'))
    
    faculty_list = [Faculty.from_dict(doc.to_dict()) for doc in storage_service.db.collection('faculty').stream()]
    departments = storage_service.get_all_departments()
    subjects = storage_service.get_all_subjects()
    
    return render_template('admin/faculty.html', 
                         faculty=faculty_list, 
                         departments=departments,
                         subjects=subjects)

@app.route('/admin/faculty/remove/<faculty_id>', methods=['POST'])
def remove_faculty(faculty_id):
    try:
        # Delete faculty document from Firestore
        faculty_ref = storage_service.db.collection('faculty').where('faculty_id', '==', faculty_id).get()
        if faculty_ref:
            for doc in faculty_ref:  # Need to loop through all matching documents
                doc.reference.delete()
            flash('Faculty removed successfully', 'success')
        else:
            flash('Faculty not found', 'error')
        return redirect(url_for('admin_faculty'))
    except Exception as e:
        logger.error(f"Error removing faculty: {str(e)}")
        flash('Error removing faculty', 'error')
        return redirect(url_for('admin_faculty'))
    

@app.route('/admin/faculty/assign_subjects/<faculty_id>', methods=['GET', 'POST'])
def assign_subjects(faculty_id):
    try:
        # Get faculty data
        faculty_ref = storage_service.db.collection('faculty').where('faculty_id', '==', faculty_id).get()
        if not faculty_ref:
            flash('Faculty not found', 'error')
            return redirect(url_for('admin_faculty'))
            
        faculty_doc = faculty_ref[0]
        faculty = Faculty.from_dict(faculty_doc.to_dict())
        
        if request.method == 'POST':
            # Get selected subjects from form
            selected_subjects = request.form.getlist('subjects')
            
            # Get previously assigned subjects
            previous_subjects = faculty.subjects if hasattr(faculty, 'subjects') else []
            
            # Update faculty's subjects in database
            faculty_doc.reference.update({'subjects': selected_subjects})
            
            # Update subject documents to add/remove this faculty_id
            for subject_id in previous_subjects:
                if subject_id not in selected_subjects:
                    # Remove faculty from this subject
                    subject_ref = storage_service.db.collection('subjects').where('subject_id', '==', subject_id).get()
                    if subject_ref:
                        subject_doc = subject_ref[0]
                        subject_data = subject_doc.to_dict()
                        if 'faculty_ids' in subject_data and faculty_id in subject_data['faculty_ids']:
                            subject_data['faculty_ids'].remove(faculty_id)
                            subject_doc.reference.update({'faculty_ids': subject_data['faculty_ids']})
            
            for subject_id in selected_subjects:
                if subject_id not in previous_subjects:
                    # Add faculty to this subject
                    subject_ref = storage_service.db.collection('subjects').where('subject_id', '==', subject_id).get()
                    if subject_ref:
                        subject_doc = subject_ref[0]
                        subject_data = subject_doc.to_dict()
                        if 'faculty_ids' not in subject_data:
                            subject_data['faculty_ids'] = []
                        if faculty_id not in subject_data['faculty_ids']:
                            subject_data['faculty_ids'].append(faculty_id)
                            subject_doc.reference.update({'faculty_ids': subject_data['faculty_ids']})
            
            flash('Subjects assigned successfully', 'success')
            return redirect(url_for('admin_faculty'))
            
        # For GET requests
        # Get all subjects
        subjects = storage_service.get_all_subjects()
        
        # Get currently assigned subjects
        assigned_subjects = faculty.subjects if hasattr(faculty, 'subjects') else []
        
        # Get department name for display
        department_name = "Unknown"
        if isinstance(faculty.departments, str):
            dept_id = faculty.departments
            dept_ref = storage_service.db.collection('departments').where('dept_id', '==', dept_id).get()
            if dept_ref:
                department_name = dept_ref[0].to_dict().get('name', "Unknown")
        
        return render_template('admin/assign_subjects.html',
                            faculty=faculty,
                            subjects=subjects,
                            department_name=department_name,
                            assigned_subjects=assigned_subjects)
                            
    except Exception as e:
        logger.error(f"Error assigning subjects: {str(e)}")
        flash('Error assigning subjects', 'error')
        return redirect(url_for('admin_faculty'))

@app.route('/admin/subjects', methods=['GET', 'POST'])
def admin_subjects():
    if request.method == 'POST':
        subject_id = request.form['subject_id']
        name = request.form['name']
        department_id = request.form['department_id']
        credits = request.form.get('credits')
        is_elective = 'is_elective' in request.form
        
        subject = Subject(
            subject_id=subject_id,
            name=name,
            department_id=department_id,
            credits=credits,
            is_elective=is_elective
        )
        storage_service.add_subject(subject)
        
        return redirect(url_for('admin_subjects'))
    
    subjects = storage_service.get_all_subjects()
    departments = storage_service.get_all_departments()
    
    return render_template('admin/subjects.html', 
                         subjects=subjects,
                         departments=departments)



@app.route('/admin/subjects/remove/<subject_id>', methods=['POST'])
def remove_subject(subject_id):
    try:
        # Delete subject document from Firestore
        subject_ref = storage_service.db.collection('subjects').where('subject_id', '==', subject_id).get()
        if subject_ref:
            for doc in subject_ref:  # Need to loop through all matching documents
                doc.reference.delete()
            
            # Also remove this subject from any faculty members who teach it
            faculty_refs = storage_service.db.collection('faculty').where('subjects', 'array_contains', subject_id).get()
            for faculty_doc in faculty_refs:
                subjects_list = faculty_doc.to_dict().get('subjects', [])
                if subject_id in subjects_list:
                    subjects_list.remove(subject_id)
                    faculty_doc.reference.update({'subjects': subjects_list})
            
            flash('Subject removed successfully', 'success')
        else:
            flash('Subject not found', 'error')
        
        return redirect(url_for('admin_subjects'))
    except Exception as e:
        logger.error(f"Error removing subject: {str(e)}")
        flash('Error removing subject', 'error')
        return redirect(url_for('admin_subjects'))
    


@app.route('/admin/enroll_student', methods=['GET', 'POST'])
def admin_enroll_student():
    if request.method == 'POST':
        student_id = request.form['student_id']
        subject_id = request.form['subject_id']
        academic_year = request.form['academic_year']
        semester = request.form['semester']
        attempt = int(request.form.get('attempt', 1))
        
        # Create a unique ID for this enrollment
        enrollment_id = f"enr_{uuid.uuid4().hex}"
        
        student_subject = StudentSubject(
            id=enrollment_id,
            student_id=student_id,
            subject_id=subject_id,
            academic_year=academic_year,
            semester=semester,
            attempt=attempt
        )
        storage_service.enroll_student_in_subject(student_subject)
        
        return redirect(url_for('admin_enroll_student'))
    
    students = storage_service.get_all_students()
    subjects = storage_service.get_all_subjects()
    enrollments = [StudentSubject.from_dict(doc.to_dict()) 
                  for doc in storage_service.db.collection('student_subjects').stream()]
    
    # Get student and subject names for display
    student_dict = {s.student_id: s.name for s in students}
    subject_dict = {s.subject_id: s.name for s in subjects}
    
    return render_template('admin/enroll_student.html',
                         students=students,
                         subjects=subjects,
                         enrollments=enrollments,
                         student_dict=student_dict,
                         subject_dict=subject_dict)






















#######################################################################################################################################
# @app.route('/upload-page')
# def upload_page():
#     # Get subject and faculty data for the form if needed
#     subjects = storage_service.get_all_subjects()
#     faculty = [Faculty.from_dict(doc.to_dict()) for doc in storage_service.db.collection('faculty').stream()]
    
#     return render_template('upload.html', subjects=subjects, faculty=faculty)

@app.route('/mark-attendance')
def mark_attendance():
    # Get subjects with their document IDs
    subjects = []
    subjects_ref = storage_service.db.collection('subjects').stream()
    for doc in subjects_ref:
        subject_data = doc.to_dict()
        subject_data['id'] = doc.id  # 🔑 Add document ID
        subjects.append(Subject.from_dict(subject_data))
    
    # Get faculty with document IDs
    faculty = []
    faculty_ref = storage_service.db.collection('faculty').stream()
    for doc in faculty_ref:
        faculty_data = doc.to_dict()
        faculty_data['id'] = doc.id  # 🔑 Add document ID
        faculty.append(Faculty.from_dict(faculty_data))

    return render_template('teacher/mark_attendance.html', 
                         subjects=subjects, 
                         faculty=faculty)
#######################################################################################################################################
















































@app.route('/student/view_attendance/<student_id>')
def student_view_attendance(student_id):
    student = storage_service.db.collection('students').document(student_id).get()
    if not student.exists:
        return "Student not found", 404
    
    student_data = Student.from_dict(student.to_dict())
    
    # Get all subjects the student is enrolled in
    enrollments = storage_service.db.collection('student_subjects') \
        .where(storage_service.db.field_path('student_id'), '==', student_id) \
        .stream()
    
    subject_ids = [enroll.to_dict()['subject_id'] for enroll in enrollments]
    
    # Get attendance for each subject
    attendance_data = []
    for subject_id in subject_ids:
        subject = storage_service.db.collection('subjects').document(subject_id).get()
        if subject.exists:
            subject_data = Subject.from_dict(subject.to_dict())
            summary = attendance_service.get_student_attendance_summary(student_id, subject_id)
            
            attendance_data.append({
                'subject_id': subject_id,
                'subject_name': subject_data.name,
                'subject_code': subject_data.code,
                'days_present': summary['present_count'],
                'total_days': summary['total_classes'],
                'percentage': summary['attendance_percentage']
            })
    
    return render_template('student/view_attendance.html', 
                         student=student_data,
                         attendance_data=attendance_data)

if __name__ == '__main__':
    app.run(debug=True)