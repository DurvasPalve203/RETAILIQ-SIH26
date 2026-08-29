import React, { useState } from 'react';
import { 
  Radio, 
  Volume2, 
  Lightbulb, 
  Smartphone, 
  Wifi, 
  ShieldAlert, 
  Zap, 
  CheckCircle2, 
  AlertTriangle,
  Play,
  Terminal
} from 'lucide-react';
import { HardwareStatus } from '../types';
import { api } from '../services/api';

interface HardwareAlertHUDProps {
  hardwareStatus?: HardwareStatus;
  onRefresh?: () => void;
}

export const HardwareAlertHUD: React.FC<HardwareAlertHUDProps> = ({
  hardwareStatus,
  onRefresh
}) => {
  const [testResult, setTestResult] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);

  const hw = hardwareStatus || {
    dashboard_active: true,
    mqtt_connected: true,
    mqtt_broker: 'localhost:1883',
    buzzer_enabled: true,
    buzzer_active: false,
    buzzer_pattern: 'OFF',
    rgb_led_enabled: true,
    rgb_led_color: 'GREEN',
    rgb_led_state: 'SOLID',
    sms_enabled: true,
    sms_status: 'READY',
    sms_manager_phone: '+1-800-555-0199'
  };

  const handleTestChannel = async (channel: string, pattern_or_color: string, label: string) => {
    setTesting(true);
    try {
      await api.testAlertChannel(channel, pattern_or_color);
      setTestResult(`Dispatched test signal to ${label}`);
      setTimeout(() => setTestResult(null), 3500);
      if (onRefresh) onRefresh();
    } catch (e) {
      console.error(e);
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 shadow-xl space-y-4">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800/80 pb-3">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-xl bg-blue-500/10 text-blue-400 border border-blue-500/20 shadow-sm">
            <Radio className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white">Multi-Channel Alert Dispatcher & Physical Peripherals</h3>
            <p className="text-xs text-slate-400">
              Zero-internet local edge dispatch across 5 concurrent channels with GSM fallback.
            </p>
          </div>
        </div>

        {testResult && (
          <div className="px-3 py-1 rounded-lg bg-cyan-950/80 border border-cyan-500/40 text-cyan-300 text-xs font-mono flex items-center space-x-1.5 animate-bounce">
            <Zap className="w-3.5 h-3.5 text-cyan-400" />
            <span>{testResult}</span>
          </div>
        )}
      </div>

      {/* 5 Channels Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
        {/* 1. Dashboard WebSocket */}
        <div className="p-3 rounded-xl bg-slate-800/60 border border-slate-700/70 space-y-2 flex flex-col justify-between">
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Dashboard</span>
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            </div>
            <p className="text-xs font-bold text-white flex items-center gap-1">
              <Wifi className="w-3.5 h-3.5 text-cyan-400" /> WebSocket Live
            </p>
          </div>
          <span className="text-[10px] text-slate-400 font-mono">0ms Local Edge Latency</span>
        </div>

        {/* 2. MQTT Mosquitto */}
        <div className="p-3 rounded-xl bg-slate-800/60 border border-slate-700/70 space-y-2 flex flex-col justify-between">
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">MQTT Broker</span>
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
            </div>
            <p className="text-xs font-bold text-white flex items-center gap-1">
              <Radio className="w-3.5 h-3.5 text-blue-400" /> Mosquitto Local
            </p>
          </div>
          <span className="text-[10px] text-slate-400 font-mono">retailiq/alerts/*</span>
        </div>

        {/* 3. GPIO Buzzer */}
        <div className="p-3 rounded-xl bg-slate-800/60 border border-slate-700/70 space-y-2 flex flex-col justify-between">
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">GPIO Buzzer</span>
              <span className={`w-2 h-2 rounded-full ${hw.buzzer_active ? 'bg-rose-400 animate-ping' : 'bg-slate-600'}`} />
            </div>
            <p className="text-xs font-bold text-white flex items-center gap-1">
              <Volume2 className="w-3.5 h-3.5 text-amber-400" /> {hw.buzzer_pattern}
            </p>
          </div>
          <button
            onClick={() => handleTestChannel('buzzer', 'HIGH', 'Piezo Buzzer')}
            className="w-full py-1 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded text-[10px] font-semibold flex items-center justify-center space-x-1"
          >
            <Play className="w-2.5 h-2.5" /> <span>Test Beep</span>
          </button>
        </div>

        {/* 4. RGB LED */}
        <div className="p-3 rounded-xl bg-slate-800/60 border border-slate-700/70 space-y-2 flex flex-col justify-between">
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">RGB LED</span>
              <span className={`w-2 h-2 rounded-full ${
                hw.rgb_led_color === 'RED' ? 'bg-rose-500 animate-pulse' : (hw.rgb_led_color === 'YELLOW' ? 'bg-amber-400' : 'bg-emerald-400')
              }`} />
            </div>
            <p className="text-xs font-bold text-white flex items-center gap-1">
              <Lightbulb className="w-3.5 h-3.5 text-yellow-400" /> {hw.rgb_led_color} ({hw.rgb_led_state})
            </p>
          </div>
          <button
            onClick={() => handleTestChannel('led', 'CRITICAL', 'RGB LED')}
            className="w-full py-1 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded text-[10px] font-semibold flex items-center justify-center space-x-1"
          >
            <Play className="w-2.5 h-2.5" /> <span>Test LED</span>
          </button>
        </div>

        {/* 5. SIM800L GSM SMS */}
        <div className="p-3 rounded-xl bg-slate-800/60 border border-slate-700/70 space-y-2 flex flex-col justify-between">
          <div className="space-y-1">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">SIM800L GSM SMS</span>
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
            </div>
            <p className="text-xs font-bold text-white flex items-center gap-1">
              <Smartphone className="w-3.5 h-3.5 text-emerald-400" /> UART AT Ready
            </p>
          </div>
          <button
            onClick={() => handleTestChannel('sms', 'CRITICAL', 'SIM800L GSM SMS')}
            className="w-full py-1 bg-gradient-to-r from-cyan-600/30 to-blue-600/30 hover:from-cyan-600/50 hover:to-blue-600/50 text-cyan-200 border border-cyan-500/30 rounded text-[10px] font-bold flex items-center justify-center space-x-1"
          >
            <Play className="w-2.5 h-2.5" /> <span>Test SMS</span>
          </button>
        </div>
      </div>

      {/* GSM AT Command Activity Log */}
      {hw.last_sms_event && (
        <div className="p-3 rounded-xl bg-slate-950/80 border border-slate-800 text-[11px] font-mono text-slate-300 space-y-1">
          <div className="flex items-center justify-between text-slate-400 text-[10px]">
            <span className="flex items-center gap-1.5"><Terminal className="w-3 h-3 text-cyan-400" /> SIM800L UART AT Sequence Dispatch</span>
            <span>Target: {hw.last_sms_event.phone}</span>
          </div>
          <p className="text-emerald-400 font-semibold">{hw.last_sms_event.at_sequence}</p>
          <p className="text-slate-400 truncate">{hw.last_sms_event.message}</p>
        </div>
      )}
    </div>
  );
};
