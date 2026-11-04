import React, { useState, useRef, useEffect } from 'react';
import {
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Sliders,
  Sun,
  Contrast,
  Layers,
  SplitSquareVertical,
  Eye,
  Crosshair,
  Sparkles,
  Ruler,
  Compass,
  ArrowUpRight,
  Trash2,
  Check,
  Columns
} from 'lucide-react';

export default function PacsViewer({
  rawImageUrl,
  heatmapUrl,
  lateralImageUrl,
  lateralHeatmapUrl,
  scanTitle = "Musculoskeletal Radiograph",
  boneInfo,
  confidence,
  initialAnnotations,
  onSaveAnnotations
}) {
  // Image adjustments
  const [brightness, setBrightness] = useState(100);
  const [contrast, setContrast] = useState(100);
  const [isInverted, setIsInverted] = useState(false);
  const [heatmapAlpha, setHeatmapAlpha] = useState(65);

  // Transform (Zoom & Pan)
  const [zoom, setZoom] = useState(1.0);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // View modes
  const [viewMode, setViewMode] = useState('curtain'); // 'curtain' | 'overlay' | 'raw'
  const [projectionTab, setProjectionTab] = useState('ap'); // 'ap' | 'lateral' | 'dual'
  const [curtainPos, setCurtainPos] = useState(50);
  const [isWiping, setIsWiping] = useState(false);
  const [showHud, setShowHud] = useState(true);

  // Interactive Measurement & Caliper Tools
  const [activeTool, setActiveTool] = useState('none'); // 'none' | 'ruler' | 'angle' | 'arrow'
  const [measurements, setMeasurements] = useState([]);
  const [draftPoints, setDraftPoints] = useState([]);

  const containerRef = useRef(null);

  // Load initial annotations if any
  useEffect(() => {
    if (initialAnnotations) {
      try {
        const parsed = typeof initialAnnotations === 'string' ? JSON.parse(initialAnnotations) : initialAnnotations;
        if (parsed?.measurements) {
          setMeasurements(parsed.measurements);
        }
      } catch (e) {
        // ignore parse error
      }
    }
  }, [initialAnnotations]);

  // Reset transforms
  const resetAll = () => {
    setBrightness(100);
    setContrast(100);
    setIsInverted(false);
    setZoom(1.0);
    setPan({ x: 0, y: 0 });
    setCurtainPos(50);
  };

  const handleZoom = (delta) => {
    setZoom((prev) => Math.min(Math.max(0.5, prev + delta), 4.0));
  };

  const handleWheel = (e) => {
    e.preventDefault();
    const delta = e.deltaY < 0 ? 0.15 : -0.15;
    handleZoom(delta);
  };

  // Canvas Mouse & Interaction handlers
  const getRelativeCoords = (e) => {
    if (!containerRef.current) return { x: 0, y: 0 };
    const rect = containerRef.current.getBoundingClientRect();
    const clientX = e.clientX - rect.left;
    const clientY = e.clientY - rect.top;
    // Map back to unzoomed / unpanned image coordinates
    const cx = rect.width / 2;
    const cy = rect.height / 2;
    const x = (clientX - cx - pan.x) / zoom + cx;
    const y = (clientY - cy - pan.y) / zoom + cy;
    return { x, y };
  };

  const handleCanvasClick = (e) => {
    if (e.target.closest('.curtain-handle') || isDragging || isWiping) return;

    if (activeTool === 'ruler') {
      const pt = getRelativeCoords(e);
      if (draftPoints.length === 0) {
        setDraftPoints([pt]);
      } else {
        const p1 = draftPoints[0];
        const p2 = pt;
        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;
        const pxDist = Math.sqrt(dx * dx + dy * dy);
        const mmDist = (pxDist * 0.18).toFixed(1); // Standard 0.18 mm/px radiograph pixel spacing

        const newMeas = {
          id: Date.now(),
          type: 'ruler',
          points: [p1, p2],
          value: `${mmDist} mm`,
          label: `Displacement: ${mmDist} mm`
        };
        const updated = [...measurements, newMeas];
        setMeasurements(updated);
        setDraftPoints([]);
        if (onSaveAnnotations) onSaveAnnotations(updated);
      }
    } else if (activeTool === 'angle') {
      const pt = getRelativeCoords(e);
      if (draftPoints.length < 2) {
        setDraftPoints([...draftPoints, pt]);
      } else {
        const [p1, p2] = draftPoints;
        const p3 = pt;
        // Vertex is p2
        const v1 = { x: p1.x - p2.x, y: p1.y - p2.y };
        const v2 = { x: p3.x - p2.x, y: p3.y - p2.y };
        const dot = v1.x * v2.x + v1.y * v2.y;
        const mag1 = Math.sqrt(v1.x * v1.x + v1.y * v1.y);
        const mag2 = Math.sqrt(v2.x * v2.x + v2.y * v2.y);
        const angleRad = Math.acos(Math.max(-1, Math.min(1, dot / (mag1 * mag2 || 1e-5))));
        const angleDeg = ((angleRad * 180) / Math.PI).toFixed(1);

        const newMeas = {
          id: Date.now(),
          type: 'angle',
          points: [p1, p2, p3],
          value: `${angleDeg}°`,
          label: `Dorsal Tilt / Angle: ${angleDeg}°`
        };
        const updated = [...measurements, newMeas];
        setMeasurements(updated);
        setDraftPoints([]);
        if (onSaveAnnotations) onSaveAnnotations(updated);
      }
    } else if (activeTool === 'arrow') {
      const pt = getRelativeCoords(e);
      if (draftPoints.length === 0) {
        setDraftPoints([pt]);
      } else {
        const p1 = draftPoints[0];
        const newMeas = {
          id: Date.now(),
          type: 'arrow',
          points: [p1, pt],
          value: 'Pathology Site',
          label: 'Cortical Step-off'
        };
        const updated = [...measurements, newMeas];
        setMeasurements(updated);
        setDraftPoints([]);
        if (onSaveAnnotations) onSaveAnnotations(updated);
      }
    }
  };

  const handleMouseDown = (e) => {
    if (e.target.closest('.curtain-handle') || activeTool !== 'none') return;
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e) => {
    if (isWiping && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const pos = ((e.clientX - rect.left) / rect.width) * 100;
      setCurtainPos(Math.min(Math.max(0, pos), 100));
    } else if (isDragging) {
      setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setIsWiping(false);
  };

  useEffect(() => {
    const handleGlobalMouseUp = () => {
      setIsDragging(false);
      setIsWiping(false);
    };
    window.addEventListener('mouseup', handleGlobalMouseUp);
    return () => window.removeEventListener('mouseup', handleGlobalMouseUp);
  }, []);

  const deleteMeasurement = (id) => {
    const updated = measurements.filter((m) => m.id !== id);
    setMeasurements(updated);
    if (onSaveAnnotations) onSaveAnnotations(updated);
  };

  const clearAllMeasurements = () => {
    setMeasurements([]);
    setDraftPoints([]);
    if (onSaveAnnotations) onSaveAnnotations([]);
  };

  // Filter styling for PACS window leveling and negative film inversion
  const filterStyle = {
    filter: `brightness(${brightness}%) contrast(${contrast}%) ${isInverted ? 'invert(100%) hue-rotate(180deg)' : ''}`,
    transition: isDragging ? 'none' : 'filter 0.1s ease',
  };

  // Active projection image selection
  const currentRaw = (projectionTab === 'lateral' && lateralImageUrl) ? lateralImageUrl : rawImageUrl;
  const currentHeatmap = (projectionTab === 'lateral' && lateralHeatmapUrl) ? lateralHeatmapUrl : (heatmapUrl || rawImageUrl);

  return (
    <div className="flex flex-col h-full bg-slate-950 border border-slate-800 rounded-2xl overflow-hidden shadow-2xl">
      {/* Top Toolbar */}
      <div className="flex flex-wrap items-center justify-between px-4 py-2.5 bg-slate-900/90 border-b border-slate-800/80 backdrop-blur text-xs select-none gap-2">
        {/* Left: View Mode Tabs & Orthogonal Selector */}
        <div className="flex items-center space-x-2">
          {/* Orthogonal Projection Switcher (if lateral view exists) */}
          {lateralImageUrl && (
            <div className="flex items-center space-x-1 bg-slate-950 p-1 rounded-lg border border-slate-800 font-mono text-[11px]">
              <button
                onClick={() => setProjectionTab('ap')}
                className={`px-2.5 py-1 rounded font-bold transition ${
                  projectionTab === 'ap' ? 'bg-sky-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                AP View
              </button>
              <button
                onClick={() => setProjectionTab('lateral')}
                className={`px-2.5 py-1 rounded font-bold transition ${
                  projectionTab === 'lateral' ? 'bg-sky-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                Lateral View
              </button>
              <button
                onClick={() => setProjectionTab('dual')}
                className={`flex items-center space-x-1 px-2.5 py-1 rounded font-bold transition ${
                  projectionTab === 'dual' ? 'bg-emerald-600 text-white' : 'text-slate-400 hover:text-white'
                }`}
              >
                <Columns className="w-3 h-3" />
                <span>Dual View</span>
              </button>
            </div>
          )}

          {/* View Modes */}
          {projectionTab !== 'dual' && (
            <div className="flex items-center space-x-1 bg-slate-950/80 p-1 rounded-lg border border-slate-800">
              <button
                onClick={() => setViewMode('curtain')}
                className={`flex items-center space-x-1 px-2.5 py-1 rounded-md font-medium transition ${
                  viewMode === 'curtain' ? 'bg-sky-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                }`}
                title="Split Curtain comparison"
              >
                <SplitSquareVertical className="w-3.5 h-3.5" />
                <span>Curtain</span>
              </button>
              <button
                onClick={() => setViewMode('overlay')}
                className={`flex items-center space-x-1 px-2.5 py-1 rounded-md font-medium transition ${
                  viewMode === 'overlay' ? 'bg-sky-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                }`}
                title="Heatmap Overlay"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Heatmap</span>
              </button>
              <button
                onClick={() => setViewMode('raw')}
                className={`flex items-center space-x-1 px-2.5 py-1 rounded-md font-medium transition ${
                  viewMode === 'raw' ? 'bg-sky-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
                }`}
                title="Raw Film"
              >
                <Eye className="w-3.5 h-3.5" />
                <span>Film</span>
              </button>
            </div>
          )}
        </div>

        {/* Center: Clinical Measurement & Caliper Tools */}
        <div className="flex items-center space-x-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
          <button
            onClick={() => {
              setActiveTool(activeTool === 'none' ? 'none' : 'none');
              setDraftPoints([]);
            }}
            className={`p-1.5 rounded transition ${activeTool === 'none' ? 'bg-slate-800 text-white' : 'text-slate-400 hover:text-white'}`}
            title="Pan / Zoom Viewport Mode"
          >
            <Crosshair className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => {
              setActiveTool(activeTool === 'ruler' ? 'none' : 'ruler');
              setDraftPoints([]);
            }}
            className={`flex items-center space-x-1 px-2 py-1 rounded text-[11px] font-semibold transition ${
              activeTool === 'ruler' ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40' : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Caliper Ruler: Click 2 points to calculate bone displacement in mm"
          >
            <Ruler className="w-3.5 h-3.5" />
            <span>Caliper (mm)</span>
          </button>
          <button
            onClick={() => {
              setActiveTool(activeTool === 'angle' ? 'none' : 'angle');
              setDraftPoints([]);
            }}
            className={`flex items-center space-x-1 px-2 py-1 rounded text-[11px] font-semibold transition ${
              activeTool === 'angle' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40' : 'text-slate-400 hover:text-slate-200'
            }`}
            title="3-Point Angle: Measure Cobb's angle / Dorsal tilt in degrees"
          >
            <Compass className="w-3.5 h-3.5" />
            <span>Angle (°)</span>
          </button>
          <button
            onClick={() => {
              setActiveTool(activeTool === 'arrow' ? 'none' : 'arrow');
              setDraftPoints([]);
            }}
            className={`flex items-center space-x-1 px-2 py-1 rounded text-[11px] font-semibold transition ${
              activeTool === 'arrow' ? 'bg-rose-500/20 text-rose-300 border border-rose-500/40' : 'text-slate-400 hover:text-slate-200'
            }`}
            title="Clinical Pointer: Mark pathology location"
          >
            <ArrowUpRight className="w-3.5 h-3.5" />
            <span>Pointer</span>
          </button>
          {measurements.length > 0 && (
            <button
              onClick={clearAllMeasurements}
              className="p-1 hover:bg-rose-950/50 rounded text-slate-500 hover:text-rose-400 transition"
              title="Clear all measurements"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* Right: Window/Level & Film Inversion */}
        <div className="flex items-center space-x-3 text-slate-300">
          <button
            onClick={() => setIsInverted(!isInverted)}
            className={`flex items-center space-x-1 px-2 py-1 rounded-lg border text-[11px] transition ${
              isInverted ? 'bg-amber-500/20 text-amber-300 border-amber-500/40' : 'bg-slate-800/60 text-slate-300 border-slate-700/60 hover:bg-slate-800'
            }`}
            title="Invert negative density"
          >
            <Contrast className="w-3.5 h-3.5" />
            <span>Invert</span>
          </button>

          <div className="flex items-center space-x-1.5">
            <Sun className="w-3.5 h-3.5 text-slate-400" />
            <input
              type="range"
              min="40"
              max="180"
              value={brightness}
              onChange={(e) => setBrightness(Number(e.target.value))}
              className="w-16 accent-sky-500 h-1 bg-slate-800 rounded-lg cursor-pointer"
              title={`WL: ${brightness}%`}
            />
          </div>

          <div className="flex items-center space-x-1.5">
            <Sliders className="w-3.5 h-3.5 text-slate-400" />
            <input
              type="range"
              min="50"
              max="220"
              value={contrast}
              onChange={(e) => setContrast(Number(e.target.value))}
              className="w-16 accent-sky-500 h-1 bg-slate-800 rounded-lg cursor-pointer"
              title={`WW: ${contrast}%`}
            />
          </div>

          <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg p-0.5">
            <button onClick={() => handleZoom(-0.2)} className="p-1 hover:bg-slate-800 rounded text-slate-300" title="Zoom Out">
              <ZoomOut className="w-3 h-3" />
            </button>
            <span className="font-mono text-[10px] px-1 text-slate-300 w-10 text-center font-bold">
              {Math.round(zoom * 100)}%
            </span>
            <button onClick={() => handleZoom(0.2)} className="p-1 hover:bg-slate-800 rounded text-slate-300" title="Zoom In">
              <ZoomIn className="w-3 h-3" />
            </button>
          </div>

          <button onClick={resetAll} className="p-1.5 hover:bg-slate-800 rounded-lg border border-slate-800 text-slate-400" title="Reset Viewport">
            <RotateCcw className="w-3 h-3" />
          </button>
        </div>
      </div>

      {/* Main Interactive Canvas Area */}
      <div
        ref={containerRef}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onClick={handleCanvasClick}
        className={`relative flex-1 bg-black overflow-hidden select-none flex items-center justify-center min-h-[460px] ${
          activeTool !== 'none' ? 'cursor-crosshair' : isDragging ? 'cursor-grabbing' : 'cursor-grab'
        }`}
      >
        {/* Reticle HUD */}
        {showHud && (
          <div className="absolute top-4 left-4 z-20 pointer-events-none bg-slate-950/75 border border-slate-800/80 backdrop-blur px-3 py-2 rounded-lg font-mono text-[11px] text-slate-300 space-y-1">
            <div className="flex items-center space-x-2 text-sky-400 font-semibold">
              <Crosshair className="w-3 h-3 animate-pulse" />
              <span>PACS-LITE WORKSTATION</span>
            </div>
            <div>SCAN: <span className="text-white">{scanTitle}</span></div>
            {boneInfo && <div>ANATOMY: <span className="text-sky-300">{boneInfo}</span></div>}
            {confidence && <div>AI CONF: <span className="text-emerald-400">{Math.round(confidence * 100)}%</span></div>}
            <div className="text-[10px] text-slate-500">
              PROJECTION: <span className="text-amber-400 uppercase">{projectionTab}</span> | TOOL: <span className="text-sky-400 uppercase">{activeTool}</span>
            </div>
          </div>
        )}

        {/* Mode: Standard Viewport (AP or Lateral) */}
        {projectionTab !== 'dual' ? (
          <div
            className="relative inline-block max-w-full max-h-full"
            style={{
              transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
              transformOrigin: 'center center',
              transition: isDragging ? 'none' : 'transform 0.05s ease-out',
            }}
          >
            {/* Raw Radiograph */}
            <img
              src={currentRaw}
              alt="Plain Musculoskeletal Radiograph"
              style={filterStyle}
              className="max-h-[530px] w-auto object-contain rounded pointer-events-none block shadow-2xl"
              draggable={false}
            />

            {/* Mode: Overlay */}
            {viewMode === 'overlay' && (
              <img
                src={currentHeatmap}
                alt="Grad-CAM Saliency"
                style={{ ...filterStyle, opacity: heatmapAlpha / 100 }}
                className="absolute inset-0 max-h-[530px] w-auto object-contain pointer-events-none mix-blend-screen"
                draggable={false}
              />
            )}

            {/* Mode: Curtain */}
            {viewMode === 'curtain' && (
              <div
                className="absolute inset-0 overflow-hidden pointer-events-none"
                style={{ clipPath: `inset(0 0 0 ${curtainPos}%)` }}
              >
                <img
                  src={currentHeatmap}
                  alt="Grad-CAM Heatmap"
                  style={filterStyle}
                  className="max-h-[530px] w-auto object-contain pointer-events-none"
                  draggable={false}
                />
              </div>
            )}

            {/* SVG Measurement Overlay (Rulers, Angles, Arrows) */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none z-20">
              {/* Existing Stored Measurements */}
              {measurements.map((m) => {
                if (m.type === 'ruler') {
                  const [p1, p2] = m.points;
                  const mx = (p1.x + p2.x) / 2;
                  const my = (p1.y + p2.y) / 2;
                  return (
                    <g key={m.id}>
                      <line x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke="#fbbf24" strokeWidth="2.5" strokeDasharray="3 3" />
                      <circle cx={p1.x} cy={p1.y} r="4" fill="#fbbf24" />
                      <circle cx={p2.x} cy={p2.y} r="4" fill="#fbbf24" />
                      <rect x={mx - 28} y={my - 10} width="56" height="18" rx="4" fill="#0f172a" stroke="#fbbf24" strokeWidth="1" />
                      <text x={mx} y={my + 3} fill="#fbbf24" fontSize="10" fontWeight="bold" textAnchor="middle">{m.value}</text>
                    </g>
                  );
                }
                if (m.type === 'angle') {
                  const [p1, p2, p3] = m.points;
                  return (
                    <g key={m.id}>
                      <line x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke="#34d399" strokeWidth="2" />
                      <line x1={p2.x} y1={p2.y} x2={p3.x} y2={p3.y} stroke="#34d399" strokeWidth="2" />
                      <circle cx={p2.x} cy={p2.y} r="5" fill="#34d399" />
                      <rect x={p2.x + 8} y={p2.y - 10} width="50" height="18" rx="4" fill="#0f172a" stroke="#34d399" strokeWidth="1" />
                      <text x={p2.x + 33} y={p2.y + 3} fill="#34d399" fontSize="10" fontWeight="bold" textAnchor="middle">{m.value}</text>
                    </g>
                  );
                }
                if (m.type === 'arrow') {
                  const [p1, p2] = m.points;
                  return (
                    <g key={m.id}>
                      <defs>
                        <marker id={`arrowhead-${m.id}`} markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
                          <polygon points="0 0, 8 3, 0 6" fill="#f43f5e" />
                        </marker>
                      </defs>
                      <line x1={p1.x} y1={p1.y} x2={p2.x} y2={p2.y} stroke="#f43f5e" strokeWidth="3" markerEnd={`url(#arrowhead-${m.id})`} />
                      <circle cx={p1.x} cy={p1.y} r="3" fill="#f43f5e" />
                    </g>
                  );
                }
                return null;
              })}

              {/* In-progress Draft Points */}
              {draftPoints.map((p, idx) => (
                <circle key={idx} cx={p.x} cy={p.y} r="5" fill="#38bdf8" stroke="#ffffff" strokeWidth="1.5" />
              ))}
            </svg>
          </div>
        ) : (
          /* Mode: Dual Orthogonal Side-by-Side Viewport */
          <div className="flex items-center justify-center space-x-4 max-w-full max-h-full p-4">
            {/* View 1: AP Projection */}
            <div className="flex flex-col items-center bg-slate-900/60 p-2 rounded-xl border border-slate-800">
              <span className="font-mono text-[10px] text-sky-400 font-bold mb-1">PROJECTION 1: AP VIEW</span>
              <img src={rawImageUrl} alt="AP Radiograph" style={filterStyle} className="max-h-[480px] w-auto object-contain rounded" />
            </div>

            {/* View 2: Lateral Projection */}
            <div className="flex flex-col items-center bg-slate-900/60 p-2 rounded-xl border border-slate-800">
              <span className="font-mono text-[10px] text-emerald-400 font-bold mb-1">PROJECTION 2: LATERAL VIEW</span>
              <img src={lateralImageUrl} alt="Lateral Radiograph" style={filterStyle} className="max-h-[480px] w-auto object-contain rounded" />
            </div>
          </div>
        )}

        {/* Curtain Draggable Divider Bar */}
        {viewMode === 'curtain' && projectionTab !== 'dual' && (
          <div
            className="curtain-handle absolute top-0 bottom-0 z-30 cursor-ew-resize flex items-center justify-center pointer-events-auto"
            style={{ left: `${curtainPos}%`, transform: 'translateX(-50%)' }}
            onMouseDown={(e) => {
              e.stopPropagation();
              setIsWiping(true);
            }}
          >
            <div className="w-[2px] h-full bg-gradient-to-b from-sky-400 via-white to-sky-400 shadow-[0_0_12px_rgba(56,189,248,0.8)]" />
            <div className="absolute w-8 h-8 rounded-full bg-slate-900 border-2 border-sky-400 flex items-center justify-center shadow-lg text-sky-400 hover:scale-110 transition active:scale-95">
              <SplitSquareVertical className="w-4 h-4" />
            </div>
          </div>
        )}
      </div>

      {/* Bottom Status & Measurement Tray */}
      <div className="px-4 py-2 bg-slate-900/95 border-t border-slate-800 text-slate-400 text-[11px] flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <span className="flex items-center space-x-1">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-slate-300 font-medium">DICOM Radiograph Pipeline Active</span>
          </span>
          {measurements.length > 0 && (
            <span className="text-sky-300 font-mono">
              • {measurements.length} Clinical Caliper Measurements Placed
            </span>
          )}
        </div>

        {activeTool !== 'none' && (
          <div className="text-amber-300 font-mono text-[11px] bg-amber-500/10 px-2.5 py-0.5 rounded border border-amber-500/20">
            {activeTool === 'ruler' && (draftPoints.length === 0 ? "Click 1st point to start distance caliper" : "Click 2nd point to lock displacement (mm)")}
            {activeTool === 'angle' && `Click vertex ${draftPoints.length + 1} of 3 to calculate angle (°)`}
            {activeTool === 'arrow' && (draftPoints.length === 0 ? "Click start of arrow" : "Click target pathology")}
          </div>
        )}
      </div>
    </div>
  );
}
