import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import {
  Building2,
  CheckCircle2,
  AlertTriangle,
  Save,
  Send,
  Loader2,
  Info,
  Layers,
  Flame,
  Accessibility,
  Laptop,
  Users,
  BookOpen,
} from 'lucide-react';
import { instituteApi, ApplicationItem, InfrastructureData } from '../../api/institute';
import { StatusPill } from '../../components/StatusPill';

const infrastructureSchema = z.object({
  total_built_up_area: z.coerce.number().min(0, 'Must be a non-negative number'),
  land_area: z.coerce.number().min(0, 'Must be a non-negative number'),
  classroom_count: z.coerce.number().int().min(0, 'Must be a non-negative integer'),
  average_classroom_area: z.coerce.number().min(0, 'Must be a non-negative number'),
  laboratory_count: z.coerce.number().int().min(0, 'Must be a non-negative integer'),
  library_area: z.coerce.number().min(0, 'Must be a non-negative number'),
  library_books_count: z.coerce.number().int().min(0, 'Must be a non-negative integer'),
  total_sanctioned_intake: z.coerce.number().int().min(0, 'Must be a non-negative integer'),
  faculty_count: z.coerce.number().int().min(0, 'Must be a non-negative integer'),
  student_count: z.coerce.number().int().min(0, 'Must be a non-negative integer'),
  computers_available: z.coerce.number().int().min(0, 'Must be a non-negative integer'),
  internet_bandwidth_mbps: z.coerce.number().min(0, 'Must be a non-negative number'),
  barrier_free_facilities: z.boolean(),
  fire_safety_installed: z.boolean(),
});

type FormValues = z.infer<typeof infrastructureSchema>;

export const InfrastructurePage: React.FC = () => {
  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [selectedAppId, setSelectedAppId] = useState<string>('');
  const [infraStatus, setInfraStatus] = useState<'DRAFT' | 'SUBMITTED'>('DRAFT');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm<FormValues>({
    resolver: zodResolver(infrastructureSchema),
    defaultValues: {
      total_built_up_area: 0,
      land_area: 0,
      classroom_count: 0,
      average_classroom_area: 0,
      laboratory_count: 0,
      library_area: 0,
      library_books_count: 0,
      total_sanctioned_intake: 0,
      faculty_count: 0,
      student_count: 0,
      computers_available: 0,
      internet_bandwidth_mbps: 0,
      barrier_free_facilities: false,
      fire_safety_installed: false,
    },
  });

  const watchedValues = watch();

  // Load applications
  useEffect(() => {
    const fetchApps = async () => {
      try {
        const res = await instituteApi.getApplications();
        if (res && res.items && res.items.length > 0) {
          setApplications(res.items);
          setSelectedAppId(res.items[0].application_id);
        }
      } catch (err) {
        console.error('Failed to load applications', err);
      }
    };
    fetchApps();
  }, []);

  // Load infrastructure details when selected application changes
  useEffect(() => {
    if (!selectedAppId) return;

    const fetchInfra = async () => {
      setIsLoading(true);
      setSuccessMessage(null);
      setErrorMessage(null);
      try {
        const data = await instituteApi.getInfrastructure(selectedAppId);
        setInfraStatus(data.status || 'DRAFT');
        reset({
          total_built_up_area: data.total_built_up_area || 0,
          land_area: data.land_area || 0,
          classroom_count: data.classroom_count || 0,
          average_classroom_area: data.average_classroom_area || 0,
          laboratory_count: data.laboratory_count || 0,
          library_area: data.library_area || 0,
          library_books_count: data.library_books_count || 0,
          total_sanctioned_intake: data.total_sanctioned_intake || 0,
          faculty_count: data.faculty_count || 0,
          student_count: data.student_count || 0,
          computers_available: data.computers_available || 0,
          internet_bandwidth_mbps: data.internet_bandwidth_mbps || 0,
          barrier_free_facilities: Boolean(data.barrier_free_facilities),
          fire_safety_installed: Boolean(data.fire_safety_installed),
        });
      } catch (err) {
        console.error('Failed to load infrastructure data', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchInfra();
  }, [selectedAppId, reset]);

  // Derived real-time calculations
  const builtUpPerIntake =
    watchedValues.total_sanctioned_intake && watchedValues.total_sanctioned_intake > 0
      ? (watchedValues.total_built_up_area / watchedValues.total_sanctioned_intake).toFixed(2)
      : '0.00';

  const facultyStudentRatio =
    watchedValues.faculty_count && watchedValues.faculty_count > 0
      ? (watchedValues.student_count / watchedValues.faculty_count).toFixed(1)
      : '0.0';

  const computerStudentRatio =
    watchedValues.student_count && watchedValues.student_count > 0
      ? (watchedValues.computers_available / watchedValues.student_count).toFixed(3)
      : '0.000';

  const onSave = async (values: FormValues, targetStatus: 'DRAFT' | 'SUBMITTED') => {
    if (!selectedAppId) return;
    setIsSaving(true);
    setSuccessMessage(null);
    setErrorMessage(null);

    try {
      const payload: Partial<InfrastructureData> = {
        ...values,
        status: targetStatus,
      };
      const res = await instituteApi.updateInfrastructure(selectedAppId, payload);
      setInfraStatus(res.status);
      setSuccessMessage(
        targetStatus === 'SUBMITTED'
          ? 'Infrastructure compliance details successfully submitted for regulatory validation!'
          : 'Infrastructure details draft saved successfully.'
      );
    } catch (err: any) {
      console.error(err);
      setErrorMessage(
        err?.response?.data?.detail || 'Failed to save infrastructure details. Please try again.'
      );
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* 1. Header & Application Selector */}
      <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            Infrastructure compliance
          </h1>
          <p className="text-sm text-slate-600 mt-1">
            Approval Process Handbook (APH 2026-27) institutional norms and parameters.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <label htmlFor="application-select" className="text-xs font-semibold text-slate-600">
            Application:
          </label>
          <select
            id="application-select"
            value={selectedAppId}
            onChange={(e) => setSelectedAppId(e.target.value)}
            className="px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-sm font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
          >
            {applications.map((app) => (
              <option key={app.id} value={app.application_id}>
                {app.application_id} ({app.category})
              </option>
            ))}
          </select>

          <StatusPill status={infraStatus} />
        </div>
      </div>

      {/* Alert Banners */}
      {successMessage && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-3 text-emerald-800 text-sm">
          <CheckCircle2 size={18} className="text-emerald-600 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {errorMessage && (
        <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-center gap-3 text-rose-800 text-sm">
          <AlertTriangle size={18} className="text-rose-600 shrink-0" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* 2. Key Derived Ratios Live Preview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Built-up Area / Intake
            </span>
            <Building2 size={18} className="text-[#0B3C9D]" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-800">{builtUpPerIntake}</span>
            <span className="text-xs text-slate-500">sq m/student</span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            AICTE Norm: <span className="font-semibold text-slate-700">&ge; 4.0 sq m</span>
          </p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Faculty-Student Ratio
            </span>
            <Users size={18} className="text-[#0B3C9D]" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-800">{facultyStudentRatio}:1</span>
            <span className="text-xs text-slate-500">students/faculty</span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            AICTE Norm: <span className="font-semibold text-slate-700">&le; 20:1</span>
          </p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Computer-Student Ratio
            </span>
            <Laptop size={18} className="text-[#0B3C9D]" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-800">{computerStudentRatio}</span>
            <span className="text-xs text-slate-500">terminals/student</span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            AICTE Norm: <span className="font-semibold text-slate-700">&ge; 0.20 (1:5)</span>
          </p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Classrooms & Labs
            </span>
            <Layers size={18} className="text-[#0B3C9D]" />
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-slate-800">
              {watchedValues.classroom_count} / {watchedValues.laboratory_count}
            </span>
            <span className="text-xs text-slate-500">rooms</span>
          </div>
          <p className="mt-1 text-xs text-slate-500">
            Norms: <span className="font-semibold text-slate-700">&ge; 16 Classrooms / &ge; 20 Labs</span>
          </p>
        </div>
      </div>

      {/* 3. Comprehensive Infrastructure Details Form */}
      <div className="bg-white rounded-[12px] border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div>
            <h2 className="text-base font-bold text-slate-800">Infrastructure Norms Form</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Enter certified institutional figures. Numbers must be non-negative.
            </p>
          </div>
          <div className="text-xs text-slate-500 bg-amber-50 text-amber-800 border border-amber-200 px-3 py-1.5 rounded-lg flex items-center gap-1.5 font-medium">
            <Info size={14} className="text-amber-600" />
            <span>* Indicates mandatory statutory field</span>
          </div>
        </div>

        {isLoading ? (
          <div className="p-12 flex flex-col items-center justify-center gap-3">
            <Loader2 size={32} className="animate-spin text-[#0B3C9D]" />
            <p className="text-sm text-slate-500">Loading infrastructure data...</p>
          </div>
        ) : (
          <form className="p-6 space-y-6">
            {/* Section 1: Land & Built-up Area */}
            <div>
              <h3 className="text-xs font-bold text-[#0B3C9D] uppercase tracking-wider mb-4 flex items-center gap-2">
                <Building2 size={16} /> 1. Land & Built-up Area
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div>
                  <label htmlFor="total-built-up-area" className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Total Built-up Area (sq m) <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="total-built-up-area"
                    type="number"
                    step="0.01"
                    {...register('total_built_up_area')}
                    className="w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                    placeholder="e.g. 42500"
                  />
                  {errors.total_built_up_area && (
                    <p className="text-xs text-rose-500 mt-1">{errors.total_built_up_area.message}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="land-area" className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Total Land Area (sq m) <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="land-area"
                    type="number"
                    step="0.01"
                    {...register('land_area')}
                    className="w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                    placeholder="e.g. 50000"
                  />
                  {errors.land_area && (
                    <p className="text-xs text-rose-500 mt-1">{errors.land_area.message}</p>
                  )}
                </div>
              </div>
            </div>

            {/* Section 2: Instructional Facilities */}
            <div className="pt-4 border-t border-slate-100">
              <h3 className="text-xs font-bold text-[#0B3C9D] uppercase tracking-wider mb-4 flex items-center gap-2">
                <Layers size={16} /> 2. Classrooms & Laboratories
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div>
                  <label htmlFor="classroom-count" className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Number of Classrooms <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="classroom-count"
                    type="number"
                    {...register('classroom_count')}
                    className="w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                    placeholder="e.g. 36"
                  />
                  {errors.classroom_count && (
                    <p className="text-xs text-rose-500 mt-1">{errors.classroom_count.message}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="average-classroom-area" className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Average Classroom Area (sq m) <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="average-classroom-area"
                    type="number"
                    step="0.1"
                    {...register('average_classroom_area')}
                    className="w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                    placeholder="e.g. 68.0"
                  />
                  {errors.average_classroom_area && (
                    <p className="text-xs text-rose-500 mt-1">{errors.average_classroom_area.message}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="laboratory-count" className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Number of Laboratories <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="laboratory-count"
                    type="number"
                    {...register('laboratory_count')}
                    className="w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                    placeholder="e.g. 24"
                  />
                  {errors.laboratory_count && (
                    <p className="text-xs text-rose-500 mt-1">{errors.laboratory_count.message}</p>
                  )}
                </div>
              </div>
            </div>

            {/* Section 3: Library & Information Resources */}
            <div className="pt-4 border-t border-slate-100">
              <h3 className="text-xs font-bold text-[#0B3C9D] uppercase tracking-wider mb-4 flex items-center gap-2">
                <BookOpen size={16} /> 3. Library & Information Resources
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                <div>
                  <label htmlFor="library-area" className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Library Carpet Area (sq m) <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="library-area"
                    type="number"
                    step="0.1"
                    {...register('library_area')}
                    className="w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                    placeholder="e.g. 1200"
                  />
                  {errors.library_area && (
                    <p className="text-xs text-rose-500 mt-1">{errors.library_area.message}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="library-books-count" className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Number of Library Books/Volumes <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="library-books-count"
                    type="number"
                    {...register('library_books_count')}
                    className="w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                    placeholder="e.g. 25000"
                  />
                  {errors.library_books_count && (
                    <p className="text-xs text-rose-500 mt-1">{errors.library_books_count.message}</p>
                  )}
                </div>
              </div>
            </div>

            {/* Section 4: Academic Cadre & Students */}
            <div className="pt-4 border-t border-slate-100">
              <h3 className="text-xs font-bold text-[#0B3C9D] uppercase tracking-wider mb-4 flex items-center gap-2">
                <Users size={16} /> 4. Students & Faculty Demographics
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                <div>
                  <label htmlFor="total-sanctioned-intake" className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Total Sanctioned Intake <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="total-sanctioned-intake"
                    type="number"
                    {...register('total_sanctioned_intake')}
                    className="w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                    placeholder="e.g. 720"
                  />
                  {errors.total_sanctioned_intake && (
                    <p className="text-xs text-rose-500 mt-1">{errors.total_sanctioned_intake.message}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="student-count" className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Total Enrolled Students <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="student-count"
                    type="number"
                    {...register('student_count')}
                    className="w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                    placeholder="e.g. 2160"
                  />
                  {errors.student_count && (
                    <p className="text-xs text-rose-500 mt-1">{errors.student_count.message}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="faculty-count" className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Approved Full-time Faculty <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="faculty-count"
                    type="number"
                    {...register('faculty_count')}
                    className="w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                    placeholder="e.g. 120"
                  />
                  {errors.faculty_count && (
                    <p className="text-xs text-rose-500 mt-1">{errors.faculty_count.message}</p>
                  )}
                </div>
              </div>
            </div>

            {/* Section 5: Computing & Facilities */}
            <div className="pt-4 border-t border-slate-100">
              <h3 className="text-xs font-bold text-[#0B3C9D] uppercase tracking-wider mb-4 flex items-center gap-2">
                <Laptop size={16} /> 5. Computing, Bandwidth & Safety Facilities
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mb-5">
                <div>
                  <label htmlFor="computers-available" className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Computers Available for Students <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="computers-available"
                    type="number"
                    {...register('computers_available')}
                    className="w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                    placeholder="e.g. 650"
                  />
                  {errors.computers_available && (
                    <p className="text-xs text-rose-500 mt-1">{errors.computers_available.message}</p>
                  )}
                </div>

                <div>
                  <label htmlFor="internet-bandwidth" className="block text-xs font-semibold text-slate-700 mb-1.5">
                    Internet Bandwidth (Mbps) <span className="text-rose-500">*</span>
                  </label>
                  <input
                    id="internet-bandwidth"
                    type="number"
                    step="0.1"
                    {...register('internet_bandwidth_mbps')}
                    className="w-full px-3.5 py-2.5 bg-white border border-slate-300 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-[#0B3C9D]"
                    placeholder="e.g. 1000"
                  />
                  {errors.internet_bandwidth_mbps && (
                    <p className="text-xs text-rose-500 mt-1">{errors.internet_bandwidth_mbps.message}</p>
                  )}
                </div>
              </div>

              {/* Toggles for Facilities */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                <label className="flex items-start gap-3 p-4 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-slate-50 cursor-pointer transition-colors">
                  <input
                    type="checkbox"
                    {...register('barrier_free_facilities')}
                    className="mt-1 w-4 h-4 text-[#0B3C9D] rounded border-slate-300 focus:ring-[#0B3C9D]"
                  />
                  <div>
                    <span className="text-sm font-semibold text-slate-800 flex items-center gap-1.5">
                      <Accessibility size={16} className="text-[#0B3C9D]" />
                      Barrier-Free Facilities for Divyangjan
                    </span>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Provision of accessible ramps, lifts, Braille signage, and specialized facilities.
                    </p>
                  </div>
                </label>

                <label className="flex items-start gap-3 p-4 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-slate-50 cursor-pointer transition-colors">
                  <input
                    type="checkbox"
                    {...register('fire_safety_installed')}
                    className="mt-1 w-4 h-4 text-[#0B3C9D] rounded border-slate-300 focus:ring-[#0B3C9D]"
                  />
                  <div>
                    <span className="text-sm font-semibold text-slate-800 flex items-center gap-1.5">
                      <Flame size={16} className="text-rose-500" />
                      Fire Safety & Hydrant Equipment Installed
                    </span>
                    <p className="text-xs text-slate-500 mt-0.5">
                      Certified active hydrant systems, alarms, and emergency evacuation compliance.
                    </p>
                  </div>
                </label>
              </div>
            </div>

            {/* Form Action Buttons */}
            <div className="pt-6 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-end gap-3">
              <button
                type="button"
                disabled={isSaving}
                onClick={handleSubmit((vals) => onSave(vals, 'DRAFT'))}
                className="w-full sm:w-auto px-5 py-2.5 rounded-lg border border-slate-300 text-slate-700 font-semibold text-sm hover:bg-slate-50 flex items-center justify-center gap-2 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {isSaving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                Save Draft
              </button>

              <button
                type="button"
                disabled={isSaving}
                onClick={handleSubmit((vals) => onSave(vals, 'SUBMITTED'))}
                className="w-full sm:w-auto px-6 py-2.5 rounded-lg bg-[#0B3C9D] text-white font-semibold text-sm hover:bg-[#0B3C9D]/90 shadow-sm flex items-center justify-center gap-2 transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {isSaving ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                Submit Infrastructure Details
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
