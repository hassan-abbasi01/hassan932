import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { ApiService } from '../services/api';
import toast from 'react-hot-toast';

const AuthCallback = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { setUser } = useAuth();

  useEffect(() => {
    const token = searchParams.get('token');
    if (token) {
      ApiService.setToken(token);
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001/api';
      fetch(`${API_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      })
        .then(res => {
          if (!res.ok) throw new Error('Failed to fetch user');
          return res.json();
        })
        .then(userData => {
          setUser({
            email: userData.email,
            firstName: userData.first_name || userData.firstName,
            lastName: userData.last_name || userData.lastName
          });
          toast.success('Login successful!');
          navigate('/features');
        })
        .catch(() => {
          toast.error('Failed to fetch user info');
          navigate('/login');
        });
    } else {
      toast.error('Authentication failed');
      navigate('/login');
    }
  }, [searchParams, navigate, setUser]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600 mx-auto"></div>
        <p className="mt-4 text-gray-600">Completing authentication...</p>
      </div>
    </div>
  );
};

export default AuthCallback;