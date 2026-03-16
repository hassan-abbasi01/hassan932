import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Menu, X, Scissors, Sparkles, ArrowUp } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

interface NavbarProps {
  mobileMenuOpen: boolean;
  setMobileMenuOpen: (open: boolean) => void;
}

const Navbar = ({ mobileMenuOpen, setMobileMenuOpen }: NavbarProps) => {
  const [scrolled, setScrolled] = useState(false);
  const [isVisible, setIsVisible] = useState(true);
  const [lastScrollY, setLastScrollY] = useState(0);
  const [showScrollTop, setShowScrollTop] = useState(false);
  const { isAuthenticated, user, logout } = useAuth();

  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;

      // Handle navbar background
      if (currentScrollY > 10) {
        setScrolled(true);
      } else {
        setScrolled(false);
      }

      // Handle navbar visibility
      if (currentScrollY > lastScrollY && currentScrollY > 100) {
        setIsVisible(false);
      } else {
        setIsVisible(true);
      }

      setLastScrollY(currentScrollY);

      // Show scroll-to-top button
      setShowScrollTop(currentScrollY > 200);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [lastScrollY]);

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <>
      <header 
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-500 ${
          scrolled 
            ? 'bg-white/95 backdrop-blur-md shadow-lg py-2' 
            : 'bg-transparent py-4'
        } ${
          isVisible ? 'translate-y-0' : '-translate-y-full'
        }`}
      >
        <div className="container mx-auto px-4 md:px-6">
          <div className="flex items-center justify-between">
            {/* Logo */}
            <div className="flex items-center">
              <Link to="/" className="flex items-center group">
                <div className="relative">
                  <Scissors className="text-purple-600 mr-3 transform group-hover:rotate-12 transition-all duration-300" size={28} />
                  <div className="absolute inset-0 bg-purple-400/20 rounded-full blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                </div>
                <span className="text-2xl font-bold">
                  <span className="bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
                    Snip
                  </span>
                  <span className="text-teal-600">X</span>
                </span>
                {/* Sparkle effect on hover */}
                <div className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                  <Sparkles className="text-purple-400 w-4 h-4 animate-sparkle" />
                </div>
              </Link>
              
              {/* Desktop Navigation */}
              <nav className="hidden md:flex items-center space-x-8 ml-12">
                {[
                  { to: '/', label: 'Home' },
                  { to: '/technologies', label: 'Technologies' },
                  { to: '/editor', label: 'Editor' },
                  { to: '/Features', label: 'Features' },
                  { to: '/help', label: 'Help' }
                ].map((item, index) => (
                  <Link 
                    key={item.to}
                    to={item.to} 
                    className="relative text-gray-700 hover:text-purple-600 transition-all duration-300 font-medium group py-2"
                    style={{ animationDelay: `${index * 100}ms` }}
                  >
                    {item.label}
                    <div className="absolute bottom-0 left-0 w-0 h-0.5 bg-gradient-to-r from-purple-600 to-pink-600 group-hover:w-full transition-all duration-300 rounded-full" />
                  </Link>
                ))}
                
                {isAuthenticated && (
                  <>
                    <Link 
                      to="/profile" 
                      className="relative text-gray-700 hover:text-purple-600 transition-all duration-300 font-medium group py-2"
                    >
                      Profile
                      <div className="absolute bottom-0 left-0 w-0 h-0.5 bg-gradient-to-r from-purple-600 to-pink-600 group-hover:w-full transition-all duration-300 rounded-full" />
                    </Link>
                    {user?.email === 'admin@snipx.com' && (
                      <Link 
                        to="/admin" 
                        className="relative text-gray-700 hover:text-purple-600 transition-all duration-300 font-medium group py-2"
                      >
                        Admin
                        <div className="absolute bottom-0 left-0 w-0 h-0.5 bg-gradient-to-r from-purple-600 to-pink-600 group-hover:w-full transition-all duration-300 rounded-full" />
                      </Link>
                    )}
                  </>
                )}
              </nav>
            </div>
            
            {/* Desktop Auth Section */}
            <div className="hidden md:flex items-center space-x-4">
              {isAuthenticated ? (
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-purple-50 to-pink-50 rounded-full">
                    <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                    <span className="text-gray-700 font-medium">
                      {user?.firstName || 'User'}
                    </span>
                  </div>
                  <button
                    onClick={logout}
                    className="bg-gradient-to-r from-gray-600 to-gray-700 text-white px-6 py-2 rounded-full hover:from-gray-700 hover:to-gray-800 transition-all duration-300 transform hover:-translate-y-0.5 hover:shadow-lg"
                  >
                    Logout
                  </button>
                </div>
              ) : (
                <>
                  <Link 
                    to="/login"
                    className="group bg-gradient-to-r from-purple-600 to-pink-600 text-white px-6 py-2 rounded-full hover:from-purple-700 hover:to-pink-700 transition-all duration-300 transform hover:-translate-y-0.5 hover:shadow-lg font-medium"
                  >
                    <span className="group-hover:scale-105 inline-block transition-transform duration-300">
                      Get Started
                    </span>
                  </Link>
                  <Link 
                    to="/admin/login"
                    className="group border-2 border-purple-600 text-purple-600 px-6 py-2 rounded-full hover:bg-purple-50 transition-all duration-300 transform hover:-translate-y-0.5 hover:shadow-lg font-medium"
                  >
                    <span className="group-hover:scale-105 inline-block transition-transform duration-300">
                      Admin
                    </span>
                  </Link>
                </>
              )}
            </div>
            
            {/* Mobile Menu Button */}
            <button 
              className="md:hidden text-gray-700 p-2 rounded-lg hover:bg-gray-100 transition-colors duration-300"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              <div className="relative w-6 h-6">
                <Menu 
                  size={24} 
                  className={`absolute inset-0 transition-all duration-300 ${
                    mobileMenuOpen ? 'opacity-0 rotate-180' : 'opacity-100 rotate-0'
                  }`} 
                />
                <X 
                  size={24} 
                  className={`absolute inset-0 transition-all duration-300 ${
                    mobileMenuOpen ? 'opacity-100 rotate-0' : 'opacity-0 -rotate-180'
                  }`} 
                />
              </div>
            </button>
          </div>
        </div>
        
        {/* Mobile Menu */}
        <div className={`md:hidden transition-all duration-500 overflow-hidden ${
          mobileMenuOpen 
            ? 'max-h-screen opacity-100' 
            : 'max-h-0 opacity-0'
        }`}>
          <div className="bg-white/95 backdrop-blur-md border-t border-gray-200/50 shadow-lg">
            <nav className="container mx-auto px-4 py-6 space-y-4">
              {[
                { to: '/', label: 'Home' },
                { to: '/technologies', label: 'Technologies' },
                { to: '/editor', label: 'Editor' },
                { to: '/Features', label: 'Features' },
                { to: '/help', label: 'Help' }
              ].map((item, index) => (
                <Link 
                  key={item.to}
                  to={item.to} 
                  className="block text-gray-700 hover:text-purple-600 transition-colors duration-300 py-3 px-4 rounded-lg hover:bg-purple-50 font-medium transform hover:translate-x-2"
                  onClick={() => setMobileMenuOpen(false)}
                  style={{ animationDelay: `${index * 50}ms` }}
                >
                  {item.label}
                </Link>
              ))}
              
              {isAuthenticated ? (
                <>
                  <Link 
                    to="/profile" 
                    className="block text-gray-700 hover:text-purple-600 transition-colors duration-300 py-3 px-4 rounded-lg hover:bg-purple-50 font-medium transform hover:translate-x-2"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    Profile
                  </Link>
                  {user?.email === 'admin@snipx.com' && (
                    <Link 
                      to="/admin" 
                      className="block text-gray-700 hover:text-purple-600 transition-colors duration-300 py-3 px-4 rounded-lg hover:bg-purple-50 font-medium transform hover:translate-x-2"
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      Admin
                    </Link>
                  )}
                  <div className="pt-4 border-t border-gray-200">
                    <div className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-purple-50 to-pink-50 rounded-lg mb-4">
                      <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                      <span className="text-gray-700 font-medium">
                        Welcome, {user?.firstName || 'User'}
                      </span>
                    </div>
                    <button
                      onClick={() => {
                        logout();
                        setMobileMenuOpen(false);
                      }}
                      className="w-full bg-gradient-to-r from-gray-600 to-gray-700 text-white py-3 px-4 rounded-lg hover:from-gray-700 hover:to-gray-800 transition-all duration-300 font-medium"
                    >
                      Logout
                    </button>
                  </div>
                </>
              ) : (
                <div className="pt-4 border-t border-gray-200 space-y-3">
                  <Link 
                    to="/login"
                    className="block w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white py-3 px-4 rounded-lg hover:from-purple-700 hover:to-pink-700 transition-all duration-300 text-center font-medium"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    Get Started
                  </Link>
                  <Link 
                    to="/admin/login"
                    className="block w-full border-2 border-purple-600 text-purple-600 py-3 px-4 rounded-lg hover:bg-purple-50 transition-all duration-300 text-center font-medium"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    Admin Login
                  </Link>
                </div>
              )}
            </nav>
          </div>
        </div>
      </header>

      {/* Scroll to Top Button */}
      {showScrollTop && (
        <button
          onClick={scrollToTop}
          className="fixed bottom-8 right-8 z-50 bg-gradient-to-r from-purple-600 to-pink-600 text-white p-3 rounded-full shadow-lg hover:shadow-xl transform hover:-translate-y-1 transition-all duration-300 group"
        >
          <ArrowUp size={20} className="group-hover:scale-110 transition-transform duration-300" />
          <div className="absolute inset-0 bg-gradient-to-r from-purple-600 to-pink-600 rounded-full blur-lg opacity-0 group-hover:opacity-50 transition-opacity duration-300" />
        </button>
      )}
    </>
  );
};

export default Navbar;