import React, { useState, useRef } from 'react';
import { X, Upload, FileImage, AlertCircle, CheckCircle, Sparkles, Columns, User, Activity } from 'lucide-react';

export default function UploadModal({ isOpen, onClose, onUploadFile, isAnalyzing }) {
  if (!isOpen) return null;

  // Primary (AP) view state
  const [apFile, setApFile] = useState(null);
  const [apPreview, setApPreview] = useState(null);
  const [apIsDicom, setApIsDicom] = useState(false);

  // Optional Lateral view state
  const [latFile, setLatFile] = useState(null);
  const [latPreview, setLatPreview] = useState(null);
  const [latIsDicom, setLatIsDicom] = useState(false);
  const [showLateral, setShowLateral] = useState(false);

  // Patient Trauma Demographics
  const [patientId, setPatientId] = useState('');
  const [patientAge, setPatientAge] = useState('');
  const [patientGender, setPatientGender] = useState('Male');
  const [injuryMechanism, setInjuryMechanism] = useState('FOOSH (Fall on outstretched hand)');

  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState('');

  const apInputRef = useRef(null);
  const latInputRef = useRef(null);

  const processSelectedFile = (file) => {
    const isDcm = file.name.toLowerCase().endsWith('.dcm') || file.name.toLowerCase().endsWith('.dicom') || file.type === 'application/dicom';
    const isImg = file.type.startsWith('image/');
    if (!isImg && !isDcm) {
      throw new Error('Please select a valid radiograph image (PNG, JPG, WEBP) or DICOM (.dcm) file.');
    }
    if (file.size > 25 * 1024 * 1024) {
      throw new Error('File size exceeds the 25 MB clinical maximum.');
    }
    return { isDcm, url: isImg ? URL.createObjectURL(file) : null };
  };

  const handleApChange = (file) => {
    if (!file) return;
    try {
      setError('');
      const { isDcm, url } = processSelectedFile(file);
      setApFile(file);
      setApIsDicom(isDcm);
      setApPreview(url);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleLatChange = (file) => {
    if (!file) return;
    try {
      setError('');
      const { isDcm, url } = processSelectedFile(file);
      setLatFile(file);
      setLatIsDicom(isDcm);
      setLatPreview(url);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!apFile) return;

    // Build multipart FormData for dual-view & demographics
    const formData = new FormData();
    formData.append('ap_file', apFile);
    if (latFile) {
      formData.append('lateral_file', latFile);
    }
    if (patientId) formData.append('patient_id', patientId);
    if (patientAge) formData.append('patient_age', patientAge);
    if (patientGender) formData.append('patient_gender', patientGender);
    if (injuryMechanism) formData.append('mechanism_of_injury', injuryMechanism);

    onUploadFile(formData);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm overflow-y-auto">
      <div className="relative w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden my-8">
        {/* Header */}
        <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/70">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 rounded-lg bg-sky-500/10 text-sky-400">
              <Upload className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">Ingest Radiographs & Trauma Case</h3>
              <p className="text-[10px] text-slate-400">Orthogonal bi-planar series (AP + Lateral) & DICOM</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit} className="p-5 space-y-4 text-xs">
          {error && (
            <div className="p-2.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Patient Case Demographics Accordion */}
          <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-xl space-y-2.5">
            <div className="text-[11px] font-bold text-slate-300 flex items-center gap-1.5">
              <User className="w-3.5 h-3.5 text-sky-400" />
              <span>Patient Trauma Demographics (Optional)</span>
            </div>
            <div className="grid grid-cols-3 gap-2">
              <div>
                <label className="text-[10px] text-slate-400 block mb-0.5">Patient / MRN ID</label>
                <input
                  type="text"
                  placeholder="PT-10492"
                  value={patientId}
                  onChange={(e) => setPatientId(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs"
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-400 block mb-0.5">Age</label>
                <input
                  type="number"
                  placeholder="34"
                  value={patientAge}
                  onChange={(e) => setPatientAge(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs"
                />
              </div>
              <div>
                <label className="text-[10px] text-slate-400 block mb-0.5">Gender</label>
                <select
                  value={patientGender}
                  onChange={(e) => setPatientGender(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs"
                >
                  <option value="Male">Male</option>
                  <option value="Female">Female</option>
                  <option value="Other">Other</option>
                </select>
              </div>
            </div>

            <div>
              <label className="text-[10px] text-slate-400 block mb-0.5">Mechanism of Trauma / Injury</label>
              <select
                value={injuryMechanism}
                onChange={(e) => setInjuryMechanism(e.target.value)}
                className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs"
              >
                <option value="FOOSH (Fall on outstretched hand)">FOOSH (Fall on outstretched hand)</option>
                <option value="Direct blunt trauma / Impact blow">Direct blunt trauma / Impact blow</option>
                <option value="High-energy motor vehicle collision">High-energy motor vehicle collision</option>
                <option value="Sports-related twisting / inversion">Sports-related twisting / inversion</option>
                <option value="Low-energy ground level fall (Fragility)">Low-energy ground level fall (Fragility)</option>
                <option value="Crush injury">Crush injury</option>
              </select>
            </div>
          </div>

          {/* Primary View Dropzone: AP Radiograph */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="font-semibold text-slate-300 flex items-center gap-1.5 text-xs">
                <span className="w-2 h-2 rounded-full bg-sky-400" />
                <span>Primary View: AP / PA Radiograph *</span>
              </span>
              <span className="text-[10px] text-slate-500 font-mono">DICOM (.dcm), JPG, PNG</span>
            </div>

            <div
              onClick={() => apInputRef.current?.click()}
              className="border-2 border-dashed border-slate-700 bg-slate-950/60 hover:border-sky-500 rounded-xl p-4 text-center cursor-pointer transition flex flex-col items-center justify-center min-h-[130px]"
            >
              <input
                ref={apInputRef}
                type="file"
                accept="image/*,.dcm,.dicom,application/dicom"
                className="hidden"
                onChange={(e) => handleApChange(e.target.files?.[0])}
              />

              {apPreview ? (
                <div className="relative h-28 flex items-center justify-center">
                  <img src={apPreview} alt="AP Preview" className="max-h-full object-contain rounded border border-slate-800 shadow" />
                </div>
              ) : apIsDicom && apFile ? (
                <div className="text-center py-2">
                  <div className="font-mono font-bold text-sky-400 text-xs mb-1">DICOM DATASET LOADED</div>
                  <p className="text-[11px] text-slate-300 font-mono truncate max-w-[280px]">{apFile.name}</p>
                </div>
              ) : (
                <>
                  <FileImage className="w-6 h-6 text-slate-500 mb-1.5" />
                  <p className="font-medium text-slate-300">Click to select primary AP film</p>
                </>
              )}
            </div>
          </div>

          {/* Toggle for Orthogonal Lateral View */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <button
                type="button"
                onClick={() => setShowLateral(!showLateral)}
                className="text-[11px] text-sky-400 hover:text-sky-300 flex items-center gap-1 font-semibold"
              >
                <Columns className="w-3.5 h-3.5" />
                <span>{showLateral ? "− Hide Orthogonal Lateral View" : "+ Add Orthogonal Lateral View (Recommended)"}</span>
              </button>
            </div>

            {showLateral && (
              <div
                onClick={() => latInputRef.current?.click()}
                className="border-2 border-dashed border-slate-700 bg-slate-950/60 hover:border-emerald-500 rounded-xl p-4 text-center cursor-pointer transition flex flex-col items-center justify-center min-h-[110px]"
              >
                <input
                  ref={latInputRef}
                  type="file"
                  accept="image/*,.dcm,.dicom,application/dicom"
                  className="hidden"
                  onChange={(e) => handleLatChange(e.target.files?.[0])}
                />

                {latPreview ? (
                  <div className="relative h-24 flex items-center justify-center">
                    <img src={latPreview} alt="Lateral Preview" className="max-h-full object-contain rounded border border-slate-800 shadow" />
                  </div>
                ) : latIsDicom && latFile ? (
                  <div className="text-center py-2">
                    <div className="font-mono font-bold text-emerald-400 text-xs mb-1">LATERAL DICOM LOADED</div>
                    <p className="text-[11px] text-slate-300 font-mono truncate max-w-[280px]">{latFile.name}</p>
                  </div>
                ) : (
                  <>
                    <FileImage className="w-5 h-5 text-slate-500 mb-1" />
                    <p className="font-medium text-slate-300">Click to select Lateral view</p>
                  </>
                )}
              </div>
            )}
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end space-x-2 pt-2 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!apFile || isAnalyzing}
              className="px-5 py-2 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-bold shadow-lg shadow-sky-600/30 transition disabled:opacity-50 flex items-center space-x-1.5"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>{isAnalyzing ? 'Triage Running...' : 'Execute Bi-Planar AI Triage'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
