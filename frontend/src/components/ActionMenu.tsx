import React, { useState, useRef, useEffect } from 'react';
import { MoreHorizontal } from 'lucide-react';

export interface ActionMenuItem {
  label: string;
  onClick: () => void;
  icon?: React.ReactNode;
  disabled?: boolean;
  danger?: boolean;
}

interface ActionMenuProps {
  primaryAction?: {
    label: string;
    onClick: () => void;
    icon?: React.ReactNode;
    disabled?: boolean;
    variant?: 'primary' | 'secondary' | 'danger';
    className?: string;
  };
  menuItems?: ActionMenuItem[];
}

export const ActionMenu: React.FC<ActionMenuProps> = ({ primaryAction, menuItems = [] }) => {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const hasMenuItems = menuItems && menuItems.length > 0;

  return (
    <div ref={containerRef} className="relative inline-flex items-center justify-end gap-1.5 w-[150px] min-w-[150px] whitespace-nowrap">
      {primaryAction && (
        <button
          type="button"
          onClick={primaryAction.onClick}
          disabled={primaryAction.disabled}
          className={
            primaryAction.className ||
            (primaryAction.variant === 'primary'
              ? 'px-3 py-1.5 text-xs font-semibold rounded bg-[#0B3C9D] text-white hover:bg-[#082B70] transition-colors whitespace-nowrap shadow-2xs'
              : 'px-3 py-1.5 text-xs font-semibold rounded border border-slate-300 bg-white hover:bg-slate-50 text-slate-800 hover:border-[#0B3C9D] transition-colors whitespace-nowrap shadow-2xs')
          }
        >
          <span className="flex items-center gap-1.5">
            {primaryAction.icon}
            {primaryAction.label}
          </span>
        </button>
      )}

      {hasMenuItems && (
        <div className="relative shrink-0">
          <button
            type="button"
            onClick={() => setIsOpen(!isOpen)}
            aria-label="More actions"
            className="p-1.5 text-slate-700 hover:text-slate-900 bg-white hover:bg-slate-100 rounded border border-slate-300 transition-colors shadow-2xs"
          >
            <MoreHorizontal size={15} />
          </button>

          {isOpen && (
            <div className="absolute right-0 mt-1 w-44 bg-white rounded-lg shadow-xl border border-slate-200 py-1 z-50 text-xs animate-in fade-in zoom-in-95 duration-100 text-left">
              {menuItems.map((item, idx) => (
                <button
                  key={idx}
                  type="button"
                  disabled={item.disabled}
                  onClick={() => {
                    setIsOpen(false);
                    item.onClick();
                  }}
                  className={`w-full text-left px-3 py-2 flex items-center gap-2 transition-colors ${
                    item.danger
                      ? 'text-red-600 hover:bg-red-50 font-medium'
                      : 'text-slate-700 hover:bg-slate-50 hover:text-slate-900 font-medium'
                  } disabled:opacity-50 disabled:cursor-not-allowed`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
