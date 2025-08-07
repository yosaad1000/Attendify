# HRMS Platform - Comprehensive School Management System

A modern, full-stack Human Resource Management System designed specifically for educational institutions. This platform provides comprehensive management tools for students, teachers, and administrators.

## 🚀 Features

### Core Functionality
- **Multi-role Authentication** (Admin, Teacher, Student)
- **Student Management** with face recognition
- **Teacher Management** and subject assignments
- **Attendance Tracking** with AI-powered face recognition
- **Grade Management** with automated calculations
- **Fee Management** with payment processing
- **Real-time Analytics** and reporting
- **Google Classroom Integration**
- **Email Notifications**
- **Mobile-responsive Design**

### Advanced Features
- **Face Recognition Attendance** using OpenCV and face_recognition
- **Bulk Operations** for grades and attendance
- **Payment Gateway Integration** (Stripe)
- **Google APIs Integration** (Calendar, Meet, Classroom)
- **Real-time Dashboard** with charts and analytics
- **File Upload** and management
- **Role-based Access Control**
- **RESTful API** with comprehensive documentation

## 🏗️ Architecture

### Frontend (React + TypeScript)
- **React 18** with TypeScript
- **Tailwind CSS** for styling
- **React Query** for state management
- **React Router** for navigation
- **Recharts** for data visualization
- **Headless UI** for accessible components

### Backend (Python + FastAPI)
- **FastAPI** for high-performance API
- **SQLAlchemy** ORM with PostgreSQL
- **Alembic** for database migrations
- **JWT Authentication** with role-based access
- **Face Recognition** with OpenCV
- **Celery** for background tasks
- **Redis** for caching and sessions

### Database Schema
- **Users** (Admin, Teacher, Student roles)
- **Students** with face encodings
- **Teachers** with subject assignments
- **Departments** and **Subjects**
- **Attendance** with AI confidence scores
- **Grades** with automatic calculations
- **Fees** with payment tracking
- **Enrollments** for student-subject relationships

## 🛠️ Installation & Setup

### Prerequisites
- Node.js 18+
- Python 3.9+
- PostgreSQL 13+
- Redis 6+

### Frontend Setup
```bash
cd hrms-frontend
npm install
npm run dev
```

### Backend Setup
```bash
cd hrms-backend
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

### Environment Variables
Create a `.env` file in the backend directory:

```env
DATABASE_URL=postgresql://user:password@localhost/hrms_db
SECRET_KEY=your-super-secret-key
REDIS_URL=redis://localhost:6379
SENDGRID_API_KEY=your-sendgrid-key
STRIPE_SECRET_KEY=your-stripe-key
GOOGLE_CLIENT_ID=your-google-client-id
```

## 📱 Mobile App Development

The system is designed to support both web and mobile applications:

### React Native Setup (Future)
```bash
npx react-native init HRMSMobile
cd HRMSMobile
npm install @react-navigation/native
npm install react-native-camera
npm install @react-native-async-storage/async-storage
```

## 🔧 API Documentation

The API is fully documented with OpenAPI/Swagger. Once the backend is running, visit:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Key Endpoints

#### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `GET /api/auth/me` - Get current user

#### Students
- `GET /api/students` - List students
- `POST /api/students` - Create student
- `POST /api/students/{id}/upload-photo` - Upload face photo

#### Attendance
- `POST /api/attendance/mark` - Mark attendance
- `POST /api/attendance/upload-image` - AI attendance via image
- `GET /api/attendance/subject/{id}` - Get subject attendance

#### Grades
- `POST /api/grades` - Create grade
- `POST /api/grades/bulk-upload` - Bulk upload grades
- `GET /api/grades/subject/{id}` - Get subject grades

## 🎯 Usage Examples

### Face Recognition Attendance
```python
# Upload class photo for automatic attendance
curl -X POST "http://localhost:8000/api/attendance/upload-image" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@class_photo.jpg" \
  -F "subject_id=SUBJECT_ID" \
  -F "date_str=2024-01-15"
```

### Bulk Grade Upload
```csv
student_id,subject_id,exam_type,marks_obtained,max_marks,comments
STU001,CS101,midterm,85,100,Good performance
STU002,CS101,midterm,92,100,Excellent work
```

### Real-time Dashboard
The dashboard provides real-time analytics including:
- Attendance rates by subject/department
- Grade distributions and trends
- Fee payment status
- Student performance metrics

## 🔐 Security Features

- **JWT Authentication** with refresh tokens
- **Role-based Access Control** (RBAC)
- **Password Hashing** with bcrypt
- **Input Validation** with Pydantic
- **SQL Injection Protection** via SQLAlchemy ORM
- **CORS Configuration** for secure cross-origin requests
- **Rate Limiting** for API endpoints

## 🚀 Deployment

### Docker Deployment
```bash
# Build and run with Docker Compose
docker-compose up --build

# Or deploy individual services
docker build -t hrms-backend ./hrms-backend
docker build -t hrms-frontend ./hrms-frontend
```

### Production Considerations
- Use environment-specific configurations
- Set up SSL/TLS certificates
- Configure reverse proxy (Nginx)
- Set up monitoring and logging
- Implement backup strategies
- Use CDN for static assets

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Email: support@hrms-platform.com
- Documentation: [docs.hrms-platform.com](https://docs.hrms-platform.com)

## 🗺️ Roadmap

- [ ] Mobile app development (React Native)
- [ ] Advanced analytics and reporting
- [ ] Integration with more payment gateways
- [ ] Multi-language support
- [ ] Advanced face recognition features
- [ ] Automated report generation
- [ ] Parent portal
- [ ] Library management system
- [ ] Hostel management
- [ ] Transport management

---

Built with ❤️ for educational institutions worldwide.