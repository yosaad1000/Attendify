import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  HomeIcon, 
  UserGroupIcon, 
  AcademicCapIcon,
  ClipboardDocumentListIcon,
  CurrencyDollarIcon,
  ChartBarIcon,
  CogIcon,
  CalendarIcon
} from '@heroicons/react/24/outline';
import { useAuth } from '../../contexts/AuthContext';

const Sidebar: React.FC = () => {
  const { user } = useAuth();

  const getNavigationItems = () => {
    const baseItems = [
      { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
      { name: 'Calendar', href: '/calendar', icon: CalendarIcon },
    ];

    switch (user?.role) {
      case 'admin':
        return [
          ...baseItems,
          { name: 'Students', href: '/students', icon: UserGroupIcon },
          { name: 'Teachers', href: '/teachers', icon: AcademicCapIcon },
          { name: 'Subjects', href: '/subjects', icon: ClipboardDocumentListIcon },
          { name: 'Attendance', href: '/attendance', icon: ClipboardDocumentListIcon },
          { name: 'Grades', href: '/grades', icon: ChartBarIcon },
          { name: 'Fees', href: '/fees', icon: CurrencyDollarIcon },
          { name: 'Analytics', href: '/analytics', icon: ChartBarIcon },
          { name: 'Settings', href: '/settings', icon: CogIcon },
        ];
      case 'teacher':
        return [
          ...baseItems,
          { name: 'My Classes', href: '/classes', icon: AcademicCapIcon },
          { name: 'Attendance', href: '/attendance', icon: ClipboardDocumentListIcon },
          { name: 'Grades', href: '/grades', icon: ChartBarIcon },
          { name: 'Students', href: '/students', icon: UserGroupIcon },
        ];
      case 'student':
        return [
          ...baseItems,
          { name: 'My Subjects', href: '/subjects', icon: ClipboardDocumentListIcon },
          { name: 'Attendance', href: '/attendance', icon: ClipboardDocumentListIcon },
          { name: 'Grades', href: '/grades', icon: ChartBarIcon },
          { name: 'Fees', href: '/fees', icon: CurrencyDollarIcon },
        ];
      default:
        return baseItems;
    }
  };

  const navigation = getNavigationItems();

  return (
    <div className="flex flex-col w-64 bg-white shadow-lg">
      <div className="flex items-center justify-center h-16 px-4 bg-primary-600">
        <h1 className="text-xl font-bold text-white">HRMS Platform</h1>
      </div>
      
      <nav className="flex-1 px-4 py-6 space-y-2">
        {navigation.map((item) => (
          <NavLink
            key={item.name}
            to={item.href}
            className={({ isActive }) =>
              `flex items-center px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                isActive
                  ? 'bg-primary-100 text-primary-700'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              }`
            }
          >
            <item.icon className="w-5 h-5 mr-3" />
            {item.name}
          </NavLink>
        ))}
      </nav>
    </div>
  );
};

export default Sidebar;