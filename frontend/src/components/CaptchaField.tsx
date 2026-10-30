import React from 'react';
import { UseFormRegisterReturn } from 'react-hook-form';
import { Shield, RotateCw } from 'lucide-react';
import { CaptchaData } from '../types/auth';

interface CaptchaFieldProps {
  captchaData: CaptchaData | null;
  onRefresh: () => void;
  isRefreshing: boolean;
  registration?: UseFormRegisterReturn;
  error?: string;
  disabled?: boolean;
}

export const CaptchaField: React.FC<CaptchaFieldProps> = ({
  captchaData,
  onRefresh,
  isRefreshing,
  registration,
  error,
  disabled = false,
}) => {
  return (
    <div className="flex flex-col gap-1.5 w-full mb-6">
      <label htmlFor="captcha_text" className="text-xs font-semibold uppercase tracking-wider text-[#0F2A5C]">
        Security Verification
      </label>

      {/* Captcha Display & Refresh */}
      <div className="flex items-center gap-3 mb-2">
        <div className="relative flex-1 h-14 bg-[#F1F4F9] rounded-lg border border-[#D5DBE5] overflow-hidden flex items-center justify-center select-none shadow-inner">
          {captchaData?.image_base64 ? (
            <img
              src={captchaData.image_base64}
              alt="Security Captcha Challenge"
              className="w-full h-full object-cover"
            />
          ) : (
            <span className="text-xs text-[#7A8699] animate-pulse">Loading challenge...</span>
          )}
        </div>

        <button
          type="button"
          onClick={onRefresh}
          disabled={disabled || isRefreshing}
          title="Get a new security code"
          aria-label="Refresh captcha challenge"
          className="h-14 w-14 flex items-center justify-center rounded-lg border border-[#D5DBE5] bg-white text-[#0B3C9D] hover:bg-[#F8FAFC] hover:border-[#0B3C9D] transition-colors focus:outline-none focus:ring-2 focus:ring-[#F58220] disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
        >
          <RotateCw size={20} className={`${isRefreshing ? 'animate-spin text-[#F58220]' : ''}`} />
        </button>
      </div>

      {/* Captcha input field */}
      <div className="relative flex items-center">
        <div className="absolute left-3.5 flex items-center pointer-events-none text-[#7A8699]">
          <Shield size={18} />
        </div>
        <input
          id="captcha_text"
          type="text"
          placeholder="Enter the code shown above"
          autoComplete="off"
          disabled={disabled}
          maxLength={8}
          {...registration}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? 'captcha-error' : undefined}
          className={`w-full h-14 bg-white rounded-lg border pl-11 pr-4 text-[#0F2A5C] text-[15px] font-medium tracking-wider uppercase placeholder:normal-case placeholder:tracking-normal placeholder:text-[#7A8699] transition-all duration-200 disabled:bg-[#F1F5F9] disabled:cursor-not-allowed ${
            error
              ? 'border-[#C62828] focus:border-[#C62828] focus:ring-2 focus:ring-[#C62828]/25'
              : 'border-[#D5DBE5] focus:border-[#F58220] focus:ring-2 focus:ring-[#F58220]/25'
          } outline-none`}
        />
      </div>

      {error && (
        <span
          id="captcha-error"
          role="alert"
          aria-live="polite"
          className="text-xs font-medium text-[#C62828] mt-0.5 flex items-center gap-1"
        >
          {error}
        </span>
      )}
    </div>
  );
};

