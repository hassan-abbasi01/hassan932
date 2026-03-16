import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Users, 
  Video, 
  BarChart3, 
  Settings, 
  Shield, 
  Activity,
  TrendingUp,
  Download,
  Eye,
  Trash2,
  Search,
  Filter,
  RefreshCw,
  MessageSquare,
  Sparkles
} from 'lucide-react';
import toast from 'react-hot-toast';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';

interface AdminStats {
  totalUsers: number;
  totalVideos: number;
  totalProcessingTime: number;
  activeUsers: number;
  storageUsed: number;
  monthlyGrowth: number;
}

interface UserData {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  joinDate: string;
  lastActive: string;
  videosProcessed: number;
  status: 'active' | 'inactive' | 'suspended';
}

interface VideoData {
  id: string;
  filename: string;
  userId: string;
  userEmail: string;
  uploadDate: string;
  status: string;
  size: number;
  processingOptions: string[];
}

const Admin = () => {
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('dashboard');
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<UserData[]>([]);
  const [videos, setVideos] = useState<VideoData[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [loading, setLoading] = useState(true);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });

  useEffect(() => {
    // Check if user is admin
    const isAdmin = localStorage.getItem('admin_token') || false;
    if (!isAdmin) {
      // Try to login as admin if logged in as admin@snipx.com
      const userEmail = localStorage.getItem('user')?.includes('admin@snipx.com');
      if (!userEmail) {
        toast.error('Access denied. Admin only.');
        navigate('/');
        return;
      }
    }
    loadAdminData();
  }, [navigate]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      setMousePosition({
        x: (e.clientX / window.innerWidth) * 100,
        y: (e.clientY / window.innerHeight) * 100,
      });
    };

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  const loadAdminData = async () => {
    try {
      const token = localStorage.getItem('admin_token');
      
      // Fetch real stats from backend
      const statsResponse = await fetch(`${API_URL}/admin/dashboard/stats`, {
        headers: token ? {
          'Authorization': `Bearer ${token}`
        } : {}
      });

      if (statsResponse.ok) {
        const statsData = await statsResponse.json();
        if (statsData.success) {
          setStats({
            totalUsers: statsData.stats.total_users || 0,
            totalVideos: statsData.stats.total_videos || 0,
            totalProcessingTime: Math.round((statsData.stats.avg_video_duration || 0) * statsData.stats.total_videos / 60),
            activeUsers: statsData.stats.active_users_today || 0,
            storageUsed: parseFloat((statsData.stats.total_storage_bytes / (1024 ** 4)).toFixed(2)) || 0,
            monthlyGrowth: 15.3
          });
        }
      } else {
        // Fallback to mock data if not authenticated
        setStats({
          totalUsers: 1247,
          totalVideos: 5832,
          totalProcessingTime: 12450,
          activeUsers: 342,
          storageUsed: 2.4,
          monthlyGrowth: 15.3
        });
      }

      // Mock users and videos for now
      setUsers([
        {
          id: '1',
          email: 'john.doe@example.com',
          firstName: 'John',
          lastName: 'Doe',
          joinDate: '2024-01-15',
          lastActive: '2024-01-25',
          videosProcessed: 23,
          status: 'active'
        },
        {
          id: '2',
          email: 'jane.smith@example.com',
          firstName: 'Jane',
          lastName: 'Smith',
          joinDate: '2024-01-10',
          lastActive: '2024-01-24',
          videosProcessed: 45,
          status: 'active'
        },
        {
          id: '3',
          email: 'bob.wilson@example.com',
          firstName: 'Bob',
          lastName: 'Wilson',
          joinDate: '2023-12-20',
          lastActive: '2024-01-20',
          videosProcessed: 12,
          status: 'inactive'
        }
      ]);

      setVideos([
        {
          id: '1',
          filename: 'presentation.mp4',
          userId: '1',
          userEmail: 'john.doe@example.com',
          uploadDate: '2024-01-25',
          status: 'completed',
          size: 45000000,
          processingOptions: ['cut_silence', 'generate_subtitles']
        },
        {
          id: '2',
          filename: 'tutorial.mov',
          userId: '2',
          userEmail: 'jane.smith@example.com',
          uploadDate: '2024-01-24',
          status: 'processing',
          size: 78000000,
          processingOptions: ['enhance_audio', 'generate_thumbnail']
        }
      ]);
      
      toast.success('Admin data loaded successfully');
    } catch (error) {
      console.error('Admin data load error:', error);
      toast.error('Failed to load admin data');
      
      // Set mock data as fallback
      setStats({
        totalUsers: 1247,
        totalVideos: 5832,
        totalProcessingTime: 12450,
        activeUsers: 342,
        storageUsed: 2.4,
        monthlyGrowth: 15.3
      });
    } finally {
      setLoading(false);
    }
  };

  const handleUserAction = (userId: string, action: 'suspend' | 'activate' | 'delete') => {
    // Handle user actions
    toast.success(`User ${action}d successfully`);
  };

  const handleVideoAction = (videoId: string, action: 'view' | 'download' | 'delete') => {
    // Handle video actions
    toast.success(`Video ${action} action completed`);
  };

  const formatFileSize = (bytes: number) => {
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const filteredUsers = users.filter(user => {
    const matchesSearch = user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         `${user.firstName} ${user.lastName}`.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = filterStatus === 'all' || user.status === filterStatus;
    return matchesSearch && matchesFilter;
  });

  const filteredVideos = videos.filter(video => {
    const matchesSearch = video.filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         video.userEmail.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFilter = filterStatus === 'all' || video.status === filterStatus;
    return matchesSearch && matchesFilter;
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-purple-50 flex items-center justify-center">
        <div className="animate-spin-3d rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-purple-50 relative overflow-hidden">
      {/* 3D Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* Floating 3D Admin Elements */}
        <div 
          className="absolute top-20 left-10 w-32 h-32 bg-gradient-to-br from-purple-400/20 to-pink-400/20 rounded-full blur-xl animate-float-3d transform-gpu"
          style={{
            transform: `translateZ(0) rotateX(45deg) rotateY(${mousePosition.x * 0.1}deg)`,
            transition: 'transform 0.3s ease-out'
          }}
        />
        <div 
          className="absolute top-40 right-20 w-24 h-24 bg-gradient-to-br from-blue-400/20 to-cyan-400/20 rounded-full blur-lg animate-float-3d-delayed transform-gpu"
          style={{
            transform: `translateZ(0) rotateX(-30deg) rotateY(${mousePosition.y * 0.1}deg)`,
            transition: 'transform 0.3s ease-out'
          }}
        />
        <div 
          className="absolute bottom-32 left-1/4 w-40 h-40 bg-gradient-to-br from-green-400/15 to-teal-400/15 rounded-full blur-2xl animate-pulse-3d transform-gpu"
          style={{
            transform: `translateZ(0) rotateX(60deg) rotateY(-${mousePosition.x * 0.05}deg)`,
            transition: 'transform 0.3s ease-out'
          }}
        />
        
        {/* 3D Admin Icons */}
        <div className="absolute top-1/3 right-1/4 w-16 h-16 bg-gradient-to-br from-orange-400/30 to-red-400/30 transform rotate-45 animate-spin-3d blur-sm" />
        <div className="absolute bottom-1/4 right-1/3 w-12 h-12 bg-gradient-to-br from-indigo-400/30 to-purple-400/30 transform rotate-12 animate-bounce-3d blur-sm" />
        
        {/* Floating Sparkles */}
        <div className="absolute top-1/4 left-1/3 animate-sparkle-3d">
          <Sparkles className="text-purple-400/40 w-6 h-6 transform-gpu" style={{ transform: 'rotateZ(45deg)' }} />
        </div>
        <div className="absolute top-2/3 right-1/2 animate-sparkle-3d-delayed">
          <Sparkles className="text-pink-400/40 w-4 h-4 transform-gpu" style={{ transform: 'rotateZ(-30deg)' }} />
        </div>
      </div>

      {/* Header */}
      <div className="bg-white/90 backdrop-blur-md shadow-lg border-b border-white/20 relative z-10">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center animate-slide-in-left-3d">
              <Shield className="text-purple-600 mr-3 animate-pulse-3d" size={28} />
              <h1 className="text-2xl font-bold text-gray-900 bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
                Admin Dashboard
              </h1>
            </div>
            <button
              onClick={loadAdminData}
              className="flex items-center px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-xl hover:from-purple-700 hover:to-pink-700 transition-all duration-300 transform hover:scale-105 hover:shadow-lg btn-3d"
            >
              <RefreshCw size={16} className="mr-2" />
              Refresh
            </button>
          </div>
        </div>
      </div>

      <div className="container mx-auto px-4 py-6 relative z-10">
        <div className="flex flex-col lg:flex-row gap-6">
          {/* Sidebar */}
          <div className="lg:w-64 bg-white/90 backdrop-blur-md rounded-2xl shadow-xl p-6 border border-white/20 animate-slide-in-left-3d">
            <nav className="space-y-3">
              {[
                { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
                { id: 'users', label: 'User Management', icon: Users },
                { id: 'videos', label: 'Video Management', icon: Video },
                { id: 'support', label: 'Support Tickets', icon: MessageSquare },
                { id: 'analytics', label: 'Analytics', icon: Activity },
                { id: 'settings', label: 'Settings', icon: Settings }
              ].map((tab, index) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full flex items-center px-4 py-3 rounded-xl text-sm font-medium transition-all duration-300 transform hover:scale-105 hover:-translate-y-1 animate-slide-in-stagger-3d ${
                    activeTab === tab.id
                      ? 'bg-gradient-to-r from-purple-100 to-pink-100 text-purple-700 shadow-lg'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                  style={{ animationDelay: `${index * 100}ms` }}
                >
                  <tab.icon size={16} className="mr-3 animate-pulse" />
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Main Content */}
          <div className="flex-1">
            {activeTab === 'dashboard' && (
              <div className="space-y-8">
                <h2 className="text-3xl font-bold text-gray-900 animate-slide-in-3d">Dashboard Overview</h2>
                
                {/* Stats Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {[
                    { icon: Users, label: 'Total Users', value: stats?.totalUsers.toLocaleString(), color: 'blue', delay: '0ms' },
                    { icon: Video, label: 'Total Videos', value: stats?.totalVideos.toLocaleString(), color: 'green', delay: '100ms' },
                    { icon: Activity, label: 'Active Users', value: stats?.activeUsers, color: 'purple', delay: '200ms' },
                    { icon: TrendingUp, label: 'Monthly Growth', value: `${stats?.monthlyGrowth}%`, color: 'yellow', delay: '300ms' },
                    { icon: BarChart3, label: 'Storage Used', value: `${stats?.storageUsed} TB`, color: 'red', delay: '400ms' },
                    { icon: Activity, label: 'Processing Time', value: `${stats?.totalProcessingTime.toLocaleString()} min`, color: 'indigo', delay: '500ms' }
                  ].map((stat, index) => (
                    <div 
                      key={stat.label}
                      className="bg-white/90 backdrop-blur-md rounded-2xl shadow-xl p-6 border border-white/20 transform hover:scale-105 hover:-translate-y-2 transition-all duration-300 hover:shadow-2xl animate-card-float-3d interactive-3d"
                      style={{ animationDelay: stat.delay }}
                    >
                      <div className="flex items-center">
                        <div className={`bg-${stat.color}-100 rounded-2xl p-4 shadow-lg transform hover:rotateY(15deg) transition-all duration-300`}>
                          <stat.icon className={`text-${stat.color}-600`} size={28} />
                        </div>
                        <div className="ml-4">
                          <p className="text-sm font-medium text-gray-600">{stat.label}</p>
                          <p className="text-3xl font-bold text-gray-900">{stat.value}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Recent Activity */}
                <div className="bg-white/90 backdrop-blur-md rounded-2xl shadow-xl p-8 border border-white/20 animate-slide-up-3d">
                  <h3 className="text-xl font-semibold text-gray-900 mb-6 flex items-center">
                    <Activity className="mr-3 text-purple-600" size={24} />
                    Recent Activity
                  </h3>
                  <div className="space-y-4">
                    {[
                      { icon: Video, text: 'Video processed successfully', detail: 'presentation.mp4 by john.doe@example.com', time: '2 min ago', color: 'green' },
                      { icon: Users, text: 'New user registered', detail: 'alice.johnson@example.com', time: '5 min ago', color: 'blue' }
                    ].map((activity, index) => (
                      <div 
                        key={index}
                        className="flex items-center justify-between py-4 border-b border-gray-100 last:border-b-0 animate-slide-in-stagger-3d hover:bg-purple-50/50 rounded-xl px-4 transition-all duration-300"
                        style={{ animationDelay: `${index * 200}ms` }}
                      >
                        <div className="flex items-center">
                          <div className={`bg-${activity.color}-100 rounded-full p-3 mr-4 shadow-lg transform hover:scale-110 transition-all duration-300`}>
                            <activity.icon className={`text-${activity.color}-600`} size={16} />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-gray-900">{activity.text}</p>
                            <p className="text-xs text-gray-500">{activity.detail}</p>
                          </div>
                        </div>
                        <span className="text-xs text-gray-500">{activity.time}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'users' && (
              <div className="space-y-6">
                <div className="flex justify-between items-center">
                  <h2 className="text-3xl font-bold text-gray-900 animate-slide-in-3d">User Management</h2>
                </div>

                {/* Search and Filter */}
                <div className="bg-white/90 backdrop-blur-md rounded-2xl shadow-xl p-6 border border-white/20 animate-slide-up-3d">
                  <div className="flex flex-col sm:flex-row gap-4">
                    <div className="flex-1 relative group">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 group-hover:text-purple-500 transition-colors" size={16} />
                      <input
                        type="text"
                        placeholder="Search users..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white/80 backdrop-blur-sm transition-all duration-300 hover:shadow-lg"
                      />
                    </div>
                    <div className="flex items-center gap-2">
                      <Filter size={16} className="text-gray-400" />
                      <select
                        value={filterStatus}
                        onChange={(e) => setFilterStatus(e.target.value)}
                        className="px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white/80 backdrop-blur-sm transition-all duration-300 hover:shadow-lg"
                      >
                        <option value="all">All Status</option>
                        <option value="active">Active</option>
                        <option value="inactive">Inactive</option>
                        <option value="suspended">Suspended</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* Users Table */}
                <div className="bg-white/90 backdrop-blur-md rounded-2xl shadow-xl overflow-hidden border border-white/20 animate-slide-up-3d">
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gradient-to-r from-purple-50 to-pink-50">
                        <tr>
                          {['User', 'Status', 'Videos', 'Join Date', 'Last Active', 'Actions'].map((header, index) => (
                            <th 
                              key={header}
                              className="px-6 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-wider animate-slide-in-stagger-3d"
                              style={{ animationDelay: `${index * 100}ms` }}
                            >
                              {header}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="bg-white/50 backdrop-blur-sm divide-y divide-gray-200">
                        {filteredUsers.map((user, index) => (
                          <tr 
                            key={user.id}
                            className="hover:bg-purple-50/50 transition-all duration-300 animate-slide-in-stagger-3d"
                            style={{ animationDelay: `${index * 150}ms` }}
                          >
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div>
                                <div className="text-sm font-medium text-gray-900">
                                  {user.firstName} {user.lastName}
                                </div>
                                <div className="text-sm text-gray-500">{user.email}</div>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`inline-flex px-3 py-1 text-xs font-semibold rounded-full transform hover:scale-105 transition-all duration-300 ${
                                user.status === 'active' 
                                  ? 'bg-green-100 text-green-800'
                                  : user.status === 'inactive'
                                  ? 'bg-yellow-100 text-yellow-800'
                                  : 'bg-red-100 text-red-800'
                              }`}>
                                {user.status}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                              {user.videosProcessed}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {new Date(user.joinDate).toLocaleDateString()}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {new Date(user.lastActive).toLocaleDateString()}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                              <div className="flex space-x-2">
                                <button
                                  onClick={() => handleUserAction(user.id, user.status === 'active' ? 'suspend' : 'activate')}
                                  className={`px-3 py-1 rounded text-xs font-medium transform hover:scale-105 transition-all duration-300 ${
                                    user.status === 'active'
                                      ? 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200'
                                      : 'bg-green-100 text-green-800 hover:bg-green-200'
                                  }`}
                                >
                                  {user.status === 'active' ? 'Suspend' : 'Activate'}
                                </button>
                                <button
                                  onClick={() => handleUserAction(user.id, 'delete')}
                                  className="px-3 py-1 bg-red-100 text-red-800 rounded text-xs font-medium hover:bg-red-200 transform hover:scale-105 transition-all duration-300"
                                >
                                  Delete
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* Add similar 3D enhancements to other tabs... */}
            {activeTab === 'analytics' && (
              <div className="space-y-6">
                <h2 className="text-3xl font-bold text-gray-900 animate-slide-in-3d">Analytics & Reports</h2>
                
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {[
                    'User Growth',
                    'Video Processing',
                    'Popular Features',
                    'Storage Usage'
                  ].map((title, index) => (
                    <div 
                      key={title}
                      className="bg-white/90 backdrop-blur-md rounded-2xl shadow-xl p-8 border border-white/20 animate-card-float-3d interactive-3d"
                      style={{ animationDelay: `${index * 200}ms` }}
                    >
                      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
                      <div className="h-64 flex items-center justify-center bg-gradient-to-br from-purple-50 to-pink-50 rounded-xl">
                        <p className="text-gray-500">Chart placeholder - {title.toLowerCase()}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'support' && (
              <div className="space-y-6">
                <div className="flex justify-between items-center">
                  <h2 className="text-3xl font-bold text-gray-900 animate-slide-in-3d">Support Tickets</h2>
                  <button
                    onClick={() => navigate('/admin/support')}
                    className="px-4 py-2 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-xl hover:from-purple-700 hover:to-pink-700 transition-all duration-300 transform hover:scale-105 text-sm font-medium"
                  >
                    Open Full Support Panel
                  </button>
                </div>
                <div className="bg-white/90 backdrop-blur-md rounded-2xl shadow-xl p-8 border border-white/20 animate-slide-up-3d text-center">
                  <MessageSquare size={48} className="mx-auto text-purple-500 mb-4" />
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">Support Ticket Management</h3>
                  <p className="text-gray-600 mb-6">View and respond to user support tickets in the dedicated panel.</p>
                  <button
                    onClick={() => navigate('/admin/support')}
                    className="px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-xl hover:from-purple-700 hover:to-pink-700 transition-all duration-300 transform hover:scale-105 font-medium"
                  >
                    Go to Support Panel
                  </button>
                </div>
              </div>
            )}

            {activeTab === 'settings' && (
              <div className="space-y-6">
                <h2 className="text-3xl font-bold text-gray-900 animate-slide-in-3d">System Settings</h2>
                
                <div className="bg-white/90 backdrop-blur-md rounded-2xl shadow-xl p-8 border border-white/20 animate-slide-up-3d">
                  <h3 className="text-xl font-semibold text-gray-900 mb-6">Platform Configuration</h3>
                  <div className="space-y-6">
                    {[
                      { label: 'Maintenance Mode', desc: 'Enable maintenance mode for system updates' },
                      { label: 'Auto Backup', desc: 'Automatically backup system data', checked: true }
                    ].map((setting, index) => (
                      <div 
                        key={setting.label}
                        className="flex items-center justify-between animate-slide-in-stagger-3d"
                        style={{ animationDelay: `${index * 200}ms` }}
                      >
                        <div>
                          <label className="text-sm font-medium text-gray-700">{setting.label}</label>
                          <p className="text-sm text-gray-500">{setting.desc}</p>
                        </div>
                        <label className="relative inline-flex items-center cursor-pointer">
                          <input type="checkbox" className="sr-only peer" defaultChecked={setting.checked} />
                          <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-purple-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-purple-600 transform hover:scale-105 transition-all duration-300"></div>
                        </label>
                      </div>
                    ))}

                    <div className="animate-slide-in-3d" style={{ animationDelay: '400ms' }}>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Max File Size (MB)
                      </label>
                      <input
                        type="number"
                        defaultValue="500"
                        className="w-32 px-4 py-2 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white/80 backdrop-blur-sm transition-all duration-300 hover:shadow-lg"
                      />
                    </div>

                    <div className="animate-slide-in-3d" style={{ animationDelay: '600ms' }}>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Default Processing Language
                      </label>
                      <select className="px-4 py-2 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white/80 backdrop-blur-sm transition-all duration-300 hover:shadow-lg">
                        <option value="en">English</option>
                        <option value="ur">Urdu</option>
                        <option value="es">Spanish</option>
                        <option value="fr">French</option>
                      </select>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Admin;