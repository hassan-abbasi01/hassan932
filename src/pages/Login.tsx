import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, Twitter, Instagram, Youtube, Scissors, Sparkles } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import toast from 'react-hot-toast';

const Login = () => {
  const navigate = useNavigate();
  const { login, loginAsDemo } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await login(email, password);
      toast.success('Login successful!');
      navigate('/editor');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDemoLogin = async () => {
    setIsLoading(true);
    try {
      await loginAsDemo();
      toast.success('Demo mode activated!');
      navigate('/editor');
    } catch (error) {
      toast.error('Demo login failed');
    } finally {
      setIsLoading(false);
    }
  };

  // OAuth handlers (copied from Signup)
  const handleGoogleLogin = () => {
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';
    window.location.href = `${API_URL}/auth/google/login`;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-purple-50 relative overflow-hidden">
      {/* 3D Background Elements */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {/* Floating 3D Login Elements */}
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
        
        {/* 3D Geometric Shapes */}
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

      {/* Navigation */}
      <nav className="bg-white/90 backdrop-blur-md shadow-lg border-b border-white/20 relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center animate-slide-in-left-3d">
              <Link to="/" className="flex-shrink-0 flex items-center group">
                <div className="relative">
                  <Scissors className="text-indigo-600 mr-3 transform group-hover:rotate-12 transition-all duration-300 animate-pulse-3d" size={28} />
                  <div className="absolute inset-0 bg-indigo-400/20 rounded-full blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                </div>
                <span className="text-2xl font-bold bg-gradient-to-r from-indigo-600 to-purple-600 bg-clip-text text-transparent">
                  SnipX
                </span>
              </Link>
            </div>
            <div className="hidden sm:ml-6 sm:flex sm:items-center animate-slide-in-right-3d">
              <Link to="/" className="text-gray-500 hover:text-gray-700 px-3 py-2 text-sm font-medium transition-all duration-300 transform hover:scale-105">
                Back to Home
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 text-white relative overflow-hidden">
        {/* 3D Background Pattern */}
        <div className="absolute inset-0 opacity-20">
          <div className="absolute top-8 left-8 w-12 h-12 border-2 border-white rounded-full animate-float-3d"></div>
          <div className="absolute top-16 right-16 w-8 h-8 border-2 border-white transform rotate-45 animate-bounce-3d"></div>
          <div className="absolute bottom-8 left-1/3 w-6 h-6 bg-white rounded-full animate-pulse-3d"></div>
        </div>
        
        <div className="max-w-7xl mx-auto py-16 px-4 sm:py-24 sm:px-6 lg:px-8 text-center relative z-10">
          <h1 className="text-5xl font-extrabold tracking-tight sm:text-6xl animate-slide-up-3d">
            Welcome back to SnipX
          </h1>
          <p className="mt-6 max-w-lg mx-auto text-xl animate-fade-in-up-3d">
            Log in to access your AI-powered video editing dashboard
          </p>
        </div>
      </div>

      {/* Login Form */}
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 -mt-12 relative z-10">
        <div className="max-w-md mx-auto bg-white/90 backdrop-blur-md rounded-2xl shadow-2xl overflow-hidden border border-white/20 animate-slide-up-3d">
          <div className="p-8">
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold text-gray-800 animate-slide-in-3d">User Login</h2>
              <p className="text-sm text-gray-600 mt-2">
                Sign in to your SnipX account
              </p>
              <p className="text-gray-600 mt-2 animate-fade-in-3d">
                Don't have an account?{' '}
                <Link to="/signup" className="text-indigo-600 hover:text-indigo-500 font-medium transition-colors duration-300">
                  Sign up
                </Link>
              </p>
            </div>

            {/* Social Login Buttons */}
            <div className="flex justify-center mb-6">
              <button 
                onClick={handleGoogleLogin}
                disabled={isLoading}
                className="bg-white/80 backdrop-blur-sm border-2 border-gray-300 text-gray-700 py-3 px-4 rounded-xl flex items-center justify-center hover:bg-gray-50 hover:border-gray-400 transition-all duration-300 disabled:opacity-50 transform hover:scale-105 hover:-translate-y-1 btn-3d animate-slide-in-3d"
                style={{width: "75%"}}
              >
                <img src="https://www.google.com/favicon.ico" alt="Google" className="w-4 h-4 mr-2" />
                Sign in with Google
              </button>
            </div>

            <div className="relative flex items-center mb-6 animate-fade-in-3d">
              <div className="flex-grow border-t border-gray-300"></div>
              <span className="flex-shrink mx-4 text-gray-500">or</span>
              <div className="flex-grow border-t border-gray-300"></div>
            </div>

            {/* Email/Password Form */}
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="animate-slide-in-left-3d">
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                  Email address
                </label>
                <input
                  type="email"
                  id="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white/80 backdrop-blur-sm transition-all duration-300 hover:shadow-lg"
                  required
                  disabled={isLoading}
                />
              </div>

              <div className="animate-slide-in-right-3d">
                <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-2">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    id="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white/80 backdrop-blur-sm transition-all duration-300 hover:shadow-lg"
                    required
                    disabled={isLoading}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors duration-300 transform hover:scale-110"
                    disabled={isLoading}
                  >
                    {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
                </div>
              </div>

              <div className="flex items-center justify-between mb-6 animate-slide-up-3d">
                <div className="flex items-center">
                  <input
                    id="remember-me"
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded transition-all duration-300 transform hover:scale-110"
                    disabled={isLoading}
                  />
                  <label htmlFor="remember-me" className="ml-2 block text-sm text-gray-700">
                    Remember me
                  </label>
                </div>
                <div className="text-sm">
                  <Link to="#" className="font-medium text-indigo-600 hover:text-indigo-500 transition-colors duration-300">
                    Forgot password?
                  </Link>
                </div>
              </div>

              <button
                type="submit"
                className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-3 px-4 rounded-xl font-medium hover:from-indigo-700 hover:to-purple-700 transition-all duration-300 disabled:opacity-50 transform hover:scale-105 hover:shadow-lg btn-3d animate-slide-up-3d"
                disabled={isLoading}
              >
                {isLoading ? (
                  <div className="flex items-center justify-center">
                    <div className="animate-spin-3d rounded-full h-5 w-5 border-b-2 border-white mr-2"></div>
                    Signing in...
                  </div>
                ) : (
                  'Sign in'
                )}
              </button>
            </form>

            {/* Demo Account Info */}
            <div className="mt-6 bg-gradient-to-r from-indigo-50 to-purple-50 border-2 border-indigo-100 rounded-xl p-6 animate-slide-up-3d">
              <h4 className="text-sm font-medium text-indigo-800 mb-2 flex items-center">
                <Sparkles className="mr-2" size={16} />
                Try Demo Mode
              </h4>
              <p className="text-xs text-indigo-600 mb-3">
                Experience SnipX features without creating an account
              </p>
              <button
                type="button"
                onClick={handleDemoLogin}
                disabled={isLoading}
                className="w-full bg-gradient-to-r from-indigo-100 to-purple-100 text-indigo-700 py-3 px-4 rounded-xl font-medium hover:from-indigo-200 hover:to-purple-200 transition-all duration-300 disabled:opacity-50 border-2 border-indigo-200 transform hover:scale-105 hover:shadow-lg btn-3d"
              >
                {isLoading ? (
                  <div className="flex items-center justify-center">
                    <div className="animate-spin-3d rounded-full h-4 w-4 border-b-2 border-indigo-600 mr-2"></div>
                    Starting Demo...
                  </div>
                ) : (
                  'Enter Demo Mode'
                )}
              </button>
              <p className="text-xs text-indigo-500 mt-2 text-center">
                Or use credentials: demo@snipx.com / demo1234
              </p>
            </div>
          </div>

          {/* Footer */}
          <div className="bg-gradient-to-r from-gray-50 to-slate-50 px-8 py-6 border-t border-gray-200">
            <p className="text-xs text-gray-500 text-center mb-3">
              By continuing, you agree to our{' '}
              <Link to="#" className="text-indigo-600 hover:text-indigo-500 transition-colors duration-300">
                Terms of Service
              </Link>{' '}
              and{' '}
              <Link to="#" className="text-indigo-600 hover:text-indigo-500 transition-colors duration-300">
                Privacy Policy
              </Link>.
            </p>
            {/* Admin Login Link */}
            <div className="pt-3 border-t border-gray-200">
              <Link 
                to="/admin/login"
                className="flex items-center justify-center gap-2 text-sm text-purple-600 hover:text-purple-700 font-medium transition-colors duration-300"
              >
                <Sparkles className="w-4 h-4" />
                Admin Portal Access
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <footer className="bg-white/90 backdrop-blur-md mt-12 border-t border-white/20">
        <div className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
          <div className="border-t border-gray-200 pt-8 flex flex-col md:flex-row justify-between items-center">
            <div className="flex items-center animate-slide-in-left-3d">
              <Scissors className="text-indigo-600 animate-pulse-3d" size={24} />
              <span className="text-xl font-bold text-gray-900 ml-2">SnipX</span>
            </div>
            <p className="mt-4 md:mt-0 text-sm text-gray-600 animate-fade-in-3d">
              &copy; {new Date().getFullYear()} SnipX Technologies. All rights reserved.
            </p>
            <div className="mt-4 md:mt-0 flex space-x-6 animate-slide-in-right-3d">
              {[Twitter, Instagram, Youtube].map((Icon, index) => (
                <Link 
                  key={index}
                  to="#" 
                  className="text-gray-400 hover:text-indigo-500 transition-all duration-300 transform hover:scale-110 hover:-translate-y-1"
                >
                  <Icon size={20} />
                </Link>
              ))}
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Login;