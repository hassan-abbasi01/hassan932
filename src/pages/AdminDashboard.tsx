import { useState, useEffect } from 'react';
import { useNavigate} from 'react-router-dom';
import {
  Users,
  Video,
  Activity,
  TrendingUp,
  Calendar,
  HardDrive,
  UserCheck,
  VideoIcon,
  BarChart3,
  LogOut,
  Shield,
  MessageSquare,
  Settings,
  Bell
} from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';

interface DashboardStats {
  total_users: number;
  total_videos: number;
  total_storage_bytes: number;
  active_users_today: number;
  videos_uploaded_today: number;
  users_this_week: number;
  users_this_month: number;
  videos_this_week: number;
  videos_this_month: number;
  total_enhancements: number;
  avg_video_duration: number;
}

interface AdminInfo {
  email: string;
  name: string;
  role: string;
  permissions: Record<string, boolean>;
}

export default function AdminDashboard() {
  const navigate = useNavigate();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [adminInfo, setAdminInfo] = useState<AdminInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    // Check authentication
    const token = localStorage.getItem('admin_token');
    const info = localStorage.getItem('admin_info');
    
    if (!token || !info) {
      navigate('/admin/login');
      return;
    }

    setAdminInfo(JSON.parse(info));
    fetchDashboardStats(token);
  }, [navigate]);

  const fetchDashboardStats = async (token: string) => {
    try {
      const response = await fetch(`${API_URL}/admin/dashboard/stats`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          localStorage.removeItem('admin_token');
          localStorage.removeItem('admin_info');
          navigate('/admin/login');
          return;
        }
        throw new Error('Failed to fetch stats');
      }

      const data = await response.json();
      if (data.success) {
        setStats(data.stats);
      }
    } catch (error) {
      console.error('Error fetching dashboard stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_info');
    navigate('/admin/login');
  };

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-purple-50 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-16 h-16 border-4 border-purple-600/30 border-t-purple-600 rounded-full animate-spin"></div>
          <p className="text-gray-600">Loading dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-purple-50">
      {/* Top Navigation Bar */}
      <nav className="bg-white/90 backdrop-blur-xl border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <Shield className="w-8 h-8 text-purple-600" />
              <h1 className="text-xl font-bold text-gray-900">Admin Portal</h1>
            </div>

            <div className="flex items-center gap-4">
              <button className="p-2 text-gray-600 hover:text-gray-900 transition-colors">
                <Bell className="w-5 h-5" />
              </button>
              
              <div className="flex items-center gap-3 px-4 py-2 bg-gray-100 rounded-lg">
                <div className="w-8 h-8 bg-gradient-to-br from-purple-600 to-pink-600 rounded-full flex items-center justify-center text-white font-semibold">
                  {adminInfo?.name.charAt(0)}
                </div>
                <div className="text-left">
                  <p className="text-sm font-medium text-gray-900">{adminInfo?.name}</p>
                  <p className="text-xs text-gray-600 capitalize">{adminInfo?.role}</p>
                </div>
              </div>

              <button
                onClick={handleLogout}
                className="flex items-center gap-2 px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg transition-colors"
              >
                <LogOut className="w-4 h-4" />
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Tab Navigation */}
        <div className="flex gap-4 mb-8 overflow-x-auto">
          {[
            { id: 'overview', label: 'Overview', icon: BarChart3 },
            { id: 'users', label: 'Users', icon: Users },
            { id: 'videos', label: 'Videos', icon: Video },
            { id: 'analytics', label: 'Analytics', icon: Activity },
            { id: 'support', label: 'Support', icon: MessageSquare },
            { id: 'settings', label: 'Settings', icon: Settings },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                if (tab.id === 'users') navigate('/admin/users');
                if (tab.id === 'videos') navigate('/admin/videos');
                if (tab.id === 'analytics') navigate('/admin/analytics');
                if (tab.id === 'support') navigate('/admin/support');
                if (tab.id === 'settings') navigate('/admin/profile');
              }}
              className={`flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-purple-600 text-white shadow-lg shadow-purple-500/30'
                  : 'bg-white/80 text-gray-600 hover:bg-white hover:text-gray-900'
              }`}
            >
              <tab.icon className="w-5 h-5" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {/* Total Users */}
          <div className="bg-gradient-to-br from-blue-500/10 to-blue-600/5 backdrop-blur-xl rounded-2xl p-6 border border-blue-500/20">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 bg-blue-500/20 rounded-xl">
                <Users className="w-6 h-6 text-blue-600" />
              </div>
              <span className="text-xs text-blue-600 font-semibold">+{stats?.users_this_week || 0} this week</span>
            </div>
            <p className="text-3xl font-bold text-gray-900 mb-1">{stats?.total_users || 0}</p>
            <p className="text-sm text-gray-600">Total Users</p>
          </div>

          {/* Total Videos */}
          <div className="bg-gradient-to-br from-purple-500/10 to-purple-600/5 backdrop-blur-xl rounded-2xl p-6 border border-purple-500/20">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 bg-purple-500/20 rounded-xl">
                <VideoIcon className="w-6 h-6 text-purple-600" />
              </div>
              <span className="text-xs text-purple-600 font-semibold">+{stats?.videos_this_week || 0} this week</span>
            </div>
            <p className="text-3xl font-bold text-gray-900 mb-1">{stats?.total_videos || 0}</p>
            <p className="text-sm text-gray-600">Total Videos</p>
          </div>

          {/* Active Today */}
          <div className="bg-gradient-to-br from-green-500/10 to-green-600/5 backdrop-blur-xl rounded-2xl p-6 border border-green-500/20">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 bg-green-500/20 rounded-xl">
                <UserCheck className="w-6 h-6 text-green-600" />
              </div>
              <span className="text-xs text-green-600 font-semibold">Active Now</span>
            </div>
            <p className="text-3xl font-bold text-gray-900 mb-1">{stats?.active_users_today || 0}</p>
            <p className="text-sm text-gray-600">Active Users Today</p>
          </div>

          {/* Storage */}
          <div className="bg-gradient-to-br from-orange-500/10 to-orange-600/5 backdrop-blur-xl rounded-2xl p-6 border border-orange-500/20">
            <div className="flex items-center justify-between mb-4">
              <div className="p-3 bg-orange-500/20 rounded-xl">
                <HardDrive className="w-6 h-6 text-orange-600" />
              </div>
              <span className="text-xs text-orange-600 font-semibold">Total Storage</span>
            </div>
            <p className="text-3xl font-bold text-gray-900 mb-1">
              {formatBytes(stats?.total_storage_bytes || 0)}
            </p>
            <p className="text-sm text-gray-600">Data Stored</p>
          </div>
        </div>

        {/* Quick Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white/90 rounded-xl p-6 border border-gray-200">
            <div className="flex items-center gap-3 mb-2">
              <Calendar className="w-5 h-5 text-gray-600" />
              <p className="text-gray-600 text-sm">Uploads Today</p>
            </div>
            <p className="text-2xl font-bold text-gray-900">{stats?.videos_uploaded_today || 0}</p>
          </div>

          <div className="bg-white/90 rounded-xl p-6 border border-gray-200">
            <div className="flex items-center gap-3 mb-2">
              <TrendingUp className="w-5 h-5 text-gray-600" />
              <p className="text-gray-600 text-sm">Enhanced Videos</p>
            </div>
            <p className="text-2xl font-bold text-gray-900">{stats?.total_enhancements || 0}</p>
          </div>

          <div className="bg-white/90 rounded-xl p-6 border border-gray-200">
            <div className="flex items-center gap-3 mb-2">
              <Activity className="w-5 h-5 text-gray-600" />
              <p className="text-gray-600 text-sm">Avg Video Duration</p>
            </div>
            <p className="text-2xl font-bold text-gray-900">
              {formatDuration(stats?.avg_video_duration || 0)}
            </p>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-white/90 rounded-2xl p-6 border border-gray-200">
          <h2 className="text-xl font-bold text-gray-900 mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <button
              onClick={() => navigate('/admin/users')}
              className="flex flex-col items-center gap-3 p-6 bg-gray-100 hover:bg-gray-200 rounded-xl transition-all border border-gray-300"
            >
              <Users className="w-8 h-8 text-purple-600" />
              <span className="text-gray-900 font-medium">Manage Users</span>
            </button>

            <button
              onClick={() => navigate('/admin/videos')}
              className="flex flex-col items-center gap-3 p-6 bg-gray-100 hover:bg-gray-200 rounded-xl transition-all border border-gray-300"
            >
              <Video className="w-8 h-8 text-blue-600" />
              <span className="text-gray-900 font-medium">Manage Videos</span>
            </button>

            <button
              onClick={() => navigate('/admin/analytics')}
              className="flex flex-col items-center gap-3 p-6 bg-gray-100 hover:bg-gray-200 rounded-xl transition-all border border-gray-300"
            >
              <BarChart3 className="w-8 h-8 text-green-600" />
              <span className="text-gray-900 font-medium">View Analytics</span>
            </button>

            <button
              onClick={() => navigate('/admin/support')}
              className="flex flex-col items-center gap-3 p-6 bg-gray-100 hover:bg-gray-200 rounded-xl transition-all border border-gray-300"
            >
              <MessageSquare className="w-8 h-8 text-orange-600" />
              <span className="text-gray-900 font-medium">Support Chat</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
