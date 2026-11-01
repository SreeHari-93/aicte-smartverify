import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';

interface DrawerProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  width?: string;
}

export const Drawer: React.FC<DrawerProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  width = 'max-w-xl',
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    } else {
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.body.style.overflow = 'hidden';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return createPortal(
    <div
      className="fixed inset-x-0 bottom-0 top-24 z-[1000] flex justify-end bg-black/35 backdrop-blur-none animate-fade-in"
      role="dialog"
      aria-modal="true"
    >
      {/* Clicking backdrop closes the drawer */}
      <div className="fixed inset-x-0 bottom-0 top-24" onClick={onClose} aria-hidden="true" />

      {/* Drawer Dialog: starts below top bar */}
      <div
        className={`relative z-10 w-full ${width} bg-white shadow-2xl flex flex-col border-l border-slate-200 animate-slide-left overflow-hidden h-full`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Sticky Fixed Header */}
        <div className="shrink-0 sticky top-0 z-20 px-6 sm:px-8 py-4 sm:py-5 border-b border-slate-100 flex items-center justify-between bg-white">
          <div className="min-w-0 pr-4">
            <h3 className="text-lg sm:text-xl font-bold text-[#0B3C9D] tracking-tight truncate">{title}</h3>
            {subtitle && <p className="text-xs text-slate-500 mt-0.5 truncate">{subtitle}</p>}
          </div>
          <button
            onClick={onClose}
            aria-label="Close drawer"
            className="shrink-0 p-2 text-slate-600 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer relative z-30"
          >
            <X size={20} />
          </button>
        </div>

        {/* Scrollable Middle Body */}
        <div className="flex-1 min-h-0 overflow-y-auto px-6 sm:px-8 py-5 sm:py-6 modal-scroll">{children}</div>

        {/* Sticky Fixed Footer */}
        <div className="shrink-0 px-6 sm:px-8 py-3 bg-slate-50 border-t border-slate-100 flex items-center justify-between">
          <span className="text-xs text-slate-600 font-medium">AICTE Regulatory Portal</span>
          <button
            onClick={onClose}
            className="px-3.5 py-1.5 bg-slate-200 hover:bg-slate-300 text-slate-800 text-xs font-semibold rounded-lg transition-colors cursor-pointer"
          >
            Close
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
};

