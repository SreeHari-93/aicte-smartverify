import React from 'react';
import { FolderOpen } from 'lucide-react';

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  actionText?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  icon,
  actionText,
  onAction,
}) => {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 text-center select-none">
      <div className="w-16 h-16 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center mb-4">
        {icon || <FolderOpen size={30} />}
      </div>
      <h4 className="text-base font-bold text-[#0F2A5C]">{title}</h4>
      <p className="text-xs text-[#7A8699] max-w-sm mt-1">{description}</p>
      {actionText && onAction && (
        <button
          onClick={onAction}
          className="mt-4 px-4 py-2 bg-[#F58220] hover:bg-[#E06F0F] text-white text-xs font-semibold rounded-[6px] transition-colors"
        >
          {actionText}
        </button>
      )}
    </div>
  );
};

