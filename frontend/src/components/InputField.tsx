import React, { useState } from 'react';
import { UseFormRegisterReturn } from 'react-hook-form';
import { Eye, EyeOff } from 'lucide-react';

interface InputFieldProps {
  id: string;
  label: string;
  type?: string;
  placeholder?: string;
  icon?: React.ReactNode;
  error?: string;
  registration?: UseFormRegisterReturn;
  disabled?: boolean;
  isPassword?: boolean;
}

export const InputField: React.FC<InputFieldProps> = ({
  id,
  label,
  type = 'text',
  placeholder,
  icon,
  error,
  registration,
  disabled = false,
  isPassword = false,
}) => {
  const [showPassword, setShowPassword] = useState(false);

  const inputType = isPassword ? (showPassword ? 'text' : 'password') : type;

  return (
    <div className="flex flex-col gap-1.5 w-full mb-4">
      <label htmlFor={id} className="text-xs font-semibold uppercase tracking-wider text-[#0F2A5C]">
        {label}
      </label>

      <div className="relative flex items-center">
        {/* Leading icon in muted blue-grey */}
        {icon && (
          <div className="absolute left-3.5 flex items-center pointer-events-none text-[#7A8699]">
            {icon}
          </div>
        )}

        {/* 56px high input with 8px radius */}
        <input
          id={id}
          type={inputType}
          placeholder={placeholder}
          disabled={disabled}
          {...registration}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${id}-error` : undefined}
          className={`w-full h-14 bg-white rounded-lg border text-[#0F2A5C] text-[15px] font-normal transition-all duration-200 placeholder:text-[#7A8699] disabled:bg-[#F1F5F9] disabled:cursor-not-allowed ${
            icon ? 'pl-11' : 'pl-4'
          } ${isPassword ? 'pr-12' : 'pr-4'} ${
            error
              ? 'border-[#C62828] focus:border-[#C62828] focus:ring-2 focus:ring-[#C62828]/25'
              : 'border-[#D5DBE5] focus:border-[#F58220] focus:ring-2 focus:ring-[#F58220]/25'
          } outline-none`}
        />

        {/* Trailing show/hide eye toggle for password */}
        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            tabIndex={0}
            className="absolute right-3.5 p-1 text-[#7A8699] hover:text-[#0F2A5C] transition-colors focus:outline-none focus:ring-2 focus:ring-[#F58220] rounded"
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        )}
      </div>

      {/* Inline accessible error message */}
      {error && (
        <span
          id={`${id}-error`}
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

