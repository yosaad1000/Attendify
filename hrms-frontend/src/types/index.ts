export interface User {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'teacher' | 'student';
  avatar?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Student extends User {
  studentId: string;
  departmentId: string;
  semester: number;
  batchYear: number;
  enrolledSubjects: string[];
  feeStatus: 'paid' | 'pending' | 'overdue';
  totalFees: number;
  paidFees: number;
}

export interface Teacher extends User {
  teacherId: string;
  departmentId: string;
  subjects: string[];
  qualification: string;
  experience: number;
}

export interface Department {
  id: string;
  name: string;
  code: string;
  hodId?: string;
  createdAt: string;
}

export interface Subject {
  id: string;
  name: string;
  code: string;
  departmentId: string;
  semester: number;
  credits: number;
  isElective: boolean;
  teacherId?: string;
}

export interface Attendance {
  id: string;
  studentId: string;
  subjectId: string;
  date: string;
  status: 'present' | 'absent' | 'late';
  markedBy: string;
}

export interface Grade {
  id: string;
  studentId: string;
  subjectId: string;
  semester: number;
  examType: 'midterm' | 'final' | 'assignment' | 'quiz';
  marks: number;
  maxMarks: number;
  gradedBy: string;
  gradedAt: string;
}

export interface Fee {
  id: string;
  studentId: string;
  amount: number;
  type: 'tuition' | 'library' | 'lab' | 'exam' | 'other';
  dueDate: string;
  paidDate?: string;
  status: 'pending' | 'paid' | 'overdue';
  paymentMethod?: string;
  transactionId?: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}