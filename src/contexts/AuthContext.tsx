import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { ApiService } from '../services/api';

interface User {
  email: string;
  firstName?: string;
  lastName?: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  loginAsDemo: () => Promise<void>;
  register: (data: {
    email: string;
    password: string;
    firstName: string;
    lastName: string;
  }) => Promise<void>;
  logout: () => void;
  setUser: (user: User | null) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const token = ApiService.getToken();
    if (token && token !== 'demo-token-123456') {
      // Fetch actual user data from backend
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
        })
        .catch(() => {
          // Token invalid, clear it
          ApiService.clearToken();
          setUser(null);
        });
    } else if (token === 'demo-token-123456') {
      // Demo user
      setUser({ email: 'demo@snipx.com', firstName: 'Demo', lastName: 'User' });
    }
  }, []);

  const login = async (email: string, password: string) => {
    try {
      const response = await ApiService.login(email, password);
      setUser(response.user);
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  };

  const loginAsDemo = async () => {
    try {
      // Create a local demo session
      ApiService.setToken('demo-token-123456');
      setUser({ 
        email: 'demo@snipx.com', 
        firstName: 'Demo', 
        lastName: 'User' 
      });
    } catch (error) {
      console.error('Demo login failed:', error);
      throw error;
    }
  };

  const register = async (data: {
    email: string;
    password: string;
    firstName: string;
    lastName: string;
  }) => {
    await ApiService.register(data);
  };

  const logout = () => {
    ApiService.clearToken();
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        login,
        loginAsDemo,
        register,
        logout,
        setUser
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}