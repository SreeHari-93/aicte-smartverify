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
    .min(4, 'Institute ID must be at least 4 characters')
    .max(50, 'Institute ID must not exceed 50 characters')
    .regex(/^[A-Za-z0-9@._-]+$/, 'Please enter a valid Institute ID or Email'),
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
  const [failedField, setFailedField] = useState<'password' | 'captcha' | 'general' | null>(null);
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

  const { setValue: setInstituteValue } = instituteForm;
  const { setValue: setAdminValue } = adminForm;

  const captchaReqId = useRef(0);

  // Fallback SVG challenge generator for offline/loading states
  const createFallbackChallenge = () => {
    const code = '12345';
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="220" height="54" viewBox="0 0 220 54">
      <rect width="220" height="54" fill="#F8FAFC"/>
      <line x1="10" y1="20" x2="210" y2="40" stroke="#E2E8F0" stroke-width="1"/>
      <line x1="20" y1="45" x2="200" y2="10" stroke="#E2E8F0" stroke-width="1"/>
      <text x="50" y="37" font-family="Arial, sans-serif" font-size="28" font-weight="bold" fill="#0B3C9D" letter-spacing="8">${code}</text>
    </svg>`;
    return {
      captcha_id: 'dev-challenge',
      image_base64: `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`,
    };
  };

  // Fetch new captcha from backend with sequence guard to prevent out-of-order race conditions
  const loadCaptcha = useCallback(async () => {
    const currentReq = ++captchaReqId.current;
    setIsCaptchaLoading(true);
    try {
      const data = await authApi.getCaptcha();
      if (currentReq === captchaReqId.current) {
        if (data && data.image_base64) {
          setCaptchaData(data);
        } else {
          setCaptchaData(createFallbackChallenge());
        }
        setInstituteValue('captcha_text', '');
        setAdminValue('captcha_text', '');
      }
    } catch (err) {
      if (currentReq === captchaReqId.current) {
        console.warn('Captcha fetch error, fallback challenge active:', err);
        setCaptchaData(createFallbackChallenge());
        setInstituteValue('captcha_text', '');
        setAdminValue('captcha_text', '');
      }
    } finally {
      if (currentReq === captchaReqId.current) {
        setIsCaptchaLoading(false);
      }
    }
  }, [setInstituteValue, setAdminValue]);

  useEffect(() => {
    loadCaptcha();
  }, [loadCaptcha]);

  // Handle Tab Switch: reset form and errors
  const handleTabChange = (tab: TabType) => {
    if (tab === activeTab) return;
    setActiveTab(tab);
    setGeneralError(null);
    setFailedField(null);
    setLockout(null);
    instituteForm.reset();
    adminForm.reset();
    loadCaptcha();
  };

  // Clear errors when the user starts typing again
  const clearErrorsOnTyping = () => {
    if (generalError) setGeneralError(null);
    if (failedField) setFailedField(null);
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
      setFailedField(null);
    }
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [lockoutTimer, lockout]);

  // Handle Institute Submit
  const onInstituteSubmit = async (data: InstituteFormData) => {
    if (isSubmitting || isFormLocked) return;
    const activeCaptchaId = captchaData?.captcha_id || 'dev-challenge';
    setIsSubmitting(true);
    setGeneralError(null);
    setFailedField(null);
    setLockout(null);

    try {
      const res = await authApi.login({
        role: 'INSTITUTE',
        institute_name: data.institute_name,
        institute_id: data.institute_id,
        password: data.password,
        captcha_id: activeCaptchaId,
        captcha_text: data.captcha_text,
      });

      setUser(res.user);
      navigate('/institute/dashboard');
    } catch (err: any) {
      if (!err.response || (err.response.status >= 500 && err.response.status < 600)) {
        // Network or server error
        setGeneralError("Can't reach the server. Try again.");
        setFailedField('general');
        loadCaptcha();
      } else if (err.response?.status === 423 && err.response?.data?.detail?.locked) {
        setLockout(err.response.data.detail);
        setLockoutTimer(err.response.data.detail.remaining_seconds || 900);
        loadCaptcha();
      } else if (err.response?.status === 400) {
        // Wrong captcha: keep other fields, refresh captcha, focus captcha field
        const message =
          typeof err.response?.data?.detail === 'string'
            ? err.response.data.detail
            : "Captcha doesn't match";
        setGeneralError(message);
        setFailedField('captcha');
        loadCaptcha();
        setTimeout(() => {
          document.getElementById('captcha_text')?.focus();
        }, 50);
      } else if (err.response?.status === 401) {
        // Wrong password: clear password field only, keep login ID, focus password field, refresh captcha
        const message =
          typeof err.response?.data?.detail === 'string'
            ? err.response.data.detail
            : 'Incorrect login ID or password';
        setGeneralError(message);
        setFailedField('password');
        setInstituteValue('password', '');
        loadCaptcha();
        setTimeout(() => {
          document.getElementById('inst_password')?.focus();
        }, 50);
      } else if (err.response?.status === 429) {
        // Rate limiting
        const message =
          typeof err.response?.data?.detail === 'string'
            ? err.response.data.detail
            : 'Too many attempts. Try again in a few minutes.';
        setGeneralError(message);
        setFailedField('general');
        loadCaptcha();
      } else {
        const message =
          typeof err.response?.data?.detail === 'string'
            ? err.response.data.detail
            : err.response?.data?.detail?.message || 'Incorrect login ID or password';
        setGeneralError(message);
        setFailedField('general');
        loadCaptcha();
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Admin Submit
  const onAdminSubmit = async (data: AdminFormData) => {
    if (isSubmitting || isFormLocked) return;
    const activeCaptchaId = captchaData?.captcha_id || 'dev-challenge';
    setIsSubmitting(true);
    setGeneralError(null);
    setFailedField(null);
    setLockout(null);

    try {
      const res = await authApi.login({
        role: 'ADMIN',
        identifier: data.identifier,
        password: data.password,
        captcha_id: activeCaptchaId,
        captcha_text: data.captcha_text,
      });

      setUser(res.user);
      navigate('/admin');
    } catch (err: any) {
      if (!err.response || (err.response.status >= 500 && err.response.status < 600)) {
        // Network or server error
        setGeneralError("Can't reach the server. Try again.");
        setFailedField('general');
        loadCaptcha();
      } else if (err.response?.status === 423 && err.response?.data?.detail?.locked) {
        setLockout(err.response.data.detail);
        setLockoutTimer(err.response.data.detail.remaining_seconds || 900);
        loadCaptcha();
      } else if (err.response?.status === 400) {
        // Wrong captcha: keep other fields, refresh captcha, focus captcha field
        const message =
          typeof err.response?.data?.detail === 'string'
            ? err.response.data.detail
            : "Captcha doesn't match";
        setGeneralError(message);
        setFailedField('captcha');
        loadCaptcha();
        setTimeout(() => {
          document.getElementById('captcha_text')?.focus();
        }, 50);
      } else if (err.response?.status === 401) {
        // Wrong password: clear password field only, keep login ID, focus password field, refresh captcha
        const message =
          typeof err.response?.data?.detail === 'string'
            ? err.response.data.detail
            : 'Incorrect login ID or password';
        setGeneralError(message);
        setFailedField('password');
        setAdminValue('password', '');
        loadCaptcha();
        setTimeout(() => {
          document.getElementById('admin_password')?.focus();
        }, 50);
      } else if (err.response?.status === 429) {
        // Rate limiting
        const message =
          typeof err.response?.data?.detail === 'string'
            ? err.response.data.detail
            : 'Too many attempts. Try again in a few minutes.';
        setGeneralError(message);
        setFailedField('general');
        loadCaptcha();
      } else {
        const message =
          typeof err.response?.data?.detail === 'string'
            ? err.response.data.detail
            : err.response?.data?.detail?.message || 'Incorrect login ID or password';
        setGeneralError(message);
        setFailedField('general');
        loadCaptcha();
      }
    } finally {
      setIsSubmitting(false);
    }
  };



  const isFormLocked = lockoutTimer > 0;

  return (
    <div className="h-screen w-full overflow-y-auto flex flex-col font-sans relative">
      {/* 1. Tricolour strip at top */}
      <TricolourStrip />

      {/* 2. Full-viewport background image covering the full webpage */}
      <div
        className="fixed inset-0 w-full h-full pointer-events-none z-0 bg-no-repeat transition-all duration-300"
        style={{
          backgroundImage: "url('/inst1.jpg')",
          backgroundSize: '100% 100%',
          backgroundPosition: 'center center',
          backgroundRepeat: 'no-repeat',
        }}
      />

      {/* 3. Top Header Bar with AICTE Golden Gear Emblem */}
      <header className="relative z-10 w-full pt-4 px-6 md:px-12 flex justify-between items-center" role="banner">
        <div className="flex items-center bg-white/90 backdrop-blur-sm p-2 rounded-xl border border-slate-200/80 shadow-md">
          <img
            src="/AICTE Golden Gear Emblem.png"
            alt="AICTE Golden Gear Emblem"
            className="w-12 h-12 object-contain select-none"
          />
        </div>
      </header>

      {/* 4. Main Content Area */}
      <main className="relative z-10 flex-1 flex flex-col justify-center items-end px-4 sm:px-8 md:px-12 lg:px-20 py-4 md:py-6">
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

            {/* Tab 1: Institute Form */}
            {activeTab === 'INSTITUTE' && (
              <form
                id="institute-panel"
                role="tabpanel"
                aria-labelledby="tab-institute"
                onSubmit={instituteForm.handleSubmit(onInstituteSubmit)}
                onInput={clearErrorsOnTyping}
                onChange={clearErrorsOnTyping}
                noValidate
              >
                <InputField
                  id="inst_name"
                  label="Institute Name (Optional)"
                  placeholder="e.g. Sri Krishna College of Engineering and Technology"
                  icon={<Building2 size={18} />}
                  registration={instituteForm.register('institute_name')}
                  disabled={isSubmitting || isFormLocked}
                />

                <InputField
                  id="inst_id"
                  label="Institute ID"
                  placeholder="e.g. 1-SKCET2026"
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
                  isInvalid={failedField === 'password'}
                  disabled={isSubmitting || isFormLocked}
                />

                <CaptchaField
                  captchaData={captchaData}
                  onRefresh={loadCaptcha}
                  isRefreshing={isCaptchaLoading}
                  registration={instituteForm.register('captcha_text')}
                  error={instituteForm.formState.errors.captcha_text?.message}
                  isInvalid={failedField === 'captcha'}
                  disabled={isSubmitting || isFormLocked}
                />

                {/* Inline Error Message above Login button */}
                {generalError && !isFormLocked && (
                  <div
                    role="alert"
                    aria-live="assertive"
                    className="mb-4 p-3 rounded-lg bg-red-50 border border-red-300 text-red-700 text-sm font-medium flex items-center gap-2.5 animate-fade-in"
                  >
                    <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
                    <span>{generalError}</span>
                  </div>
                )}

                {/* Full-width Solid Orange Login Button */}
                <button
                  type="submit"
                  disabled={isSubmitting || isFormLocked}
                  className="w-full h-14 bg-[#F58220] hover:bg-[#E06F0F] text-white text-[15px] font-semibold rounded-lg transition-all duration-200 flex items-center justify-center gap-2 shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#F58220] disabled:opacity-60 disabled:cursor-not-allowed select-none active:scale-[0.99]"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 size={20} className="animate-spin" />
                      <span>Signing in…</span>
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
                onInput={clearErrorsOnTyping}
                onChange={clearErrorsOnTyping}
                noValidate
              >
                <InputField
                  id="admin_identifier"
                  label="Official Email / Employee ID"
                  placeholder="e.g. admin@aicte.gov.in"
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
                  isInvalid={failedField === 'password'}
                  disabled={isSubmitting || isFormLocked}
                />

                <CaptchaField
                  captchaData={captchaData}
                  onRefresh={loadCaptcha}
                  isRefreshing={isCaptchaLoading}
                  registration={adminForm.register('captcha_text')}
                  error={adminForm.formState.errors.captcha_text?.message}
                  isInvalid={failedField === 'captcha'}
                  disabled={isSubmitting || isFormLocked}
                />

                {/* Inline Error Message above Login button */}
                {generalError && !isFormLocked && (
                  <div
                    role="alert"
                    aria-live="assertive"
                    className="mb-4 p-3 rounded-lg bg-red-50 border border-red-300 text-red-700 text-sm font-medium flex items-center gap-2.5 animate-fade-in"
                  >
                    <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
                    <span>{generalError}</span>
                  </div>
                )}

                {/* Full-width Solid Orange Login Button */}
                <button
                  type="submit"
                  disabled={isSubmitting || isFormLocked}
                  className="w-full h-14 bg-[#F58220] hover:bg-[#E06F0F] text-white text-[15px] font-semibold rounded-lg transition-all duration-200 flex items-center justify-center gap-2 shadow-md hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-[#F58220] disabled:opacity-60 disabled:cursor-not-allowed select-none active:scale-[0.99]"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 size={20} className="animate-spin" />
                      <span>Signing in…</span>
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
        </div>
      </main>
    </div>
  );
};
