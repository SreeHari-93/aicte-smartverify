import React, { useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
  maxWidth?: string;
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  footer,
  maxWidth = 'max-w-[840px]',
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
      className="fixed inset-0 z-[1000] flex justify-center items-start overflow-hidden px-4 pb-6 animate-fade-in modal-overlay-wrapper"
      style={{
        paddingTop: 'calc(var(--topbar-height, 96px) + 16px)',
        paddingBottom: '24px',
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      {/* Dim backdrop: clicking closes the modal */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-xs transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Modal Card: constrained height, strictly below top bar */}
      <div
        className={`relative z-10 w-[92vw] ${maxWidth} bg-white rounded-2xl shadow-2xl border border-slate-200/90 overflow-hidden flex flex-col admin-modal-card`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Sticky Fixed Header */}
        <div className="shrink-0 sticky top-0 z-20 px-6 sm:px-8 py-4 sm:py-5 border-b border-slate-100 flex items-center justify-between bg-white modal-header-padding">
          <div className="min-w-0 pr-4">
            <h3 id="modal-title" className="text-lg sm:text-xl font-bold text-[#0B3C9D] tracking-tight truncate">
              {title}
            </h3>
            {subtitle && <p className="text-xs text-slate-500 mt-0.5 truncate">{subtitle}</p>}
          </div>
          <button
            onClick={onClose}
            aria-label="Close dialog"
            className="shrink-0 p-2 text-slate-600 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors cursor-pointer relative z-30"
          >
            <X size={20} />
          </button>
        </div>

        {/* Scrollable Middle Body */}
        <div className="p-6 sm:p-8 modal-scroll flex-1 min-h-0 overflow-y-auto modal-body-padding">
          {children}
        </div>

        {/* Fixed Bottom Footer */}
        {footer && (
          <div className="shrink-0 sticky bottom-0 z-20 px-6 sm:px-8 py-3.5 sm:py-4 bg-slate-50 border-t border-slate-100 flex items-center justify-end gap-3 modal-footer-padding">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body
  );
};


