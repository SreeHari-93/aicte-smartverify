import React, { useEffect, useState } from 'react';
import {
  GraduationCap,
  CheckCircle2,
  FileText,
  XCircle,
  Trophy,
  BookOpen,
  MapPin,
  Phone,
  Building,
  Loader2,
} from 'lucide-react';
import { instituteApi, DashboardData } from '../../api/institute';
import { StatCard } from '../../components/StatCard';
import { StarRing } from '../../components/StarRing';

export const DashboardPage: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        setIsLoading(true);
        const res = await instituteApi.getDashboard();
        setData(res);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load institute dashboard data.');
      } finally {
        setIsLoading(false);
      }
    };
    fetchDashboard();
  }, []);

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] text-white">
        <Loader2 size={36} className="animate-spin text-[#F58220] mb-3" />
        <p className="text-sm font-semibold tracking-wide drop-shadow">Loading Institute Dashboard...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-white rounded-[12px] p-8 shadow-[0_6px_18px_rgba(0,0,0,0.18)] max-w-lg mx-auto text-center mt-12">
        <p className="text-red-600 font-bold mb-2">Error</p>
        <p className="text-slate-600 text-sm mb-4">{error || 'Data unavailable.'}</p>
        <button
          onClick={() => window.location.reload()}
          className="px-4 py-2 bg-[#F58220] text-white text-xs font-semibold rounded-[6px]"
        >
          Retry
        </button>
      </div>
    );
  }

  const instName = data.name || 'SRI KRISHNA COLLEGE OF ENGINEERING AND TECHNOLOGY';
  const accred = data.accreditation;

  return (
    <div className="space-y-8 animate-fade-in pb-12">
      {/* 1. Top of Main Area: Institute Name in huge white bold uppercase with dark text shadow + underline bar */}
      <div className="pt-2">
        <h1
          className="text-2xl sm:text-3xl md:text-4xl lg:text-5xl font-extrabold uppercase tracking-tight text-white font-sans max-w-5xl leading-tight"
          style={{
            textShadow: '0 3px 10px rgba(0, 0, 0, 0.75), 0 1px 3px rgba(0, 0, 0, 0.9)',
          }}
        >
          {instName}
        </h1>
        {/* Short white underline bar (~100px, 3px) beneath it */}
        <div
          className="w-24 h-[3px] bg-white mt-3 rounded-full shadow-[0_2px_4px_rgba(0,0,0,0.6)]"
          aria-hidden="true"
        />
      </div>

      {/* 2. Row of 4 Stat Cards: Application Filed, Approved, Pending, Rejected */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <StatCard
          label="Application Filed"
          value={data.stats.filed}
          icon={<GraduationCap size={28} />}
          tint="blue"
        />
        <StatCard
          label="Approved"
          value={data.stats.approved}
          icon={<CheckCircle2 size={28} />}
          tint="green"
        />
        <StatCard
          label="Pending"
          value={data.stats.pending}
          icon={<FileText size={28} />}
          tint="lavender"
        />
        <StatCard
          label="Rejected"
          value={data.stats.rejected}
          icon={<XCircle size={28} />}
          tint="pink"
        />
      </div>

      {/* 3. Below, Two Cards Side by Side (~60% / 40%) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Card (~60%): Ranking & Accreditation */}
        <div className="lg:col-span-7 bg-white rounded-[12px] p-6 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100 flex flex-col min-h-[380px]">
          {/* Card Header: Trophy icon + Blue bold title */}
          <div className="flex items-center gap-2.5 pb-4 border-b border-slate-100">
            <Trophy size={22} className="text-[#0B3C9D]" />
            <h2 className="text-lg font-bold text-[#0B3C9D] tracking-tight">
              Ranking & Accreditation
            </h2>
          </div>

          {/* Card Body: Split Columns with thin vertical divider */}
          <div className="flex-1 grid grid-cols-1 md:grid-cols-12 gap-6 items-center pt-6">
            {/* Left Column: NIRF Rank inside 8 stars + NAAC Grade */}
            <div className="md:col-span-5 flex justify-center py-2">
              <StarRing
                rank={accred?.nirf_rank || 73}
                grade={accred?.naac_grade || 'A++ (CGPA 3.62)'}
              />
            </div>

            {/* Thin vertical divider on desktop */}
            <div className="hidden md:block w-px bg-slate-200 h-52 self-center" />

            {/* Right Column: Accreditations, College Code, Location, Phone */}
            <div className="md:col-span-6 flex flex-col justify-center space-y-4 text-xs">
              <div>
                <h3 className="text-sm font-bold text-[#0F2A5C] uppercase tracking-wider mb-2">
                  Accreditations & Registry
                </h3>
                <div className="space-y-1.5 text-slate-700">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-slate-500">NBA Status:</span>
                    <span className="font-bold text-[#1E7036] bg-[#E2F6E6] px-2 py-0.5 rounded">
                      {accred?.nba_accredited_courses || 9} Accredited Programmes
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Building size={14} className="text-[#0B3C9D] shrink-0" />
                    <span className="font-semibold text-slate-500">College Code:</span>
                    <span className="font-bold text-[#0F2A5C]">{accred?.college_code || 'C-26922 / TNEA 2718'}</span>
                  </div>
                </div>
              </div>

              {/* Location Address */}
              <div className="pt-2 border-t border-slate-100">
                <div className="flex items-start gap-2 text-slate-700">
                  <MapPin size={16} className="text-[#F58220] shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-slate-500 block">Campus Location:</span>
                    <p className="text-slate-800 leading-relaxed font-medium">
                      {accred?.location_address || 'Sugunapuram, Kuniamuthur, Coimbatore, Tamil Nadu - 641008'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Phone with bold number */}
              <div className="pt-2 border-t border-slate-100 flex items-center gap-2">
                <Phone size={15} className="text-[#0B3C9D] shrink-0" />
                <span className="font-semibold text-slate-500">Telephone:</span>
                <span className="font-bold text-[#0F2A5C] text-sm tracking-wide">
                  {accred?.phone || '+91 422 2678001 / 02'}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Card (~40%): Courses */}
        <div className="lg:col-span-5 bg-white rounded-[12px] p-6 shadow-[0_6px_18px_rgba(0,0,0,0.18)] border border-slate-100 flex flex-col min-h-[380px]">
          {/* Card Header: Open-book icon + Blue bold title */}
          <div className="flex items-center justify-between pb-4 border-b border-slate-100">
            <div className="flex items-center gap-2.5">
              <BookOpen size={22} className="text-[#0B3C9D]" />
              <h2 className="text-lg font-bold text-[#0B3C9D] tracking-tight">Courses</h2>
            </div>
            <span className="text-xs font-semibold text-slate-500 bg-slate-100 px-2.5 py-0.5 rounded-full">
              {data.courses.length} Programmes
            </span>
          </div>

          {/* List of course names, each row separated by a thin line, scrolls if long */}
          <div className="flex-1 overflow-y-auto max-h-[300px] divide-y divide-slate-100 pr-1 mt-2">
            {data.courses.length === 0 ? (
              <p className="text-xs text-slate-400 py-6 text-center">No registered courses found.</p>
            ) : (
              data.courses.map((course) => (
                <div
                  key={course.id}
                  className="py-3 flex items-center justify-between hover:bg-slate-50/80 px-2 rounded-md transition-colors"
                >
                  <div className="flex flex-col pr-2">
                    <span className="text-xs font-semibold text-[#0F2A5C] leading-snug">
                      {course.name}
                    </span>
                    <span className="text-[10px] text-slate-400 uppercase tracking-wider mt-0.5">
                      Intake: <strong className="text-slate-600 font-semibold">{course.intake} seats</strong>
                    </span>
                  </div>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded shrink-0 ${
                      course.level === 'PG'
                        ? 'bg-purple-50 text-purple-700'
                        : 'bg-blue-50 text-[#0B3C9D]'
                    }`}
                  >
                    {course.level}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

