import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Building2, Mail, Lock, CreditCard, ArrowLeft, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { authApi } from '../api/auth';
import { TricolourStrip } from '../components/TricolourStrip';

const registerSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z
    .string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Must contain at least 1 uppercase letter')
    .regex(/[a-z]/, 'Must contain at least 1 lowercase letter')
    .regex(/[0-9]/, 'Must contain at least 1 number')
    .regex(/[!@#$%^&*(),.?":{}|<>\-_]/, 'Must contain at least 1 special character'),
  aicte_institute_id: z
    .string()
    .min(6, 'Institute ID must be 6-20 characters')
    .max(20, 'Institute ID must be 6-20 characters'),
  institute_name: z.string().min(3, 'Institute name is required'),
  state: z.string().min(2, 'State is required'),
});

type RegisterFormData = z.infer<typeof registerSchema>;

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
  });

  const onSubmit = async (data: RegisterFormData) => {
    setIsSubmitting(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      const res = await authApi.register({
        email: data.email,
        password: data.password,
        role: 'INSTITUTE',
        aicte_institute_id: data.aicte_institute_id,
        institute_name: data.institute_name,
        state: data.state,
      });
      setSuccessMsg(res.message);
      setTimeout(() => {
        navigate('/login');
      }, 2500);
    } catch (err: any) {
      setErrorMsg(
        err.response?.data?.detail || 'Registration failed. Please check your details.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="relative min-h-screen bg-slate-50 flex flex-col justify-center items-center px-4 py-12">
      <TricolourStrip />

      <div className="w-full max-w-md bg-white rounded-2xl shadow-card border border-[#E8EEF5] p-8">
        <Link
          to="/login"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#0B3C9D] hover:underline mb-6"
        >
          <ArrowLeft size={16} />
          <span>Back to Login</span>
        </Link>

        <h1 className="text-2xl font-bold text-[#0B3C9D] mb-1">New Institute Registration</h1>
        <p className="text-xs text-[#7A8699] mb-6">
          Step 1: Create your AICTE SmartVerify AI credentials
        </p>

        {successMsg && (
          <div className="mb-5 p-3.5 rounded-xl bg-green-50 border border-green-200 text-[#2E7D32] text-xs font-medium flex items-center gap-2">
            <CheckCircle className="w-4 h-4 shrink-0" />
            <span>{successMsg} Redirecting to login...</span>
          </div>
        )}

        {errorMsg && (
          <div className="mb-5 p-3.5 rounded-xl bg-red-50 border border-red-200 text-[#C62828] text-xs font-medium flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-[#0F2A5C] block mb-1">
              AICTE Institute ID
            </label>
            <div className="relative flex items-center">
              <CreditCard size={18} className="absolute left-3.5 text-[#7A8699]" />
              <input
                {...register('aicte_institute_id')}
                placeholder="e.g. DEL0101"
                className="w-full h-14 bg-white rounded-lg border border-[#D5DBE5] pl-11 pr-4 text-sm text-[#0F2A5C] focus:border-[#F58220] focus:ring-2 focus:ring-[#F58220]/25 outline-none"
              />
            </div>
            {errors.aicte_institute_id && (
              <p className="text-xs text-[#C62828] mt-1">{errors.aicte_institute_id.message}</p>
            )}
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-[#0F2A5C] block mb-1">
              Institute Name
            </label>
            <div className="relative flex items-center">
              <Building2 size={18} className="absolute left-3.5 text-[#7A8699]" />
              <input
                {...register('institute_name')}
                placeholder="e.g. Delhi Institute of Technology"
                className="w-full h-14 bg-white rounded-lg border border-[#D5DBE5] pl-11 pr-4 text-sm text-[#0F2A5C] focus:border-[#F58220] focus:ring-2 focus:ring-[#F58220]/25 outline-none"
              />
            </div>
            {errors.institute_name && (
              <p className="text-xs text-[#C62828] mt-1">{errors.institute_name.message}</p>
            )}
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-[#0F2A5C] block mb-1">
              Official Email Address
            </label>
            <div className="relative flex items-center">
              <Mail size={18} className="absolute left-3.5 text-[#7A8699]" />
              <input
                type="email"
                {...register('email')}
                placeholder="e.g. principal@institute.edu.in"
                className="w-full h-14 bg-white rounded-lg border border-[#D5DBE5] pl-11 pr-4 text-sm text-[#0F2A5C] focus:border-[#F58220] focus:ring-2 focus:ring-[#F58220]/25 outline-none"
              />
            </div>
            {errors.email && (
              <p className="text-xs text-[#C62828] mt-1">{errors.email.message}</p>
            )}
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-[#0F2A5C] block mb-1">
              State / Region
            </label>
            <input
              {...register('state')}
              placeholder="e.g. Delhi"
              className="w-full h-14 bg-white rounded-lg border border-[#D5DBE5] px-4 text-sm text-[#0F2A5C] focus:border-[#F58220] focus:ring-2 focus:ring-[#F58220]/25 outline-none"
            />
            {errors.state && (
              <p className="text-xs text-[#C62828] mt-1">{errors.state.message}</p>
            )}
          </div>

          <div>
            <label className="text-xs font-semibold uppercase tracking-wider text-[#0F2A5C] block mb-1">
              Password
            </label>
            <div className="relative flex items-center">
              <Lock size={18} className="absolute left-3.5 text-[#7A8699]" />
              <input
                type="password"
                {...register('password')}
                placeholder="Min 8 chars, 1 upper, 1 lower, 1 digit, 1 special"
                className="w-full h-14 bg-white rounded-lg border border-[#D5DBE5] pl-11 pr-4 text-sm text-[#0F2A5C] focus:border-[#F58220] focus:ring-2 focus:ring-[#F58220]/25 outline-none"
              />
            </div>
            {errors.password && (
              <p className="text-xs text-[#C62828] mt-1">{errors.password.message}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full h-14 bg-[#F58220] hover:bg-[#E06F0F] text-white text-[15px] font-semibold rounded-lg transition-all duration-200 flex items-center justify-center gap-2 shadow-md mt-6 disabled:opacity-60"
          >
            {isSubmitting ? (
              <>
                <Loader2 size={20} className="animate-spin" />
                <span>Registering Account...</span>
              </>
            ) : (
              <span>Create Account</span>
            )}
          </button>
        </form>
      </div>

      <footer className="mt-8 text-center text-xs text-slate-500">
        © AICTE, Ministry of Education, Govt. of India
      </footer>
    </div>
  );
};

