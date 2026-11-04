import React, { useState, useEffect } from 'react';
import {
  FileText,
  CheckCircle,
  FileDown,
  Edit3,
  Award,
  AlertTriangle,
  Stethoscope,
  Clock,
  Sparkles,
  Lock,
  Save,
  Mail,
  Send,
  Database,
  User,
  Activity,
  Ruler,
  X
} from 'lucide-react';
import { api } from '../services/api';

export default function ReportReviewCard({
  analysis,
  currentUser,
  onSaveAndSign,
  onDownloadPdf,
  isSaving
}) {
  if (!analysis) return null;

  const [isEditing, setIsEditing] = useState(false);
  const [bone, setBone] = useState(analysis.bone || 'Osseous structure');
  const [location, setLocation] = useState(analysis.location || 'Metaphysis');
  const [fractureType, setFractureType] = useState(analysis.fracture_type || 'Transverse');
  const [displacement, setDisplacement] = useState(analysis.displacement || 'Non-displaced');
  const [severity, setSeverity] = useState(analysis.severity || 'Moderate');
  const [reportText, setReportText] = useState(analysis.report_text || '');
  const [clinicalNotes, setClinicalNotes] = useState(analysis.clinical_notes || '');

  // Dispatch modal state
  const [emailModalOpen, setEmailModalOpen] = useState(false);
  const [recipientEmail, setRecipientEmail] = useState('');
  const [dispatchNotes, setDispatchNotes] = useState('');
  const [isDispatching, setIsDispatching] = useState(false);
  const [dispatchStatus, setDispatchStatus] = useState(null);

  // FHIR Export state
  const [fhirModalOpen, setFhirModalOpen] = useState(false);
  const [fhirData, setFhirData] = useState(null);

  useEffect(() => {
    setBone(analysis.bone || 'Osseous structure');
    setLocation(analysis.location || 'Metaphysis');
    setFractureType(analysis.fracture_type || 'Transverse');
    setDisplacement(analysis.displacement || 'Non-displaced');
    setSeverity(analysis.severity || 'Moderate');
    setReportText(analysis.report_text || '');
    setClinicalNotes(analysis.clinical_notes || '');
  }, [analysis]);

  const isSigned = Boolean(analysis.signed_off);

  const handleSignOff = () => {
    onSaveAndSign({
      bone,
      location,
      fracture_type: fractureType,
      displacement,
      severity,
      report_text: reportText,
      clinical_notes: clinicalNotes,
      signed_off: true
    });
  };

  const handleSaveDraft = () => {
    onSaveAndSign({
      bone,
      location,
      fracture_type: fractureType,
      displacement,
      severity,
      report_text: reportText,
      clinical_notes: clinicalNotes,
      signed_off: false
    });
    setIsEditing(false);
  };

  const handleSendEmail = async (e) => {
    e.preventDefault();
    if (!recipientEmail) return;
    setIsDispatching(true);
    try {
      await api.sendEmailReport(analysis.id, {
        recipient_email: recipientEmail,
        notes: dispatchNotes
      });
      setDispatchStatus('success');
      setTimeout(() => {
        setEmailModalOpen(false);
        setDispatchStatus(null);
      }, 2000);
    } catch (err) {
      setDispatchStatus('error');
    } finally {
      setIsDispatching(false);
    }
  };

  const handleOpenFhir = async () => {
    try {
      const data = await api.getFhirExport(analysis.id);
      setFhirData(data);
      setFhirModalOpen(true);
    } catch (err) {
      alert('Failed to load FHIR resource.');
    }
  };

  // Parse measurements if stored
  let parsedMeasurements = [];
  if (analysis.annotations) {
    try {
      const parsed = typeof analysis.annotations === 'string' ? JSON.parse(analysis.annotations) : analysis.annotations;
      parsedMeasurements = parsed.measurements || (Array.isArray(parsed) ? parsed : []);
    } catch (e) {
      // ignore
    }
  }

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
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl overflow-hidden shadow-xl flex flex-col h-full backdrop-blur">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400">
            <FileText className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <span>Clinical Radiology Report</span>
              <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full border ${getSeverityBadge(severity)}`}>
                {severity} Severity
              </span>
            </h3>
            <p className="text-[11px] text-slate-400">
              Scan ID: <span className="font-mono text-slate-300">FRX-{String(analysis.id).padStart(6, '0')}</span> • Human-in-the-Loop Co-Pilot
            </p>
          </div>
        </div>

        {/* Status Badge */}
        {isSigned ? (
          <div className="flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-semibold">
            <Award className="w-3.5 h-3.5 text-emerald-400" />
            <span>Physician Signed</span>
          </div>
        ) : (
          <div className="flex items-center space-x-1.5 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs font-semibold">
            <Clock className="w-3.5 h-3.5 text-amber-400" />
            <span>Preliminary AI Draft</span>
          </div>
        )}
      </div>

      {/* Main Content Area */}
      <div className="p-5 space-y-4 flex-1 overflow-y-auto text-xs">
        {/* Patient Clinical Case Card (if demographics present) */}
        {(analysis.patient_id || analysis.patient_age || analysis.mechanism_of_injury) && (
          <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center justify-between font-mono text-[11px]">
            <div className="flex items-center space-x-3 text-slate-300">
              <span className="flex items-center gap-1 text-sky-400 font-bold">
                <User className="w-3.5 h-3.5" />
                <span>{analysis.patient_id || 'PATIENT'}</span>
              </span>
              <span>{analysis.patient_gender || 'M/F'}, {analysis.patient_age ? `${analysis.patient_age}y` : 'Age N/A'}</span>
              {analysis.mechanism_of_injury && (
                <span className="text-amber-400 font-sans">
                  • Trauma: <strong>{analysis.mechanism_of_injury}</strong>
                </span>
              )}
            </div>
          </div>
        )}

        {/* Anatomical Extraction Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
            <span className="text-[10px] text-slate-400 uppercase font-mono tracking-wider block mb-1">Bone</span>
            {isEditing && !isSigned ? (
              <input
                type="text"
                value={bone}
                onChange={(e) => setBone(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-100 font-semibold"
              />
            ) : (
              <span className="font-semibold text-slate-200 block truncate">{bone}</span>
            )}
          </div>

          <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
            <span className="text-[10px] text-slate-400 uppercase font-mono tracking-wider block mb-1">Location</span>
            {isEditing && !isSigned ? (
              <input
                type="text"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-100 font-semibold"
              />
            ) : (
              <span className="font-semibold text-slate-200 block truncate">{location}</span>
            )}
          </div>

          <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
            <span className="text-[10px] text-slate-400 uppercase font-mono tracking-wider block mb-1">Fracture Type</span>
            {isEditing && !isSigned ? (
              <input
                type="text"
                value={fractureType}
                onChange={(e) => setFractureType(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-100 font-semibold"
              />
            ) : (
              <span className="font-semibold text-slate-200 block truncate">{fractureType}</span>
            )}
          </div>

          <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800/80">
            <span className="text-[10px] text-slate-400 uppercase font-mono tracking-wider block mb-1">Displacement</span>
            {isEditing && !isSigned ? (
              <input
                type="text"
                value={displacement}
                onChange={(e) => setDisplacement(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-100 font-semibold"
              />
            ) : (
              <span className="font-semibold text-slate-200 block truncate">{displacement}</span>
            )}
          </div>
        </div>

        {/* Caliper Measurements Placed (if any) */}
        {parsedMeasurements.length > 0 && (
          <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800">
            <div className="flex items-center space-x-1.5 text-amber-400 font-bold mb-2">
              <Ruler className="w-3.5 h-3.5" />
              <span>PACS Caliper Measurements ({parsedMeasurements.length})</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {parsedMeasurements.map((m, i) => (
                <span key={i} className="px-2 py-1 bg-slate-900 rounded-lg border border-slate-700 font-mono text-[10px] text-slate-200">
                  {m.type === 'ruler' ? '📏' : m.type === 'angle' ? '📐' : '📍'} {m.label || m.value}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* 3-Sentence Synthesized Radiology Findings */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-[11px] font-bold text-slate-300 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5 text-sky-400" />
              <span>Radiological Findings (3-Sentence Standard)</span>
            </label>
            {!isSigned && (
              <button
                onClick={() => setIsEditing(!isEditing)}
                className="text-[11px] text-sky-400 hover:text-sky-300 flex items-center gap-1 font-medium transition"
              >
                <Edit3 className="w-3 h-3" />
                <span>{isEditing ? 'Preview Mode' : 'Edit Findings'}</span>
              </button>
            )}
          </div>

          {isEditing && !isSigned ? (
            <textarea
              rows={4}
              value={reportText}
              onChange={(e) => setReportText(e.target.value)}
              className="w-full bg-slate-950 border border-sky-500/50 rounded-xl p-3 text-slate-200 text-xs focus:ring-2 focus:ring-sky-500 focus:outline-none leading-relaxed"
            />
          ) : (
            <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800/90 text-slate-300 leading-relaxed font-sans text-xs">
              {reportText || "Visualized radiograph demonstrates intact bone contours."}
            </div>
          )}
        </div>

        {/* Attending Physician Notes */}
        <div className="space-y-1.5">
          <label className="text-[11px] font-bold text-slate-300 flex items-center gap-1.5">
            <Stethoscope className="w-3.5 h-3.5 text-emerald-400" />
            <span>Attending Orthopedic Management & Immobilization Notes</span>
          </label>
          <textarea
            disabled={isSigned}
            rows={2}
            value={clinicalNotes}
            onChange={(e) => setClinicalNotes(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-slate-200 text-xs focus:ring-1 focus:ring-emerald-500 focus:outline-none disabled:opacity-75 leading-relaxed"
            placeholder={isSigned ? "Notes sealed with digital signature." : "Enter immobilization orders, splint type, ortho follow-up timeline..."}
          />
        </div>

        {/* Digital Signature Stamp Box */}
        {isSigned && (
          <div className="p-3.5 rounded-xl bg-emerald-950/30 border border-emerald-500/40 text-emerald-200 flex items-start space-x-3">
            <Award className="w-5 h-5 text-emerald-400 flex-shrink-0 mt-0.5" />
            <div className="space-y-1">
              <div className="font-bold text-emerald-300 flex items-center gap-2">
                <span>DIGITALLY VERIFIED & SIGNED OFF</span>
                <span className="text-[10px] bg-emerald-500/20 text-emerald-300 px-2 py-0.2 rounded font-mono">
                  MCI COMPLIANT
                </span>
              </div>
              <p className="text-[11px] text-emerald-100 font-medium">
                {analysis.signed_by || `Dr. ${currentUser?.full_name || 'Attending Clinician'} (${currentUser?.registration_number || 'MCI-VERIFIED'})`}
              </p>
              <p className="text-[10px] text-emerald-400/80 font-mono">
                Stamped: {analysis.signed_at ? new Date(analysis.signed_at).toLocaleString() : 'Verified Timestamp'}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Footer Actions */}
      <div className="p-4 bg-slate-950/80 border-t border-slate-800 flex items-center justify-between gap-2 flex-wrap">
        <div className="flex items-center space-x-2">
          {/* Download Clinical PDF */}
          <button
            onClick={onDownloadPdf}
            className="flex items-center space-x-1 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition"
            title="Download stamped ReportLab PDF report"
          >
            <FileDown className="w-3.5 h-3.5 text-sky-400" />
            <span>PDF</span>
          </button>

          {/* Email Dispatch Button */}
          <button
            onClick={() => setEmailModalOpen(true)}
            className="flex items-center space-x-1 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition"
            title="Dispatch stamped PDF report via email"
          >
            <Mail className="w-3.5 h-3.5 text-sky-400" />
            <span>Email</span>
          </button>

          {/* FHIR Export Button */}
          <button
            onClick={handleOpenFhir}
            className="flex items-center space-x-1 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold border border-slate-700 transition"
            title="View HL7 FHIR DiagnosticReport Resource JSON"
          >
            <Database className="w-3.5 h-3.5 text-purple-400" />
            <span>FHIR</span>
          </button>
        </div>

        <div className="flex items-center space-x-2">
          {isEditing && !isSigned && (
            <button
              onClick={handleSaveDraft}
              disabled={isSaving}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold border border-slate-700 transition"
            >
              <Save className="w-3.5 h-3.5" />
              <span>Save Draft</span>
            </button>
          )}

          {!isSigned ? (
            <button
              onClick={handleSignOff}
              disabled={isSaving}
              className="flex items-center space-x-1.5 px-4 py-1.5 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold shadow-lg shadow-emerald-900/40 transition disabled:opacity-50"
            >
              <Award className="w-4 h-4" />
              <span>{isSaving ? "Stamping..." : "Approve & Sign"}</span>
            </button>
          ) : (
            <div className="flex items-center space-x-1.5 text-xs text-emerald-400 font-semibold px-3 py-1 bg-emerald-500/10 rounded-lg border border-emerald-500/20">
              <CheckCircle className="w-4 h-4" />
              <span>Finalized</span>
            </div>
          )}
        </div>
      </div>

      {/* Email Dispatch Modal */}
      {emailModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="relative w-full max-w-sm bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden p-5 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2 text-sky-400 font-bold text-sm">
                <Mail className="w-4 h-4" />
                <span>Dispatch Signed PDF Report</span>
              </div>
              <button onClick={() => setEmailModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSendEmail} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-300 font-semibold mb-1">Recipient Clinician / Patient Email</label>
                <input
                  type="email"
                  required
                  placeholder="trauma.ortho@hospital.org"
                  value={recipientEmail}
                  onChange={(e) => setRecipientEmail(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-slate-100 focus:ring-1 focus:ring-sky-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-semibold mb-1">Urgent Triage Instructions (Optional)</label>
                <textarea
                  rows={2}
                  placeholder="Immediate posterior splinting required..."
                  value={dispatchNotes}
                  onChange={(e) => setDispatchNotes(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg p-2.5 text-slate-100 focus:ring-1 focus:ring-sky-500"
                />
              </div>

              {dispatchStatus === 'success' && (
                <div className="p-2 bg-emerald-950 border border-emerald-500 text-emerald-300 rounded text-center">
                  PDF Report Dispatched Successfully!
                </div>
              )}

              <div className="flex items-center justify-end space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setEmailModalOpen(false)}
                  className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isDispatching}
                  className="flex items-center space-x-1.5 px-4 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-bold"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>{isDispatching ? 'Sending...' : 'Send Email'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* FHIR JSON Export Modal */}
      {fhirModalOpen && fhirData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="relative w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden p-5 space-y-3">
            <div className="flex items-center justify-between border-b border-slate-800 pb-2">
              <div className="flex items-center space-x-2 text-purple-400 font-bold text-sm">
                <Database className="w-4 h-4" />
                <span>HL7 FHIR R4 DiagnosticReport Resource</span>
              </div>
              <button onClick={() => setFhirModalOpen(false)} className="text-slate-400 hover:text-white">
                <X className="w-4 h-4" />
              </button>
            </div>
            <pre className="bg-slate-950 p-3 rounded-lg border border-slate-800 text-[10px] font-mono text-purple-300 max-h-80 overflow-y-auto">
              {JSON.stringify(fhirData, null, 2)}
            </pre>
            <div className="flex justify-end">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(JSON.stringify(fhirData, null, 2));
                  alert('FHIR JSON copied to clipboard!');
                }}
                className="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white font-semibold rounded-lg text-xs"
              >
                Copy FHIR JSON
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
