import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, User, Shield, Save, Bell, Lock } from 'lucide-react';

export default function AdminProfile() {
  const navigate = useNavigate();
  const [adminInfo, setAdminInfo] = useState<any>(null);
  const [activeTab, setActiveTab] = useState('profile');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const info = localStorage.getItem('admin_info');
    if (info) {
      setAdminInfo(JSON.parse(info));
    } else {
      navigate('/admin/login');
    }
  }, [navigate]);

  const handleSave = async () => {
    setLoading(true);
    // TODO: Implement save functionality
    setTimeout(() => {
      setLoading(false);
      alert('Settings saved successfully!');
    }, 1000);
  };

  if (!adminInfo) {
    return <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-purple-50 flex items-center justify-center">
      <div className="w-12 h-12 border-4 border-purple-500/30 border-t-purple-500 rounded-full animate-spin"></div>
    </div>;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-purple-50">
      <div className="bg-white/90 backdrop-blur-xl border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/admin/dashboard')} className="p-2 text-gray-600 hover:text-gray-900">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <h1 className="text-2xl font-bold text-gray-900">Settings & Profile</h1>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Profile Header */}
        <div className="bg-white/90 rounded-2xl p-8 border border-gray-200 mb-6">
          <div className="flex items-center gap-6">
            <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center text-white text-3xl font-bold">
              {adminInfo.name.charAt(0)}
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-1">{adminInfo.name}</h2>
              <p className="text-gray-600">{adminInfo.email}</p>
              <span className="inline-block mt-2 px-3 py-1 bg-purple-500/20 text-purple-600 rounded-full text-sm font-medium capitalize">
                {adminInfo.role}
              </span>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-4 mb-6">
          {[
            { id: 'profile', label: 'Profile', icon: User },
            { id: 'security', label: 'Security', icon: Shield },
            { id: 'notifications', label: 'Notifications', icon: Bell },
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-6 py-3 rounded-xl font-medium transition-all ${
                activeTab === tab.id
                  ? 'bg-purple-600 text-white'
                  : 'bg-white/80 text-gray-600 hover:bg-white border border-gray-200'
              }`}
            >
              <tab.icon className="w-5 h-5" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="bg-white/90 rounded-2xl p-8 border border-gray-200">
          {activeTab === 'profile' && (
            <div className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Full Name</label>
                <input
                  type="text"
                  defaultValue={adminInfo.name}
                  className="w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-lg text-gray-900 focus:border-purple-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Email Address</label>
                <input
                  type="email"
                  defaultValue={adminInfo.email}
                  className="w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-lg text-gray-900 focus:border-purple-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Role</label>
                <input
                  type="text"
                  value={adminInfo.role}
                  disabled
                  className="w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-lg text-gray-600 cursor-not-allowed capitalize"
                />
              </div>
            </div>
          )}

          {activeTab === 'security' && (
            <div className="space-y-6">
              <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg flex items-start gap-3">
                <Lock className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-yellow-400 font-medium mb-1">Security Settings</p>
                  <p className="text-sm text-yellow-400/80">
                    Contact super admin to change password or security settings
                  </p>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Current Password</label>
                <input
                  type="password"
                  placeholder="Enter current password"
                  className="w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-lg text-gray-900 focus:border-purple-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">New Password</label>
                <input
                  type="password"
                  placeholder="Enter new password"
                  className="w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-lg text-gray-900 focus:border-purple-600 focus:outline-none"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Confirm New Password</label>
                <input
                  type="password"
                  placeholder="Confirm new password"
                  className="w-full px-4 py-3 bg-gray-100 border border-gray-300 rounded-lg text-gray-900 focus:border-purple-600 focus:outline-none"
                />
              </div>
            </div>
          )}

          {activeTab === 'notifications' && (
            <div className="space-y-4">
              {[
                { label: 'Email notifications for new users', checked: true },
                { label: 'Email notifications for new videos', checked: true },
                { label: 'Email notifications for support tickets', checked: false },
                { label: 'Daily activity summary', checked: true },
                { label: 'Weekly platform report', checked: false },
              ].map((item, index) => (
                <label key={index} className="flex items-center gap-3 p-4 bg-gray-100 rounded-lg cursor-pointer hover:bg-gray-200 transition-colors border border-gray-200">
                  <input
                    type="checkbox"
                    defaultChecked={item.checked}
                    className="w-5 h-5 rounded accent-purple-600"
                  />
                  <span className="text-gray-700">{item.label}</span>
                </label>
              ))}
            </div>
          )}

          {/* Save Button */}
          <div className="mt-8 pt-6 border-t border-gray-200">
            <button
              onClick={handleSave}
              disabled={loading}
              className="flex items-center gap-2 px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors disabled:opacity-50"
            >
              <Save className="w-5 h-5" />
              {loading ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>

        {/* Permissions Section */}
        <div className="bg-white/90 rounded-2xl p-8 border border-gray-200 mt-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">Your Permissions</h3>
          <div className="grid grid-cols-2 gap-4">
            {Object.entries(adminInfo.permissions || {}).map(([key, value]: [string, any]) => (
              <div
                key={key}
                className={`p-4 rounded-lg border ${
                  value
                    ? 'bg-green-500/10 border-green-500/30 text-green-600'
                    : 'bg-gray-100 border-gray-300 text-gray-600'
                }`}
              >
                <div className="flex items-center gap-2">
                  {value ? (
                    <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                  ) : (
                    <div className="w-2 h-2 bg-gray-500 rounded-full"></div>
                  )}
                  <span className="text-sm font-medium capitalize">{key.replace(/_/g, ' ')}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
