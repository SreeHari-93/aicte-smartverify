import React from 'react';
import { useAuth } from '../context/AuthContext';
import { TricolourStrip } from '../components/TricolourStrip';
import { Building2, LogOut, ShieldCheck, CheckCircle2 } from 'lucide-react';

export const InstituteDashboard: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      <TricolourStrip />

      {/* Top Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-[#0B3C9D] flex items-center justify-center text-white">
              <Building2 size={22} />
            </div>
            <div>
              <h1 className="text-lg font-bold text-[#0B3C9D] leading-none">
                AICTE SmartVerify AI
              </h1>
              <span className="text-xs text-[#7A8699]">Institute Portal</span>
            </div>
          </div>

          <button
            onClick={logout}
            className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-[#0F2A5C] hover:text-[#C62828] hover:bg-red-50 rounded-lg transition-colors border border-slate-200"
          >
            <LogOut size={16} />
            <span>Logout</span>
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto w-full p-6 sm:p-8 flex-1">
        <div className="bg-white rounded-2xl border border-slate-200 p-8 shadow-sm mb-6">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-100">
            <div>
              <span className="text-xs uppercase tracking-wider font-semibold text-[#F58220] bg-orange-50 px-2.5 py-1 rounded">
                Verified Institute Session
              </span>
              <h2 className="text-2xl font-bold text-[#0F2A5C] mt-2">
                Welcome, {user?.institute?.name || user?.email || 'Institute Officer'}
              </h2>
              <p className="text-sm text-slate-500 mt-1">
                AICTE ID: <span className="font-semibold text-slate-800">{user?.institute?.aicte_institute_id || 'DEL0101'}</span> | State: {user?.institute?.state || 'National'}
              </p>
            </div>

            <div className="inline-flex items-center gap-2 bg-emerald-50 border border-emerald-200 text-emerald-800 px-3.5 py-2 rounded-xl text-xs font-semibold">
              <CheckCircle2 size={16} className="text-emerald-600" />
              <span>Authentication Token Active</span>
            </div>
          </div>

          {/* User Details Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
              <span className="text-xs text-slate-500 uppercase tracking-wider font-medium">Logged in Account</span>
              <p className="text-sm font-bold text-[#0F2A5C] mt-1">{user?.email}</p>
            </div>
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
              <span className="text-xs text-slate-500 uppercase tracking-wider font-medium">Role Privilege</span>
              <p className="text-sm font-bold text-[#0F2A5C] mt-1">{user?.role}</p>
            </div>
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200">
              <span className="text-xs text-slate-500 uppercase tracking-wider font-medium">Institute Status</span>
              <p className="text-sm font-bold text-emerald-700 mt-1">{user?.institute?.status || 'ACTIVE'}</p>
            </div>
          </div>
        </div>

        {/* Next Step placeholder card */}
        <div className="bg-gradient-to-r from-blue-50 to-orange-50 rounded-2xl border border-blue-100 p-8">
          <div className="flex items-center gap-3 mb-2">
            <ShieldCheck size={24} className="text-[#0B3C9D]" />
            <h3 className="text-lg font-bold text-[#0B3C9D]">Step 1 Authentication Complete</h3>
          </div>
          <p className="text-sm text-slate-700 leading-relaxed max-w-2xl">
            You are securely logged into the AICTE SmartVerify AI platform. This dashboard is ready to receive
            <strong> Step 2: Application Submission & Document Upload</strong> (OCR, multi-page PDF processing, and anomaly inspection pipeline).
          </p>
        </div>
      </main>

      <footer className="w-full py-4 text-center text-xs text-slate-500 border-t border-slate-200">
        © AICTE, Ministry of Education, Govt. of India | Secured by SmartVerify AI
      </footer>
    </div>
  );
};
