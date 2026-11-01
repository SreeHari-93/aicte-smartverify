import React from 'react';
import { Loader2 } from 'lucide-react';

export interface ColumnDef<T> {
  key: string;
  header: React.ReactNode;
  width?: string; // e.g. "20%" or "150px"
  align?: 'left' | 'right' | 'center'; // left for text/status, right for numbers/days and actions
  sticky?: boolean; // sticky first column on wide tables
  className?: string;
  headerClassName?: string;
  render?: (item: T, index: number) => React.ReactNode;
}

export interface DataTableProps<T> {
  columns: ColumnDef<T>[];
  data: T[];
  keyExtractor: (item: T, index: number) => string | number;
  isLoading?: boolean;
  emptyMessage?: string;
  emptySubtitle?: string;
  onClearFilters?: () => void;
  isWide?: boolean; // wide table: overflow-x: auto, sticky first column
  isLong?: boolean; // long table (>12 rows): max-height: 60vh, overflow-y: auto
  className?: string;
  rowClassName?: (item: T, index: number) => string;
}

export function DataTable<T>({
  columns,
  data,
  keyExtractor,
  isLoading = false,
  emptyMessage = 'No records found.',
  emptySubtitle,
  onClearFilters,
  isWide = false,
  isLong = false,
  className = '',
  rowClassName,
}: DataTableProps<T>) {
  // Determine if vertical scrolling should be active (> 12 rows and isLong or data.length > 12)
  const shouldScrollVertically = isLong || data.length > 12;

  const containerClasses = [
    'w-full bg-white rounded-lg border border-slate-200 overflow-hidden',
    isWide ? 'table-scroll-container' : 'table-container',
    shouldScrollVertically ? 'table-scroll-long' : '',
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div className={containerClasses}>
      <table className="w-full table-fixed border-collapse text-[13px] leading-snug">
        <colgroup>
          {columns.map((col, idx) => (
            <col
              key={col.key || idx}
              style={col.width ? { width: col.width } : undefined}
            />
          ))}
        </colgroup>

        <thead className={shouldScrollVertically ? 'sticky top-0 z-20 bg-slate-50' : 'bg-slate-50'}>
          <tr className="border-b border-slate-200 text-slate-700 font-semibold h-10 min-h-[40px]">
            {columns.map((col, idx) => {
              const alignClass =
                col.align === 'right'
                  ? 'text-right'
                  : col.align === 'center'
                  ? 'text-center'
                  : 'text-left';

              const stickyClass =
                col.sticky && isWide
                  ? 'sticky left-0 z-10 bg-slate-50 shadow-[1px_0_0_0_#e2e8f0]'
                  : '';

              return (
                <th
                  key={col.key || idx}
                  className={`px-4 py-2 align-middle text-xs text-slate-700 font-semibold tracking-tight ${alignClass} ${stickyClass} ${
                    col.headerClassName || ''
                  }`}
                >
                  <div className={`truncate ${col.align === 'right' ? 'justify-end' : ''}`}>
                    {col.header}
                  </div>
                </th>
              );
            })}
          </tr>
        </thead>

        <tbody className="divide-y divide-slate-100 font-normal text-slate-800">
          {isLoading ? (
            <tr>
              <td
                colSpan={columns.length}
                className="py-12 px-4 text-center text-slate-600 align-middle"
              >
                <div className="flex flex-col items-center justify-center gap-2">
                  <Loader2 size={24} className="animate-spin text-[#0B3C9D]" />
                  <span className="text-xs font-medium">Loading data...</span>
                </div>
              </td>
            </tr>
          ) : data.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="py-12 px-4 text-center text-slate-600 align-middle"
              >
                <div className="flex flex-col items-center justify-center gap-2 max-w-sm mx-auto">
                  <p className="text-sm font-semibold text-slate-800">{emptyMessage}</p>
                  {emptySubtitle && (
                    <p className="text-xs text-slate-600">{emptySubtitle}</p>
                  )}
                  {onClearFilters && (
                    <button
                      type="button"
                      onClick={onClearFilters}
                      className="mt-2 px-3 py-1.5 text-xs font-semibold rounded-md border border-slate-300 hover:border-[#0B3C9D] bg-white text-slate-700 hover:text-[#0B3C9D] transition-colors"
                    >
                      Clear filters
                    </button>
                  )}
                </div>
              </td>
            </tr>
          ) : (
            data.map((item, rowIdx) => {
              const customClass = rowClassName ? rowClassName(item, rowIdx) : '';
              return (
                <tr
                  key={keyExtractor(item, rowIdx)}
                  className={`min-h-[52px] h-[52px] hover:bg-slate-50/70 transition-colors ${customClass}`}
                >
                  {columns.map((col, colIdx) => {
                    const alignClass =
                      col.align === 'right'
                        ? 'text-right'
                        : col.align === 'center'
                        ? 'text-center'
                        : 'text-left';

                    const stickyClass =
                      col.sticky && isWide
                        ? 'sticky left-0 z-10 bg-white shadow-[1px_0_0_0_#e2e8f0]'
                        : '';

                    const content = col.render
                      ? col.render(item, rowIdx)
                      : (item as any)[col.key];

                    return (
                      <td
                        key={col.key || colIdx}
                        className={`px-4 py-2.5 align-middle text-slate-800 ${alignClass} ${stickyClass} ${
                          col.className || ''
                        }`}
                      >
                        {content}
                      </td>
                    );
                  })}
                </tr>
              );
            })
          )}
        </tbody>
      </table>
    </div>
  );
}

