import React, { useState } from 'react';
import {
  X,
  Stethoscope,
  Lock,
  Mail,
  User,
  Building,
  Award,
  Phone,
  ShieldCheck,
  Sparkles,
  ArrowRight
} from 'lucide-react';
import { api } from '../services/api';

export default function AuthModal({ isOpen, onClose, onAuthSuccess }) {
  if (!isOpen) return null;

  const [mode, setMode] = useState('login'); // 'login' | 'signup' | 'otp'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Login state
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  // Signup state (14 profile fields)
  const [signupForm, setSignupForm] = useState({
    email: '',
    password: '',
    full_name: '',
    registration_number: '',
    specialization: 'Orthopedic Trauma Surgery',
    qualification: 'MBBS, MS (Orthopedics)',
    hospital: 'Apex Trauma & Emergency Center',
    department: 'Orthopedics & Traumatology',
    experience: '8 Years',
    phone: '+91 98765 43210',
    gender: 'Male',
    city: 'New Delhi',
    state: 'Delhi',
    country: 'India'
  });

  // OTP state
  const [otpCode, setOtpCode] = useState('');
  const [pendingEmail, setPendingEmail] = useState('');

  // Instant 1-Click Demo Login as verified doctor
  const handleQuickDemoLogin = async () => {
    setLoading(true);
    setError('');
    try {
      // First try logging in with demo credentials
      const demoEmail = 'dr.sharma@verifact.hospital';
      const demoPass = 'Verifact2026!';
      try {
        await api.login(demoEmail, demoPass);
        onAuthSuccess();
        onClose();
        return;
      } catch {
        // If demo user does not exist yet in DB, auto-register it
        await api.signup({
          email: demoEmail,
          password: demoPass,
          full_name: 'Ananya Sharma',
          registration_number: 'NMC/2018/049182',
          specialization: 'Orthopedic Trauma & Musculoskeletal Radiology',
          qualification: 'MBBS, MS (Orthopedics), DNB, MCh',
          hospital: 'National Trauma & Emergency Institute',
          department: 'Department of Orthopedic Surgery',
          experience: '12 Years',
          phone: '+91 98110 23456',
          city: 'New Delhi',
          state: 'Delhi',
          country: 'India'
        });
        await api.login(demoEmail, demoPass);
        onAuthSuccess();
        onClose();
      }
    } catch (err) {
      setError(err.message || 'Quick demo login failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await api.login(loginEmail, loginPassword);
      onAuthSuccess();
      onClose();
    } catch (err) {
      setError(err.message || 'Login failed. Check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await api.signup(signupForm);
      setPendingEmail(signupForm.email);
      // Auto login right after signup since is_verified defaults to True in the backend
      try {
        await api.login(signupForm.email, signupForm.password);
        onAuthSuccess();
        onClose();
      } catch {
        setMode('otp');
      }
    } catch (err) {
      setError(err.message || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await api.verifyOtp(pendingEmail, otpCode);
      await api.login(pendingEmail, signupForm.password);
      onAuthSuccess();
      onClose();
    } catch (err) {
      setError(err.message || 'Invalid or expired OTP code.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="relative w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden max-h-[92vh] flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/70">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-sky-500/10 border border-sky-500/20 text-sky-400">
              <Stethoscope className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Verified Clinician Portal</h3>
              <p className="text-xs text-slate-400">HL7 / MCI Certified Diagnostic Co-Pilot Access</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 1-Click Fast Track Demo Login Banner */}
        <div className="px-6 pt-4">
          <div className="p-3.5 rounded-xl bg-gradient-to-r from-sky-950/70 via-slate-900 to-sky-950/70 border border-sky-500/30 flex items-center justify-between">
            <div>
              <div className="text-xs font-bold text-sky-300 flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5" />
                <span>1-Click Evaluator Access</span>
              </div>
              <p className="text-[11px] text-slate-400">
                Log in as Dr. Ananya Sharma (NMC/2018/049182)
              </p>
            </div>
            <button
              onClick={handleQuickDemoLogin}
              disabled={loading}
              className="px-3.5 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold shadow-md transition active:scale-95 flex items-center space-x-1"
            >
              <span>Quick Login</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mx-6 mt-3 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
            {error}
          </div>
        )}

        {/* Content Form Body */}
        <div className="p-6 overflow-y-auto flex-1 text-xs">
          {mode === 'login' && (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-slate-300 font-medium mb-1">Doctor Email</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
                  <input
                    type="email"
                    required
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    placeholder="doctor@hospital.org"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-slate-200 text-xs focus:ring-2 focus:ring-sky-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Password</label>
                <div className="relative">
                  <Lock className="absolute left-3 top-2.5 w-4 h-4 text-slate-500" />
                  <input
                    type="password"
                    required
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-3 py-2 text-slate-200 text-xs focus:ring-2 focus:ring-sky-500 focus:outline-none"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs shadow-lg shadow-sky-600/30 transition disabled:opacity-50"
              >
                {loading ? 'Authenticating...' : 'Sign In to Workstation'}
              </button>

              <div className="text-center text-slate-400 pt-2">
                New physician?{' '}
                <button
                  type="button"
                  onClick={() => setMode('signup')}
                  className="text-sky-400 hover:underline font-semibold"
                >
                  Register Profile
                </button>
              </div>
            </form>
          )}

          {mode === 'signup' && (
            <form onSubmit={handleSignup} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Full Name</label>
                  <input
                    type="text"
                    required
                    value={signupForm.full_name}
                    onChange={(e) => setSignupForm({ ...signupForm, full_name: e.target.value })}
                    placeholder="Dr. Rajesh Patel"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 text-xs focus:ring-1 focus:ring-sky-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">MCI/NMC Reg No.</label>
                  <input
                    type="text"
                    required
                    value={signupForm.registration_number}
                    onChange={(e) => setSignupForm({ ...signupForm, registration_number: e.target.value })}
                    placeholder="MCI/2021/78912"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 text-xs focus:ring-1 focus:ring-sky-500 focus:outline-none font-mono"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Specialization</label>
                  <input
                    type="text"
                    required
                    value={signupForm.specialization}
                    onChange={(e) => setSignupForm({ ...signupForm, specialization: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 text-xs focus:ring-1 focus:ring-sky-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Qualification</label>
                  <input
                    type="text"
                    required
                    value={signupForm.qualification}
                    onChange={(e) => setSignupForm({ ...signupForm, qualification: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 text-xs focus:ring-1 focus:ring-sky-500 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-slate-300 font-medium mb-1">Hospital / Medical Center</label>
                <input
                  type="text"
                  required
                  value={signupForm.hospital}
                  onChange={(e) => setSignupForm({ ...signupForm, hospital: e.target.value })}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 text-xs focus:ring-1 focus:ring-sky-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Official Email</label>
                  <input
                    type="email"
                    required
                    value={signupForm.email}
                    onChange={(e) => setSignupForm({ ...signupForm, email: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 text-xs focus:ring-1 focus:ring-sky-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Password (min 8)</label>
                  <input
                    type="password"
                    required
                    minLength={8}
                    value={signupForm.password}
                    onChange={(e) => setSignupForm({ ...signupForm, password: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-slate-200 text-xs focus:ring-1 focus:ring-sky-500 focus:outline-none"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 py-2.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs shadow-lg shadow-sky-600/30 transition disabled:opacity-50"
              >
                {loading ? 'Registering...' : 'Register Verified Doctor Profile'}
              </button>

              <div className="text-center text-slate-400 pt-1">
                Already registered?{' '}
                <button
                  type="button"
                  onClick={() => setMode('login')}
                  className="text-sky-400 hover:underline font-semibold"
                >
                  Sign In
                </button>
              </div>
            </form>
          )}

          {mode === 'otp' && (
            <form onSubmit={handleVerifyOtp} className="space-y-4 text-center">
              <div className="p-3 rounded-full bg-sky-500/10 text-sky-400 w-12 h-12 mx-auto flex items-center justify-center">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <h4 className="font-bold text-slate-100 text-sm">Enter 6-Digit OTP</h4>
              <p className="text-xs text-slate-400">
                A verification code was sent to <span className="text-sky-300 font-medium">{pendingEmail}</span>
              </p>

              <input
                type="text"
                maxLength={6}
                required
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value)}
                placeholder="123456"
                className="w-48 mx-auto bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-center text-lg font-mono tracking-widest text-white focus:ring-2 focus:ring-sky-500 focus:outline-none"
              />

              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs shadow-lg transition"
              >
                {loading ? 'Verifying...' : 'Verify & Continue'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
