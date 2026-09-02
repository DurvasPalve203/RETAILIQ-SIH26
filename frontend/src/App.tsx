import React, { useState, useEffect, useRef } from 'react';
import { Navbar } from './components/Navbar';
import { LiveActionFeed } from './components/LiveActionFeed';
import { ZoneMapView } from './components/ZoneMapView';
import { ZoneCalibrationModal } from './components/ZoneCalibrationModal';
import { MerchandisingInsights } from './components/MerchandisingInsights';
import { SkuOnboarding } from './components/SkuOnboarding';
import { ReviewQueue } from './components/ReviewQueue';
import { RoiImpactPanel } from './components/RoiImpactPanel';
import { SystemHealthHUD } from './components/SystemHealthHUD';
import { SimulationControls } from './components/SimulationControls';
import { PrivacySplitScreenModal } from './components/PrivacySplitScreenModal';
import { CameraSourceModal } from './components/CameraSourceModal';
import { LiveFeedSocket } from './services/websocket';
import { api } from './services/api';
import { Zone, LiveStatePayload, LiveAlert, ZoneStatus } from './types';
import { WifiOff, AlertTriangle, RefreshCw, Smartphone } from 'lucide-react';

// Simple Error Boundary Component
class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { hasError: boolean; error: Error | null }> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('[RetailIQ UI ErrorBoundary]:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 m-6 bg-slate-900 border border-rose-500/40 rounded-3xl text-center space-y-4 text-slate-200">
          <AlertTriangle className="w-10 h-10 text-rose-400 mx-auto" />
          <h2 className="text-lg font-bold text-white">Dashboard Encountered a Rendering Error</h2>
          <p className="text-xs text-slate-400 max-w-lg mx-auto font-mono">
            {this.state.error?.message || 'Unexpected UI state'}
          </p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-xl text-xs font-bold"
          >
            Reload RetailIQ Dashboard
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('feed');
  const [zones, setZones] = useState<Zone[]>([]);
  const [liveState, setLiveState] = useState<LiveStatePayload | null>(null);
  const [isCalibrating, setIsCalibrating] = useState(false);
  const [isSimOpen, setIsSimOpen] = useState(false);
  const [isPrivacyOpen, setIsPrivacyOpen] = useState(false);
  const [isSourceModalOpen, setIsSourceModalOpen] = useState(false);
  const [pendingReviewsCount, setPendingReviewsCount] = useState(0);
  const [wsConnected, setWsConnected] = useState(true);
  const [isDataStale, setIsDataStale] = useState(false);
  const [videoFeedKey, setVideoFeedKey] = useState(Date.now());

  const lastPacketTsRef = useRef<number>(Date.now());

  // Fetch initial zones & pending review count
  const fetchInitialData = async () => {
    try {
      const [zonesData, reviews] = await Promise.all([
        api.getZones(),
        api.getReviewQueue()
      ]);
      setZones(zonesData);
      setPendingReviewsCount(reviews.length);
    } catch (e) {
      console.error('[RetailIQ Data Fetch]:', e);
    }
  };

  useEffect(() => {
    fetchInitialData();

    // Subscribe to WebSocket live stream
    const socket = new LiveFeedSocket(
      (state) => {
        setLiveState(state);
        lastPacketTsRef.current = Date.now();
        setIsDataStale(false);
      },
      (connected) => {
        setWsConnected(connected);
      }
    );

    // Review count poller
    const pollInterval = setInterval(async () => {
      try {
        const reviews = await api.getReviewQueue();
        setPendingReviewsCount(reviews.length);
      } catch (e) {}
    }, 5000);

    // Stale data watchdog (warns if no socket message arrived for > 6s)
    const staleWatchdog = setInterval(() => {
      if (Date.now() - lastPacketTsRef.current > 6000) {
        setIsDataStale(true);
      }
    }, 2000);

    return () => {
      socket.close();
      clearInterval(pollInterval);
      clearInterval(staleWatchdog);
    };
  }, []);

  const handleRestock = async (zoneId: string) => {
    try {
      await api.controlSimulation('restock', { zone_id: zoneId });
    } catch (e) {
      console.error(e);
    }
  };

  const activeAlerts: LiveAlert[] = liveState?.active_alerts || [];
  const zoneStatuses: ZoneStatus[] = liveState?.zone_statuses || [];
  const inferenceFps = liveState?.fps || 0.0;
  const isSynthetic = liveState?.is_synthetic ?? false;
  const cameraStatus = liveState?.camera_status;
  const isCameraDisconnected = cameraStatus && !cameraStatus.is_connected && !cameraStatus.is_synthetic;

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between selection:bg-cyan-500 selection:text-white">
        <div>
          <Navbar
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            activeAlertsCount={activeAlerts.length}
            pendingReviewCount={pendingReviewsCount}
            inferenceFps={inferenceFps}
            isOnline={wsConnected}
            isSynthetic={isSynthetic}
            onOpenSourceModal={() => setIsSourceModalOpen(true)}
            onOpenSimControls={() => setIsSimOpen(true)}
            onOpenPrivacyModal={() => setIsPrivacyOpen(true)}
          />

          {/* Stale Telemetry Warning Banner */}
          {isDataStale && wsConnected && (
            <div className="bg-amber-950/80 border-b border-amber-500/40 px-4 py-2 text-center text-xs text-amber-200 flex items-center justify-center space-x-2">
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-amber-400" />
              <span>Awaiting fresh inference telemetry from edge device...</span>
            </div>
          )}

          {/* WebSocket Offline Banner */}
          {!wsConnected && (
            <div className="bg-rose-950/80 border-b border-rose-500/40 px-4 py-2 text-center text-xs text-rose-200 flex items-center justify-center space-x-2">
              <WifiOff className="w-4 h-4 text-rose-400 animate-pulse" />
              <span>Edge WebSocket disconnected — Auto-reconnecting to stream in background...</span>
            </div>
          )}

          {/* Camera Disconnected Action Banner */}
          {isCameraDisconnected && (
            <div className="bg-slate-900/90 border-b border-rose-500/30 px-4 py-2.5 max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2 text-xs">
              <div className="flex items-center space-x-2 text-rose-300">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-500 animate-ping" />
                <span>
                  <strong>Camera Reconnecting:</strong> Searching for live mobile stream at <code className="font-mono text-cyan-300">{cameraStatus?.source}</code>.
                </span>
              </div>
              <button
                onClick={() => setIsSourceModalOpen(true)}
                className="px-3 py-1 bg-rose-600 hover:bg-rose-500 text-white rounded-lg font-bold text-[11px] flex items-center gap-1"
              >
                <Smartphone className="w-3 h-3" /> Change Camera Source
              </button>
            </div>
          )}

          <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            {activeTab === 'feed' && (
              <LiveActionFeed
                alerts={activeAlerts}
                zoneStatuses={zoneStatuses}
                queueStates={liveState?.queue_states}
                queuePredictions={liveState?.queue_predictions}
                hardwareStatus={liveState?.hardware_status}
                isOccluded={liveState?.is_occluded || false}
                isLowLight={liveState?.is_low_light || false}
                isSynthetic={isSynthetic}
                footfallToday={liveState?.footfall_today ?? 0}
                onRestock={handleRestock}
                onRefreshData={fetchInitialData}
                onOpenPrivacyModal={() => setIsPrivacyOpen(true)}
                onOpenSourceModal={() => setIsSourceModalOpen(true)}
                videoFeedKey={videoFeedKey}
              />
            )}

            {activeTab === 'map' && (
              <ZoneMapView
                zones={zones}
                zoneStatuses={zoneStatuses}
                onOpenCalibration={() => setIsCalibrating(true)}
              />
            )}

            {activeTab === 'insights' && <MerchandisingInsights />}

            {activeTab === 'onboarding' && <SkuOnboarding />}

            {activeTab === 'review' && <ReviewQueue />}

            {activeTab === 'roi' && <RoiImpactPanel />}
          </main>
        </div>

        {/* Footer Diagnostic HUD */}
        <footer className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 w-full">
          <SystemHealthHUD inferenceFps={inferenceFps} />
          <div className="text-center text-[11px] text-slate-500 mt-4 font-mono">
            RetailIQ Edge Architecture — 100% Offline Single-Board Intelligence Pipeline
          </div>
        </footer>

        {/* Modals */}
        <ZoneCalibrationModal
          isOpen={isCalibrating}
          onClose={() => setIsCalibrating(false)}
          zones={zones}
          onRefreshZones={fetchInitialData}
        />

        <SimulationControls
          isOpen={isSimOpen}
          onClose={() => setIsSimOpen(false)}
        />

        <PrivacySplitScreenModal
          isOpen={isPrivacyOpen}
          onClose={() => setIsPrivacyOpen(false)}
        />

        <CameraSourceModal
          isOpen={isSourceModalOpen}
          onClose={() => setIsSourceModalOpen(false)}
          onSourceChanged={() => { setVideoFeedKey(Date.now()); fetchInitialData(); }}
        />
      </div>
    </ErrorBoundary>
  );
};
