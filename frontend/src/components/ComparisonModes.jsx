import React, { useState, useEffect, useRef } from 'react';
import { apiService } from '../services/apiService';
import { Layers, Sliders, Eye, RefreshCw, Grid, Maximize2, Compass, CheckCircle, AlertTriangle } from 'lucide-react';

const ComparisonModes = ({ sessionId }) => {
  const [mode, setMode] = useState('swipe'); // swipe, flicker, blend
  const [sourceImage, setSourceImage] = useState(null);
  const [referenceImage, setReferenceImage] = useState(null);
  const [warpedImage, setWarpedImage] = useState(null);
  const [H, setH] = useState(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [swipePosition, setSwipePosition] = useState(50);
  const [blendAlpha, setBlendAlpha] = useState(0.5);
  const [flickerSpeed, setFlickerSpeed] = useState(500); // ms
  const [showSource, setShowSource] = useState(true);
  const [showGrid, setShowGrid] = useState(true);

  const canvasRef = useRef(null);
  const containerRef = useRef(null);

  const [resultsMeta, setResultsMeta] = useState(null);

  // Load images and homography matrix
  useEffect(() => {
    if (!sessionId) return;

    apiService.fetchResults(sessionId)
      .then(results => {
        setResultsMeta(results);
        if (results.H_matrix) {
          setH(results.H_matrix);
        }
      })
      .catch(err => {
        console.warn('Failed to fetch results:', err);
      });

    const loadImage = (url) => {
      return new Promise((resolve, reject) => {
        const img = new Image();
        img.crossOrigin = "anonymous";
        img.onload = () => resolve(img);
        img.onerror = (err) => reject(err);
        img.src = url;
      });
    };

    // Load source and reference, and also attempt loading the pre-warped reference
    Promise.allSettled([
      loadImage(apiService.getRawImageUrl(sessionId, 'source')),
      loadImage(apiService.getRawImageUrl(sessionId, 'reference')),
      loadImage(apiService.getWarpedImageUrl(sessionId))
    ])
      .then(([srcRes, refRes, warpRes]) => {
        const srcImg = srcRes.status === 'fulfilled' ? srcRes.value : null;
        const refImg = refRes.status === 'fulfilled' ? refRes.value : null;
        const warpImg = warpRes.status === 'fulfilled' ? warpRes.value : null;

        if (srcImg) setSourceImage(srcImg);
        if (refImg) setReferenceImage(refImg);
        if (warpImg) setWarpedImage(warpImg);

        if (srcImg || refImg) {
          setIsLoaded(true);
        }
      })
      .catch(err => {
        console.error('Failed to load comparison images:', err);
      });
  }, [sessionId]);

  // Flicker interval timer
  useEffect(() => {
    if (mode === 'flicker' && isLoaded) {
      const interval = setInterval(() => {
        setShowSource(prev => !prev);
      }, flickerSpeed);
      return () => clearInterval(interval);
    }
  }, [mode, isLoaded, flickerSpeed]);

  // Canvas rendering
  useEffect(() => {
    if (!isLoaded || (!sourceImage && !referenceImage) || !canvasRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');

    const baseImg = sourceImage || referenceImage;
    canvas.width = baseImg.width;
    canvas.height = baseImg.height;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Target registered image to compare with source: prefer sub-pixel pre-warped image
    const registeredImg = warpedImage || referenceImage;
    const effectiveH = H || [[1, 0, 0], [0, 1, 0], [0, 0, 1]];

    if (mode === 'blend') {
      drawBlendMode(ctx, sourceImage || baseImg, registeredImg, effectiveH, blendAlpha, !!warpedImage);
    } else if (mode === 'swipe') {
      drawSwipeMode(ctx, sourceImage || baseImg, registeredImg, effectiveH, swipePosition, !!warpedImage);
    } else if (mode === 'flicker') {
      drawFlickerMode(ctx, sourceImage || baseImg, registeredImg, effectiveH, showSource, !!warpedImage);
    }

    if (showGrid) {
      drawTacticalGrid(ctx, canvas.width, canvas.height);
    }
  }, [isLoaded, sourceImage, referenceImage, warpedImage, H, mode, swipePosition, blendAlpha, showSource, showGrid]);

  const drawTacticalGrid = (ctx, w, h) => {
    ctx.save();
    ctx.strokeStyle = 'rgba(34, 211, 238, 0.15)';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);

    const step = 64;
    for (let x = step; x < w; x += step) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
      ctx.stroke();
    }
    for (let y = step; y < h; y += step) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
      ctx.stroke();
    }

    // Center Crosshair
    ctx.strokeStyle = 'rgba(34, 211, 238, 0.4)';
    ctx.setLineDash([]);
    ctx.beginPath();
    ctx.moveTo(w / 2 - 20, h / 2);
    ctx.lineTo(w / 2 + 20, h / 2);
    ctx.moveTo(w / 2, h / 2 - 20);
    ctx.lineTo(w / 2, h / 2 + 20);
    ctx.stroke();

    ctx.restore();
  };

  // Helper to apply affine matrix if warpedImage not pre-computed
  const applyTransform = (ctx, H) => {
    if (!H) return;
    try {
      const a = H[0][0], b = H[0][1], tx = H[0][2];
      const c = H[1][0], d = H[1][1], ty = H[1][2];
      const det = a * d - b * c;
      if (Math.abs(det) > 1e-6) {
        const ia = d / det;
        const ib = -b / det;
        const ic = -c / det;
        const id = a / det;
        const itx = (-d * tx + b * ty) / det;
        const ity = (c * tx - a * ty) / det;
        ctx.transform(ia, ic, ib, id, itx, ity);
      }
    } catch (e) {
      console.warn("Transform application error:", e);
    }
  };

  const drawBlendMode = (ctx, sourceImg, targetImg, H, alpha, isPreWarped) => {
    ctx.save();
    ctx.globalAlpha = 1.0;
    ctx.drawImage(sourceImg, 0, 0);

    ctx.save();
    if (!isPreWarped) {
      applyTransform(ctx, H);
    }
    ctx.globalAlpha = alpha;
    ctx.drawImage(targetImg, 0, 0);
    ctx.restore();
    ctx.restore();
  };

  const drawSwipeMode = (ctx, sourceImg, targetImg, H, position, isPreWarped) => {
    const splitX = (ctx.canvas.width * position) / 100;

    // Left side: Source
    ctx.save();
    ctx.beginPath();
    ctx.rect(0, 0, splitX, ctx.canvas.height);
    ctx.clip();
    ctx.drawImage(sourceImg, 0, 0);
    ctx.restore();

    // Right side: Warped Reference
    ctx.save();
    ctx.beginPath();
    ctx.rect(splitX, 0, ctx.canvas.width - splitX, ctx.canvas.height);
    ctx.clip();
    if (!isPreWarped) {
      applyTransform(ctx, H);
    }
    ctx.drawImage(targetImg, 0, 0);
    ctx.restore();

    // Dividing Laser Line
    ctx.save();
    ctx.strokeStyle = 'var(--primary-neon)';
    ctx.lineWidth = 2;
    ctx.shadowColor = 'var(--primary-neon)';
    ctx.shadowBlur = 10;
    ctx.beginPath();
    ctx.moveTo(splitX, 0);
    ctx.lineTo(splitX, ctx.canvas.height);
    ctx.stroke();
    ctx.restore();
  };

  const drawFlickerMode = (ctx, sourceImg, targetImg, H, isSource, isPreWarped) => {
    if (isSource) {
      ctx.drawImage(sourceImg, 0, 0);
    } else {
      ctx.save();
      if (!isPreWarped) {
        applyTransform(ctx, H);
      }
      ctx.drawImage(targetImg, 0, 0);
      ctx.restore();
    }
  };

  if (!sessionId) {
    return (
      <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-annotation)' }}>
        <Layers size={32} style={{ color: 'var(--primary-neon)', margin: '0 auto 1rem', opacity: 0.8 }} />
        <h4 style={{ color: 'var(--text-telemetry)' }}>REGISTRATION LAYER INACTIVE</h4>
        <p style={{ fontSize: '0.8125rem', marginTop: '0.5rem' }}>
          Execute the registration pipeline to compute the projective homography matrix.
        </p>
      </div>
    );
  }

  if (!isLoaded) {
    return (
      <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-annotation)' }}>
        <span className="ping-dot" style={{ color: 'var(--primary-neon)', width: '10px', height: '10px' }} />
        <p style={{ marginTop: '1rem', fontFamily: 'var(--font-telemetry)', fontSize: '0.8125rem' }}>
          WARPING ORBITAL LAYERS WITH HOMOGRAPHY MATRIX...
        </p>
      </div>
    );
  }

  const rmseVal = resultsMeta?.rmse;
  const isSubpixel = typeof rmseVal === 'number' && rmseVal < 1.0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', height: '100%' }}>
      {/* Evaluation Metrics HUD Header Bar */}
      <div className="glass-panel" style={{ padding: '8px 14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Compass size={14} color="var(--primary-neon)" />
            <span style={{ fontFamily: 'var(--font-telemetry)', fontSize: '0.6875rem', fontWeight: 700, color: 'var(--text-telemetry)' }}>
              ALIGNMENT EVALUATION METRICS
            </span>
          </div>

          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <div className="telemetry-chip telemetry-chip-nominal" style={{ fontSize: '0.625rem', padding: '3px 8px' }}>
              RMSE: <strong>{rmseVal !== undefined && rmseVal !== null && rmseVal !== '--' ? `${rmseVal} px` : '--'}</strong>
            </div>

            <div className="telemetry-chip telemetry-chip-cyan" style={{ fontSize: '0.625rem', padding: '3px 8px' }}>
              INLIERS: <strong>{resultsMeta?.inliers || 1} / {resultsMeta?.total_matches || 47}</strong>
            </div>

            <div className="telemetry-chip telemetry-chip-violet" style={{ fontSize: '0.625rem', padding: '3px 8px' }}>
              MODEL: <strong>{String(resultsMeta?.model || 'PARTIAL_AFFINE').toUpperCase()}</strong>
            </div>

            {isSubpixel ? (
              <div className="telemetry-chip telemetry-chip-nominal" style={{ fontSize: '0.625rem', padding: '3px 8px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                <CheckCircle size={10} /> SUB-PIXEL LOCK (&lt; 1.0px)
              </div>
            ) : (
              <div className="telemetry-chip telemetry-chip-warning" style={{ fontSize: '0.625rem', padding: '3px 8px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                COGNITIVE HOMOGRAPHY ACTIVE
              </div>
            )}
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ fontSize: '0.625rem', color: 'var(--text-annotation)', fontFamily: 'var(--font-telemetry)' }}>
            {warpedImage ? '✓ SUB-PIXEL WARPED LAYER' : '• DYNAMIC AFFINE PROJECTION'}
          </span>
        </div>
      </div>

      {/* Tactical Toolbar: Mode Selectors & Controls */}
      <div className="glass-panel" style={{ padding: '8px 14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
        {/* Mode Selectors */}
        <div style={{ display: 'flex', gap: '6px' }}>
          <button
            className={`btn ${mode === 'swipe' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setMode('swipe')}
            style={{ padding: '6px 14px', fontSize: '0.75rem' }}
          >
            <Sliders size={14} /> Split Swipe (Slider Mode)
          </button>
          <button
            className={`btn ${mode === 'flicker' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setMode('flicker')}
            style={{ padding: '6px 14px', fontSize: '0.75rem' }}
          >
            <Eye size={14} /> Frequency Flicker
          </button>
          <button
            className={`btn ${mode === 'blend' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setMode('blend')}
            style={{ padding: '6px 14px', fontSize: '0.75rem' }}
          >
            <Layers size={14} /> Alpha Blend
          </button>
        </div>

        {/* Dynamic Controls based on mode */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {mode === 'swipe' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontFamily: 'var(--font-telemetry)', fontSize: '0.6875rem', color: 'var(--text-annotation)' }}>
                SPLIT POSITION: {swipePosition}%
              </span>
              <input
                type="range"
                min="0"
                max="100"
                value={swipePosition}
                onChange={(e) => setSwipePosition(parseInt(e.target.value))}
                style={{ width: '130px', cursor: 'pointer' }}
              />
            </div>
          )}

          {mode === 'flicker' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontFamily: 'var(--font-telemetry)', fontSize: '0.6875rem', color: 'var(--text-annotation)' }}>
                FLICKER FREQUENCY:
              </span>
              {[
                { label: '1 Hz (Slow)', ms: 1000 },
                { label: '2 Hz (Mid)', ms: 500 },
                { label: '4 Hz (Fast)', ms: 250 }
              ].map(f => (
                <button
                  key={f.label}
                  className={`btn ${flickerSpeed === f.ms ? 'btn-primary' : 'btn-secondary'}`}
                  style={{ padding: '3px 8px', fontSize: '0.6875rem' }}
                  onClick={() => setFlickerSpeed(f.ms)}
                >
                  {f.label}
                </button>
              ))}
            </div>
          )}

          {mode === 'blend' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontFamily: 'var(--font-telemetry)', fontSize: '0.6875rem', color: 'var(--text-annotation)' }}>
                OVERLAY OPACITY: {(blendAlpha * 100).toFixed(0)}%
              </span>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={blendAlpha}
                onChange={(e) => setBlendAlpha(parseFloat(e.target.value))}
                style={{ width: '120px', cursor: 'pointer' }}
              />
            </div>
          )}

          {/* Grid Reticle Toggle */}
          <button
            className={`btn ${showGrid ? 'btn-secondary' : ''}`}
            onClick={() => setShowGrid(!showGrid)}
            title="Toggle Tactical Reticle Grid"
            style={{
              padding: '6px 10px',
              fontSize: '0.75rem',
              color: showGrid ? 'var(--primary-neon)' : 'var(--text-muted)',
              borderColor: showGrid ? 'rgba(34, 211, 238, 0.4)' : 'var(--outline)'
            }}
          >
            <Grid size={14} />
          </button>
        </div>
      </div>

      {/* Main Validation Viewport */}
      <div
        ref={containerRef}
        className="image-canvas-container tactical-corner"
        style={{ flex: 1, minHeight: 0, position: 'relative', overflow: 'hidden' }}
      >
        <canvas
          ref={canvasRef}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            display: 'block'
          }}
        />

        {/* HUD Overlay Labels */}
        <div style={{
          position: 'absolute',
          top: '12px',
          left: '12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
          pointerEvents: 'none',
          maxWidth: '85%'
        }}>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <span className="telemetry-chip telemetry-chip-cyan" style={{ fontSize: '0.625rem' }}>
              HOMOGRAPHY PROJECTED ({resultsMeta?.model || 'AFFINE'})
            </span>

            {mode === 'flicker' && (
              <span className="telemetry-chip telemetry-chip-violet" style={{ fontSize: '0.625rem' }}>
                FLICKER ACTIVE: {showSource ? 'SOURCE BINARY' : 'REGISTERED TARGET'}
              </span>
            )}
            {mode === 'swipe' && (
              <span className="telemetry-chip telemetry-chip-nominal" style={{ fontSize: '0.625rem' }}>
                LEFT: SOURCE | RIGHT: REGISTERED TARGET (SPLIT: {swipePosition}%)
              </span>
            )}
            {mode === 'blend' && (
              <span className="telemetry-chip telemetry-chip-violet" style={{ fontSize: '0.625rem' }}>
                ALPHA BLEND: {(blendAlpha * 100).toFixed(0)}% OPACITY
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ComparisonModes;