import React from 'react';
import {
  Bone,
  Stethoscope,
  LogOut,
  User,
  Upload,
  LayoutDashboard,
  Tv2,
  CheckCircle2,
  Sparkles
} from 'lucide-react';

export default function Navbar({
  currentUser,
  activeTab,
  setActiveTab,
  onOpenAuth,
  onLogout,
  onOpenUpload
}) {
  return (
    <header className="bg-slate-900/90 border-b border-slate-800 backdrop-blur sticky top-0 z-40 select-none">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand Logo & Title */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-sky-600 to-cyan-500 flex items-center justify-center shadow-lg shadow-sky-500/20 text-white">
            <Bone className="w-6 h-6 transform -rotate-45" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-lg font-black tracking-tight bg-gradient-to-r from-white via-sky-200 to-sky-400 bg-clip-text text-transparent">
                VERIFACT
              </span>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20 font-bold">
                Clinical Fracture Co-Pilot
              </span>
            </div>
            <p className="text-[10px] text-slate-400 hidden sm:block">
              Musculoskeletal Fracture Triage & Grad-CAM Visual Explainability
            </p>
          </div>
        </div>

        {/* Center: Navigation Tabs */}
        <div className="flex items-center space-x-1 bg-slate-950 p-1 rounded-xl border border-slate-800">
          <button
            onClick={() => setActiveTab('workstation')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'workstation'
                ? 'bg-sky-600 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Tv2 className="w-4 h-4" />
            <span>PACS Workstation</span>
          </button>
          <button
            onClick={() => setActiveTab('registry')}
            className={`flex items-center space-x-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
              activeTab === 'registry'
                ? 'bg-sky-600 text-white shadow-md'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <LayoutDashboard className="w-4 h-4" />
            <span>Registry & KPI</span>
          </button>
        </div>

        {/* Right: Actions & Doctor Profile */}
        <div className="flex items-center space-x-3">
          {/* Upload Button */}
          <button
            onClick={onOpenUpload}
            className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-sky-400 hover:text-sky-300 border border-slate-700 text-xs font-semibold transition active:scale-95 shadow-sm"
          >
            <Upload className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Upload X-Ray</span>
          </button>

          {/* User Profile Pill or Login Trigger */}
          {currentUser ? (
            <div className="flex items-center space-x-2 pl-2 border-l border-slate-800">
              <div className="text-right hidden md:block">
                <div className="text-xs font-bold text-slate-200">
                  {currentUser.full_name ? `Dr. ${currentUser.full_name}` : currentUser.email}
                </div>
                <div className="text-[10px] text-emerald-400 font-mono flex items-center justify-end gap-1">
                  <CheckCircle2 className="w-2.5 h-2.5" />
                  <span>{currentUser.registration_number || 'MCI-VERIFIED'}</span>
                </div>
              </div>
              <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-sky-400 font-bold text-xs">
                {currentUser.full_name ? currentUser.full_name[0] : 'D'}
              </div>
              <button
                onClick={onLogout}
                className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-rose-400 transition"
                title="Sign Out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <button
              onClick={onOpenAuth}
              className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white text-xs font-semibold transition shadow-md"
            >
              <User className="w-3.5 h-3.5" />
              <span>Doctor Portal</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
