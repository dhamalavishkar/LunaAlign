import React, { useState, useEffect, useRef } from 'react';
import * as THREE from 'three';
import { apiService } from '../services/apiService';
import {
  Mountain,
  Sun,
  RotateCw,
  Eye,
  Download,
  Layers,
  Sparkles,
  Maximize2,
  Sliders,
  Compass
} from 'lucide-react';

const DemVisualizer = ({ sessionId }) => {
  const [demData, setDemData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // 3D Visualizer controls
  const [exaggeration, setExaggeration] = useState(3.0);
  const [sunAngle, setSunAngle] = useState(45);
  const [wireframe, setWireframe] = useState(false);
  const [textureMode, setTextureMode] = useState('colormap'); // colormap, surface, shaded
  const [autoRotate, setAutoRotate] = useState(true);

  const mountRef = useRef(null);
  const sceneRef = useRef(null);
  const meshRef = useRef(null);
  const dirLightRef = useRef(null);
  const rendererRef = useRef(null);

  // Fetch or trigger DEM computation
  useEffect(() => {
    if (!sessionId) return;

    setLoading(true);
    setError(null);

    apiService.fetchDemData(sessionId)
      .then(data => {
        setDemData(data);
        setLoading(false);
      })
      .catch(err => {
        console.log("DEM data not found, generating on the fly...", err);
        return apiService.generateDem(sessionId);
      })
      .then(res => {
        if (res && res.data) {
          setDemData(res.data);
        }
        setLoading(false);
      })
      .catch(err => {
        console.error("DEM generation error:", err);
        setError(err.message || "Failed to compute 3D Elevation Model");
        setLoading(false);
      });
  }, [sessionId]);

  // Three.js 3D Canvas Lifecycle
  useEffect(() => {
    if (!demData || !mountRef.current) return;

    const container = mountRef.current;
    const width = container.clientWidth || 800;
    const height = container.clientHeight || 500;

    // Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x080d1a);
    sceneRef.current = scene;

    // Camera
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.set(0, -60, 60);
    camera.up.set(0, 0, 1);
    camera.lookAt(0, 0, 0);

    // Renderer
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    rendererRef.current = renderer;

    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.4);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0x8aebff, 1.8);
    const rad = (sunAngle * Math.PI) / 180;
    dirLight.position.set(Math.cos(rad) * 60, Math.sin(rad) * 60, 40);
    dirLight.castShadow = true;
    scene.add(dirLight);
    dirLightRef.current = dirLight;

    // Grid geometry from DEM elevation grid
    const grid = demData.normalized_grid;
    const rows = grid.length;
    const cols = grid[0].length;
    const planeWidth = 50;
    const planeHeight = 50;

    const geometry = new THREE.PlaneGeometry(planeWidth, planeHeight, cols - 1, rows - 1);
    const pos = geometry.attributes.position;

    // Set vertex elevation (Z axis)
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const index = r * cols + c;
        const normZ = grid[r][c]; // 0.0 to 1.0
        // Inverted so craters depress downwards
        pos.setZ(index, (normZ - 0.5) * 12 * exaggeration);
      }
    }
    geometry.computeVertexNormals();

    // Texturing
    const textureLoader = new THREE.TextureLoader();
    const colormapUrl = apiService.getDemImageUrl(sessionId, 'colormap');
    const sourceImageUrl = apiService.getRawImageUrl(sessionId, 'source');

    const colormapTexture = textureLoader.load(colormapUrl, () => renderer.render(scene, camera));
    const sourceTexture = textureLoader.load(sourceImageUrl, () => renderer.render(scene, camera));

    let activeTexture = colormapTexture;
    if (textureMode === 'surface') activeTexture = sourceTexture;

    const material = new THREE.MeshStandardMaterial({
      map: textureMode === 'shaded' ? null : activeTexture,
      wireframe: wireframe,
      roughness: 0.85,
      metalness: 0.1,
      color: textureMode === 'shaded' ? 0x7e8ca0 : 0xffffff
    });

    const mesh = new THREE.Mesh(geometry, material);
    mesh.receiveShadow = true;
    mesh.castShadow = true;
    scene.add(mesh);
    meshRef.current = mesh;

    // Add tactical ground coordinate ring
    const ringGeo = new THREE.RingGeometry(35, 35.5, 64);
    const ringMat = new THREE.MeshBasicMaterial({ color: 0x22d3ee, side: THREE.DoubleSide, transparent: true, opacity: 0.25 });
    const ringMesh = new THREE.Mesh(ringGeo, ringMat);
    ringMesh.position.set(0, 0, -8);
    scene.add(ringMesh);

    // Mouse Interaction (Orbiting)
    let isDragging = false;
    let previousMousePosition = { x: 0, y: 0 };
    let spherical = { radius: 85, theta: 0, phi: Math.PI / 4 };

    const updateCameraPos = () => {
      camera.position.x = spherical.radius * Math.sin(spherical.phi) * Math.sin(spherical.theta);
      camera.position.y = -spherical.radius * Math.sin(spherical.phi) * Math.cos(spherical.theta);
      camera.position.z = spherical.radius * Math.cos(spherical.phi);
      camera.lookAt(0, 0, 0);
    };
    updateCameraPos();

    const onMouseDown = (e) => {
      isDragging = true;
      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const onMouseMove = (e) => {
      if (!isDragging) return;
      const deltaX = e.clientX - previousMousePosition.x;
      const deltaY = e.clientY - previousMousePosition.y;

      spherical.theta += deltaX * 0.01;
      spherical.phi = Math.max(0.1, Math.min(Math.PI / 2.1, spherical.phi - deltaY * 0.01));

      updateCameraPos();
      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const onMouseUp = () => {
      isDragging = false;
    };

    const onWheel = (e) => {
      e.preventDefault();
      spherical.radius = Math.max(30, Math.min(180, spherical.radius + e.deltaY * 0.08));
      updateCameraPos();
    };

    const dom = renderer.domElement;
    dom.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    dom.addEventListener('wheel', onWheel, { passive: false });

    // Animation Loop
    let animationFrameId;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      if (autoRotate && !isDragging) {
        spherical.theta += 0.003;
        updateCameraPos();
      }
      renderer.render(scene, camera);
    };
    animate();

    // Handle Resize
    const handleResize = () => {
      if (!mountRef.current) return;
      const w = mountRef.current.clientWidth;
      const h = mountRef.current.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(animationFrameId);
      dom.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      dom.removeEventListener('wheel', onWheel);
      window.removeEventListener('resize', handleResize);
      if (container && renderer.domElement) {
        container.removeChild(renderer.domElement);
      }
      geometry.dispose();
      material.dispose();
    };
  }, [demData, textureMode, wireframe]);

  // Update Vertical Exaggeration on existing mesh
  useEffect(() => {
    if (!meshRef.current || !demData) return;
    const geometry = meshRef.current.geometry;
    const pos = geometry.attributes.position;
    const grid = demData.normalized_grid;
    const rows = grid.length;
    const cols = grid[0].length;

    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const index = r * cols + c;
        const normZ = grid[r][c];
        pos.setZ(index, (normZ - 0.5) * 12 * exaggeration);
      }
    }
    pos.needsUpdate = true;
    geometry.computeVertexNormals();
  }, [exaggeration, demData]);

  // Update Sun Direction Light
  useEffect(() => {
    if (!dirLightRef.current) return;
    const rad = (sunAngle * Math.PI) / 180;
    dirLightRef.current.position.set(Math.cos(rad) * 60, Math.sin(rad) * 60, 40);
  }, [sunAngle]);

  const exportDemJson = () => {
    if (!demData) return;
    const dataStr = JSON.stringify(demData, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `lunaalign_dem_${sessionId}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const exportDemReport = () => {
    if (!demData) return;
    const now = new Date().toLocaleString();
    const grid = demData.normalized_grid || [];
    const totalCells = (demData.grid_width || 64) * (demData.grid_height || 64);
    const elevRange = (demData.max_elevation_m - demData.min_elevation_m).toFixed(1);

    // Elevation histogram buckets (5 bins)
    const flatGrid = grid.flat();
    const bins = [0, 0, 0, 0, 0];
    flatGrid.forEach(v => {
      const idx = Math.min(4, Math.floor(v * 5));
      bins[idx]++;
    });
    const barChart = bins.map((count, i) => {
      const label = ['Very Low  (0–20%)', 'Low       (20–40%)', 'Mid       (40–60%)', 'High      (60–80%)', 'Very High (80–100%)'];
      const pct = ((count / totalCells) * 100).toFixed(1);
      const bar = '█'.repeat(Math.round(count / totalCells * 30));
      return `  ${label[i].padEnd(22)} ${bar.padEnd(30)} ${pct}%`;
    });

    const lines = [
      '=================================================================',
      '   LunaAlign AI — 3D Digital Elevation Model (DEM) Report',
      '   ISRO Smart India Hackathon (SIH 2025) | SIH26166',
      '=================================================================',
      '',
      `  Generated         : ${now}`,
      `  Session ID        : ${sessionId}`,
      '',
      '-----------------------------------------------------------------',
      '  DEM COMPUTATION PARAMETERS',
      '-----------------------------------------------------------------',
      `  Algorithm         : ${demData.algorithm || 'OpenCV StereoSGBM (Semi-Global Block Matching 3-Way)'}`,
      `  Elevation Grid    : ${demData.grid_width || 64} × ${demData.grid_height || 64} cells`,
      `  Baseline Parallax : ${demData.baseline_parallax_deg || 4.8}° (cross-track stereo angle)`,
      `  Resolution        : ~${demData.resolution_m_per_pixel || 5.0} metres per pixel`,
      `  Total Grid Cells  : ${totalCells.toLocaleString()}`,
      '',
      '-----------------------------------------------------------------',
      '  TOPOGRAPHIC ELEVATION STATISTICS',
      '-----------------------------------------------------------------',
      `  Minimum Elevation : ${demData.min_elevation_m} m  (basin / crater floor)`,
      `  Maximum Elevation : ${demData.max_elevation_m} m  (rim / highland peak)`,
      `  Mean Elevation    : ${demData.mean_elevation_m} m`,
      `  Total Relief Depth: ${demData.relief_depth_m} m  (max − min)`,
      `  Elevation Range   : ${elevRange} m`,
      '',
      '  Interpretation:',
      `    The terrain spans ${demData.relief_depth_m} metres of vertical relief.`,
      demData.relief_depth_m > 1500
        ? '    Significant crater-rim-to-floor topography detected.'
        : '    Relatively flat terrain with mild undulations.',
      '',
      '-----------------------------------------------------------------',
      '  ELEVATION DISTRIBUTION (Normalized Height Histogram)',
      '-----------------------------------------------------------------',
      ...barChart,
      '',
      '-----------------------------------------------------------------',
      '  SCIENTIFIC INTERPRETATION',
      '-----------------------------------------------------------------',
      '  The 3D DEM was computed using OpenCV StereoSGBM which estimates',
      '  pixel parallax shifts between a stereo image pair. These shifts',
      '  correspond to depth variations in the lunar surface terrain.',
      '',
      '  Key findings:',
      `  • The deepest depression is ~${Math.abs(demData.min_elevation_m).toFixed(0)} m below the datum.`,
      `  • The highest feature is ~${demData.max_elevation_m.toFixed(0)} m above the datum.`,
      `  • Total terrain relief of ${demData.relief_depth_m} m indicates`,
      demData.relief_depth_m > 2000
        ? '    major crater morphology or volcanic highland terrain.'
        : '    moderate topographic variation consistent with mare plains.',
      '',
      '  Applications: Orthorectification, slope hazard mapping,',
      '  landing site analysis, change detection, crater morphometry.',
      '',
      '=================================================================',
      '  End of LunaAlign DEM Report',
      '=================================================================',
    ];

    const content = lines.join('\n');
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `lunaalign_dem_report_${sessionId}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (!sessionId) {
    return (
      <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-annotation)' }}>
        <Mountain size={36} style={{ color: 'var(--primary-neon)', margin: '0 auto 1rem', opacity: 0.8 }} />
        <h4 style={{ color: 'var(--text-telemetry)' }}>3D DIGITAL ELEVATION MODEL INACTIVE</h4>
        <p style={{ fontSize: '0.8125rem', marginTop: '0.5rem' }}>
          Ingest an overlapping stereo pair and execute the pipeline to compute Semi-Global Block Matching (StereoSGBM) parallax depth.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-annotation)' }}>
        <span className="ping-dot" style={{ color: 'var(--primary-neon)', width: '10px', height: '10px' }} />
        <h4 style={{ color: 'var(--primary-neon)', marginTop: '1rem' }}>COMPUTING STEREO-SGBM DISPARITY...</h4>
        <p style={{ fontSize: '0.8125rem', marginTop: '0.5rem' }}>
          Extracting pixel parallax shifts & interpolating 3D lunar surface mesh.
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-panel" style={{ padding: '2rem', color: 'var(--status-critical)' }}>
        <h4 style={{ color: 'var(--status-critical)' }}>DEM Computation Alert</h4>
        <p style={{ fontSize: '0.8125rem', marginTop: '0.5rem' }}>{error}</p>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', height: '100%' }}>
      {/* 3D Viewport Toolbar */}
      <div className="glass-panel" style={{ padding: '10px 14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="telemetry-chip telemetry-chip-cyan">
            <Mountain size={13} /> 3D STEREO-SGBM DEM
          </span>
          <span className="telemetry-chip telemetry-chip-violet">
            GRID: {demData?.grid_width || 64}×{demData?.grid_height || 64}
          </span>
        </div>

        {/* Tactical Controls Toolbar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          {/* Exaggeration Slider */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontFamily: 'var(--font-telemetry)', fontSize: '0.6875rem', color: 'var(--text-annotation)' }}>
              RELIEF: {exaggeration.toFixed(1)}x
            </span>
            <input
              type="range"
              min="0.5"
              max="6.0"
              step="0.2"
              value={exaggeration}
              onChange={(e) => setExaggeration(parseFloat(e.target.value))}
              style={{ width: '80px' }}
            />
          </div>

          {/* Sun Angle Slider */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sun size={14} color="var(--status-warning)" />
            <span style={{ fontFamily: 'var(--font-telemetry)', fontSize: '0.6875rem', color: 'var(--text-annotation)' }}>
              AZIMUTH: {sunAngle}°
            </span>
            <input
              type="range"
              min="0"
              max="360"
              value={sunAngle}
              onChange={(e) => setSunAngle(parseInt(e.target.value))}
              style={{ width: '80px' }}
            />
          </div>

          {/* Texture Mode */}
          <div style={{ display: 'flex', gap: '4px' }}>
            <button
              className={`btn ${textureMode === 'colormap' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setTextureMode('colormap')}
              style={{ padding: '4px 8px', fontSize: '0.6875rem' }}
              title="Topographic Pseudo-Color"
            >
              Topo
            </button>
            <button
              className={`btn ${textureMode === 'surface' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setTextureMode('surface')}
              style={{ padding: '4px 8px', fontSize: '0.6875rem' }}
              title="Raw Lunar Albedo"
            >
              Albedo
            </button>
            <button
              className={`btn ${textureMode === 'shaded' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setTextureMode('shaded')}
              style={{ padding: '4px 8px', fontSize: '0.6875rem' }}
              title="Hillshade Model"
            >
              Shaded
            </button>
          </div>

          {/* Wireframe */}
          <button
            className={`btn ${wireframe ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setWireframe(!wireframe)}
            style={{ padding: '4px 8px', fontSize: '0.6875rem' }}
            title="Toggle Wireframe Mesh"
          >
            Lattice
          </button>

          {/* Auto Rotate */}
          <button
            className={`btn ${autoRotate ? 'btn-secondary' : ''}`}
            onClick={() => setAutoRotate(!autoRotate)}
            style={{ padding: '4px 8px', fontSize: '0.6875rem', color: autoRotate ? 'var(--primary-neon)' : 'var(--text-muted)' }}
            title="Auto Orbit Rotation"
          >
            <RotateCw size={12} />
          </button>

          {/* Export Buttons */}
          <button
            className="btn btn-secondary"
            onClick={exportDemJson}
            style={{ padding: '4px 10px', fontSize: '0.6875rem' }}
          >
            <Download size={12} color="var(--primary-neon)" /> Export JSON
          </button>
          <button
            className="btn btn-secondary"
            onClick={exportDemReport}
            style={{ padding: '4px 10px', fontSize: '0.6875rem', color: 'var(--secondary-neon)', borderColor: 'rgba(167,139,250,0.4)' }}
          >
            <Download size={12} color="var(--secondary-neon)" /> DEM Report (.txt)
          </button>
        </div>
      </div>

      {/* Main 3D Canvas Area */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 280px', gap: '12px', flex: 1, minHeight: 0 }}>
        {/* Three.js Viewport */}
        <div
          ref={mountRef}
          className="image-canvas-container tactical-corner"
          style={{ flex: 1, minHeight: 0, position: 'relative', cursor: 'grab' }}
        >
          {/* HUD Instructions Overlay */}
          <div style={{
            position: 'absolute',
            bottom: '12px',
            left: '12px',
            background: 'rgba(8, 13, 26, 0.85)',
            border: '1px solid var(--outline)',
            borderRadius: 'var(--radius-sm)',
            padding: '6px 10px',
            fontFamily: 'var(--font-telemetry)',
            fontSize: '0.6875rem',
            color: 'var(--text-annotation)',
            pointerEvents: 'none',
            display: 'flex',
            gap: '12px'
          }}>
            <span>• LEFT DRAG: ORBIT</span>
            <span>• RIGHT DRAG: PAN</span>
            <span>• SCROLL: ZOOM</span>
          </div>
        </div>

        {/* Right Side: Elevation Telemetry & Colormap Preview */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {/* Topographic Telemetry Metrics */}
          <div className="glass-panel tactical-corner" style={{ padding: '12px' }}>
            <div className="rail-section-header" style={{ marginBottom: '8px' }}>
              <span>Topographic Telemetry</span>
              <Compass size={12} color="var(--primary-neon)" />
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                <span style={{ color: 'var(--text-annotation)' }}>Max Crater Rim:</span>
                <span style={{ fontFamily: 'var(--font-telemetry)', fontWeight: 600, color: 'var(--status-warning)' }}>
                  +{demData?.max_elevation_m || '0.0'} m
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                <span style={{ color: 'var(--text-annotation)' }}>Min Crater Basin:</span>
                <span style={{ fontFamily: 'var(--font-telemetry)', fontWeight: 600, color: 'var(--primary-neon)' }}>
                  {demData?.min_elevation_m || '0.0'} m
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', borderTop: '1px solid var(--outline)', paddingTop: '4px' }}>
                <span style={{ color: 'var(--text-annotation)' }}>Total Relief Depth:</span>
                <span style={{ fontFamily: 'var(--font-telemetry)', fontWeight: 700, color: 'var(--status-nominal)' }}>
                  {demData?.relief_depth_m || '0.0'} m
                </span>
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem' }}>
                <span style={{ color: 'var(--text-annotation)' }}>Stereo Parallax:</span>
                <span style={{ fontFamily: 'var(--font-telemetry)', color: 'var(--secondary-neon)' }}>
                  ~{demData?.baseline_parallax_deg || '4.8'}° baseline
                </span>
              </div>
            </div>
          </div>

          {/* Colormap 2D Preview */}
          <div className="glass-panel tactical-corner" style={{ padding: '12px', flex: 1, display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontFamily: 'var(--font-telemetry)', fontSize: '0.6875rem', color: 'var(--text-annotation)', textTransform: 'uppercase', marginBottom: '6px' }}>
              Orthorectified Elevation Map
            </span>
            <div style={{
              flex: 1,
              borderRadius: 'var(--radius-sm)',
              overflow: 'hidden',
              border: '1px solid var(--outline)',
              background: '#000',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <img
                src={apiService.getDemImageUrl(sessionId, 'colormap')}
                alt="DEM Colormap"
                style={{ width: '100%', height: '100%', objectFit: 'contain' }}
              />
            </div>
            {/* Color Scale Legend */}
            <div style={{ marginTop: '6px' }}>
              <div style={{
                height: '8px',
                borderRadius: '2px',
                background: 'linear-gradient(90deg, #30123b, #4662d8, #28bbec, #a2fc3c, #fb8022, #7a0403)'
              }} />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.625rem', fontFamily: 'var(--font-telemetry)', color: 'var(--text-annotation)', marginTop: '2px' }}>
                <span>Basin Floor (-m)</span>
                <span>Crater Rim (+m)</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DemVisualizer;
