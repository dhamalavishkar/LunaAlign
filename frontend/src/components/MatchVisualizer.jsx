import React, { useState, useEffect } from 'react';
import { apiService } from '../services/apiService';
import { Download, Crosshair, Radar, FileCode, Cpu, ShieldCheck } from 'lucide-react';

const MatchVisualizer = ({ sessionId, metrics }) => {
  const [dossier, setDossier] = useState(null);
  const [dossierError, setDossierError] = useState(null);

  useEffect(() => {
    if (sessionId && metrics.dossier_index !== null && metrics.dossier_index !== undefined && metrics.dossier_index >= 0) {
      apiService.fetchResults(sessionId)
        .then(() => {
          const wsUrl = apiService.getWebSocketUrl(sessionId);
          const httpUrl = wsUrl.replace('ws://', 'http://')
                               .replace('/api/v1/registration/ws/progress/', '/api/v1/results/');
          return fetch(`${httpUrl}/dossier/${metrics.dossier_index}`);
        })
        .then(res => {
          if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
          }
          return res.json();
        })
        .then(data => {
          setDossier(data);
          setDossierError(null);
        })
        .catch(err => {
          console.error("Error loading dossier", err);
          setDossier(null);
          setDossierError(`Telemetry retrieval failed: ${err.message}`);
        });
    } else {
      setDossier(null);
      setDossierError(null);
    }
  }, [sessionId, metrics]);

  if (!sessionId) {
    return (
      <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-annotation)' }}>
        <Crosshair size={32} style={{ color: 'var(--primary-neon)', margin: '0 auto 1rem', opacity: 0.8 }} />
        <h4 style={{ color: 'var(--text-telemetry)' }}>NO ORBITAL TELEMETRY RECORDED</h4>
        <p style={{ fontSize: '0.8125rem', marginTop: '0.5rem' }}>
          Execute the registration pipeline to compute mathematical correspondences and generate XAI dossiers.
        </p>
      </div>
    );
  }

  if (dossierError) {
    return (
      <div className="glass-panel" style={{ padding: '2rem', color: 'var(--status-critical)' }}>
        <h4 style={{ color: 'var(--status-critical)' }}>Telemetry Dossier Error</h4>
        <p style={{ fontSize: '0.8125rem', marginTop: '0.5rem' }}>{dossierError}</p>
      </div>
    );
  }

  const isLoading = sessionId && metrics.dossier_index >= 0 && !dossier && !dossierError;
  if (isLoading) {
    return (
      <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-annotation)' }}>
        <span className="ping-dot" style={{ color: 'var(--primary-neon)', width: '10px', height: '10px' }} />
        <p style={{ marginTop: '1rem', fontFamily: 'var(--font-telemetry)', fontSize: '0.8125rem' }}>
          ASSEMBLING SUB-PIXEL DOSSIER FOR MATCH #{metrics.dossier_index}...
        </p>
      </div>
    );
  }

  if (!dossier) {
    return (
      <div className="glass-panel" style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-annotation)' }}>
        <p>No inlier tie points or dossier telemetry available for this run.</p>
      </div>
    );
  }

  const matchInfo = dossier && dossier['Match Information'] ? dossier['Match Information'] : {};
  const hasMatchInfo = Object.keys(matchInfo).length > 0;

  const formatValue = (key, value) => {
    if (typeof value === 'number') {
      if (key.includes('Coordinate') || key.includes('Distance') || key.includes('Scale')) {
        return `${value.toFixed(3)} px`;
      } else if (key.includes('Angle')) {
        return `${value.toFixed(2)}°`;
      } else if (key === 'Descriptor Distance') {
        return `${value.toFixed(4)}`;
      } else if (key.includes('Ratio')) {
        return `${value.toFixed(3)}`;
      }
      return value.toString();
    }
    return typeof value === 'string' ? value : JSON.stringify(value);
  };

  const exportReport = () => {
    if (!dossier) return;
    const dataStr = JSON.stringify(dossier, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `lunaalign_dossier_${sessionId}_match_${metrics.dossier_index}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', height: '100%', overflowY: 'auto', paddingRight: '4px' }}>
      {/* Dossier Header Bar */}
      <div className="glass-panel" style={{ padding: '12px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{
            width: '28px',
            height: '28px',
            borderRadius: '6px',
            background: 'rgba(34, 211, 238, 0.15)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--primary-neon)'
          }}>
            <Cpu size={16} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className="telemetry-chip telemetry-chip-violet">
                <span className="ping-dot" /> XAI TIE-POINT VERIFIED
              </span>
              <span className="telemetry-chip telemetry-chip-cyan">
                INLIER #{metrics.dossier_index}
              </span>
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-annotation)', marginTop: '2px' }}>
              Sub-Pixel Illumination-Invariant Coordinate Correlation
            </p>
          </div>
        </div>

        <button className="btn btn-secondary" onClick={exportReport} style={{ padding: '6px 12px', fontSize: '0.75rem' }}>
          <Download size={14} color="var(--primary-neon)" /> Export JSON Telemetry
        </button>
      </div>

      {/* Top 3 High-Level Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
        <div className="glass-panel tactical-corner" style={{ padding: '12px' }}>
          <span style={{ fontFamily: 'var(--font-telemetry)', fontSize: '0.625rem', color: 'var(--text-annotation)', textTransform: 'uppercase' }}>
            REGISTRATION RESIDUAL (RMSE)
          </span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginTop: '4px' }}>
            <span style={{ fontFamily: 'var(--font-telemetry)', fontSize: '1.25rem', fontWeight: 700, color: 'var(--status-nominal)' }}>
              {metrics.rmse !== '--' ? metrics.rmse : '--'}
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-annotation)' }}>px</span>
          </div>
          <span style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>Sub-pixel convergence limit: &lt; 0.5px</span>
        </div>

        <div className="glass-panel tactical-corner" style={{ padding: '12px' }}>
          <span style={{ fontFamily: 'var(--font-telemetry)', fontSize: '0.625rem', color: 'var(--text-annotation)', textTransform: 'uppercase' }}>
            INLIER CORRESPONDENCES
          </span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginTop: '4px' }}>
            <span style={{ fontFamily: 'var(--font-telemetry)', fontSize: '1.25rem', fontWeight: 700, color: 'var(--primary-neon)' }}>
              {metrics.inliers}
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-annotation)' }}>
              / {metrics.total_matches || metrics.inliers}
            </span>
          </div>
          <span style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>
            Inlier ratio: {metrics.total_matches > 0 ? `${(metrics.inliers / metrics.total_matches * 100).toFixed(1)}%` : '100%'}
          </span>
        </div>

        <div className="glass-panel tactical-corner" style={{ padding: '12px' }}>
          <span style={{ fontFamily: 'var(--font-telemetry)', fontSize: '0.625rem', color: 'var(--text-annotation)', textTransform: 'uppercase' }}>
            TRANSFORMATION MODEL
          </span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '6px', marginTop: '4px' }}>
            <span style={{ fontFamily: 'var(--font-telemetry)', fontSize: '1.125rem', fontWeight: 700, color: 'var(--secondary-neon)' }}>
              {String(metrics.model).toUpperCase()}
            </span>
          </div>
          <span style={{ fontSize: '0.6875rem', color: 'var(--text-muted)' }}>8-DOF Projective Homography</span>
        </div>
      </div>

      {/* Main Grid: Data Table + Feature Patch */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: '14px' }}>
        {/* Match Information Table */}
        <div className="glass-panel" style={{ padding: '14px', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
            <span style={{ fontFamily: 'var(--font-telemetry)', fontSize: '0.6875rem', fontWeight: 600, color: 'var(--text-annotation)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Sub-Pixel Vector Coordinates
            </span>
            <ShieldCheck size={14} color="var(--status-nominal)" />
          </div>

          <div style={{ overflowX: 'auto', flex: 1 }}>
            <table className="telemetry-table">
              <tbody>
                {hasMatchInfo && Object.entries(matchInfo).map(([k, v]) => (
                  <tr key={k}>
                    <td style={{ color: 'var(--text-annotation)', width: '55%' }}>{k}</td>
                    <td style={{ color: 'var(--text-telemetry)', fontWeight: 600, textAlign: 'right' }}>
                      {formatValue(k, v)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Local Pixel Patch Visualizer */}
        <div className="glass-panel tactical-corner" style={{ padding: '14px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <span style={{ fontFamily: 'var(--font-telemetry)', fontSize: '0.6875rem', fontWeight: 600, color: 'var(--text-annotation)', textTransform: 'uppercase', letterSpacing: '0.08em', alignSelf: 'flex-start', marginBottom: '8px' }}>
            Neighborhood Patch Correlation
          </span>

          <div style={{
            position: 'relative',
            padding: '4px',
            background: 'rgba(8, 13, 26, 0.9)',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--outline)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <img
              src={apiService.getImageUrl(sessionId, 'patch', metrics.dossier_index)}
              alt="Feature Patch Comparison"
              onError={(e) => {
                console.error("Patch load error", e);
              }}
              style={{
                width: '100%',
                maxHeight: '190px',
                objectFit: 'contain',
                borderRadius: '4px'
              }}
            />
          </div>
          <p style={{ marginTop: '8px', fontSize: '0.6875rem', color: 'var(--text-muted)', textAlign: 'center' }}>
            Dual 32×32 pixel neighborhood windows centered at sub-pixel tie point.
          </p>
        </div>
      </div>

      {/* Uncertainty Field Viewers */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
        <div className="glass-panel tactical-corner" style={{ padding: '12px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', marginBottom: '8px' }}>
            <span style={{ fontFamily: 'var(--font-telemetry)', fontSize: '0.6875rem', color: 'var(--text-annotation)', textTransform: 'uppercase' }}>
              Source Uncertainty Field
            </span>
            <Radar size={14} color="var(--primary-neon)" />
          </div>
          <img
            src={apiService.getImageUrl(sessionId, 'src_uncertainty', metrics.dossier_index)}
            alt="Source Uncertainty"
            style={{ width: '100%', maxHeight: '180px', objectFit: 'contain', borderRadius: '4px' }}
          />
        </div>

        <div className="glass-panel tactical-corner" style={{ padding: '12px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', marginBottom: '8px' }}>
            <span style={{ fontFamily: 'var(--font-telemetry)', fontSize: '0.6875rem', color: 'var(--text-annotation)', textTransform: 'uppercase' }}>
              Reference Target Uncertainty Field
            </span>
            <Radar size={14} color="var(--secondary-neon)" />
          </div>
          <img
            src={apiService.getImageUrl(sessionId, 'ref_uncertainty', metrics.dossier_index)}
            alt="Reference Uncertainty"
            style={{ width: '100%', maxHeight: '180px', objectFit: 'contain', borderRadius: '4px' }}
          />
        </div>
      </div>
    </div>
  );
};

export default MatchVisualizer;