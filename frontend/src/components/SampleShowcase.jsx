import React from 'react';
import { Play, ShieldCheck, AlertTriangle, CheckCircle2, Sparkles, Activity } from 'lucide-react';

const STATIC_SAMPLES = [
  {
    id: "distal_radius_fracture",
    title: "Distal Radius Fracture",
    category: "Forearm Trauma",
    anatomy: "Wrist / Forearm (AP)",
    description: "Transverse cortical disruption across distal radial metaphysis with dorsal tilt.",
    severity: "Moderate",
    severityColor: "text-amber-400 bg-amber-500/10 border-amber-500/30",
    image: "/samples/distal_radius_fracture.png"
  },
  {
    id: "normal_femur_control",
    title: "Intact Femur (Control)",
    category: "Normal Control",
    anatomy: "Femur Shaft (AP)",
    description: "Continuous cortical density without fracture, periosteal breach, or step-off.",
    severity: "Normal / None",
    severityColor: "text-emerald-400 bg-emerald-500/10 border-emerald-500/30",
    image: "/samples/normal_femur_control.png"
  },
  {
    id: "clavicle_displaced_fracture",
    title: "Clavicle Displaced Fracture",
    category: "Shoulder Girdle",
    anatomy: "Clavicle (AP)",
    description: "Comminuted mid-shaft cortical disruption with vertical displacement gap.",
    severity: "Severe",
    severityColor: "text-rose-400 bg-rose-500/10 border-rose-500/30",
    image: "/samples/clavicle_displaced_fracture.png"
  },
  {
    id: "scaphoid_hairline_fracture",
    title: "Scaphoid Hairline Fracture",
    category: "Carpal Bones",
    anatomy: "Carpal Scaphoid View",
    description: "Subtle non-displaced radiolucent hairline line traversing scaphoid waist.",
    severity: "Low",
    severityColor: "text-blue-400 bg-blue-500/10 border-blue-500/30",
    image: "/samples/scaphoid_hairline_fracture.png"
  }
];

export default function SampleShowcase({ onSelectSample, activeSampleId, isAnalyzing }) {
  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 backdrop-blur-sm">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2.5">
          <div className="p-2 rounded-lg bg-sky-500/10 border border-sky-500/20 text-sky-400">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              <span>Verified Clinical Showcase Cases</span>
              <span className="text-[10px] bg-sky-500/20 text-sky-300 font-mono px-2 py-0.5 rounded-full border border-sky-500/30">
                1-Click Instant Demo
              </span>
            </h3>
            <p className="text-xs text-slate-400">Demo showcase for interface evaluation and caliper testing [DEMO SAMPLE - not a live analysis]</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {STATIC_SAMPLES.map((sample) => {
          const isCurrent = activeSampleId === sample.id;
          return (
            <div
              key={sample.id}
              onClick={() => !isAnalyzing && onSelectSample(sample.id)}
              className={`group relative rounded-xl border p-3 cursor-pointer transition-all duration-200 flex flex-col justify-between ${
                isCurrent
                  ? 'bg-sky-950/40 border-sky-500/80 shadow-[0_0_20px_rgba(2,132,199,0.25)] ring-1 ring-sky-500'
                  : 'bg-slate-950/60 border-slate-800 hover:border-slate-700 hover:bg-slate-900/80'
              }`}
            >
              {/* Thumbnail with overlay badge */}
              <div className="relative aspect-[4/3] w-full rounded-lg overflow-hidden bg-black mb-3 border border-slate-800/80">
                <img
                  src={sample.image}
                  alt={sample.title}
                  className="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-300 opacity-90 group-hover:opacity-100"
                />
                <div className="absolute top-2 left-2">
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded-md border font-medium ${sample.severityColor}`}>
                    {sample.severity}
                  </span>
                </div>
                <div className="absolute bottom-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-sky-600 text-white rounded-md p-1 shadow-lg">
                  <Play className="w-3.5 h-3.5 fill-current" />
                </div>
              </div>

              {/* Text Info */}
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <h4 className="text-xs font-bold text-slate-200 group-hover:text-sky-300 transition">
                    {sample.title}
                  </h4>
                </div>
                <div className="text-[11px] font-mono text-slate-400 mb-1">{sample.anatomy}</div>
                <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed mb-3">
                  {sample.description}
                </p>
              </div>

              {/* Action Button */}
              <button
                disabled={isAnalyzing}
                className={`w-full py-1.5 px-3 rounded-lg text-xs font-medium flex items-center justify-center space-x-1.5 transition ${
                  isCurrent
                    ? 'bg-sky-600 text-white shadow-md'
                    : 'bg-slate-800/80 hover:bg-sky-600/90 hover:text-white text-slate-300 border border-slate-700/60'
                }`}
              >
                {isAnalyzing && isCurrent ? (
                  <>
                    <Activity className="w-3.5 h-3.5 animate-spin text-sky-300" />
                    <span>Analyzing...</span>
                  </>
                ) : (
                  <>
                    <Play className="w-3 h-3 fill-current" />
                    <span>Run 1-Click Scan</span>
                  </>
                )}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
