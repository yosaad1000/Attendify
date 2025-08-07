import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { analyticsApi } from '../lib/api';
import { 
  UserGroupIcon, 
  AcademicCapIcon, 
  ClipboardDocumentListIcon,
  CurrencyDollarIcon 
} from '@heroicons/react/24/outline';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';

const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await analyticsApi.getDashboardStats(user?.role || 'student');
        if (response.data.success) {
          setStats(response.data.data);
        }
      } catch (error) {
        console.error('Failed to fetch dashboard stats:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, [user?.role]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  const getStatsCards = () => {
    switch (user?.role) {
      case 'admin':
        return [
          { name: 'Total Students', value: stats?.totalStudents || 0, icon: UserGroupIcon, color: 'bg-blue-500' },
          { name: 'Total Teachers', value: stats?.totalTeachers || 0, icon: AcademicCapIcon, color: 'bg-green-500' },
          { name: 'Total Subjects', value: stats?.totalSubjects || 0, icon: ClipboardDocumentListIcon, color: 'bg-purple-500' },
          { name: 'Pending Fees', value: `$${stats?.pendingFees || 0}`, icon: CurrencyDollarIcon, color: 'bg-red-500' },
        ];
      case 'teacher':
        return [
          { name: 'My Classes', value: stats?.totalClasses || 0, icon: AcademicCapIcon, color: 'bg-blue-500' },
          { name: 'Students', value: stats?.totalStudents || 0, icon: UserGroupIcon, color: 'bg-green-500' },
          { name: 'Attendance Rate', value: `${stats?.attendanceRate || 0}%`, icon: ClipboardDocumentListIcon, color: 'bg-purple-500' },
        ];
      case 'student':
        return [
          { name: 'Enrolled Subjects', value: stats?.enrolledSubjects || 0, icon: ClipboardDocumentListIcon, color: 'bg-blue-500' },
          { name: 'Attendance Rate', value: `${stats?.attendanceRate || 0}%`, icon: ClipboardDocumentListIcon, color: 'bg-green-500' },
          { name: 'Pending Fees', value: `$${stats?.pendingFees || 0}`, icon: CurrencyDollarIcon, color: 'bg-red-500' },
        ];
      default:
        return [];
    }
  };

  const statsCards = getStatsCards();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600">Welcome to your HRMS dashboard</p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statsCards.map((stat, index) => (
          <div key={index} className="card p-6">
            <div className="flex items-center">
              <div className={`p-3 rounded-lg ${stat.color}`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">{stat.name}</p>
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Attendance Chart */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Attendance Overview</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={stats?.attendanceData || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="attendance" fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Performance Chart */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance Trends</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={stats?.performanceData || []}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="performance" stroke="#10b981" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent Activities */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Activities</h3>
        <div className="space-y-4">
          {(stats?.recentActivities || []).map((activity: any, index: number) => (
            <div key={index} className="flex items-center space-x-3">
              <div className="w-2 h-2 bg-primary-500 rounded-full"></div>
              <p className="text-sm text-gray-600">{activity.message}</p>
              <span className="text-xs text-gray-400">{activity.time}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;