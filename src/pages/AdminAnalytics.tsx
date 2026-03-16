import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Users, Video, Activity } from 'lucide-react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';

export default function AdminAnalytics() {
  const navigate = useNavigate();
  const [period, setPeriod] = useState('week');
  const [usersData, setUsersData] = useState<any>(null);
  const [videosData, setVideosData] = useState<any>(null);
  const [activityData, setActivityData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalyticsData();
  }, [period]);

  const fetchAnalyticsData = async () => {
    const token = localStorage.getItem('admin_token');
    if (!token) {
      navigate('/admin/login');
      return;
    }

    try {
      const [users, videos, activity] = await Promise.all([
        fetch(`${API_URL}/admin/analytics/chart/users?period=${period}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }).then(r => r.json()),
        fetch(`${API_URL}/admin/analytics/chart/videos?period=${period}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }).then(r => r.json()),
        fetch(`${API_URL}/admin/analytics/chart/activity?period=${period}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }).then(r => r.json())
      ]);

      if (users.success) {
        const chartData = users.labels.map((label: string, index: number) => ({
          date: label,
          users: users.data[index]
        }));
        setUsersData(chartData);
      }

      if (videos.success) {
        const chartData = videos.labels.map((label: string, index: number) => ({
          date: label,
          videos: videos.data[index]
        }));
        setVideosData(chartData);
      }

      if (activity.success) {
        const chartData = activity.labels.map((label: string, index: number) => ({
          date: label,
          activity: activity.data[index]
        }));
        setActivityData(chartData);
      }
    } catch (error) {
      console.error('Error fetching analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-purple-50">
      <div className="bg-white/90 backdrop-blur-xl border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button onClick={() => navigate('/admin/dashboard')} className="p-2 text-gray-600 hover:text-gray-900">
                <ArrowLeft className="w-5 h-5" />
              </button>
              <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
            </div>

            <div className="flex gap-2">
              {['week', 'month', 'year'].map(p => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  className={`px-4 py-2 rounded-lg capitalize transition-colors ${
                    period === p ? 'bg-purple-600 text-white' : 'bg-white/80 text-gray-600 hover:bg-white border border-gray-200'
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* User Growth Chart */}
        <div className="bg-white/90 rounded-2xl p-6 border border-gray-200">
          <div className="flex items-center gap-3 mb-6">
            <Users className="w-6 h-6 text-blue-600" />
            <h2 className="text-xl font-bold text-gray-900">User Growth</h2>
          </div>
          {loading || !usersData ? (
            <div className="h-80 flex items-center justify-center">
              <div className="w-12 h-12 border-4 border-purple-500/30 border-t-purple-500 rounded-full animate-spin"></div>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={usersData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }} />
                <Line type="monotone" dataKey="users" stroke="#3b82f6" strokeWidth={2} dot={{ fill: '#3b82f6' }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Video Uploads Chart */}
        <div className="bg-white/90 rounded-2xl p-6 border border-gray-200">
          <div className="flex items-center gap-3 mb-6">
            <Video className="w-6 h-6 text-purple-600" />
            <h2 className="text-xl font-bold text-gray-900">Video Uploads</h2>
          </div>
          {loading || !videosData ? (
            <div className="h-80 flex items-center justify-center">
              <div className="w-12 h-12 border-4 border-purple-500/30 border-t-purple-500 rounded-full animate-spin"></div>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={videosData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }} />
                <Bar dataKey="videos" fill="#a855f7" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Platform Activity Chart */}
        <div className="bg-white/90 rounded-2xl p-6 border border-gray-200">
          <div className="flex items-center gap-3 mb-6">
            <Activity className="w-6 h-6 text-green-600" />
            <h2 className="text-xl font-bold text-gray-900">Platform Activity</h2>
          </div>
          {loading || !activityData ? (
            <div className="h-80 flex items-center justify-center">
              <div className="w-12 h-12 border-4 border-purple-500/30 border-t-purple-500 rounded-full animate-spin"></div>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={activityData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }} />
                <Line type="monotone" dataKey="activity" stroke="#10b981" strokeWidth={2} dot={{ fill: '#10b981' }} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}
