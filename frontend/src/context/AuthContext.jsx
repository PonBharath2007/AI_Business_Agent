import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(localStorage.getItem('token') || '');
  const [authNotification, setAuthNotification] = useState(null);

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

  // Check URL parameters for OAuth callbacks / redirects
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const tokenParam = urlParams.get('token');
    const errorParam = urlParams.get('error');
    const messageParam = urlParams.get('message');
    const providerParam = urlParams.get('provider');
    const actionParam = urlParams.get('action');

    if (tokenParam) {
      localStorage.setItem('token', tokenParam);
      setToken(tokenParam);

      // Clean query parameters from address bar
      window.history.replaceState({}, document.title, window.location.pathname);

      if (actionParam === 'linked') {
        setAuthNotification({
          type: 'info',
          title: 'Google Account Linked',
          message: 'Your Google identity was successfully linked to your account.'
        });
      } else if (actionParam === 'created') {
        setAuthNotification({
          type: 'success',
          title: 'Welcome to AI Business Agent',
          message: 'Your new business account was created with Google.'
        });
      } else {
        setAuthNotification({
          type: 'success',
          title: 'Signed in with Google',
          message: 'Successfully authenticated via Google.'
        });
      }
    } else if (errorParam) {
      window.history.replaceState({}, document.title, window.location.pathname);
      const decodedMessage = messageParam ? decodeURIComponent(messageParam) : 'Google sign-in was cancelled or failed.';
      setAuthNotification({
        type: 'warning',
        title: 'Authentication Notice',
        message: decodedMessage
      });
    }

    fetchCurrentUser();
  }, [fetchCurrentUser]);

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

  const loginWithGoogle = async (credentialOrCode) => {
    const payload = typeof credentialOrCode === 'string'
      ? { credential: credentialOrCode }
      : credentialOrCode;

    const res = await api.post('/auth/google/verify', payload);
    const authToken = res.data.access_token;
    const authUser = res.data.user;

    localStorage.setItem('token', authToken);
    setToken(authToken);
    setUser(authUser);
    return res.data;
  };

  const initiateGoogleLogin = () => {
    const apiBase = api.defaults.baseURL || '/api';
    window.location.href = `${apiBase}/auth/google/login`;
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken('');
    setUser(null);
  };

  const quickDemoLogin = async () => {
    return await login('admin@summitdigital.com', 'admin123');
  };

  const clearAuthNotification = () => setAuthNotification(null);

  return (
    <AuthContext.Provider value={{
      user,
      token,
      loading,
      login,
      register,
      loginWithGoogle,
      initiateGoogleLogin,
      logout,
      quickDemoLogin,
      authNotification,
      clearAuthNotification,
      refreshUser: fetchCurrentUser
    }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
