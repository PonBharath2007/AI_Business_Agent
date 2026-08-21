import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../services/api';
import { useAuth } from './AuthContext';

const BusinessContext = createContext(null);

const DEFAULT_BUSINESS = {
  name: 'My Business',
  category: 'Small Business Services',
  currency: 'USD',
  timezone: 'America/New_York',
  payment_terms: 'Standard 30-day payment terms',
  email: ''
};

export const BusinessProvider = ({ children }) => {
  const { user, token } = useAuth();
  const [business, setBusiness] = useState(DEFAULT_BUSINESS);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);

  const fetchProfile = useCallback(async () => {
    if (!token && !user) {
      setBusiness(DEFAULT_BUSINESS);
      return;
    }
    try {
      const res = await api.get('/settings/profile');
      if (res.data) setBusiness(res.data);
    } catch (err) {
      console.warn('Could not fetch profile:', err);
    }
  }, [token, user]);

  const fetchSummary = useCallback(async () => {
    if (!token && !user) {
      setStats(null);
      return;
    }
    try {
      const res = await api.get('/dashboard/summary');
      if (res.data) setStats(res.data);
    } catch (err) {
      console.warn('Could not fetch summary:', err);
    }
  }, [token, user]);

  useEffect(() => {
    if (token && user) {
      fetchProfile();
      fetchSummary();
    } else {
      setBusiness(DEFAULT_BUSINESS);
      setStats(null);
    }
  }, [token, user, fetchProfile, fetchSummary]);

  const updateProfile = async (data) => {
    setLoading(true);
    try {
      const res = await api.put('/settings/profile', data);
      setBusiness(res.data);
      return res.data;
    } finally {
      setLoading(false);
    }
  };

  const resetDemoData = async () => {
    setLoading(true);
    try {
      const res = await api.post('/settings/reset-demo');
      await fetchProfile();
      await fetchSummary();
      return res.data;
    } finally {
      setLoading(false);
    }
  };

  const formatMoney = (amount) => {
    const sym = business.currency === 'INR' || business.currency === '₹' ? '₹' : (business.currency === 'EUR' ? '€' : (business.currency === 'GBP' ? '£' : '$'));
    const num = typeof amount === 'number' ? amount : parseFloat(amount || 0);
    return `${sym}${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  };

  return (
    <BusinessContext.Provider value={{
      business,
      loading,
      stats,
      fetchProfile,
      fetchSummary,
      updateProfile,
      resetDemoData,
      formatMoney
    }}>
      {children}
    </BusinessContext.Provider>
  );
};

export const useBusiness = () => useContext(BusinessContext);
