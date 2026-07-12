import { useState, useEffect } from 'react';
import { Camera, Video, Trash2, Eye, RefreshCw, Cpu, X } from 'lucide-react';
import './App.css';

interface CameraStatus {
  id: string;
  name: string;
  source: string;
  status: string;
  sentinel: {
    enabled: boolean;
    type: string;
    confidence_threshold: number;
  };
}

interface ClipInfo {
  filename: string;
  filepath: string;
  created_at: number;
  size_bytes: number;
}

export default function App() {
  const [cameras, setCameras] = useState<CameraStatus[]>([]);
  const [selectedCamId, setSelectedCamId] = useState<string | null>(null);
  const [clips, setClips] = useState<ClipInfo[]>([]);
  const [activeClip, setActiveClip] = useState<ClipInfo | null>(null);
  const [loadingCams, setLoadingCams] = useState(false);
  const [loadingClips, setLoadingClips] = useState(false);
  const [configInfo, setConfigInfo] = useState<{ clip_length: number } | null>(null);

  // Load cameras list and global config
  const fetchCamerasAndConfig = async () => {
    setLoadingCams(true);
    try {
      const configRes = await fetch('/api/config');
      if (configRes.ok) {
        const configData = await configRes.json();
        setConfigInfo(configData);
      }

      const res = await fetch('/api/cameras');
      if (res.ok) {
        const data = await res.json();
        setCameras(data);
        if (data.length > 0 && !selectedCamId) {
          setSelectedCamId(data[0].id);
        }
      }
    } catch (err) {
      console.error("Error fetching cameras:", err);
    } finally {
      setLoadingCams(false);
    }
  };

  // Load clips for selected camera
  const fetchClips = async (camId: string) => {
    setLoadingClips(true);
    try {
      const res = await fetch(`/api/cameras/${camId}/clips`);
      if (res.ok) {
        const data = await res.json();
        setClips(data);
      }
    } catch (err) {
      console.error("Error fetching clips:", err);
    } finally {
      setLoadingClips(false);
    }
  };

  useEffect(() => {
    fetchCamerasAndConfig();
    const interval = setInterval(fetchCamerasAndConfig, 10000); // refresh every 10s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (selectedCamId) {
      fetchClips(selectedCamId);
      // Auto-poll clips every 5 seconds to catch new recordings immediately
      const interval = setInterval(() => fetchClips(selectedCamId), 5000);
      return () => clearInterval(interval);
    }
  }, [selectedCamId]);

  const handleDeleteClip = async (filename: string) => {
    if (!selectedCamId) return;
    if (!confirm(`Are you sure you want to delete this clip? This cannot be undone.`)) return;

    try {
      const res = await fetch(`/api/clips/${selectedCamId}/${filename}`, {
        method: 'DELETE'
      });
      if (res.ok) {
        setClips(clips.filter(c => c.filename !== filename));
        if (activeClip && activeClip.filename === filename) {
          setActiveClip(null);
        }
      } else {
        alert("Failed to delete clip from server.");
      }
    } catch (err) {
      console.error("Error deleting clip:", err);
    }
  };

  const selectedCam = cameras.find(c => c.id === selectedCamId);

  // Format dates beautifully
  const formatTime = (epoch: number) => {
    return new Date(epoch * 1000).toLocaleString(undefined, {
      month: 'short',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  const formatSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="app-container">
      {/* Top Header */}
      <header>
        <div className="logo-section">
          <h1>mycameras</h1>
          <p>Personal webcam subscription stream recorder & smart gallery</p>
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          {configInfo && (
            <span style={{ fontSize: '0.9rem', color: '#64748b', background: '#1e293b', padding: '0.4rem 0.8rem', borderRadius: '6px', border: '1px solid #334155' }}>
              Recording Interval: <strong>{configInfo.clip_length}s</strong>
            </span>
          )}
          <button className="btn-refresh" onClick={() => selectedCamId && fetchClips(selectedCamId)}>
            <RefreshCw size={16} /> Refresh Clips
          </button>
        </div>
      </header>

      {/* Main Dashboard Layout */}
      <div className="dashboard-grid">
        {/* Left column: Camera List */}
        <aside className="sidebar">
          <h2>Webcam Subscriptions</h2>
          {loadingCams && cameras.length === 0 ? (
            <div style={{ color: '#64748b' }}>Loading cameras...</div>
          ) : (
            <div className="camera-list">
              {cameras.map(cam => (
                <div
                  key={cam.id}
                  className={`camera-card ${selectedCamId === cam.id ? 'active-selection' : ''}`}
                  onClick={() => setSelectedCamId(cam.id)}
                >
                  <div className="camera-name">{cam.name}</div>
                  <div className="camera-meta">
                    <span className={`status-badge ${cam.status}`}>
                      <span className="pulse-dot"></span>
                      {cam.status.toUpperCase()}
                    </span>
                    <span className="source-label" title={cam.source}>
                      {cam.source === 'dummy' ? 'Simulated Stream' : cam.source}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Future Sentinel Integration Placeholder */}
          {selectedCam && (
            <div className="sentinel-section" style={{ marginTop: '2rem', padding: '1rem' }}>
              <div className="sentinel-title" style={{ fontSize: '0.95rem' }}>
                <Cpu size={16} /> Sentinel Settings
              </div>
              <div className="sentinel-placeholder-box" style={{ padding: '0.75rem', fontSize: '0.8rem', marginTop: '0.5rem' }}>
                <p style={{ margin: '0 0 0.5rem 0', color: selectedCam.sentinel?.enabled ? '#10b981' : '#64748b' }}>
                  Future Sentinel Status: <strong>{selectedCam.sentinel?.enabled ? 'Active' : 'Inactive (Config Placeholder)'}</strong>
                </p>
                <p style={{ margin: 0, color: '#475569' }}>
                  Type: {selectedCam.sentinel?.type || 'N/A'}<br/>
                  Threshold: {selectedCam.sentinel?.confidence_threshold || 0.0}
                </p>
              </div>
            </div>
          )}
        </aside>

        {/* Right column: Main Workspace (Live view and recordings) */}
        <main className="main-content">
          {selectedCam ? (
            <>
              {/* Live Preview / Active Player */}
              <div className="live-preview-box">
                <h3 className="section-title">
                  <Eye size={18} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
                  Active Video Feed Preview: {selectedCam.name}
                </h3>
                <div className="live-player-container">
                  <div className="live-indicator-overlay">
                    <span className="pulse-dot" style={{ backgroundColor: '#ef4444', animation: 'pulse 1.5s infinite' }}></span>
                    LIVE STREAMING & RECORDING
                  </div>
                  {/* Since RTSP streams cannot be rendered directly in raw HTML5 video players, we stream the newest recorded N-second clip as a looped simulated "live feed". This is standard and beautiful. */}
                  {clips.length > 0 ? (
                    <video
                      key={clips[0].filename}
                      className="live-player-video"
                      src={`/api/clips/${selectedCam.id}/${clips[0].filename}`}
                      autoPlay
                      muted
                      loop
                      playsInline
                    />
                  ) : (
                    <div className="no-video-placeholder">
                      <Camera size={48} />
                      <p>Initializing ffmpeg background segmenter... Waiting for first {configInfo?.clip_length || 10}s clip.</p>
                    </div>
                  )}
                </div>
              </div>

              {/* Chronological Clips Gallery */}
              <div className="gallery-section">
                <h3 className="section-title">
                  <Video size={18} style={{ marginRight: '0.5rem', verticalAlign: 'middle' }} />
                  Recorded N-Second Clips Gallery ({clips.length})
                </h3>
                {loadingClips && clips.length === 0 ? (
                  <div style={{ color: '#64748b', textAlign: 'center', padding: '2rem' }}>Scanning for clips...</div>
                ) : clips.length === 0 ? (
                  <div className="empty-gallery">
                    <Video size={36} style={{ color: '#334155', marginBottom: '0.5rem' }} />
                    <p>No video clips found for this camera yet.</p>
                  </div>
                ) : (
                  <div className="gallery-grid">
                    {clips.map(clip => (
                      <div key={clip.filename} className="clip-card">
                        <div className="clip-thumbnail-wrapper" onClick={() => setActiveClip(clip)}>
                          <video
                            className="clip-video-preview"
                            src={`/api/clips/${selectedCam.id}/${clip.filename}`}
                            muted
                            playsInline
                            onMouseOver={(e) => (e.target as HTMLVideoElement).play()}
                            onMouseOut={(e) => {
                              const v = e.target as HTMLVideoElement;
                              v.pause();
                              v.currentTime = 0;
                            }}
                          />
                          <div className="play-hover-btn">
                            <Eye size={20} />
                          </div>
                          <span className="clip-duration-badge">{configInfo?.clip_length || 10}s</span>
                        </div>
                        <div className="clip-info-body">
                          <div className="clip-timestamp" title={clip.filename}>
                            {formatTime(clip.created_at)}
                          </div>
                          <div className="clip-meta-details">
                            <span>{formatSize(clip.size_bytes)}</span>
                            <button
                              className="delete-btn"
                              title="Delete clip"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleDeleteClip(clip.filename);
                              }}
                            >
                              <Trash2 size={15} />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          ) : (
            <div style={{ color: '#64748b', textAlign: 'center', padding: '4rem' }}>
              Please select a camera subscription.
            </div>
          )}
        </main>
      </div>

      {/* Video Modal / Detailed Player */}
      {activeClip && selectedCam && (
        <div className="modal-overlay" onClick={() => setActiveClip(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h4 className="modal-title">{selectedCam.name} - {formatTime(activeClip.created_at)}</h4>
              <button className="modal-close-btn" onClick={() => setActiveClip(null)}>
                <X size={20} />
              </button>
            </div>
            <div className="modal-body">
              <div className="modal-player-wrapper">
                <video
                  className="modal-player"
                  src={`/api/clips/${selectedCam.id}/${activeClip.filename}`}
                  controls
                  autoPlay
                  playsInline
                />
              </div>
              <div className="modal-meta-row">
                <span>File: <code>{activeClip.filename}</code></span>
                <span>Size: {formatSize(activeClip.size_bytes)}</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
