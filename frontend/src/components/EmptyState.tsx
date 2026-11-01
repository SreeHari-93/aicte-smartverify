import React from 'react';

interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  actionText?: string;
  onAction?: () => void;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  actionText,
  onAction,
}) => {
  return (
    <div className="py-12 px-4 text-center">
      <p className="text-sm font-medium text-slate-600">{title}</p>
      {description && <p className="text-xs text-slate-600 mt-1">{description}</p>}
      {actionText && onAction && (
        <button
          onClick={onAction}
          className="mt-3 px-3.5 py-1.5 bg-[#0B3C9D] hover:bg-[#0F2A5C] text-white text-xs font-medium rounded-md transition-colors"
        >
          {actionText}
        </button>
      )}
    </div>
  );
};

