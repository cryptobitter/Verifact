import React from 'react';
import {
  Activity,
  CheckCircle2,
  AlertTriangle,
  Clock,
  FileDown,
  Eye,
  Calendar,
  Layers,
  Award
} from 'lucide-react';

export default function DashboardHistory({
  history = [],
  onSelectRecord,
  onDownloadPdf,
  currentId
}) {
  const totalScans = history.length;
  const fractureCount = history.filter((h) => h.fracture_detected).length;
  const fractureRatio = totalScans > 0 ? Math.round((fractureCount / totalScans) * 100) : 0;
  const signedCount = history.filter((h) => h.signed_off).length;
  const signedRatio = totalScans > 0 ? Math.round((signedCount / totalScans) * 100) : 0;

  const getSeverityBadge = (sev) => {
    const s = (sev || '').toLowerCase();
    if (s === 'severe' || s === 'high') {
      return 'bg-rose-500/10 text-rose-400 border-rose-500/30';
    }
    if (s === 'moderate' || s === 'medium') {
      return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
    }
    if (s === 'low') {
      return 'bg-sky-500/10 text-sky-400 border-sky-500/30';
    }
    return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
  };

  return (
    <div className="space-y-6">
      {/* KPI Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Scans */}
        <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-lg backdrop-blur">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Scans</span>
            <div className="p-2 rounded-xl bg-sky-500/10 text-sky-400">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-white tracking-tight">{totalScans}</div>
          <div className="text-[11px] text-slate-500 mt-1">Ingested musculoskeletal X-rays</div>
        </div>

        {/* Fracture Ratio */}
        <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-lg backdrop-blur">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Fracture Ratio</span>
            <div className="p-2 rounded-xl bg-amber-500/10 text-amber-400">
              <AlertTriangle className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-amber-400 tracking-tight">{fractureRatio}%</div>
          <div className="text-[11px] text-slate-500 mt-1">{fractureCount} positive cortical fractures</div>
        </div>

        {/* Verified Sign-Off Ratio */}
        <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-lg backdrop-blur">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Physician Sign-Off</span>
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400">
              <Award className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-emerald-400 tracking-tight">{signedRatio}%</div>
          <div className="text-[11px] text-slate-500 mt-1">{signedCount} legally stamped records</div>
        </div>

        {/* Turnaround Time */}
        <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 shadow-lg backdrop-blur">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Avg AI Triage Time</span>
            <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400">
              <Clock className="w-4 h-4" />
            </div>
          </div>
          <div className="text-2xl font-extrabold text-purple-400 tracking-tight">&lt; 2.5s</div>
          <div className="text-[11px] text-slate-500 mt-1">Dual-engine inference & Grad-CAM</div>
        </div>
      </div>

      {/* Historical Records Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-xl backdrop-blur">
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
          <div>
            <h3 className="text-sm font-bold text-slate-100">Radiograph Scan Registry</h3>
            <p className="text-xs text-slate-400">Comprehensive patient triage and digital verification audit trail</p>
          </div>
          <span className="text-xs font-mono px-2.5 py-1 rounded-lg bg-slate-800 text-slate-300 border border-slate-700">
            {history.length} Records
          </span>
        </div>

        {history.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-xs">
            <Layers className="w-8 h-8 mx-auto mb-2 text-slate-600 stroke-[1.5]" />
            <p>No historical scans found. Run a 1-click sample or upload an X-ray to start triage.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase font-mono text-[10px] bg-slate-950/40">
                  <th className="py-3 px-4">Scan</th>
                  <th className="py-3 px-4">ID & Date</th>
                  <th className="py-3 px-4">Anatomy</th>
                  <th className="py-3 px-4">Finding & Severity</th>
                  <th className="py-3 px-4">Physician Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {history.map((record) => {
                  const isSelected = currentId === record.id;
                  const dateStr = record.created_at
                    ? new Date(record.created_at).toLocaleDateString(undefined, {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })
                    : 'N/A';

                  return (
                    <tr
                      key={record.id}
                      className={`hover:bg-slate-800/40 transition-colors ${
                        isSelected ? 'bg-sky-950/30 font-medium' : ''
                      }`}
                    >
                      {/* Thumbnail Preview */}
                      <td className="py-3 px-4 w-14">
                        <div className="w-10 h-10 rounded-lg bg-black overflow-hidden border border-slate-800 flex items-center justify-center">
                          {record.image_url ? (
                            <img
                              src={record.image_url}
                              alt="Scan Thumbnail"
                              className="w-full h-full object-cover"
                            />
                          ) : (
                            <Activity className="w-4 h-4 text-slate-600" />
                          )}
                        </div>
                      </td>

                      {/* ID & Date */}
                      <td className="py-3 px-4">
                        <div className="font-mono font-bold text-sky-400">
                          FRX-{String(record.id).padStart(6, '0')}
                        </div>
                        <div className="text-[11px] text-slate-400 flex items-center gap-1 mt-0.5">
                          <Calendar className="w-3 h-3 text-slate-500" />
                          <span>{dateStr}</span>
                        </div>
                      </td>

                      {/* Anatomy */}
                      <td className="py-3 px-4">
                        <span className="text-slate-200 font-semibold">{record.bone || 'Musculoskeletal'}</span>
                      </td>

                      {/* Severity / Finding */}
                      <td className="py-3 px-4">
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-mono border font-medium ${getSeverityBadge(
                              record.severity
                            )}`}
                          >
                            {record.severity || (record.fracture_detected ? 'Positive' : 'Normal')}
                          </span>
                        </div>
                      </td>

                      {/* Physician Status */}
                      <td className="py-3 px-4">
                        {record.signed_off ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 text-[10px] font-semibold">
                            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                            <span>Signed & Sealed</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-500/10 text-amber-300 border border-amber-500/30 text-[10px] font-semibold">
                            <Clock className="w-3 h-3 text-amber-400" />
                            <span>Pending Sign-Off</span>
                          </span>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end space-x-2">
                          <button
                            onClick={() => onSelectRecord(record.id)}
                            className="p-1.5 rounded-lg bg-slate-800 hover:bg-sky-600 text-slate-300 hover:text-white transition"
                            title="Load in PACS Workstation"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => onDownloadPdf(record.id)}
                            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition"
                            title="Download Clinical PDF"
                          >
                            <FileDown className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
