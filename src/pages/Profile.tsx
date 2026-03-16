import { useState, useEffect } from 'react';
import { User, Edit3, Download, Clock, Settings, Shield, Eye, Trash2, Save, Sparkles } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { ApiService } from '../services/api';
import toast from 'react-hot-toast';

interface VideoHistory {
  id: string;
  filename: string;
  uploadDate: string;
  status: string;
  size: number;
  duration?: number;
  processedOptions?: string[];
}

interface UserProfile {
  email: string;
  firstName: string;
  lastName: string;
  joinDate: string;
  totalVideos: number;
  totalProcessingTime: number;
  preferences: {
    defaultLanguage: string;
    autoEnhanceAudio: boolean;
    generateThumbnails: boolean;
    emailNotifications: boolean;
  };
}

const Profile = () => {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('profile');
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [videoHistory, setVideoHistory] = useState<VideoHistory[]>([]);
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({
    firstName: '',
    lastName: '',
    email: ''
  });
  const [loading, setLoading] = useState(true);
  const [videoLoading, setVideoLoading] = useState(false);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    loadProfileData();
    loadVideoHistory();
  }, []);

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

  const loadProfileData = async () => {
    try {
      // Use real user data from auth context
      const profileData: UserProfile = {
        email: user?.email || 'demo@snipx.com',
        firstName: user?.firstName || 'Demo',
        lastName: user?.lastName || 'User',
        joinDate: user?.createdAt || new Date().toISOString(),
        totalVideos: 0, // Will be updated after loading videos
        totalProcessingTime: 0,
        preferences: {
          defaultLanguage: 'en',
          autoEnhanceAudio: true,
          generateThumbnails: true,
          emailNotifications: false
        }
      };
      setProfile(profileData);
      setEditForm({
        firstName: profileData.firstName,
        lastName: profileData.lastName,
        email: profileData.email
      });
    } catch (error) {
      toast.error('Failed to load profile data');
    } finally {
      setLoading(false);
    }
  };

  const loadVideoHistory = async () => {
    setVideoLoading(true);
    try {
      console.log('Loading video history for user...');
      console.log('Token available:', !!ApiService.getToken());
      const videos = await ApiService.getUserVideos();
      console.log('Raw video data from API:', videos);
      console.log('Videos type:', typeof videos, 'isArray:', Array.isArray(videos));
      
      if (Array.isArray(videos) && videos.length > 0) {
        const processedVideos = videos.map((video: any) => {
          console.log('Processing video:', video);
          return {
            id: video._id || video.id,
            filename: video.filename,
            uploadDate: video.upload_date || video.uploadDate,
            status: video.status,
            size: video.size,
            duration: video.metadata?.duration,
            processedOptions: video.processing_options ? Object.keys(video.processing_options).filter(key => 
              video.processing_options[key] === true
            ) : []
          };
        });
        console.log('Processed video history:', processedVideos);
        setVideoHistory(processedVideos);
        
        // Update profile stats with real video count
        if (profile) {
          const totalDuration = processedVideos.reduce((acc, v) => acc + (v.duration || 0), 0);
          setProfile({
            ...profile,
            totalVideos: processedVideos.length,
            totalProcessingTime: Math.round(totalDuration)
          });
        }
      } else {
        console.log('No videos found for user or empty array');
        setVideoHistory([]);
        // Update profile stats
        if (profile) {
          setProfile({
            ...profile,
            totalVideos: 0,
            totalProcessingTime: 0
          });
        }
      }
    } catch (error) {
      console.error('Failed to load video history:', error);
      toast.error('Failed to load video history. Please try again.');
      setVideoHistory([]);
    } finally {
      setVideoLoading(false);
    }
  };

  const handleSaveProfile = async () => {
    try {
      // API call to update profile
      toast.success('Profile updated successfully');
      setIsEditing(false);
      if (profile) {
        setProfile({
          ...profile,
          firstName: editForm.firstName,
          lastName: editForm.lastName,
          email: editForm.email
        });
      }
    } catch (error) {
      toast.error('Failed to update profile');
    }
  };

  const handlePreferenceChange = (key: string, value: boolean | string) => {
    if (profile) {
      setProfile({
        ...profile,
        preferences: {
          ...profile.preferences,
          [key]: value
        }
      });
    }
  };

  const formatFileSize = (bytes: number) => {
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleDeleteAccount = async () => {
    setIsDeleting(true);
    try {
      await ApiService.deleteAccount();
      toast.success('Account deleted successfully');
      // Clear user data and redirect to home
      logout();
      window.location.href = '/';
    } catch (error) {
      toast.error('Failed to delete account. Please try again.');
      console.error('Delete account error:', error);
    } finally {
      setIsDeleting(false);
      setShowDeleteConfirm(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-purple-50 flex items-center justify-center">
        <div className="animate-spin-3d rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-purple-50 py-8 relative overflow-hidden">
      {/* 3D Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* Floating 3D Profile Elements */}
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
        
        {/* 3D User Icons */}
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

      <div className="container mx-auto px-4 max-w-6xl relative z-10">
        <div className="bg-white/90 backdrop-blur-md rounded-2xl shadow-2xl overflow-hidden border border-white/20 animate-slide-up-3d">
          {/* Header with 3D Effects */}
          <div className="bg-gradient-to-r from-purple-600 via-pink-600 to-indigo-600 px-8 py-12 relative overflow-hidden">
            {/* 3D Background Pattern */}
            <div className="absolute inset-0 opacity-20">
              <div className="absolute top-4 left-4 w-8 h-8 border-2 border-white rounded-full animate-float-3d"></div>
              <div className="absolute top-8 right-8 w-6 h-6 border-2 border-white transform rotate-45 animate-bounce-3d"></div>
              <div className="absolute bottom-4 left-1/3 w-4 h-4 bg-white rounded-full animate-pulse-3d"></div>
            </div>
            
            <div className="flex items-center relative z-10">
              <div className="bg-white/20 backdrop-blur-md rounded-full p-4 mr-6 shadow-lg transform hover:scale-110 transition-all duration-300 animate-float-3d">
                <User className="text-white" size={40} />
              </div>
              <div className="text-white">
                <h1 className="text-3xl font-bold mb-2 animate-slide-in-left-3d">
                  {profile?.firstName} {profile?.lastName}
                </h1>
                <p className="opacity-90 text-lg animate-slide-in-left-3d" style={{ animationDelay: '200ms' }}>
                  {profile?.email}
                </p>
                <p className="text-sm opacity-75 mt-1 animate-slide-in-left-3d" style={{ animationDelay: '400ms' }}>
                  Member since {new Date(profile?.joinDate || '').toLocaleDateString()}
                </p>
              </div>
            </div>
          </div>

          {/* Navigation Tabs with 3D Effects */}
          <div className="border-b border-gray-200 bg-white/50 backdrop-blur-sm">
            <nav className="flex space-x-8 px-8 overflow-x-auto">
              {[
                { id: 'profile', label: 'Profile', icon: User },
                { id: 'history', label: 'Video History', icon: Clock },
                { id: 'settings', label: 'Settings', icon: Settings }
              ].map((tab, index) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center py-4 px-2 border-b-2 font-medium text-sm transition-all duration-300 transform hover:scale-105 hover:-translate-y-1 animate-slide-in-3d ${
                    activeTab === tab.id
                      ? 'border-purple-500 text-purple-600 shadow-lg'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                  style={{ animationDelay: `${index * 100}ms` }}
                >
                  <tab.icon size={16} className="mr-2 animate-pulse" />
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Tab Content with 3D Animations */}
          <div className="p-8 animate-content-reveal-3d">
            {activeTab === 'profile' && (
              <div className="space-y-8">
                <div className="flex justify-between items-center">
                  <h2 className="text-2xl font-semibold text-gray-900 animate-slide-in-3d">Profile Information</h2>
                  <button
                    onClick={() => setIsEditing(!isEditing)}
                    className="flex items-center px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-xl hover:from-purple-700 hover:to-pink-700 transition-all duration-300 transform hover:scale-105 hover:shadow-lg btn-3d"
                  >
                    <Edit3 size={16} className="mr-2" />
                    {isEditing ? 'Cancel' : 'Edit Profile'}
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div className="space-y-6">
                    {['firstName', 'lastName', 'email'].map((field, index) => (
                      <div key={field} className="animate-slide-in-left-3d" style={{ animationDelay: `${index * 100}ms` }}>
                        <label className="block text-sm font-medium text-gray-700 mb-2 capitalize">
                          {field.replace(/([A-Z])/g, ' $1').trim()}
                        </label>
                        {isEditing ? (
                          <input
                            type={field === 'email' ? 'email' : 'text'}
                            value={editForm[field as keyof typeof editForm]}
                            onChange={(e) => setEditForm({...editForm, [field]: e.target.value})}
                            className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-purple-500 bg-white/80 backdrop-blur-sm transition-all duration-300 hover:shadow-lg"
                          />
                        ) : (
                          <p className="text-gray-900 bg-gray-50 px-4 py-3 rounded-xl">
                            {profile?.[field as keyof UserProfile] as string}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>

                  <div className="space-y-6">
                    <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-2xl p-6 shadow-lg border border-purple-100 animate-card-float-3d">
                      <h3 className="font-medium text-purple-900 mb-4 flex items-center">
                        <Shield className="mr-2" size={20} />
                        Account Statistics
                      </h3>
                      <div className="space-y-4">
                        {[
                          { label: 'Total Videos Processed', value: profile?.totalVideos, delay: '0ms' },
                          { label: 'Processing Time', value: `${profile?.totalProcessingTime} minutes`, delay: '100ms' },
                          { label: 'Member Since', value: new Date(profile?.joinDate || '').toLocaleDateString(), delay: '200ms' }
                        ].map((stat, index) => (
                          <div 
                            key={stat.label}
                            className="flex justify-between items-center animate-bounce-in-3d"
                            style={{ animationDelay: stat.delay }}
                          >
                            <span className="text-purple-700">{stat.label}</span>
                            <span className="font-semibold text-purple-900">{stat.value}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {isEditing && (
                  <div className="flex justify-end space-x-4 animate-slide-up-3d">
                    <button
                      onClick={() => setIsEditing(false)}
                      className="px-6 py-3 border-2 border-gray-300 text-gray-700 rounded-xl hover:bg-gray-50 transition-all duration-300 transform hover:scale-105"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleSaveProfile}
                      className="flex items-center px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 text-white rounded-xl hover:from-green-700 hover:to-emerald-700 transition-all duration-300 transform hover:scale-105 hover:shadow-lg btn-3d"
                    >
                      <Save size={16} className="mr-2" />
                      Save Changes
                    </button>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'history' && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-2xl font-semibold text-gray-900 animate-slide-in-3d">Video History</h2>
                  <button
                    onClick={loadVideoHistory}
                    disabled={videoLoading}
                    className="flex items-center px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-all duration-300 disabled:opacity-50"
                  >
                    <Clock size={16} className={`mr-2 ${videoLoading ? 'animate-spin' : ''}`} />
                    {videoLoading ? 'Loading...' : 'Refresh'}
                  </button>
                </div>
                
                {videoLoading ? (
                  <div className="flex items-center justify-center py-12">
                    <div className="text-center">
                      <div className="animate-spin-3d rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto mb-4"></div>
                      <p className="text-gray-600">Loading video history...</p>
                    </div>
                  </div>
                ) : videoHistory.length === 0 ? (
                  <div className="text-center py-12 bg-gradient-to-br from-purple-50 to-pink-50 rounded-2xl border border-purple-100">
                    <Clock className="mx-auto h-16 w-16 text-purple-400 mb-4" />
                    <h3 className="text-lg font-medium text-purple-900 mb-2">No videos yet</h3>
                    <p className="text-purple-600">Upload your first video to see it here!</p>
                  </div>
                ) : (
                  <div className="overflow-x-auto animate-slide-up-3d">
                    <table className="min-w-full divide-y divide-gray-200 bg-white/80 backdrop-blur-sm rounded-xl shadow-lg">
                      <thead className="bg-gradient-to-r from-purple-50 to-pink-50">
                        <tr>
                          {['Video', 'Status', 'Processing', 'Date', 'Actions'].map((header, index) => (
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
                        {videoHistory.map((video, index) => (
                          <tr 
                            key={video.id} 
                            className="hover:bg-purple-50/50 transition-all duration-300 animate-slide-in-stagger-3d"
                            style={{ animationDelay: `${index * 150}ms` }}
                          >
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="flex items-center gap-3">
                                <div className="w-16 h-10 bg-gradient-to-br from-purple-100 to-pink-100 rounded-lg flex items-center justify-center overflow-hidden">
                                  <svg className="w-6 h-6 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                  </svg>
                                </div>
                                <div>
                                  <div className="text-sm font-medium text-gray-900 max-w-[200px] truncate" title={video.filename}>
                                    {video.filename}
                                  </div>
                                  <div className="text-xs text-gray-500">
                                    {formatFileSize(video.size)} • {video.duration ? formatDuration(Math.round(video.duration)) : 'N/A'}
                                  </div>
                                </div>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`inline-flex px-3 py-1 text-xs font-semibold rounded-full transform hover:scale-105 transition-all duration-300 ${
                                video.status === 'completed' 
                                  ? 'bg-green-100 text-green-800'
                                  : video.status === 'processing'
                                  ? 'bg-yellow-100 text-yellow-800'
                                  : video.status === 'uploaded'
                                  ? 'bg-blue-100 text-blue-800'
                                  : 'bg-red-100 text-red-800'
                              }`}>
                                {video.status}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="flex flex-wrap gap-1">
                                {video.processedOptions && video.processedOptions.length > 0 ? (
                                  video.processedOptions.map((option) => (
                                    <span
                                      key={option}
                                      className="inline-flex px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded-full transform hover:scale-105 transition-all duration-300"
                                    >
                                      {option.replace(/_/g, ' ')}
                                    </span>
                                  ))
                                ) : (
                                  <span className="text-xs text-gray-400">None</span>
                                )}
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {new Date(video.uploadDate).toLocaleDateString()}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                              <div className="flex space-x-3">
                                <button 
                                  onClick={() => window.open(`/editor?video=${video.id}`, '_blank')}
                                  className="text-purple-600 hover:text-purple-900 transform hover:scale-110 transition-all duration-300"
                                  title="View Video"
                                >
                                  <Eye size={16} />
                                </button>
                                <button 
                                  onClick={async () => {
                                    try {
                                      toast.loading('Preparing download...');
                                      const response = await fetch(`http://localhost:5000/api/videos/${video.id}/download`, {
                                        headers: {
                                          'Authorization': `Bearer ${localStorage.getItem('token')}`
                                        }
                                      });
                                      if (response.ok) {
                                        const blob = await response.blob();
                                        const url = window.URL.createObjectURL(blob);
                                        const a = document.createElement('a');
                                        a.href = url;
                                        a.download = video.filename;
                                        a.click();
                                        window.URL.revokeObjectURL(url);
                                        toast.dismiss();
                                        toast.success('Download started!');
                                      } else {
                                        toast.dismiss();
                                        toast.error('Download failed');
                                      }
                                    } catch (error) {
                                      toast.dismiss();
                                      toast.error('Download failed');
                                    }
                                  }}
                                  className="text-green-600 hover:text-green-900 transform hover:scale-110 transition-all duration-300"
                                  title="Download Video"
                                >
                                  <Download size={16} />
                                </button>
                                <button 
                                  onClick={async () => {
                                    if (confirm('Are you sure you want to delete this video?')) {
                                      try {
                                        await ApiService.deleteVideo(video.id);
                                        toast.success('Video deleted successfully');
                                        loadVideoHistory();
                                      } catch (error) {
                                        toast.error('Failed to delete video');
                                      }
                                    }
                                  }}
                                  className="text-red-600 hover:text-red-900 transform hover:scale-110 transition-all duration-300"
                                  title="Delete Video"
                                >
                                  <Trash2 size={16} />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'settings' && (
              <div className="space-y-8">
                <h2 className="text-2xl font-semibold text-gray-900 animate-slide-in-3d">Settings & Preferences</h2>
                
                <div className="space-y-8">
                  {/* Danger Zone */}
                  <div className="bg-gradient-to-br from-red-50 to-pink-50 border-2 border-red-200 rounded-2xl p-8 shadow-lg animate-slide-up-3d">
                    <h3 className="text-lg font-medium text-red-900 mb-6 flex items-center">
                      <Shield className="mr-3" size={24} />
                      Danger Zone
                    </h3>
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <div>
                          <label className="text-sm font-medium text-red-800">Delete Account</label>
                          <p className="text-sm text-red-600">Permanently delete your account and all data</p>
                        </div>
                        <button 
                          onClick={() => setShowDeleteConfirm(true)}
                          className="px-6 py-3 bg-gradient-to-r from-red-600 to-pink-600 text-white rounded-xl hover:from-red-700 hover:to-pink-700 transition-all duration-300 transform hover:scale-105 hover:shadow-lg btn-3d"
                        >
                          Delete Account
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Delete Account Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl p-8 max-w-md w-full mx-4 shadow-2xl transform animate-scale-up">
            <div className="text-center">
              <div className="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-red-100 mb-4">
                <Trash2 className="h-6 w-6 text-red-600" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Delete Account</h3>
              <p className="text-sm text-gray-500 mb-6">
                Are you sure you want to delete your account? This action cannot be undone. 
                All your videos, data, and settings will be permanently removed.
              </p>
              <div className="flex space-x-4">
                <button
                  onClick={() => setShowDeleteConfirm(false)}
                  disabled={isDeleting}
                  className="flex-1 px-4 py-2 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDeleteAccount}
                  disabled={isDeleting}
                  className="flex-1 px-4 py-2 bg-red-600 text-white rounded-xl hover:bg-red-700 transition-colors disabled:opacity-50 flex items-center justify-center"
                >
                  {isDeleting ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Deleting...
                    </>
                  ) : (
                    'Delete Account'
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Profile;