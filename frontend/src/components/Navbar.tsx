import React from 'react';
import { 
  Activity, 
  Layers, 
  TrendingUp, 
  PackagePlus, 
  CheckCircle2, 
  DollarSign, 
  Sliders, 
  Radio,
  Cpu,
  ShieldCheck
} from 'lucide-react';

interface NavbarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  activeAlertsCount: number;
  pendingReviewCount: number;
  inferenceFps: number;
  isOnline: boolean;
  onOpenSimControls: () => void;
  onOpenPrivacyModal: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  setActiveTab,
  activeAlertsCount,
  pendingReviewCount,
  inferenceFps,
  isOnline,
  onOpenSimControls,
  onOpenPrivacyModal
}) => {
  const navItems = [
    { id: 'feed', label: 'Live Action Feed', icon: Activity, badge: activeAlertsCount > 0 ? activeAlertsCount : undefined, badgeColor: 'bg-rose-500' },
    { id: 'map', label: 'Zone Map & Live Video', icon: Layers },
    { id: 'insights', label: 'Merchandising Insights', icon: TrendingUp },
    { id: 'onboarding', label: 'Few-Shot SKU Onboarding', icon: PackagePlus },
    { id: 'review', label: 'Active Learning Triage', icon: CheckCircle2, badge: pendingReviewCount > 0 ? pendingReviewCount : undefined, badgeColor: 'bg-amber-500' },
    { id: 'roi', label: 'ROI & Impact', icon: DollarSign },
  ];

  return (
    <header className="sticky top-0 z-40 bg-slate-900/90 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Node Branding */}
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 ring-1 ring-cyan-400/30">
              <Radio className="w-5 h-5 text-white animate-pulse" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-100 to-slate-300">
                  Retail<span className="text-cyan-400">IQ</span>
                </span>
                <span className="px-2 py-0.5 text-[10px] font-semibold bg-cyan-950 text-cyan-300 rounded border border-cyan-800/60 uppercase tracking-wider">
                  Edge Native
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-medium">Apex Retail • Bay Area Express</p>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden lg:flex items-center space-x-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id)}
                  className={`relative flex items-center space-x-2 px-3.5 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${
                    isActive
                      ? 'bg-slate-800 text-cyan-400 shadow-sm border border-slate-700/60'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
                  }`}
                >
                  <Icon className={`w-4 h-4 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                  {item.badge !== undefined && (
                    <span className={`px-1.5 py-0.2 text-[10px] font-bold text-white rounded-full ${item.badgeColor} animate-pulse`}>
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Quick HUD & Sim Controls */}
          <div className="flex items-center space-x-3">
            {/* FPS Indicator */}
            <div className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 bg-slate-800/80 rounded-md border border-slate-700/60 text-xs font-mono">
              <Cpu className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-slate-400">FPS:</span>
              <span className="font-semibold text-emerald-400">{inferenceFps.toFixed(1)}</span>
            </div>

            {/* Privacy Redaction Status Button */}
            <button
              onClick={onOpenPrivacyModal}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-emerald-950/40 hover:bg-emerald-950/70 text-emerald-300 rounded-lg border border-emerald-500/30 text-xs font-semibold shadow-sm transition-all"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Privacy Blur</span>
            </button>

            {/* Sim Control Button */}
            <button
              onClick={onOpenSimControls}
              className="flex items-center space-x-1.5 px-3 py-1.5 bg-gradient-to-r from-cyan-600/20 to-blue-600/20 hover:from-cyan-600/30 hover:to-blue-600/30 text-cyan-300 rounded-lg border border-cyan-500/30 text-xs font-semibold shadow-sm transition-all"
            >
              <Sliders className="w-3.5 h-3.5" />
              <span>Sim Controls</span>
            </button>
          </div>
        </div>

        {/* Mobile Tab bar */}
        <div className="lg:hidden flex space-x-1 py-2 overflow-x-auto border-t border-slate-800">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`flex-shrink-0 px-3 py-1.5 rounded-md text-xs font-medium ${
                activeTab === item.id ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/30' : 'text-slate-400'
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      </div>
    </header>
  );
};
