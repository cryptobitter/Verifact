import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import PacsViewer from './components/PacsViewer';
import SampleShowcase from './components/SampleShowcase';
import ReportReviewCard from './components/ReportReviewCard';
import DashboardHistory from './components/DashboardHistory';
import AuthModal from './components/AuthModal';
import UploadModal from './components/UploadModal';
import { api, getCurrentUser, setCurrentUser } from './services/api';
import {
  Sparkles,
  AlertCircle,
  CheckCircle,
  FileDown,
  Info,
  Tv2,
  Layers,
  ArrowRight
} from 'lucide-react';

export default function App() {
  const [currentUser, setUser] = useState(getCurrentUser());
  const [activeTab, setActiveTab] = useState('workstation'); // 'workstation' | 'registry'

  const [currentAnalysis, setCurrentAnalysis] = useState(null);
  const [activeSampleId, setActiveSampleId] = useState('distal_radius_fracture');
  const [history, setHistory] = useState([]);

  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [toast, setToast] = useState(null);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  // Ensure an authenticated session exists (auto-demo login if no user present)
  const ensureAuth = async () => {
    let user = getCurrentUser();
    if (!user) {
      try {
        const demoEmail = 'dr.sharma@verifact.hospital';
        const demoPass = 'Verifact2026!';
        try {
          const authData = await api.login(demoEmail, demoPass);
          setUser(authData.user);
          return authData.user;
        } catch {
          await api.signup({
            email: demoEmail,
            password: demoPass,
            full_name: 'Ananya Sharma',
            registration_number: 'NMC/2018/049182',
            specialization: 'Orthopedic Trauma & Musculoskeletal Radiology',
            qualification: 'MBBS, MS (Orthopedics), DNB, MCh',
            hospital: 'National Trauma & Emergency Institute',
            department: 'Department of Orthopedic Surgery',
            experience: '12 Years',
            phone: '+91 98110 23456',
            city: 'New Delhi',
            state: 'Delhi',
            country: 'India'
          });
          const authData = await api.login(demoEmail, demoPass);
          setUser(authData.user);
          return authData.user;
        }
      } catch (err) {
        console.warn('Auto auth error:', err);
      }
    }
    return user;
  };

  // Load history from backend
  const loadHistory = async () => {
    try {
      const data = await api.getHistory();
      setHistory(data);
    } catch (err) {
      console.warn('Could not load history:', err);
    }
  };

  // Run 1-Click sample case
  const handleSelectSample = async (sampleId) => {
    setActiveSampleId(sampleId);
    setIsAnalyzing(true);
    try {
      await ensureAuth();
      const result = await api.analyzeSample(sampleId);
      setCurrentAnalysis(result);
      await loadHistory();
      showToast(`Analyzed ${result.bone || 'Showcase'} radiograph successfully.`);
    } catch (err) {
      console.error('Analysis failed:', err);
      showToast(err.message || 'Analysis failed.', 'error');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Run custom file or dual-view upload
  const handleUploadFile = async (payload) => {
    setIsAnalyzing(true);
    setUploadModalOpen(false);
    try {
      await ensureAuth();
      let result;
      if (payload instanceof FormData) {
        result = await api.analyzeDualView(payload);
      } else {
        result = await api.analyzeFile(payload);
      }
      setCurrentAnalysis(result);
      setActiveSampleId(null);
      await loadHistory();
      setActiveTab('workstation');
      showToast(`Dual-engine analysis completed for ${result.bone || 'uploaded study'}.`);
    } catch (err) {
      console.error('Upload analysis failed:', err);
      showToast(err.message || 'Failed to analyze uploaded file.', 'error');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Doctor Review & Digital Sign-off
  const handleSaveAndSign = async (updateData) => {
    if (!currentAnalysis) return;
    setIsSaving(true);
    try {
      const updated = await api.updateAndSignAnalysis(currentAnalysis.id, updateData);
      setCurrentAnalysis(updated);
      await loadHistory();
      if (updateData.signed_off) {
        showToast('Clinical report approved & stamped with physician credentials!');
      } else {
        showToast('Report draft updated successfully.');
      }
    } catch (err) {
      console.error('Sign-off failed:', err);
      showToast(err.message || 'Failed to update report.', 'error');
    } finally {
      setIsSaving(false);
    }
  };

  // Download PDF Report
  const handleDownloadPdf = async (analysisId) => {
    const targetId = analysisId || currentAnalysis?.id;
    if (!targetId) return;

    try {
      showToast('Generating stamped clinical PDF...');
      const blob = await api.getPdfBlob(targetId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `VERIFACT_Analysis_${targetId}_Report.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      showToast('Clinical PDF report downloaded.');
    } catch (err) {
      console.error('PDF download error:', err);
      showToast('Could not download PDF report.', 'error');
    }
  };

  // Select historical record to view in workstation
  const handleSelectRecord = async (recordId) => {
    try {
      const record = await api.getAnalysis(recordId);
      setCurrentAnalysis(record);
      setActiveTab('workstation');
      showToast(`Loaded Scan FRX-${String(record.id).padStart(6, '0')} in PACS viewer.`);
    } catch (err) {
      showToast('Failed to load scan record.', 'error');
    }
  };

  // Initial load
  useEffect(() => {
    const initApp = async () => {
      await ensureAuth();
      await loadHistory();
      // Auto run default sample on first launch
      handleSelectSample('distal_radius_fracture');
    };
    initApp();
  }, []);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Toast Notification Banner */}
      {toast && (
        <div
          className={`fixed bottom-5 right-5 z-50 flex items-center space-x-2.5 px-4 py-3 rounded-xl shadow-2xl border text-xs font-semibold backdrop-blur-md transition transform ${
            toast.type === 'error'
              ? 'bg-rose-950/90 border-rose-500/40 text-rose-200'
              : 'bg-emerald-950/90 border-emerald-500/40 text-emerald-200'
          }`}
        >
          {toast.type === 'error' ? (
            <AlertCircle className="w-4 h-4 text-rose-400" />
          ) : (
            <CheckCircle className="w-4 h-4 text-emerald-400" />
          )}
          <span>{toast.message}</span>
        </div>
      )}

      {/* Main Navigation */}
      <Navbar
        currentUser={currentUser}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenAuth={() => setAuthModalOpen(true)}
        onLogout={() => {
          api.login('', ''); // clears token
          setUser(null);
          showToast('Signed out of clinician workstation.', 'info');
        }}
        onOpenUpload={() => setUploadModalOpen(true)}
      />

      {/* Main Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 flex flex-col space-y-6">
        {/* 1-Click Showcase Gallery (Always visible at the top for instant testing) */}
        <SampleShowcase
          onSelectSample={handleSelectSample}
          activeSampleId={activeSampleId}
          isAnalyzing={isAnalyzing}
        />

        {/* Tab 1: PACS-Lite Workstation View */}
        {activeTab === 'workstation' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1 items-stretch">
            {/* Left Column: Interactive PACS Viewer (7 cols) */}
            <div className="lg:col-span-7 flex flex-col min-h-[580px]">
              {currentAnalysis ? (
                <PacsViewer
                  rawImageUrl={currentAnalysis.image_url}
                  heatmapUrl={currentAnalysis.heatmap_url}
                  lateralImageUrl={currentAnalysis.lateral_image_url}
                  lateralHeatmapUrl={currentAnalysis.lateral_heatmap_url}
                  scanTitle={`FRX-${String(currentAnalysis.id).padStart(6, '0')}`}
                  boneInfo={currentAnalysis.bone}
                  confidence={currentAnalysis.confidence}
                  pixelSpacing={currentAnalysis.pixel_spacing}
                  initialAnnotations={currentAnalysis.annotations}
                  onSaveAnnotations={(measurements) => {
                    handleSaveAndSign({ annotations: JSON.stringify({ measurements }) });
                  }}
                />
              ) : (
                <div className="flex-1 bg-slate-900/60 border border-slate-800 rounded-2xl flex flex-col items-center justify-center p-8 text-slate-500 text-xs">
                  <Tv2 className="w-10 h-10 mb-3 text-slate-600 stroke-[1.5]" />
                  <p className="font-semibold text-slate-300 mb-1">No Scan Active</p>
                  <p>Click any showcase case above or upload an X-ray to inspect.</p>
                </div>
              )}
            </div>

            {/* Right Column: Human-in-the-Loop Report Review & Digital Signature (5 cols) */}
            <div className="lg:col-span-5 flex flex-col min-h-[580px]">
              {currentAnalysis ? (
                <ReportReviewCard
                  analysis={currentAnalysis}
                  currentUser={currentUser}
                  onSaveAndSign={handleSaveAndSign}
                  onDownloadPdf={() => handleDownloadPdf()}
                  isSaving={isSaving}
                />
              ) : (
                <div className="flex-1 bg-slate-900/60 border border-slate-800 rounded-2xl flex flex-col items-center justify-center p-8 text-slate-500 text-xs">
                  <p>Awaiting radiograph selection...</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 2: Scan Registry & Historical KPI View */}
        {activeTab === 'registry' && (
          <DashboardHistory
            history={history}
            onSelectRecord={handleSelectRecord}
            onDownloadPdf={handleDownloadPdf}
            currentId={currentAnalysis?.id}
          />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/80 py-4 px-6 text-center text-[11px] text-slate-500 select-none">
        <p>
          VERIFACT v1.0 • Verified Fracture Radiology AI Clinical Co-Pilot & PACS Workstation • Enforcing Human-in-the-Loop Physician Verification
        </p>
      </footer>

      {/* Modals */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        onAuthSuccess={async () => {
          const user = await api.getProfile();
          setUser(user);
          showToast(`Welcome Dr. ${user.full_name || 'Clinician'}`);
        }}
      />

      <UploadModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        onUploadFile={handleUploadFile}
        isAnalyzing={isAnalyzing}
      />
    </div>
  );
}
