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
def start_processing_image(image_data , subject_id, faculty_id):
    """Start processing image in background and return session ID"""
    try:
        # Create a new session with binary image data
        # Note: SessionManager.create_session only takes image_data as argument
        session_id = session_manager.create_session(image_data)
        session_manager.update_session(session_id, {
            'metadata': {
                'subject_id': subject_id,
                'faculty_id': faculty_id
            }
        })
        
        # Add debug log
        logger.info(f"Created session {session_id} and started processing")
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
        
        # Get metadata from session
        metadata = session_data.get('metadata', {})
        subject_id = metadata.get('subject_id', 'default_subject')
        faculty_id = metadata.get('faculty_id')
        
        # Initialize services
        attendance_service = AttendanceService()
        
        # First, get all students enrolled in this subject
        subject_doc = storage_service.db.collection('subjects').document(subject_id).get()
        if not subject_doc.exists:
            session_manager.update_session(session_id, {
                'status': 'error',
                'error': f'Subject {subject_id} not found'
            })
            logger.error(f"Subject {subject_id} not found for session {session_id}")
            return
            
        subject_data = subject_doc.to_dict()
        enrolled_student_ids = subject_data.get('enrolled_students', [])
        
        if not enrolled_student_ids:
            session_manager.update_session(session_id, {
                'status': 'completed',
                'error': 'No students enrolled in this subject'
            })
            logger.warning(f"No students enrolled in subject {subject_id}")
            return
        
        # Track which students are present (will be updated during face detection)
        present_student_ids = set()
        
        # Detect faces in the image using FaceService
        np_image, face_locations = face_service.detect_faces(image_data)
        
        # Process each face
        processed_faces = []
        
        # Track names and student_ids for later drawing all faces at once
        all_names = []
        all_student_ids = []
        
        # Process detected faces and mark present students
        if face_locations:
            for i, face_location in enumerate(face_locations):
                try:
                    # Get face encoding using FaceService
                    face_encoding = face_service.encode_face(np_image, face_location)
                    
                    # Find matching face using StorageService
                    student_id, name, score = storage_service.find_matching_face(face_encoding)
                    
                    # If a valid student was identified (student_id is not None)
                    if student_id:
                        # Add to set of present students
                        present_student_ids.add(student_id)
                        
                        # Mark attendance for this student
                        if subject_id:
                            # Mark the student as present in this subject
                            attendance_result = attendance_service.mark_attendance(
                                student_id=student_id,
                                subject_id=subject_id,
                                faculty_id=faculty_id,
                                status="present"
                            )
                            
                            # Log the attendance result
                            if attendance_result:
                                logger.info(f"Marked attendance for student {student_id} ({name}) in subject {subject_id}")
                            else:
                                logger.info(f"Attendance already marked or error for student {student_id} in subject {subject_id}")
                        else:
                            logger.warning(f"No subject_id provided in metadata, cannot mark attendance for {student_id}")

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
        else:
            logger.warning(f"No faces detected in session {session_id}")
            full_image_data = None
        
        # Find absent students (enrolled but not present)
        absent_student_ids = [sid for sid in enrolled_student_ids if sid not in present_student_ids]
        
        # Mark absent students
        absent_students_count = 0
        for student_id in absent_student_ids:
            try:
                attendance_result = attendance_service.mark_attendance(
                    student_id=student_id,
                    subject_id=subject_id,
                    faculty_id=faculty_id,
                    status="absent"
                )
                
                if attendance_result:
                    absent_students_count += 1
                    logger.info(f"Marked student {student_id} absent for subject {subject_id}")
            except Exception as e:
                logger.error(f"Error marking student {student_id} absent: {str(e)}")
        
        # Mark processing as completed
        session_manager.update_session(session_id, {
            'status': 'completed',
            'full_image': full_image_data,
            'total_faces': len(processed_faces),
            'present_count': len(present_student_ids),
            'absent_count': absent_students_count
        })
        logger.info(f"Completed processing session {session_id}: {len(present_student_ids)} present, {absent_students_count} absent")
        
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
    































#####################################################################################################################
#saksham work here


######################################################################################################################
@app.route('/register_student', methods=['GET'])
def register_student():
    """Show registration options for new and existing students"""
    departments = storage_service.get_all_departments()
    return render_template('register.html', 
                          departments=departments, 
                          current_year=date.today().year)

@app.route('/register_new_student', methods=['POST'])
def register_new_student():
    """Handle new student registration"""
    try:
        name = request.form['name']
        student_id = request.form['student_id']
        email = request.form.get('email', '')
        department_id = request.form.get('department_id', '')
        batch_year = request.form.get('batch_year', datetime.now().year)
        current_semester = request.form.get('current_semester', '1')

        if storage_service.student_exists(student_id):
            return jsonify({"success": False, "message": "Student ID already registered"}), 400

        # Get image from either file upload or camera capture
        image_data = None
        if 'file' in request.files:
            file = request.files['file']
            if file and allowed_file(file.filename):
                image_data = file.read()
        elif 'captured_image' in request.form:
            captured_image = request.form['captured_image']
            if captured_image:
                if ',' in captured_image:
                    image_data = base64.b64decode(captured_image.split(',')[1])
                else:
                    image_data = base64.b64decode(captured_image)

        if not image_data:
            return jsonify({"success": False, "message": "No image provided"}), 400

        # Process face for recognition
        process_image_for_registration(image_data, student_id, name)

        # Create and store student record
        student = Student(
            student_id=student_id,
            name=name,
            email=email,
            department_id=department_id,
            batch_year=batch_year,
            current_semester=current_semester
        )
        storage_service.add_student(student)

        # Return success response for AJAX request
        flash(f'{student.student_id} registered successfully', 'success')
        return redirect(url_for('register_student'))
    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500

@app.route('/register_existing_student', methods=['GET', 'POST'])
def register_existing_student():
    storage_service = StorageService()
    departments = storage_service.get_all_departments()
    current_year = datetime.now().year
    
    if request.method == 'POST':
        student_id = request.form['student_id']
        department_id = request.form['department_id']
        new_semester = int(request.form['new_semester'])
        
        # Validate student exists
        student = storage_service.get_student(student_id)
        if not student:
            flash('Student ID not found', 'danger')
            return render_template('register_existing_student.html', 
                                   departments=departments, 
                                   current_year=current_year)
        
        # Update student semester
        storage_service.update_student_semester(student_id, new_semester)
        
        # Get courses for this department and semester
        # First clear any existing course enrollments for this student
        storage_service.clear_student_enrollments(student_id)
        
        courses = storage_service.get_courses_by_department_semester(department_id, new_semester)
        
        if courses:
            # Enroll student in all courses for this semester
            course_ids = [course.subject_id for course in courses]
            storage_service.enroll_student_in_courses(student_id, course_ids)
            
            flash(f'Student successfully registered for semester {new_semester} with {len(courses)} courses', 'success')
        else:
            flash(f'Student\'s semester updated, but no courses found for semester {new_semester}', 'warning')
        return redirect(url_for("register_student"))
    
    return render_template('register_existing_student.html', 
                           departments=departments, 
                           current_year=current_year)




######################################################################################################################




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
        
        # Get subject and faculty names from IDs
        subject_name = "Unknown Subject"
        faculty_name = "Unknown Faculty"
        
        subject = storage_service.db.collection('subjects').document(subject_id).get()
        if subject.exists:
            subject_name = subject.to_dict().get('name', 'Unknown Subject')
            
        faculty = storage_service.db.collection('faculty').document(faculty_id).get() 
        if faculty.exists:
            faculty_name = faculty.to_dict().get('name', 'Unknown Faculty')

        # Start processing and get session ID
        session_id = start_processing_image(image_data , subject_id , faculty_id)
        
        return render_template('processing.html', 
                    session_id=session_id,
                    subject_id=subject_id,  # Pass subject_id to the template
                    faculty_name=faculty_name,
                    subject_name=subject_name)
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return f"Error processing image: {str(e)}", 500

@app.route('/api/subject/<subject_id>/enrolled_students')
def get_enrolled_students(subject_id):
    """API endpoint to get students enrolled in a specific subject"""
    try:
        logger.info(f"Getting enrolled students for subject: {subject_id}")
        
        # Handle empty or 'undefined' subject_id
        if not subject_id or subject_id == 'undefined':
            logger.warning(f"Invalid subject_id received: {subject_id}")
            return jsonify({'error': 'Invalid subject ID'}), 400
        
        # Get the subject document from Firestore
        subject_doc = storage_service.db.collection('subjects').document(subject_id).get()
        
        if not subject_doc.exists:
            logger.warning(f"Subject not found: {subject_id}")
            return jsonify({
                'subject_id': subject_id,
                'subject_name': 'Unknown Subject',
                'students': []
            })
            
        subject_data = subject_doc.to_dict()
        enrolled_student_ids = subject_data.get('enrolled_students', [])
        
        logger.info(f"Found {len(enrolled_student_ids)} enrolled student IDs for subject {subject_id}")
        
        # Get details for each enrolled student
        students = []
        for student_id in enrolled_student_ids:
            student = storage_service.get_student(student_id)
            if student:
                students.append({
                    'student_id': student.student_id,
                    'name': student.name,
                    'roll_number': student.roll_number if hasattr(student, 'roll_number') else '',
                    'email': student.email if hasattr(student, 'email') else ''
                })
            else:
                logger.warning(f"Student {student_id} listed in subject but not found in database")
        
        logger.info(f"Returning {len(students)} student details for subject {subject_id}")
        
        return jsonify({
            'subject_id': subject_id,
            'subject_name': subject_data.get('name'),
            'students': students
        })
        
    except Exception as e:
        logger.error(f"Error fetching enrolled students: {e}")
        return jsonify({
            'error': str(e),
            'subject_id': subject_id,
            'students': []
        }), 500




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
        credits = int(request.form.get('credits', 0))
        is_elective = 'is_elective' in request.form
        semester = int(request.form.get('semester', 1))
        
        subject = Subject(
            subject_id=subject_id,
            name=name,
            department_id=department_id,
            credits=credits,
            is_elective=is_elective,
            semester=semester
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
    





















#####################################################################################################################

@app.route('/admin/enroll_student', methods=['GET', 'POST'])
def admin_enroll_student():
    """Handle student enrollment page and form submission"""
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        subject_id = request.form.get('subject_id')
        
        if not student_id or not subject_id:
            flash('Student and subject are required', 'danger')
            return redirect(url_for('admin_enroll_student'))
        
        # Enroll the student in the selected subject
        success = storage_service.enroll_student_in_courses(student_id, [subject_id])
        
        if not success:
            flash('Failed to enroll student in subject', 'danger')
        else:
            # Get student and subject details for the confirmation message
            student = storage_service.get_student(student_id)
            subject_details = None
            
            # Find the subject details from all subjects
            subjects = storage_service.get_all_subjects()
            for subject in subjects:
                if subject.subject_id == subject_id:
                    subject_details = subject
                    break
            
            if student and subject_details:
                flash(f'Successfully enrolled {student.name} in {subject_details.name}', 'success')
            else:
                flash('Student enrolled successfully', 'success')
        
        return redirect(url_for('admin_enroll_student'))
    
    # For GET requests, prepare data for the template
    students = storage_service.get_all_students()
    subjects = storage_service.get_all_subjects()
    departments = storage_service.get_all_departments()
    
    # Get all subjects with their enrolled students
    subjects_with_enrollments = []
    for subject in subjects:
        # Get the list of student names for display
        enrolled_student_names = []
        for student_id in subject.enrolled_students or []:
            student = storage_service.get_student(student_id)
            if student:
                enrolled_student_names.append(student.name)
        
        subjects_with_enrollments.append({
            'subject': subject,
            'enrolled_students': enrolled_student_names
        })
    
    return render_template('admin/enroll_student.html',
                           students=students,
                           subjects=subjects,
                           departments=departments,
                           enrollments=subjects_with_enrollments)

@app.route('/api/subjects', methods=['GET'])
def get_subjects():
    """API endpoint to get subjects by department and semester"""
    department_id = request.args.get('department_id')
    semester = request.args.get('semester')
    
    if not department_id or not semester:
        return jsonify({'error': 'Department ID and semester are required'}), 400
    
    try:
        semester = int(semester)
        subjects = storage_service.get_courses_by_department_semester(department_id, semester)
        
        # Convert subjects to a format suitable for JSON response
        subjects_data = []
        for subject in subjects:
            subjects_data.append({
                'subject_id': subject.subject_id,
                'name': subject.name,
                'department_id': subject.department_id,
                'semester': subject.semester
            })
        
        return jsonify({'subjects': subjects_data})
    except Exception as e:
        app.logger.error(f"Error fetching subjects: {e}")
        return jsonify({'error': 'Failed to fetch subjects'}), 500


@app.route('/admin/bulk_enroll_student', methods=['GET', 'POST'])
def admin_bulk_enroll_student():
    """Route to handle bulk enrollment of students in semester courses"""
    if request.method == 'POST':
        student_id = request.form['student_id']
        department_id = request.form['department_id']
        semester = int(request.form['semester'])
        
        # First clear existing enrollments if checkbox is checked
        if request.form.get('clear_existing', False):
            storage_service.clear_student_enrollments(student_id)
        
        # Get all courses for this department and semester
        courses = storage_service.get_courses_by_department_semester(department_id, semester)
        course_ids = [course.subject_id for course in courses]
        
        # Enroll student in all courses
        success = storage_service.enroll_student_in_courses(student_id, course_ids)
        
        # Update student's current semester
        if success and request.form.get('update_semester', False):
            storage_service.update_student_semester(student_id, semester)
            flash(f'Student semester updated to {semester}', 'success')
        
        if success:
            flash(f'Student enrolled in {len(course_ids)} courses for semester {semester}', 'success')
        else:
            flash('Failed to enroll student in courses', 'error')
        
        return redirect(url_for('admin_bulk_enroll_student'))
    
    students = storage_service.get_all_students()
    departments = storage_service.get_all_departments()
    
    return render_template('admin/bulk_enroll_student.html',
                         students=students,
                         departments=departments)





@app.route('/admin/student_enrollments/<student_id>', methods=['GET', 'POST'])
def admin_student_enrollments(student_id):
    """Route to display and manage a student's enrollments"""
    student = storage_service.get_student(student_id)
    if not student:
        flash('Student not found', 'error')
        return redirect(url_for('admin_dashboard'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'drop_course':
            # Drop a single course
            course_id = request.form.get('course_id')
            
            # Remove course from student's enrolled courses
            if course_id in student.course_enrolled_ids:
                student.course_enrolled_ids.remove(course_id)
                storage_service.update_student(student)
            
            # Remove student from course's enrolled students
            course_ref = storage_service.db.collection('subjects').document(course_id)
            course_doc = course_ref.get()
            if course_doc.exists:
                course_data = course_doc.to_dict()
                enrolled_students = course_data.get('enrolled_students', [])
                if student_id in enrolled_students:
                    enrolled_students.remove(student_id)
                    course_ref.update({'enrolled_students': enrolled_students})
            
            flash(f'Student dropped from course', 'success')
            
        elif action == 'clear_all':
            # Clear all enrollments
            success = storage_service.clear_student_enrollments(student_id)
            if success:
                flash('All enrollments cleared', 'success')
            else:
                flash('Failed to clear enrollments', 'error')
        
        return redirect(url_for('admin_student_enrollments', student_id=student_id))
    
    # Get all subjects the student is enrolled in
    enrolled_subjects = storage_service.get_student_subjects(student_id)
    
    return render_template('admin/student_enrollments.html',
                          student=student,
                          enrolled_subjects=enrolled_subjects)













#######################################################################################################################################
# @app.route('/upload-page')
# def upload_page():
#     # Get subject and faculty data for the form if needed
#     subjects = storage_service.get_all_subjects()
#     faculty = [Faculty.from_dict(doc.to_dict()) for doc in storage_service.db.collection('faculty').stream()]
    
#     return render_template('upload.html', subjects=subjects, faculty=faculty)

@app.route('/mark-attendance')
def mark_attendance():
    """
    Render the mark attendance page with faculty list
    """
    # Get faculty with document IDs
    faculty = []
    faculty_ref = storage_service.db.collection('faculty').stream()
    for doc in faculty_ref:
        faculty_data = doc.to_dict()
        faculty_data['faculty_id'] = doc.id  # Ensure we have the document ID
        faculty.append(Faculty.from_dict(faculty_data))

    return render_template('teacher/mark_attendance.html', faculty=faculty)

@app.route('/get-faculty-subjects/<faculty_id>')
def get_faculty_subjects(faculty_id):
    """
    API endpoint to get subjects taught by a faculty member
    """
    try:
        # Get faculty document to fetch subjects
        faculty_doc = storage_service.db.collection('faculty').document(faculty_id).get()
        
        if not faculty_doc.exists:
            return jsonify({'success': False, 'message': 'Faculty not found', 'subjects': []}), 404
        
        faculty_data = faculty_doc.to_dict()
        subject_ids = faculty_data.get('subjects', [])
        
        # Get subject details for each subject ID
        subjects = []
        for subject_id in subject_ids:
            subject_doc = storage_service.db.collection('subjects').document(subject_id).get()
            if subject_doc.exists:
                subject_data = subject_doc.to_dict()
                subject_data['subject_id'] = subject_id  # Ensure we have the document ID
                subjects.append(subject_data)
        
        return jsonify({
            'success': True,
            'faculty_id': faculty_id,
            'subjects': subjects
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}",
            'subjects': []
        }), 500
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