import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Search,
  X,
  ChevronDown,
  BookOpen,
  Copy,
  Check,
  ShieldAlert,
  Lightbulb,
  Layers,
  FileCheck2,
  Cpu,
  Clock,
  ArrowUpDown,
  RotateCcw,
} from 'lucide-react';
import {
  instituteApi,
  RulesResponse,
} from '../../api/institute';

// Helper component for soft-amber search term highlighting
const HighlightedText: React.FC<{ text: string; query: string }> = ({ text, query }) => {
  if (!query || !query.trim()) return <>{text}</>;
  const q = query.trim();
  const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(`(${escaped})`, 'gi');
  const parts = text.split(regex);

  return (
    <>
      {parts.map((part, i) =>
        part.toLowerCase() === q.toLowerCase() ? (
          <mark key={i} className="bg-[#FFF0D6] text-[#B85700] px-1 py-0.5 rounded font-semibold">
            {part}
          </mark>
        ) : (
          part
        )
      )}
    </>
  );
};

export const RulesPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const deepLinkRuleCode = searchParams.get('rule');

  // Search & Filter state
  const [searchInput, setSearchInput] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [selectedType, setSelectedType] = useState<'ALL' | 'MANDATORY' | 'ADVISORY'>('ALL');
  const [sortOrder, setSortOrder] = useState<'rule_code' | 'recent'>('rule_code');

  // Accordion & Expansion states
  const [openCategories, setOpenCategories] = useState<Record<string, boolean>>({});
  const [expandedCards, setExpandedCards] = useState<Record<string, boolean>>({});
  const [copiedCode, setCopiedCode] = useState<string | null>(null);
  const [highlightedCode, setHighlightedCode] = useState<string | null>(null);

  // Data & Request State
  const [data, setData] = useState<RulesResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Debounce search input by 250ms
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(searchInput);
    }, 250);
    return () => clearTimeout(timer);
  }, [searchInput]);

  // Fetch Rules from API
  const fetchRules = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const res = await instituteApi.getRules({
        q: debouncedSearch || undefined,
        category: selectedCategory !== 'All' ? selectedCategory : undefined,
        type: selectedType !== 'ALL' ? selectedType : undefined,
        sort: sortOrder,
      });
      setData(res);

      // Open all categories by default on first fetch
      const initOpen: Record<string, boolean> = {};
      res.groups.forEach((g) => {
        initOpen[g.category] = true;
      });
      setOpenCategories((prev) => (Object.keys(prev).length === 0 ? initOpen : prev));
    } catch (err: any) {
      console.error(err);
      setError(err?.response?.data?.detail || 'Failed to load statutory checklist rules.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
  }, [debouncedSearch, selectedCategory, selectedType, sortOrder]);

  // Handle Deep Linking (?rule=APH-2026-CH2-R02)
  const initialDeepLinkHandled = useRef(false);
  useEffect(() => {
    if (deepLinkRuleCode && data && !initialDeepLinkHandled.current) {
      initialDeepLinkHandled.current = true;
      // Find category of the rule
      let targetCat: string | null = null;
      for (const g of data.groups) {
        if (g.rules.some((r) => r.rule_code === deepLinkRuleCode)) {
          targetCat = g.category;
          break;
        }
      }

      if (targetCat) {
        setOpenCategories((prev) => ({ ...prev, [targetCat!]: true }));
        setExpandedCards((prev) => ({ ...prev, [deepLinkRuleCode]: true }));
        setHighlightedCode(deepLinkRuleCode);

        setTimeout(() => {
          const el = document.getElementById(`rule-${deepLinkRuleCode}`);
          if (el) {
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
        }, 300);

        // Remove highlight animation after 3 seconds
        setTimeout(() => {
          setHighlightedCode(null);
        }, 3000);
      }
    }
  }, [deepLinkRuleCode, data]);

  // Total matching rules count
  const totalFoundRules = useMemo(() => {
    if (!data) return 0;
    return data.groups.reduce((acc, g) => acc + g.rules.length, 0);
  }, [data]);

  // Category counts list
  const categoryChips = useMemo(() => {
    if (!data?.summary?.category_counts) return [];
    return Object.entries(data.summary.category_counts).map(([name, count]) => ({
      name,
      count,
    }));
  }, [data]);

  // Toggle Category Accordion
  const toggleCategory = (cat: string) => {
    setOpenCategories((prev) => ({
      ...prev,
      [cat]: !prev[cat],
    }));
  };

  // Toggle Rule Card Details
  const toggleRuleCard = (code: string) => {
    setExpandedCards((prev) => ({
      ...prev,
      [code]: !prev[code],
    }));
  };

  // Expand / Collapse All Categories
  const areAllCategoriesOpen = useMemo(() => {
    if (!data?.groups || data.groups.length === 0) return false;
    return data.groups.every((g) => openCategories[g.category]);
  }, [data, openCategories]);

  const handleToggleExpandAll = () => {
    if (!data) return;
    const nextState = !areAllCategoriesOpen;
    const updated: Record<string, boolean> = {};
    data.groups.forEach((g) => {
      updated[g.category] = nextState;
    });
    setOpenCategories(updated);
  };

  // Copy rule code to clipboard
  const handleCopyCode = (code: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(code);
    setCopiedCode(code);
    setTimeout(() => {
      setCopiedCode((prev) => (prev === code ? null : prev));
    }, 1500);
  };

  // Clear all filters
  const handleClearFilters = () => {
    setSearchInput('');
    setDebouncedSearch('');
    setSelectedCategory('All');
    setSelectedType('ALL');
    setSortOrder('rule_code');
    setSearchParams({});
  };

  return (
    <div className="space-y-5 animate-fade-in pb-16">
      {/* =================================================================== */}
      {/* A. HEADER CARD                                                      */}
      {/* =================================================================== */}
      <div className="bg-white rounded-xl p-5 sm:p-6 shadow-sm border border-slate-200 flex flex-col gap-4">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              Rules and timelines
            </h1>
            <p className="text-sm text-slate-600 mt-1">
              Official statutory guidelines from the Approval Process Handbook (APH 2026-27).
            </p>
          </div>

          {/* Right: Version & Last Updated Chips */}
          <div className="flex items-center gap-2 self-start lg:self-center shrink-0">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200 select-none">
              <Clock size={12} className="text-slate-500" />
              <span>Updated: Oct 2026</span>
            </span>
            <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-bold bg-[#E3F0FF] text-[#0B3C9D] border border-blue-200 select-none">
              APH v2026.1
            </span>
          </div>
        </div>

        {/* Search input with live counter & clear button */}
        <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-slate-100">
          <div className="relative flex-1 max-w-xl">
            <Search size={15} className="absolute left-3.5 top-3 text-slate-500" />
            <input
              type="text"
              placeholder="Search rule ID, title, description, or handbook section..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="w-full h-10 pl-10 pr-9 text-xs sm:text-sm rounded-lg border border-[#D5DBE5] text-[#0F2A5C] placeholder:text-slate-500 focus:border-[#F58220] focus:ring-2 focus:ring-[#F58220]/20 outline-none transition-all bg-white"
            />
            {searchInput && (
              <button
                type="button"
                onClick={() => setSearchInput('')}
                aria-label="Clear search input"
                className="absolute right-2.5 top-2.5 p-1 rounded-md text-slate-500 hover:text-slate-800 hover:bg-slate-100 transition-colors"
              >
                <X size={15} />
              </button>
            )}
          </div>

          <div className="flex items-center gap-3 text-xs text-slate-600 shrink-0">
            <span className="font-semibold text-[#0F2A5C] bg-slate-100 px-3 py-1 rounded-full border border-slate-200">
              {isLoading ? 'Searching...' : `${totalFoundRules} rules found`}
            </span>
          </div>
        </div>
      </div>

      {/* =================================================================== */}
      {/* B. SUMMARY STRIP (4 Mini Stat Cards)                                 */}
      {/* =================================================================== */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Rules */}
        <div className="bg-white rounded-[12px] p-4 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100 flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-full bg-[#E3F0FF] text-[#0B3C9D] flex items-center justify-center shrink-0">
            <BookOpen size={22} />
          </div>
          <div className="min-w-0">
            <span className="text-[11px] uppercase tracking-wider font-semibold text-slate-500 block truncate">
              Total Rules
            </span>
            <span className="text-xl sm:text-2xl font-bold text-[#0F2A5C] leading-tight">
              {data?.summary?.total ?? '--'}
            </span>
          </div>
        </div>

        {/* Mandatory */}
        <div className="bg-white rounded-[12px] p-4 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100 flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-full bg-[#FFF0D6] text-[#B85700] flex items-center justify-center shrink-0">
            <ShieldAlert size={22} />
          </div>
          <div className="min-w-0">
            <span className="text-[11px] uppercase tracking-wider font-semibold text-slate-500 block truncate">
              Mandatory
            </span>
            <span className="text-xl sm:text-2xl font-bold text-[#0F2A5C] leading-tight">
              {data?.summary?.mandatory ?? '--'}
            </span>
          </div>
        </div>

        {/* Advisory */}
        <div className="bg-white rounded-[12px] p-4 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100 flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-full bg-[#E2F6E6] text-[#1E7036] flex items-center justify-center shrink-0">
            <Lightbulb size={22} />
          </div>
          <div className="min-w-0">
            <span className="text-[11px] uppercase tracking-wider font-semibold text-slate-500 block truncate">
              Advisory
            </span>
            <span className="text-xl sm:text-2xl font-bold text-[#0F2A5C] leading-tight">
              {data?.summary?.advisory ?? '--'}
            </span>
          </div>
        </div>

        {/* Categories */}
        <div className="bg-white rounded-[12px] p-4 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100 flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-full bg-[#ECE8FB] text-[#4A3B82] flex items-center justify-center shrink-0">
            <Layers size={22} />
          </div>
          <div className="min-w-0">
            <span className="text-[11px] uppercase tracking-wider font-semibold text-slate-500 block truncate">
              Categories
            </span>
            <span className="text-xl sm:text-2xl font-bold text-[#0F2A5C] leading-tight">
              {data?.summary?.categories_count ?? '--'}
            </span>
          </div>
        </div>
      </div>

      {/* =================================================================== */}
      {/* C. FILTER BAR                                                       */}
      {/* =================================================================== */}
      <div className="bg-white rounded-[12px] p-4 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100 space-y-3.5">
        {/* Category Chips (Horizontally Scrollable) */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs no-scrollbar">
          <button
            type="button"
            onClick={() => setSelectedCategory('All')}
            className={`px-3.5 py-1.5 rounded-full font-semibold whitespace-nowrap transition-all shrink-0 ${
              selectedCategory === 'All'
                ? 'bg-[#F58220] text-white shadow-sm'
                : 'bg-slate-100 text-slate-700 hover:bg-slate-200/80 border border-slate-200'
            }`}
          >
            All Categories ({data?.summary?.total ?? 0})
          </button>
          {categoryChips.map((cat) => {
            const isActive = selectedCategory === cat.name;
            return (
              <button
                key={cat.name}
                type="button"
                onClick={() => setSelectedCategory(cat.name)}
                className={`px-3.5 py-1.5 rounded-full font-semibold whitespace-nowrap transition-all shrink-0 ${
                  isActive
                    ? 'bg-[#F58220] text-white shadow-sm'
                    : 'bg-slate-100 text-slate-700 hover:bg-slate-200/80 border border-slate-200'
                }`}
              >
                {cat.name} ({cat.count})
              </button>
            );
          })}
        </div>

        {/* Sub-row: Type toggle + Sort dropdown + Expand/Collapse All */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2.5 border-t border-slate-100 text-xs">
          {/* Segmented Type Toggle */}
          <div className="inline-flex rounded-lg border border-[#D5DBE5] p-0.5 bg-slate-50 self-start">
            {(['ALL', 'MANDATORY', 'ADVISORY'] as const).map((type) => {
              const active = selectedType === type;
              return (
                <button
                  key={type}
                  type="button"
                  onClick={() => setSelectedType(type)}
                  className={`px-3 py-1.5 rounded-md font-semibold capitalize transition-all ${
                    active
                      ? 'bg-white text-[#0B3C9D] shadow-sm font-bold'
                      : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  {type === 'ALL' ? 'All Types' : type.toLowerCase()}
                </button>
              );
            })}
          </div>

          <div className="flex items-center gap-3 self-end sm:self-center">
            {/* Sort Dropdown */}
            <div className="flex items-center gap-1.5">
              <ArrowUpDown size={14} className="text-slate-600" />
              <select
                value={sortOrder}
                onChange={(e) => setSortOrder(e.target.value as any)}
                className="h-8 px-2.5 rounded-md border border-[#D5DBE5] text-[#0F2A5C] bg-white font-medium outline-none focus:border-[#F58220] cursor-pointer"
              >
                <option value="rule_code">Sort: Rule ID</option>
                <option value="recent">Sort: Recently Updated</option>
              </select>
            </div>

            {/* Expand / Collapse All */}
            <button
              type="button"
              onClick={handleToggleExpandAll}
              className="text-[#0B3C9D] hover:text-[#092E7A] font-semibold underline underline-offset-2 px-1 py-1"
            >
              {areAllCategoriesOpen ? 'Collapse all' : 'Expand all'}
            </button>
          </div>
        </div>
      </div>

      {/* =================================================================== */}
      {/* D & E. CATEGORY SECTIONS (ACCORDION) & RULE CARDS                   */}
      {/* =================================================================== */}
      {isLoading ? (
        // Skeleton Loaders
        <div className="space-y-4">
          {[1, 2, 3].map((n) => (
            <div
              key={n}
              className="bg-white rounded-[12px] p-6 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100 animate-pulse space-y-4"
            >
              <div className="h-6 bg-slate-200 rounded w-1/3" />
              <div className="space-y-2">
                <div className="h-16 bg-slate-100 rounded" />
                <div className="h-16 bg-slate-100 rounded" />
              </div>
            </div>
          ))}
        </div>
      ) : error ? (
        // Error State
        <div className="bg-white rounded-[12px] p-10 text-center shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100">
          <ShieldAlert size={36} className="text-[#C62828] mx-auto mb-3" />
          <h3 className="text-base font-bold text-[#0F2A5C]">Failed to Load Regulations</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">{error}</p>
          <button
            type="button"
            onClick={fetchRules}
            className="mt-4 px-4 py-2 bg-[#0B3C9D] text-white rounded-lg text-xs font-semibold hover:bg-[#092E7A] transition-colors inline-flex items-center gap-1.5"
          >
            <RotateCcw size={14} />
            <span>Retry</span>
          </button>
        </div>
      ) : totalFoundRules === 0 ? (
        // Empty State
        <div className="bg-white rounded-[12px] p-12 text-center shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100">
          <BookOpen size={40} className="text-slate-500 mx-auto mb-3" />
          <h3 className="text-base font-bold text-[#0F2A5C]">No rules match your search</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            Try adjusting your search query, selecting another category, or resetting all filters.
          </p>
          <button
            type="button"
            onClick={handleClearFilters}
            className="mt-4 px-4 py-2 bg-[#F58220] hover:bg-[#E06F0F] text-white rounded-lg text-xs font-semibold transition-colors shadow-sm"
          >
            Clear all filters
          </button>
        </div>
      ) : (
        <div className="space-y-5">
          {data?.groups.map((group) => {
            const isOpen = openCategories[group.category] ?? true;

            return (
              <div
                key={group.category}
                className="bg-white rounded-[12px] shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100 overflow-hidden"
              >
                {/* Accordion Category Header (Sticky While Scrolling) */}
                <button
                  type="button"
                  onClick={() => toggleCategory(group.category)}
                  aria-expanded={isOpen}
                  className="w-full px-5 py-3.5 bg-white/95 backdrop-blur-sm sticky top-24 z-20 border-b border-slate-100 flex items-center justify-between hover:bg-slate-50/90 transition-colors select-none text-left"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="w-7 h-7 rounded-full bg-[#E3F0FF] text-[#0B3C9D] font-bold text-xs flex items-center justify-center shrink-0">
                      {group.rules.length}
                    </span>
                    <div className="flex items-baseline gap-2.5 flex-wrap min-w-0">
                      <h2 className="text-sm font-bold text-[#0F2A5C] uppercase tracking-wide truncate">
                        {group.category}
                      </h2>
                      <span className="text-[11px] font-normal text-slate-500 whitespace-nowrap">
                        ({group.mandatory_count} mandatory, {group.advisory_count} advisory)
                      </span>
                    </div>
                  </div>

                  <div className="p-1 rounded-md text-slate-600 hover:text-slate-700 transition-transform duration-200">
                    <ChevronDown
                      size={18}
                      className={`transform transition-transform duration-250 ${
                        isOpen ? 'rotate-180' : ''
                      }`}
                    />
                  </div>
                </button>

                {/* Category Rule Cards Container */}
                {isOpen && (
                  <div className="p-4 sm:p-5 space-y-3.5 bg-slate-50/40">
                    {group.rules.map((rule) => {
                      const isMandatory = rule.rule_type === 'MANDATORY' || rule.is_mandatory;
                      const isExpanded = expandedCards[rule.rule_code] ?? false;
                      const isHighlighted = highlightedCode === rule.rule_code;
                      const isCopied = copiedCode === rule.rule_code;

                      return (
                        <div
                          key={rule.id}
                          id={`rule-${rule.rule_code}`}
                          tabIndex={0}
                          role="region"
                          aria-label={`Rule ${rule.rule_code}: ${rule.title}`}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              toggleRuleCard(rule.rule_code);
                            }
                          }}
                          className={`rounded-[10px] bg-white border border-slate-200/90 transition-all duration-200 shadow-sm hover:shadow-md hover:-translate-y-0.5 focus-visible:ring-2 focus-visible:ring-[#F58220] outline-none ${
                            isMandatory ? 'border-l-4 border-l-[#F58220]' : 'border-l-4 border-l-[#0B3C9D]'
                          } ${isHighlighted ? 'ring-2 ring-[#F58220] bg-orange-50/40' : ''}`}
                        >
                          {/* Card Main Header (Click to expand) */}
                          <div
                            onClick={() => toggleRuleCard(rule.rule_code)}
                            className="p-4 sm:p-4.5 cursor-pointer select-none"
                          >
                            {/* Row 1: Monospace Code Chip + Title + Badges */}
                            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
                              <div className="flex items-center gap-2.5 flex-wrap min-w-0">
                                {/* Rule Code Monospace Chip with Copy Button */}
                                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-100 border border-slate-200/80 text-[11.5px] font-mono font-bold text-[#0B3C9D]">
                                  <span>
                                    <HighlightedText text={rule.rule_code} query={debouncedSearch} />
                                  </span>
                                  <button
                                    type="button"
                                    onClick={(e) => handleCopyCode(rule.rule_code, e)}
                                    aria-label={`Copy rule code ${rule.rule_code}`}
                                    title="Copy Rule ID"
                                    className="p-0.5 text-slate-600 hover:text-[#0B3C9D] rounded transition-colors"
                                  >
                                    {isCopied ? (
                                      <Check size={12} className="text-green-600" />
                                    ) : (
                                      <Copy size={12} />
                                    )}
                                  </button>
                                  {isCopied && (
                                    <span className="text-[10px] font-sans font-semibold text-green-700 animate-fade-in">
                                      Copied
                                    </span>
                                  )}
                                </div>

                                <h3 className="text-sm font-bold text-[#0F2A5C] leading-snug">
                                  <HighlightedText text={rule.title} query={debouncedSearch} />
                                </h3>
                              </div>

                              {/* Right: Version + Type Pill */}
                              <div className="flex items-center gap-2 shrink-0 self-start sm:self-center">
                                <span className="text-[11px] font-semibold text-slate-500 bg-slate-100 px-2 py-0.5 rounded select-none">
                                  {rule.version}
                                </span>
                                {isMandatory ? (
                                  <span className="inline-flex items-center gap-1 text-[11.5px] font-bold text-[#C62828] bg-[#FDE7E9] px-2.5 py-0.5 rounded-full select-none">
                                    <ShieldAlert size={12} />
                                    <span>Mandatory</span>
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center gap-1 text-[11.5px] font-bold text-[#0B3C9D] bg-[#E3F0FF] px-2.5 py-0.5 rounded-full select-none">
                                    <Lightbulb size={12} />
                                    <span>Advisory</span>
                                  </span>
                                )}
                              </div>
                            </div>

                            {/* Row 2: Description (14px, leading 1.6, max 2 lines with Read more) */}
                            <div className="mt-2 text-sm text-[#475569] leading-[1.6]">
                              <p className={isExpanded ? '' : 'line-clamp-2'}>
                                <HighlightedText text={rule.description} query={debouncedSearch} />
                              </p>
                              <div className="flex items-center justify-between pt-1">
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    toggleRuleCard(rule.rule_code);
                                  }}
                                  className="text-[12px] font-semibold text-[#0B3C9D] hover:underline"
                                >
                                  {isExpanded ? 'Show less' : 'Read more & view verification checks'}
                                </button>
                                <span className="text-slate-600">
                                  <ChevronDown
                                    size={15}
                                    className={`transform transition-transform duration-200 ${
                                      isExpanded ? 'rotate-180' : ''
                                    }`}
                                  />
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* Expanded Details Section */}
                          {isExpanded && (
                            <div className="px-4 pb-4 sm:px-5 sm:pb-5 pt-3 border-t border-slate-100 bg-[#FBFDFF] rounded-b-[10px] space-y-4 text-xs animate-fade-in">
                              {/* 1. What the AI checks */}
                              {rule.ai_checks && rule.ai_checks.length > 0 && (
                                <div>
                                  <h4 className="text-[11px] uppercase tracking-wider font-bold text-[#0B3C9D] flex items-center gap-1.5 mb-2">
                                    <Cpu size={14} className="text-[#F58220]" />
                                    <span>What the AI checks</span>
                                  </h4>
                                  <ul className="space-y-1.5 pl-1 text-slate-700">
                                    {rule.ai_checks.map((check, idx) => (
                                      <li key={idx} className="flex items-start gap-2 leading-relaxed">
                                        <span className="w-1.5 h-1.5 rounded-full bg-[#F58220] mt-1.5 shrink-0" />
                                        <span>
                                          <HighlightedText text={check} query={debouncedSearch} />
                                        </span>
                                      </li>
                                    ))}
                                  </ul>
                                </div>
                              )}

                              {/* 2. Evidence required */}
                              {rule.evidence_required && rule.evidence_required.length > 0 && (
                                <div>
                                  <h4 className="text-[11px] uppercase tracking-wider font-bold text-[#0B3C9D] flex items-center gap-1.5 mb-2">
                                    <FileCheck2 size={14} className="text-[#0B3C9D]" />
                                    <span>Evidence required</span>
                                  </h4>
                                  <div className="flex items-center gap-2 flex-wrap">
                                    {rule.evidence_required.map((doc, idx) => (
                                      <span
                                        key={idx}
                                        className="inline-flex items-center px-2.5 py-1 rounded-md bg-white border border-slate-200 text-[#0F2A5C] font-medium shadow-2xs"
                                      >
                                        {doc}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* 3. Applies to */}
                              {rule.applies_to && rule.applies_to.length > 0 && (
                                <div>
                                  <h4 className="text-[11px] uppercase tracking-wider font-bold text-slate-500 mb-1.5">
                                    Applies to
                                  </h4>
                                  <div className="flex items-center gap-1.5 flex-wrap">
                                    {rule.applies_to.map((item, idx) => (
                                      <span
                                        key={idx}
                                        className="inline-flex items-center px-2 py-0.5 rounded text-[11px] bg-slate-100 text-slate-600 font-medium"
                                      >
                                        {item}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* 4. Handbook Source Chip & History */}
                              <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-t border-slate-200/60">
                                <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-[#E3F0FF]/60 text-[#0B3C9D] font-semibold text-xs border border-blue-100 w-fit">
                                  <BookOpen size={13} className="shrink-0" />
                                  <span>Handbook Source: {rule.handbook_reference}</span>
                                </div>

                                {/* Version History List */}
                                {rule.version_history && rule.version_history.length > 0 && (
                                  <div className="text-[11px] text-slate-500">
                                    <span className="font-semibold text-slate-700">History: </span>
                                    {rule.version_history.map((vh, i) => (
                                      <span key={i} className="mr-2">
                                        {vh.version} ({vh.date}): {vh.note}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
