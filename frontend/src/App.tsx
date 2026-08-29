import React, { useState, useEffect } from 'react';
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
import { LiveFeedSocket } from './services/websocket';
import { api } from './services/api';
import { Zone, LiveStatePayload, LiveAlert, ZoneStatus } from './types';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState('feed');
  const [zones, setZones] = useState<Zone[]>([]);
  const [liveState, setLiveState] = useState<LiveStatePayload | null>(null);
  const [isCalibrating, setIsCalibrating] = useState(false);
  const [isSimOpen, setIsSimOpen] = useState(false);
  const [isPrivacyOpen, setIsPrivacyOpen] = useState(false);
  const [pendingReviewsCount, setPendingReviewsCount] = useState(0);

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
      console.error(e);
    }
  };

  useEffect(() => {
    fetchInitialData();

    // Subscribe to WebSocket live stream
    const socket = new LiveFeedSocket((state) => {
      setLiveState(state);
    });

    const pollInterval = setInterval(async () => {
      try {
        const reviews = await api.getReviewQueue();
        setPendingReviewsCount(reviews.length);
      } catch (e) {}
    }, 5000);

    return () => {
      socket.close();
      clearInterval(pollInterval);
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
  const inferenceFps = liveState?.fps || 8.0;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col justify-between selection:bg-cyan-500 selection:text-white">
      <div>
        <Navbar
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          activeAlertsCount={activeAlerts.length}
          pendingReviewCount={pendingReviewsCount}
          inferenceFps={inferenceFps}
          isOnline={true}
          onOpenSimControls={() => setIsSimOpen(true)}
          onOpenPrivacyModal={() => setIsPrivacyOpen(true)}
        />

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
              footfallToday={liveState?.footfall_today || 18}
              onRestock={handleRestock}
              onRefreshData={fetchInitialData}
              onOpenPrivacyModal={() => setIsPrivacyOpen(true)}
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
    </div>
  );
};
