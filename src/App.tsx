import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Navbar from './components/Navbar';
import Home from './pages/Home';
import Editor from './components/VideoEditor';
import Features from './pages/Features';
import Technologies from './pages/Technologies';
import Profile from './pages/Profile';
import Admin from './pages/Admin';
import Help from './pages/Help';
import AdminTickets from './pages/AdminTickets';
import Login from './pages/Login';
import Signup from './pages/Signup';
import AuthCallback from './components/AuthCallback';
import LiveChat from './components/LiveChat';
import KeyboardShortcuts from './components/KeyboardShortcuts';
import VoiceControlButton from './components/VoiceControlButton';
import { useAuth } from './contexts/AuthContext';

// New Admin Portal Imports
import AdminLogin from './pages/AdminLogin';
import AdminDashboard from './pages/AdminDashboard';
import AdminUsers from './pages/AdminUsers';
import AdminVideos from './pages/AdminVideos';
import AdminAnalytics from './pages/AdminAnalytics';
import AdminSupport from './pages/AdminSupport';
import AdminProfile from './pages/AdminProfile';

function App() {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { isAuthenticated } = useAuth();
  
    // Move main layout logic into a wrapper inside Router
    function MainLayout() {
      const location = useLocation();
      return (
        <div className="min-h-screen bg-gray-50 text-gray-900 flex flex-col">
          <Toaster position="top-right" />
          <LiveChat />
          <KeyboardShortcuts />
          <VoiceControlButton />
          <Routes>
            <Route path="/login" element={!isAuthenticated ? <Login /> : <Navigate to="/editor" />} />
            <Route path="/signup" element={!isAuthenticated ? <Signup /> : <Navigate to="/editor" />} />
            <Route path="/auth/callback" element={<AuthCallback />} />
            
            {/* New Admin Portal Routes - No Navbar */}
            <Route path="/admin/login" element={<AdminLogin />} />
            <Route path="/admin/dashboard" element={<AdminDashboard />} />
            <Route path="/admin/users" element={<AdminUsers />} />
            <Route path="/admin/videos" element={<AdminVideos />} />
            <Route path="/admin/analytics" element={<AdminAnalytics />} />
            <Route path="/admin/support" element={<AdminSupport />} />
            <Route path="/admin/profile" element={<AdminProfile />} />
            
            <Route
              path="*"
              element={
                <>
                  <Navbar mobileMenuOpen={mobileMenuOpen} setMobileMenuOpen={setMobileMenuOpen} />
                  <main className={`flex-grow${location.pathname === '/' ? '' : ' pt-20 md:pt-24'}`}>
                    <Routes>
                      <Route path="/" element={<Home />} />
                      <Route path="/technologies" element={<Technologies />} />
                      <Route path="/editor" element={<Editor />} />
                      <Route path="/Features" element={<Features />} />
                      <Route path="/profile" element={isAuthenticated ? <Profile /> : <Navigate to="/login" />} />
                      <Route path="/admin" element={isAuthenticated ? <Admin /> : <Navigate to="/login" />} />
                      <Route path="/admin/tickets" element={isAuthenticated ? <AdminTickets /> : <Navigate to="/login" />} />
                      <Route path="/help" element={<Help />} />
                    </Routes>
                  </main>
                </>
              }
            />
          </Routes>
        </div>
      );
    }

  return (
    <Router
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true
      }}
    >
        <MainLayout />
    </Router>
  );
}

export default App;