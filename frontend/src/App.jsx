import React, { useState, useEffect } from 'react';
import {
  Layers,
  Image as ImageIcon,
  Crosshair,
  Play,
  Satellite,
  Clock,
  Radio,
  Copy,
  Check,
  AlertCircle,
  Activity,
  Compass,
  FileText,
  Mountain,
  BarChart3,
  ChevronLeft,
  ChevronRight,
  Info
} from 'lucide-react';
import ImageViewer from './components/ImageViewer';
import MatchVisualizer from './components/MatchVisualizer';
import PipelineVisualizer from './components/PipelineVisualizer';
import ComparisonModes from './components/ComparisonModes';
import DemVisualizer from './components/DemVisualizer';
import { apiService } from './services/apiService';
import './App.css';

function App() {
  const [activeTab, setActiveTab] = useState('raw');
  const [sessionId, setSessionId] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [copiedSession, setCopiedSession] = useState(false);
  const [showTelemetry, setShowTelemetry] = useState(false);
  const [railCollapsed, setRailCollapsed] = useState(false);
  const [activeSpecTab, setActiveSpecTab] = useState('benchmarks');
  const [utcTime, setUtcTime] = useState('');
  const [telemetryLogs, setTelemetryLogs] = useState([
    { time: 'INIT', msg: 'Orbital Ground Station telemetry initialized.' },
    { time: 'READY', msg: 'FastAPI mathematical solver listening on port 8001.' }
  ]);

  const [pipelineState, setPipelineState] = useState({
    stage: 'raw',
    progress: 0,
    metrics: {
      rmse: '--',
      inliers: '--',
      total_matches: '--',
      model: '--',
      dossier_index: null,
      H_matrix: null
    }
  });

  const [files, setFiles] = useState({ source: null, reference: null });

  // Live UTC Clock
  useEffect(() => {
    const updateClock = () => {
      const now = new Date();
      setUtcTime(now.toISOString().substring(11, 19) + ' UTC');
    };
    updateClock();
    const timer = setInterval(updateClock, 1000);
    return () => clearInterval(timer);
  }, []);

  const addLog = (msg) => {
    const time = new Date().toISOString().substring(14, 19);
    setTelemetryLogs(prev => [{ time, msg }, ...prev.slice(0, 19)]);
  };

  // WebSocket Telemetry Connection
  useEffect(() => {
    let socket = null;
    if (sessionId && isProcessing) {
      addLog(`Connecting telemetry socket for session ${sessionId.substring(0, 8)}...`);
      socket = new WebSocket(apiService.getWebSocketUrl(sessionId));

      socket.onopen = () => {
        addLog('Telemetry bridge connected. Commencing orbital pipeline.');
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          addLog(`Telemetry stage transition: ${data.stage.toUpperCase()} (${data.progress}%)`);

          setPipelineState(prev => ({
            ...prev,
            stage: data.stage,
            progress: data.progress,
            metrics: data.metrics ? { ...prev.metrics, ...data.metrics } : prev.metrics
          }));

          if (data.stage === 'complete') {
            setIsProcessing(false);
            addLog('Mathematical convergence verified. Tie points locked.');
            setActiveTab('matches');
          } else if (data.stage === 'error') {
            setIsProcessing(false);
            addLog(`Pipeline fault: ${data.metrics?.error || 'Exhaustion'}`);
          }
        } catch (err) {
          console.error('Error parsing WS telemetry:', err);
        }
      };

      socket.onclose = () => {
        addLog('Telemetry socket closed.');
      };

      socket.onerror = (err) => {
        console.error('WebSocket telemetry error:', err);
        setIsProcessing(false);
        addLog('Telemetry socket fault.');
      };
    }

    return () => {
      if (socket) socket.close();
    };
  }, [sessionId, isProcessing]);

  const handleUploadAndRun = async () => {
    if (!files.source || !files.reference) {
      alert('Please provide both Source and Reference images before starting the pipeline.');
      return;
    }

    try {
      addLog(`Uploading payloads: ${files.source.name} & ${files.reference.name}...`);
      const uploadRes = await apiService.uploadImages(files.source, files.reference);
      setSessionId(uploadRes.session_id);
      addLog(`Session token allocated: ${uploadRes.session_id.substring(0, 8)}...`);

      setIsProcessing(true);
      setPipelineState(prev => ({
        ...prev,
        stage: 'raw',
        progress: 0,
        metrics: { rmse: '--', inliers: '--', total_matches: '--', model: '--', dossier_index: null, H_matrix: null }
      }));

      await apiService.triggerRegistration(uploadRes.session_id);
      addLog('Background OpenCV registration task dispatched.');
    } catch (err) {
      console.error(err);
      addLog(`Failed to start: ${err.message}`);
      alert(`Pipeline execution failed: ${err.message}`);
      setIsProcessing(false);
    }
  };

  const copySessionId = () => {
    if (!sessionId) return;
    navigator.clipboard.writeText(sessionId);
    setCopiedSession(true);
    setTimeout(() => setCopiedSession(false), 2000);
  };

  return (
    <div className="orbital-layout">
      {/* Top Operational Mission Header */}
      <header className="mission-header">
        {/* Brand */}
        <div className="mission-brand">
          <div className="brand-icon">
            <Satellite size={20} />
          </div>
          <div>
            <div className="brand-title">
              LunaAlign AI
              <span className="telemetry-chip telemetry-chip-cyan" style={{ fontSize: '0.625rem', padding: '2px 8px' }}>
                SIH26166 ISRO
              </span>
            </div>
            <div className="brand-subtitle">
              Orbital Intelligence Dashboard // Sub-Pixel Registration
            </div>
          </div>
        </div>

        {/* Real-time Telemetry Metrics */}
        <div className="header-telemetry-bar">
          <div className="telemetry-item">
            <span className="telemetry-label">Mission Target</span>
            <span className="telemetry-value" style={{ color: 'var(--primary-neon)' }}>
              CHANDRAYAAN-2 TMC-2 / LROC
            </span>
          </div>

          <div className="telemetry-item">
            <span className="telemetry-label">Orbit Coordinates</span>
            <span className="telemetry-value">89.9°S, 0.0°E (100km Polar)</span>
          </div>

          <div className="telemetry-item">
            <span className="telemetry-label">Mission Time</span>
            <span className="telemetry-value" style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Clock size={12} color="var(--primary-neon)" /> {utcTime}
            </span>
          </div>

          {/* Telemetry Status Chip */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className={`telemetry-chip ${isProcessing ? 'telemetry-chip-violet' : 'telemetry-chip-nominal'}`}>
              <span className="ping-dot" />
              {isProcessing ? 'SOLVER ACTIVE' : 'TELEMETRY NOMINAL'}
            </span>

            {/* Telemetry HUD Toggle Button */}
            <button
              className={`btn ${showTelemetry ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setShowTelemetry(!showTelemetry)}
              style={{ padding: '6px 12px', fontSize: '0.75rem', gap: '6px' }}
              title="Toggle Matrix & Telemetry Feed Drawer"
            >
              <BarChart3 size={14} />
              <span>Telemetry HUD</span>
              {pipelineState.metrics.rmse !== '--' && (
                <span className="telemetry-chip telemetry-chip-nominal" style={{ fontSize: '0.5625rem', padding: '1px 5px', marginLeft: '4px' }}>
                  {pipelineState.metrics.rmse}px
                </span>
              )}
            </button>

            {sessionId && (
              <button
                className="btn btn-secondary"
                onClick={copySessionId}
                style={{ padding: '4px 8px', fontSize: '0.6875rem' }}
                title="Copy Session ID"
              >
                {copiedSession ? <Check size={12} color="var(--status-nominal)" /> : <Copy size={12} />}
                <span className="font-mono">{sessionId.substring(0, 8)}...</span>
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Adaptive Flexible Dashboard Grid */}
      <div className={`dashboard-grid ${!showTelemetry ? 'right-collapsed' : ''} ${railCollapsed ? 'left-collapsed' : ''}`}>
        {/* Left Orbital Rail (HUD Controls & Sequencer) */}
        <aside className={`orbital-rail ${railCollapsed ? 'collapsed' : ''}`}>
          {/* Collapse/Expand Header */}
          <div style={{ display: 'flex', justifyContent: railCollapsed ? 'center' : 'space-between', alignItems: 'center', width: '100%', marginBottom: '2px' }}>
            {!railCollapsed && (
              <span style={{ fontFamily: 'var(--font-telemetry)', fontSize: '0.6875rem', color: 'var(--text-annotation)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                Mission Control
              </span>
            )}
            <button
              className="btn btn-secondary"
              onClick={() => setRailCollapsed(!railCollapsed)}
              style={{ padding: '4px', minWidth: '26px', height: '26px' }}
              title={railCollapsed ? "Expand Control Rail" : "Collapse Control Rail"}
            >
              {railCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
            </button>
          </div>

          {/* Primary Action Button */}
          <button
            className="btn btn-primary"
            onClick={handleUploadAndRun}
            disabled={isProcessing || !files.source || !files.reference}
            style={{
              padding: railCollapsed ? '10px' : '12px',
              fontSize: railCollapsed ? '0.75rem' : '0.875rem',
              letterSpacing: '0.02em',
              justifyContent: 'center',
              width: '100%'
            }}
            title="Execute Registration Pipeline"
          >
            <Play size={16} fill={!isProcessing ? 'currentColor' : 'none'} />
            {!railCollapsed && (isProcessing ? `EXECUTING (${pipelineState.progress}%)` : 'EXECUTE REGISTRATION')}
          </button>

          {!railCollapsed && (
            <>
              {/* Streamlined Combined Benchmarks & Sensor Specs Card */}
              <div className="glass-panel" style={{ padding: '10px' }}>
                <div style={{ display: 'flex', gap: '4px', marginBottom: '8px', borderBottom: '1px solid var(--outline)', paddingBottom: '4px' }}>
                  <button
                    className={`btn ${activeSpecTab === 'benchmarks' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setActiveSpecTab('benchmarks')}
                    style={{ padding: '3px 8px', fontSize: '0.6875rem', flex: 1 }}
                  >
                    Benchmarks
                  </button>
                  <button
                    className={`btn ${activeSpecTab === 'sensors' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setActiveSpecTab('sensors')}
                    style={{ padding: '3px 8px', fontSize: '0.6875rem', flex: 1 }}
                  >
                    Sensors
                  </button>
                </div>

                {activeSpecTab === 'benchmarks' ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.6875rem' }}>
                      <span style={{ color: 'var(--text-annotation)' }}>TMC2 vs TMC2:</span>
                      <span className="telemetry-chip telemetry-chip-nominal" style={{ fontSize: '0.5625rem', padding: '1px 5px' }}>
                        22 INL (AFFINE)
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.6875rem' }}>
                      <span style={{ color: 'var(--text-annotation)' }}>OHRC vs OHRC:</span>
                      <span className="telemetry-chip telemetry-chip-cyan" style={{ fontSize: '0.5625rem', padding: '1px 5px' }}>
                        5 INL (ROT 15°)
                      </span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.6875rem' }}>
                      <span style={{ color: 'var(--text-annotation)' }}>OHRC vs TMC2:</span>
                      <span className="telemetry-chip telemetry-chip-warning" style={{ fontSize: '0.5625rem', padding: '1px 5px' }}>
                        0 INL (20X SCALE)
                      </span>
                    </div>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '0.6875rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-annotation)' }}>Source:</span>
                      <span style={{ fontFamily: 'var(--font-telemetry)', color: 'var(--text-telemetry)' }}>TMC-2 Stereo</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-annotation)' }}>Reference:</span>
                      <span style={{ fontFamily: 'var(--font-telemetry)', color: 'var(--text-telemetry)' }}>LROC NAC</span>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                      <span style={{ color: 'var(--text-annotation)' }}>Verification:</span>
                      <span style={{ fontFamily: 'var(--font-telemetry)', color: 'var(--status-nominal)' }}>MAGSAC++</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Pipeline Stage Sequencer with Full Vertical Breathing Room */}
              <div className="glass-panel" style={{ padding: '12px', flex: 1, display: 'flex', flexDirection: 'column', minHeight: '260px' }}>
                <div className="rail-section-header" style={{ marginBottom: '8px' }}>
                  <span>Orbital Pipeline Sequence</span>
                  <Activity size={12} color="var(--primary-neon)" />
                </div>
                <div style={{ flex: 1, overflowY: 'auto' }}>
                  <PipelineVisualizer currentStage={pipelineState.stage} progress={pipelineState.progress} />
                </div>
              </div>
            </>
          )}
        </aside>

        {/* Center Operational Canvas */}
        <main className="center-canvas">
          {/* Spacious, Un-congested HUD Nav Tabs */}
          <div className="hud-nav">
            <button
              className={`hud-nav-tab ${activeTab === 'raw' ? 'active' : ''}`}
              onClick={() => setActiveTab('raw')}
            >
              <span className="tab-badge">01</span>
              <ImageIcon size={16} />
              <span>Ingestion & Presets</span>
            </button>

            <button
              className={`hud-nav-tab ${activeTab === 'matches' ? 'active' : ''}`}
              onClick={() => setActiveTab('matches')}
              disabled={!sessionId || isProcessing || pipelineState.stage !== 'complete'}
              title={!sessionId ? "Execute registration to view XAI match diagnostics" : ""}
            >
              <span className="tab-badge">02</span>
              <Crosshair size={16} />
              <span>XAI Match Diagnostics</span>
            </button>

            <button
              className={`hud-nav-tab ${activeTab === 'compare' ? 'active' : ''}`}
              onClick={() => setActiveTab('compare')}
              disabled={!sessionId || isProcessing || pipelineState.stage !== 'complete'}
              title={!sessionId ? "Execute registration to view alignment validation" : ""}
            >
              <span className="tab-badge">03</span>
              <Layers size={16} />
              <span>Alignment Studio</span>
            </button>

            <button
              className={`hud-nav-tab ${activeTab === 'dem' ? 'active' : ''}`}
              onClick={() => setActiveTab('dem')}
              disabled={!sessionId || isProcessing}
              title={!sessionId ? "Ingest stereo images to view 3D DEM" : ""}
            >
              <span className="tab-badge">04</span>
              <Mountain size={16} color="var(--primary-neon)" />
              <span>3D Elevation (DEM)</span>
            </button>
          </div>

          {/* Main Visualizer Panel */}
          <div className="glass-panel" style={{ flex: 1, padding: '14px', position: 'relative', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            {activeTab === 'raw' && <ImageViewer files={files} setFiles={setFiles} />}
            {activeTab === 'matches' && <MatchVisualizer sessionId={sessionId} metrics={pipelineState.metrics} />}
            {activeTab === 'compare' && <ComparisonModes sessionId={sessionId} />}
            {activeTab === 'dem' && <DemVisualizer sessionId={sessionId} />}

            {/* Tactical Radar Spinner Overlay during Execution */}
            {isProcessing && (
              <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                background: 'rgba(8, 13, 26, 0.85)',
                backdropFilter: 'blur(8px)',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 40
              }}>
                <div style={{
                  width: '64px',
                  height: '64px',
                  borderRadius: '50%',
                  border: '2px solid rgba(34, 211, 238, 0.2)',
                  borderTopColor: 'var(--primary-neon)',
                  borderBottomColor: 'var(--secondary-neon)',
                  animation: 'radarSweep 1.2s cubic-bezier(0.4, 0, 0.2, 1) infinite',
                  boxShadow: '0 0 24px rgba(34, 211, 238, 0.4)'
                }} />
                <h3 style={{ marginTop: '20px', fontFamily: 'var(--font-display)', letterSpacing: '0.04em', color: 'var(--primary-neon)' }}>
                  STAGE EXECUTING: {pipelineState.stage.toUpperCase()}
                </h3>
                <p style={{ fontFamily: 'var(--font-telemetry)', fontSize: '0.8125rem', color: 'var(--text-annotation)', marginTop: '6px' }}>
                  Solving sub-pixel tie point convergence ({pipelineState.progress}% complete)...
                </p>
                <style>{`
                  @keyframes radarSweep {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                  }
                `}</style>
              </div>
            )}
          </div>
        </main>

        {/* Right Telemetry & Analytics Sidebar (Collapsible) */}
        {showTelemetry && (
          <aside className="telemetry-sidebar">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2px' }}>
              <span style={{ fontFamily: 'var(--font-telemetry)', fontSize: '0.6875rem', color: 'var(--text-annotation)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                Orbital Telemetry HUD
              </span>
              <button
                className="btn btn-secondary"
                onClick={() => setShowTelemetry(false)}
                style={{ padding: '2px 8px', fontSize: '0.6875rem' }}
                title="Collapse Telemetry Sidebar"
              >
                ✕ Close
              </button>
            </div>

            {/* Key Convergence Metrics */}
            <div className="glass-panel tactical-corner" style={{ padding: '12px' }}>
              <div className="rail-section-header" style={{ marginBottom: '8px' }}>
                <span>Convergence Telemetry</span>
                <Compass size={12} color="var(--primary-neon)" />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
              <div className="glass-panel-inset" style={{ padding: '8px' }}>
                <span style={{ fontFamily: 'var(--font-telemetry)', fontSize: '0.625rem', color: 'var(--text-annotation)', textTransform: 'uppercase' }}>
                  Residual RMSE
                </span>
                <div style={{ fontFamily: 'var(--font-telemetry)', fontSize: '1.125rem', fontWeight: 700, color: 'var(--status-nominal)', marginTop: '2px' }}>
                  {pipelineState.metrics.rmse !== '--' ? `${pipelineState.metrics.rmse} px` : '--'}
                </div>
              </div>

              <div className="glass-panel-inset" style={{ padding: '8px' }}>
                <span style={{ fontFamily: 'var(--font-telemetry)', fontSize: '0.625rem', color: 'var(--text-annotation)', textTransform: 'uppercase' }}>
                  Inlier Points
                </span>
                <div style={{ fontFamily: 'var(--font-telemetry)', fontSize: '1.125rem', fontWeight: 700, color: 'var(--primary-neon)', marginTop: '2px' }}>
                  {pipelineState.metrics.inliers}
                </div>
              </div>
            </div>

            <div style={{ marginTop: '8px', display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', padding: '4px 2px' }}>
              <span style={{ color: 'var(--text-annotation)' }}>Selected Transform:</span>
              <span style={{ fontFamily: 'var(--font-telemetry)', fontWeight: 600, color: 'var(--secondary-neon)' }}>
                {pipelineState.metrics.model && pipelineState.metrics.model !== '--' ? String(pipelineState.metrics.model).toUpperCase() : '--'}
              </span>
            </div>
          </div>

          {/* Transformation Matrix 3x3 */}
          <div className="glass-panel" style={{ padding: '14px' }}>
            <div className="rail-section-header" style={{ marginBottom: '8px' }}>
              <span>Homography Matrix H (3x3)</span>
              <span className="telemetry-chip telemetry-chip-cyan" style={{ fontSize: '0.5625rem', padding: '1px 6px' }}>
                8-DOF
              </span>
            </div>

            <div className="matrix-grid">
              {pipelineState.metrics.H_matrix ? (
                pipelineState.metrics.H_matrix.flat().map((val, i) => (
                  <div key={i} className="matrix-cell">
                    {typeof val === 'number' ? val.toFixed(3) : val}
                  </div>
                ))
              ) : (
                [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0].map((val, i) => (
                  <div key={i} className="matrix-cell" style={{ color: 'var(--text-muted)' }}>
                    {val.toFixed(2)}
                  </div>
                ))
              )}
            </div>
            <p style={{ marginTop: '6px', fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
              Projective warp matrix maps source coordinates (u, v) into reference frame.
            </p>
          </div>

          {/* Real-time Telemetry Event Feed */}
          <div className="glass-panel" style={{ padding: '14px', flex: 1, display: 'flex', flexDirection: 'column' }}>
            <div className="rail-section-header" style={{ marginBottom: '8px' }}>
              <span>Telemetry Event Stream</span>
              <span className="ping-dot" style={{ color: 'var(--status-nominal)' }} />
            </div>

            <div style={{
              flex: 1,
              overflowY: 'auto',
              fontFamily: 'var(--font-telemetry)',
              fontSize: '0.6875rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '6px',
              paddingRight: '4px'
            }}>
              {telemetryLogs.map((log, i) => (
                <div key={i} style={{ display: 'flex', gap: '8px', lineHeight: 1.4 }}>
                  <span style={{ color: 'var(--text-annotation)', minWidth: '40px' }}>{log.time}</span>
                  <span style={{ color: 'var(--text-telemetry)' }}>{log.msg}</span>
                </div>
              ))}
            </div>
          </div>
        </aside>
      )}
      </div>
    </div>
  );
}

export default App;