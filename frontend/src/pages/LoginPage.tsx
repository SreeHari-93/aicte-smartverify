import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  Building2,
  CreditCard,
  Lock,
  Mail,
  Loader2,
  AlertCircle,
  ShieldCheck,
} from 'lucide-react';

import { authApi } from '../api/auth';
import { CaptchaData, LockoutDetail } from '../types/auth';
import { useAuth } from '../context/AuthContext';
import { TricolourStrip } from '../components/TricolourStrip';
import { TabSlider, TabType } from '../components/TabSlider';
import { InputField } from '../components/InputField';
import { CaptchaField } from '../components/CaptchaField';

// Institute Form Zod Schema
const instituteSchema = z.object({
  institute_name: z.string().optional(),
  institute_id: z
    .string()
    .min(1, 'Institute ID is required')
    .min(6, 'Institute ID must be at least 6 characters')
    .max(20, 'Institute ID must not exceed 20 characters')
    .regex(/^[A-Za-z0-9_-]+$/, 'Institute ID must be alphanumeric'),
  password: z
    .string()
    .min(1, 'Password is required')
    .min(8, 'Password must be at least 8 characters'),
  captcha_text: z.string().min(1, 'Security code is required'),
});

// Admin Form Zod Schema
const adminSchema = z.object({
  identifier: z
    .string()
    .min(1, 'Official Email or Employee ID is required')
    .refine(
      (val) => val.includes('@') || val.length >= 4,
      'Please enter a valid email or employee ID'
    ),
  password: z
    .string()
    .min(1, 'Password is required')
    .min(8, 'Password must be at least 8 characters'),
  captcha_text: z.string().min(1, 'Security code is required'),
});

type InstituteFormData = z.infer<typeof instituteSchema>;
type AdminFormData = z.infer<typeof adminSchema>;

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { setUser } = useAuth();

  const [activeTab, setActiveTab] = useState<TabType>('INSTITUTE');
  const [captchaData, setCaptchaData] = useState<CaptchaData | null>(null);
  const [isCaptchaLoading, setIsCaptchaLoading] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [lockout, setLockout] = useState<LockoutDetail | null>(null);
  const [lockoutTimer, setLockoutTimer] = useState<number>(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Separate forms for Institute and Admin
  const instituteForm = useForm<InstituteFormData>({
    resolver: zodResolver(instituteSchema),
    mode: 'onTouched',
    defaultValues: {
      institute_name: '',
      institute_id: '',
      password: '',
      captcha_text: '',
    },
  });

  const adminForm = useForm<AdminFormData>({
    resolver: zodResolver(adminSchema),
    mode: 'onTouched',
    defaultValues: {
      identifier: '',
      password: '',
      captcha_text: '',
    },
  });

  // Fetch new captcha from backend
  const loadCaptcha = useCallback(async () => {
    setIsCaptchaLoading(true);
    try {
      const data = await authApi.getCaptcha();
      setCaptchaData(data);
      // Clear captcha text input on refresh
      instituteForm.setValue('captcha_text', '');
      adminForm.setValue('captcha_text', '');
    } catch {
      setGeneralError('Unable to load security verification challenge. Please check your connection.');
    } finally {
      setIsCaptchaLoading(false);
    }
  }, [instituteForm, adminForm]);

  useEffect(() => {
    loadCaptcha();
  }, [loadCaptcha]);

  // Handle Tab Switch: reset form and errors
  const handleTabChange = (tab: TabType) => {
    if (tab === activeTab) return;
    setActiveTab(tab);
    setGeneralError(null);
    setLockout(null);
    instituteForm.reset();
    adminForm.reset();
    loadCaptcha();
  };

  // Lockout countdown timer
  useEffect(() => {
    if (lockoutTimer > 0) {
      timerRef.current = setTimeout(() => {
        setLockoutTimer((prev) => prev - 1);
      }, 1000);
    } else if (lockoutTimer === 0 && lockout) {
      setLockout(null);
      setGeneralError(null);
    }
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [lockoutTimer, lockout]);

  // Handle Institute Submit
  const onInstituteSubmit = async (data: InstituteFormData) => {
    if (!captchaData) return;
    setIsSubmitting(true);
    setGeneralError(null);
    setLockout(null);

    try {
      const res = await authApi.login({
        role: 'INSTITUTE',
        institute_name: data.institute_name,
        institute_id: data.institute_id,
        password: data.password,
        captcha_id: captchaData.captcha_id,
        captcha_text: data.captcha_text,
      });

      setUser(res.user);
      navigate('/institute/dashboard');
    } catch (err: any) {
      const respData = err.response?.data;
      if (err.response?.status === 423 && respData?.detail?.locked) {
        setLockout(respData.detail);
        setLockoutTimer(respData.detail.remaining_seconds || 900);
      } else {
        const message =
          typeof respData?.detail === 'string'
            ? respData.detail
            : respData?.detail?.message || 'Login failed. Please check your credentials.';
        setGeneralError(message);
      }
      loadCaptcha();
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Admin Submit
  const onAdminSubmit = async (data: AdminFormData) => {
    if (!captchaData) return;
    setIsSubmitting(true);
    setGeneralError(null);
    setLockout(null);

    try {
      const res = await authApi.login({
        role: 'ADMIN',
        identifier: data.identifier,
        password: data.password,
        captcha_id: captchaData.captcha_id,
        captcha_text: data.captcha_text,
      });

      setUser(res.user);
      navigate('/admin/dashboard');
    } catch (err: any) {
      const respData = err.response?.data;
      if (err.response?.status === 423 && respData?.detail?.locked) {
        setLockout(respData.detail);
        setLockoutTimer(respData.detail.remaining_seconds || 900);
      } else {
        const message =
          typeof respData?.detail === 'string'
            ? respData.detail
            : respData?.detail?.message || 'Login failed. Please check your credentials.';
        setGeneralError(message);
      }
      loadCaptcha();
    } finally {
      setIsSubmitting(false);
    }
  };

  const isFormLocked = lockoutTimer > 0;

  return (
    <div className="relative min-h-screen w-full flex flex-col font-sans">
      {/* 1. Tricolour strip at top */}
      <TricolourStrip />

      {/* 2. Full-viewport background image covering the full webpage, zoomed out so the full scene is visible */}
      <div
        className="fixed inset-0 w-full h-full pointer-events-none z-0 bg-no-repeat transition-all duration-300"
        style={{
          backgroundImage: "url('/inst1.jpg')",
          backgroundSize: '100% 100%',
          backgroundPosition: 'center center',
          backgroundRepeat: 'no-repeat',
        }}
      />

      {/* 4. Main Content Area */}
      <main className="relative z-10 flex-1 flex flex-col justify-center items-end px-4 sm:px-8 md:px-12 lg:px-20 py-8 md:py-12">
        {/* The Card container: sits cleanly on the right on desktop, never overlapping top-left logo */}
        <div className="w-full max-w-[440px] mx-auto md:mx-0 md:mr-6 lg:mr-16 flex flex-col items-center">
          {/* Card: 16px radius, soft shadow, 32px padding, white background */}
          <div className="w-full bg-white/98 backdrop-blur-sm rounded-2xl shadow-card border border-[#E8EEF5] p-6 sm:p-8 animate-fade-in relative z-20 my-auto md:my-0">
            {/* Login Heading: Bold Royal Blue */}
            <h1 className="text-2xl font-bold text-[#0B3C9D] mb-6 tracking-tight">Login</h1>

            {/* Segmented Tab Slider */}
            <TabSlider activeTab={activeTab} onChange={handleTabChange} />

            {/* Lockout Notice with Live Countdown */}
            {isFormLocked && (
              <div
                role="alert"
                aria-live="assertive"
                className="mb-5 p-4 rounded-xl bg-red-50 border border-red-200 text-red-900 flex items-start gap-3"
              >
                <AlertCircle className="w-5 h-5 text-[#C62828] shrink-0 mt-0.5" />
                <div className="text-xs">
                  <p className="font-semibold text-sm text-[#C62828]">Account Temporarily Locked</p>
                  <p className="mt-1 text-slate-700">
                    Too many consecutive failed attempts. For your security, this account is locked.
                  </p>
                  <div className="mt-2 inline-flex items-center gap-1.5 font-mono text-xs bg-red-100 text-[#C62828] px-2.5 py-1 rounded-md font-semibold">
                    <span>Try again in:</span>
                    <span>
                      {Math.floor(lockoutTimer / 60)}m {lockoutTimer % 60}s
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* General Error Message */}
            {generalError && !isFormLocked && (
              <div
                role="alert"
                aria-live="polite"
                className="mb-5 p-3.5 rounded-xl bg-red-50 border border-red-200 text-[#C62828] text-xs font-medium flex items-center gap-2.5"
              >
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{generalError}</span>
              </div>
            )}

            {/* Tab 1: Institute Form */}
            {activeTab === 'INSTITUTE' && (
              <form
                id="institute-panel"
                role="tabpanel"
                aria-labelledby="tab-institute"
                onSubmit={instituteForm.handleSubmit(onInstituteSubmit)}
                noValidate
              >
                <InputField
                  id="inst_name"
                  label="Institute Name (Optional)"
                  placeholder="e.g. Delhi Institute of Technology"
                  icon={<Building2 size={18} />}
                  registration={instituteForm.register('institute_name')}
                  disabled={isSubmitting || isFormLocked}
                />

                <InputField
                  id="inst_id"
                  label="Institute ID"
                  placeholder="e.g. DEL0101"
                  icon={<CreditCard size={18} />}
                  registration={instituteForm.register('institute_id')}
                  error={instituteForm.formState.errors.institute_id?.message}
                  disabled={isSubmitting || isFormLocked}
                />

                <InputField
                  id="inst_password"
                  label="Password"
                  placeholder="Enter your account password"
                  isPassword={true}
                  icon={<Lock size={18} />}
                  registration={instituteForm.register('password')}
                  error={instituteForm.formState.errors.password?.message}
                  disabled={isSubmitting || isFormLocked}
                />

                <CaptchaField
                  captchaData={captchaData}
                  onRefresh={loadCaptcha}
                  isRefreshing={isCaptchaLoading}
                  registration={instituteForm.register('captcha_text')}
                  error={instituteForm.formState.errors.captcha_text?.message}
                  disabled={isSubmitting || isFormLocked}
                />

                {/* Full-width Solid Orange Login Button */}
                <button
                  type="submit"
                  disabled={isSubmitting || isFormLocked}
                  className="w-full h-14 bg-[#F58220] hover:bg-[#E06F0F] text-white text-[15px] font-semibold rounded-lg transition-all duration-200 flex items-center justify-center gap-2 shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#F58220] disabled:opacity-60 disabled:cursor-not-allowed select-none active:scale-[0.99]"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 size={20} className="animate-spin" />
                      <span>Authenticating...</span>
                    </>
                  ) : (
                    <span>Login</span>
                  )}
                </button>
              </form>
            )}

            {/* Tab 2: Admin Form */}
            {activeTab === 'ADMIN' && (
              <form
                id="admin-panel"
                role="tabpanel"
                aria-labelledby="tab-admin"
                onSubmit={adminForm.handleSubmit(onAdminSubmit)}
                noValidate
              >
                <InputField
                  id="admin_identifier"
                  label="Official Email / Employee ID"
                  placeholder="e.g. admin@aicte-india.org"
                  icon={<Mail size={18} />}
                  registration={adminForm.register('identifier')}
                  error={adminForm.formState.errors.identifier?.message}
                  disabled={isSubmitting || isFormLocked}
                />

                <InputField
                  id="admin_password"
                  label="Password"
                  placeholder="Enter your admin password"
                  isPassword={true}
                  icon={<Lock size={18} />}
                  registration={adminForm.register('password')}
                  error={adminForm.formState.errors.password?.message}
                  disabled={isSubmitting || isFormLocked}
                />

                <CaptchaField
                  captchaData={captchaData}
                  onRefresh={loadCaptcha}
                  isRefreshing={isCaptchaLoading}
                  registration={adminForm.register('captcha_text')}
                  error={adminForm.formState.errors.captcha_text?.message}
                  disabled={isSubmitting || isFormLocked}
                />

                {/* Full-width Solid Orange Login Button */}
                <button
                  type="submit"
                  disabled={isSubmitting || isFormLocked}
                  className="w-full h-14 bg-[#F58220] hover:bg-[#E06F0F] text-white text-[15px] font-semibold rounded-lg transition-all duration-200 flex items-center justify-center gap-2 shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#F58220] disabled:opacity-60 disabled:cursor-not-allowed select-none active:scale-[0.99]"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 size={20} className="animate-spin" />
                      <span>Authenticating...</span>
                    </>
                  ) : (
                    <span>Login</span>
                  )}
                </button>
              </form>
            )}

            {/* Divider with "OR" in the middle */}
            <div className="relative my-6 flex items-center justify-center">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-[#D5DBE5]" />
              </div>
              <div className="relative bg-white px-3 text-xs font-semibold uppercase tracking-wider text-[#7A8699]">
                OR
              </div>
            </div>

            {/* Outlined Orange "New User? Register" Button */}
            <Link
              to="/register"
              className="w-full h-14 border border-[#F58220] text-[#F58220] hover:bg-[#F58220]/5 text-[15px] font-semibold rounded-lg transition-all duration-200 flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#F58220] select-none"
            >
              New User? Register
            </Link>
          </div>

          {/* Under the card note: "Secured by SmartVerify AI" */}
          <div className="mt-4 flex items-center gap-1.5 text-xs text-slate-800 md:text-white/95 font-medium drop-shadow-sm select-none">
            <ShieldCheck size={14} className="text-[#F58220]" />
            <span>Secured by SmartVerify AI</span>
          </div>
        </div>
      </main>

      {/* 5. Footer Line */}
      <footer className="relative z-10 w-full py-3 px-4 text-center text-xs text-slate-700 md:text-white/90 drop-shadow-sm font-normal">
        © AICTE, Ministry of Education, Govt. of India
      </footer>
    </div>
  );
};
