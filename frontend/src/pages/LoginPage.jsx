import React, { useState, useEffect } from 'react';
import { Sparkles, Mail, Lock, LogIn, KeyRound, CheckCircle2, ShieldCheck, AlertCircle, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationContext';
import Button from '../components/common/Button';
import Modal from '../components/common/Modal';
import api from '../services/api';
import opsnovaLogo from '../assets/opsnova_logo.jpeg';

const LoginPage = ({ onSwitchToRegister }) => {
  const { login, authNotification, clearAuthNotification } = useAuth();
  const { addToast } = useNotifications();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  // Forgot Password state
  const [forgotModalOpen, setForgotModalOpen] = useState(false);
  const [resetEmail, setResetEmail] = useState('');
  const [resetPassword, setResetPassword] = useState('');
  const [resetConfirmPassword, setResetConfirmPassword] = useState('');
  const [showResetPassword, setShowResetPassword] = useState(false);
  const [showResetConfirmPassword, setShowResetConfirmPassword] = useState(false);
  const [resetLoading, setResetLoading] = useState(false);
  const [resetError, setResetError] = useState('');
  const [resetSuccess, setResetSuccess] = useState(false);

  useEffect(() => {
    if (authNotification) {
      addToast(authNotification.type || 'info', authNotification.title, authNotification.message);
      clearAuthNotification();
    }
  }, [authNotification, addToast, clearAuthNotification]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password) {
      addToast('warning', 'Missing Fields', 'Please enter both email and password.');
      return;
    }
    setLoading(true);
    try {
      await login(email, password);
      addToast('success', 'Welcome Back', `Signed in as ${email.trim()}.`);
    } catch (err) {
      console.error('Login submit error:', err);
      const msg = err.response?.data?.detail || err.message || 'Invalid email or password. Please check your credentials.';
      addToast('error', 'Login Failed', msg);
    } finally {
      setLoading(false);
    }
  };

  const openForgotPassword = () => {
    setResetEmail(email.trim());
    setResetPassword('');
    setResetConfirmPassword('');
    setShowResetPassword(false);
    setShowResetConfirmPassword(false);
    setResetError('');
    setResetSuccess(false);
    setForgotModalOpen(true);
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setResetError('');

    if (!resetEmail.trim()) {
      setResetError('Please enter your account email address.');
      return;
    }

    if (!resetPassword) {
      setResetError('Please enter a new password.');
      return;
    }

    if (resetPassword.length < 4) {
      setResetError('Password must be at least 4 characters long.');
      return;
    }

    if (resetPassword !== resetConfirmPassword) {
      setResetError('Passwords do not match. Please re-type to confirm.');
      return;
    }

    setResetLoading(true);
    try {
      const res = await api.post('/auth/forgot-password', {
        email: resetEmail.trim(),
        new_password: resetPassword
      });

      setResetSuccess(true);
      setEmail(resetEmail.trim());
      setPassword(resetPassword);
      addToast('success', 'Password Reset', res.data?.message || 'Password successfully updated!');
    } catch (err) {
      console.error('Forgot password error:', err);
      const msg = err.response?.data?.detail || err.message || 'Failed to reset password. Please verify your email.';
      setResetError(msg);
      addToast('error', 'Reset Failed', msg);
    } finally {
      setResetLoading(false);
    }
  };

  const handleFinishReset = () => {
    setForgotModalOpen(false);
    setResetSuccess(false);
    setResetPassword('');
    setResetConfirmPassword('');
  };

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#09090b] flex items-center justify-center p-4 relative">
      {/* Subtle background glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-indigo-500/10 dark:bg-indigo-600/10 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md bg-white dark:bg-[#141417] rounded-3xl p-8 border border-slate-200 dark:border-[#26262c] shadow-xl dark:shadow-2xl relative z-10 space-y-6">
        {/* Logo and title */}
        <div className="text-center space-y-2.5">
          <div className="inline-block relative">
            <img
              src={opsnovaLogo}
              alt="OpsNova AI Logo"
              className="w-20 h-20 rounded-2xl object-contain mx-auto shadow-lg border border-slate-200 dark:border-[#2e2e38] transition-transform hover:scale-105"
            />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
              Welcome to OpsNova AI
            </h1>
            <p className="text-xs font-semibold text-indigo-600 dark:text-indigo-400 tracking-wider uppercase mt-1">
              AI BUSINESS OPERATIONS AGENT
            </p>
            <p className="text-[10px] text-slate-400 dark:text-slate-500 font-medium tracking-widest uppercase mt-0.5">
              AUTOMATE • ANALYZE • ACCELERATE
            </p>
          </div>
        </div>

        {/* Email & Password Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Email Address</label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@yourcompany.com"
                required
                className="w-full bg-slate-50 dark:bg-[#18181d] border border-slate-300 dark:border-[#2e2e36] rounded-xl pl-10 pr-4 py-2.5 text-xs text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:bg-white dark:focus:bg-[#18181d] transition-colors"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300">Password</label>
              <button
                type="button"
                onClick={openForgotPassword}
                className="text-xs text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 font-medium cursor-pointer transition-colors"
              >
                Forgot password?
              </button>
            </div>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="w-full bg-slate-50 dark:bg-[#18181d] border border-slate-300 dark:border-[#2e2e36] rounded-xl pl-10 pr-10 py-2.5 text-xs text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:bg-white dark:focus:bg-[#18181d] transition-colors"
              />
              <button
                type="button"
                onClick={() => setShowPassword((prev) => !prev)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors p-0.5 focus:outline-none cursor-pointer"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                title={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>

          <Button
            type="submit"
            variant="primary"
            size="md"
            loading={loading}
            icon={LogIn}
            className="w-full text-xs font-bold py-2.5 cursor-pointer shadow-md shadow-indigo-600/20"
          >
            Sign In to Dashboard
          </Button>
        </form>

        <div className="text-center text-xs text-slate-500 dark:text-slate-400 pt-2 border-t border-slate-200 dark:border-[#26262c]">
          Don't have an account?{' '}
          <button
            type="button"
            onClick={onSwitchToRegister}
            className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-700 dark:hover:text-indigo-300 font-semibold cursor-pointer"
          >
            Register Business
          </button>
        </div>
      </div>

      {/* Forgot / Reset Password Modal */}
      <Modal
        isOpen={forgotModalOpen}
        onClose={() => setForgotModalOpen(false)}
        title="Reset Account Password"
        maxWidth="max-w-md"
      >
        {!resetSuccess ? (
          <form onSubmit={handleResetPassword} className="space-y-4 text-xs">
            <div className="flex items-center gap-3 p-3 rounded-xl bg-indigo-50 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-500/20">
              <div className="p-2 rounded-lg bg-indigo-100 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400">
                <KeyRound className="w-5 h-5" />
              </div>
              <p className="text-xs text-slate-700 dark:text-slate-300">
                Enter your registered business email and choose a new password to recover access.
              </p>
            </div>

            {resetError && (
              <div className="flex items-start gap-2.5 p-3 rounded-xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-500/30 text-rose-700 dark:text-rose-300 text-xs">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{resetError}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Email Address</label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type="email"
                  value={resetEmail}
                  onChange={(e) => setResetEmail(e.target.value)}
                  placeholder="you@yourcompany.com"
                  required
                  className="w-full bg-slate-50 dark:bg-[#18181d] border border-slate-300 dark:border-[#2e2e36] rounded-xl pl-10 pr-4 py-2.5 text-xs text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">New Password</label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type={showResetPassword ? 'text' : 'password'}
                  value={resetPassword}
                  onChange={(e) => setResetPassword(e.target.value)}
                  placeholder="Min. 4 characters"
                  required
                  className="w-full bg-slate-50 dark:bg-[#18181d] border border-slate-300 dark:border-[#2e2e36] rounded-xl pl-10 pr-10 py-2.5 text-xs text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
                <button
                  type="button"
                  onClick={() => setShowResetPassword((prev) => !prev)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors p-0.5 focus:outline-none cursor-pointer"
                  aria-label={showResetPassword ? 'Hide password' : 'Show password'}
                  title={showResetPassword ? 'Hide password' : 'Show password'}
                >
                  {showResetPassword ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Confirm New Password</label>
              <div className="relative">
                <ShieldCheck className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type={showResetConfirmPassword ? 'text' : 'password'}
                  value={resetConfirmPassword}
                  onChange={(e) => setResetConfirmPassword(e.target.value)}
                  placeholder="Re-type new password"
                  required
                  className="w-full bg-slate-50 dark:bg-[#18181d] border border-slate-300 dark:border-[#2e2e36] rounded-xl pl-10 pr-10 py-2.5 text-xs text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
                <button
                  type="button"
                  onClick={() => setShowResetConfirmPassword((prev) => !prev)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors p-0.5 focus:outline-none cursor-pointer"
                  aria-label={showResetConfirmPassword ? 'Hide password' : 'Show password'}
                  title={showResetConfirmPassword ? 'Hide password' : 'Show password'}
                >
                  {showResetConfirmPassword ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            <div className="flex gap-3 pt-2">
              <Button
                type="button"
                variant="ghost"
                size="md"
                onClick={() => setForgotModalOpen(false)}
                className="flex-1 text-xs"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                size="md"
                loading={resetLoading}
                icon={KeyRound}
                className="flex-1 text-xs font-bold cursor-pointer"
              >
                Reset Password
              </Button>
            </div>
          </form>
        ) : (
          <div className="space-y-4 text-center py-2 text-xs">
            <div className="inline-flex p-3.5 rounded-full bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20">
              <CheckCircle2 className="w-8 h-8 animate-in zoom-in-75 duration-200" />
            </div>
            <div>
              <h4 className="text-base font-bold text-slate-900 dark:text-white">Password Reset Successfully</h4>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-xs mx-auto">
                Your credentials have been updated for <span className="text-indigo-600 dark:text-indigo-300 font-semibold">{resetEmail}</span>. Your login fields are pre-filled.
              </p>
            </div>
            <Button
              type="button"
              variant="primary"
              size="md"
              onClick={handleFinishReset}
              className="w-full text-xs font-bold py-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 cursor-pointer shadow-lg shadow-indigo-600/30"
            >
              Sign In Now
            </Button>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default LoginPage;
