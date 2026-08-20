import React, { useState } from 'react';
import { Sparkles, Mail, Lock, LogIn, KeyRound, CheckCircle2, ShieldCheck, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useNotifications } from '../context/NotificationContext';
import Button from '../components/common/Button';
import Modal from '../components/common/Modal';
import api from '../services/api';

const LoginPage = ({ onSwitchToRegister }) => {
  const { login, quickDemoLogin } = useAuth();
  const { addToast } = useNotifications();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [demoLoading, setDemoLoading] = useState(false);

  // Forgot Password state
  const [forgotModalOpen, setForgotModalOpen] = useState(false);
  const [resetEmail, setResetEmail] = useState('');
  const [resetPassword, setResetPassword] = useState('');
  const [resetConfirmPassword, setResetConfirmPassword] = useState('');
  const [resetLoading, setResetLoading] = useState(false);
  const [resetError, setResetError] = useState('');
  const [resetSuccess, setResetSuccess] = useState(false);

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

  const handleDemoClick = async (e) => {
    e.preventDefault();
    setDemoLoading(true);
    try {
      await quickDemoLogin();
      addToast('success', 'Demo Account Active', 'Signed in as Summit Digital Agency (Demo Account).');
    } catch (err) {
      console.error('Demo login error:', err);
      addToast('error', 'Demo Error', 'Could not start demo session. Please try again.');
    } finally {
      setDemoLoading(false);
    }
  };

  const openForgotPassword = () => {
    setResetEmail(email.trim());
    setResetPassword('');
    setResetConfirmPassword('');
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
    <div className="min-h-screen bg-[#0b0f19] flex items-center justify-center p-4">
      {/* Background glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-indigo-600/15 rounded-full blur-3xl pointer-events-none" />

      <div className="w-full max-w-md glass-panel rounded-3xl p-8 border border-slate-800 shadow-2xl relative z-10 space-y-6">
        {/* Logo and title */}
        <div className="text-center space-y-2">
          <div className="inline-flex p-3 rounded-2xl bg-gradient-to-br from-indigo-500 to-violet-600 text-white shadow-lg shadow-indigo-500/30 mb-1">
            <Sparkles className="w-6 h-6 animate-pulse" />
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">AI Business Operations Agent</h1>
          <p className="text-xs text-slate-400">An Intelligent Digital Employee for Small Businesses</p>
        </div>

        {/* 1-Click Quick Demo Login Pill */}
        <div className="p-3.5 rounded-2xl bg-indigo-950/40 border border-indigo-500/30 text-center space-y-2">
          <span className="text-[11px] text-indigo-300 font-semibold uppercase tracking-wider block">
            ⚡ Quick Demonstration Access
          </span>
          <Button
            type="button"
            onClick={handleDemoClick}
            variant="primary"
            size="sm"
            loading={demoLoading}
            className="w-full text-xs font-bold py-2.5 bg-gradient-to-r from-indigo-600 to-violet-600 cursor-pointer shadow-lg shadow-indigo-600/30"
          >
            Login with Demo Account (Summit Digital)
          </Button>
        </div>

        <div className="relative flex items-center justify-center">
          <div className="border-t border-slate-800 w-full" />
          <span className="bg-[#0f172a] px-3 text-[11px] uppercase tracking-wider text-slate-500 absolute font-semibold">
            Or sign in with your email
          </span>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Email Address</label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@yourcompany.com"
                required
                className="w-full bg-slate-900 border border-slate-700/80 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-xs font-semibold text-slate-300">Password</label>
              <button
                type="button"
                onClick={openForgotPassword}
                className="text-xs text-indigo-400 hover:text-indigo-300 font-medium cursor-pointer transition-colors"
              >
                Forgot password?
              </button>
            </div>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="w-full bg-slate-900 border border-slate-700/80 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <Button
            type="submit"
            variant="secondary"
            size="md"
            loading={loading}
            icon={LogIn}
            className="w-full text-xs font-bold py-2.5 cursor-pointer"
          >
            Sign In to Dashboard
          </Button>
        </form>

        <div className="text-center text-xs text-slate-400 pt-2 border-t border-slate-800">
          Don't have an account?{' '}
          <button
            type="button"
            onClick={onSwitchToRegister}
            className="text-indigo-400 hover:text-indigo-300 font-semibold cursor-pointer"
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
          <form onSubmit={handleResetPassword} className="space-y-4">
            <div className="flex items-center gap-3 p-3 rounded-xl bg-indigo-950/30 border border-indigo-500/20">
              <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
                <KeyRound className="w-5 h-5" />
              </div>
              <p className="text-xs text-slate-300">
                Enter your registered business email and choose a new password to recover access.
              </p>
            </div>

            {resetError && (
              <div className="flex items-start gap-2.5 p-3 rounded-xl bg-rose-950/30 border border-rose-500/30 text-rose-300 text-xs">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{resetError}</span>
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Email Address</label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type="email"
                  value={resetEmail}
                  onChange={(e) => setResetEmail(e.target.value)}
                  placeholder="you@yourcompany.com"
                  required
                  className="w-full bg-slate-900 border border-slate-700/80 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">New Password</label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type="password"
                  value={resetPassword}
                  onChange={(e) => setResetPassword(e.target.value)}
                  placeholder="Min. 4 characters"
                  required
                  className="w-full bg-slate-900 border border-slate-700/80 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Confirm New Password</label>
              <div className="relative">
                <ShieldCheck className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                <input
                  type="password"
                  value={resetConfirmPassword}
                  onChange={(e) => setResetConfirmPassword(e.target.value)}
                  placeholder="Re-type new password"
                  required
                  className="w-full bg-slate-900 border border-slate-700/80 rounded-xl pl-10 pr-4 py-2.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                />
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
                className="flex-1 text-xs font-bold bg-gradient-to-r from-indigo-600 to-violet-600 cursor-pointer shadow-lg shadow-indigo-600/30"
              >
                Reset Password
              </Button>
            </div>
          </form>
        ) : (
          <div className="space-y-4 text-center py-2">
            <div className="inline-flex p-3.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <CheckCircle2 className="w-8 h-8 animate-in zoom-in-75 duration-200" />
            </div>
            <div>
              <h4 className="text-base font-bold text-white">Password Reset Successfully</h4>
              <p className="text-xs text-slate-400 mt-1 max-w-xs mx-auto">
                Your credentials have been updated for <span className="text-indigo-300 font-semibold">{resetEmail}</span>. Your login fields are pre-filled.
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
