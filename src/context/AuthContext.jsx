import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('token') || '');

  const fetchCurrentUser = useCallback(async () => {
    const storedToken = localStorage.getItem('token');
    if (!storedToken) {
      setUser(null);
      setLoading(false);
      return;
    }

    try {
      const res = await api.get('/auth/me');
      if (res.data && res.data.id) {
        setUser(res.data);
      } else {
        localStorage.removeItem('token');
        setToken('');
        setUser(null);
      }
    } catch (err) {
      console.warn('Session verification failed:', err.response?.data?.detail || err.message);
      localStorage.removeItem('token');
      setToken('');
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCurrentUser();
  }, [fetchCurrentUser, token]);

  const login = async (email, password) => {
    if (!email || !password) {
      throw new Error('Please provide both email and password.');
    }

    const res = await api.post('/auth/login', {
      email: email.trim().toLowerCase(),
      password
    });

    const authToken = res.data.access_token;
    const authUser = res.data.user;

    localStorage.setItem('token', authToken);
    setToken(authToken);
    setUser(authUser);
    return res.data;
  };

  const register = async (name, email, password, business_name, currency) => {
    if (!email || !password || !name) {
      throw new Error('Please fill in all required fields.');
    }

    const res = await api.post('/auth/register', {
      name: name.trim(),
      email: email.trim().toLowerCase(),
      password,
      business_name: business_name ? business_name.trim() : 'My Business',
      currency: currency || 'USD'
    });

    const authToken = res.data.access_token;
    const authUser = res.data.user;

    localStorage.setItem('token', authToken);
    setToken(authToken);
    setUser(authUser);
    return res.data;
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken('');
    setUser(null);
  };

  const quickDemoLogin = async () => {
    return await login('admin@summitdigital.com', 'admin123');
  };

  return (
    <AuthContext.Provider value={{
      user,
      token,
      loading,
      login,
      register,
      logout,
      quickDemoLogin,
      refreshUser: fetchCurrentUser
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
