import React, { useState } from 'react';
import { RouterControls, Language } from '../types';
import { translations } from '../services/translations';
import { routerSimulator } from '../services/routerSimulator';
import {
  Signal,
  Wifi,
  Lightbulb,
  Clock,
  RotateCw,
  Power,
  CheckCircle2,
  AlertCircle,
  ToggleLeft,
  ToggleRight,
} from 'lucide-react';

interface ControlsTabProps {
  controls: RouterControls;
  lang: Language;
  onReboot: () => void;
}

export const ControlsTab: React.FC<ControlsTabProps> = ({ controls, lang, onReboot }) => {
  const t = translations[lang];
  const [successToast, setSuccessToast] = useState<string | null>(null);

  const triggerSuccess = (msg: string) => {
    setSuccessToast(msg);
    setTimeout(() => setSuccessToast(null), 3000);
  };

  const handleToggleMobileData = () => {
    routerSimulator.toggleMobileData();
    triggerSuccess(`${t.mobileData}: ${!controls.mobileDataEnabled ? 'ON' : 'OFF'}`);
  };

  const handleToggleWifiMaster = () => {
    routerSimulator.toggleWifiMaster();
    triggerSuccess(`${t.wifiMaster}: ${!controls.wifiMasterEnabled ? 'ON' : 'OFF'}`);
  };

  const handleToggleWifi2g = () => {
    routerSimulator.toggleWifi2g();
    triggerSuccess(`${t.wifi2g}: ${!controls.wifi2gEnabled ? 'ON' : 'OFF'}`);
  };

  const handleToggleWifi5g = () => {
    routerSimulator.toggleWifi5g();
    triggerSuccess(`${t.wifi5g}: ${!controls.wifi5gEnabled ? 'ON' : 'OFF'}`);
  };

  const handleToggleOduLed = () => {
    routerSimulator.toggleOduLed();
    triggerSuccess(`${t.oduLed}: ${!controls.oduLedEnabled ? 'ON' : 'OFF'}`);
  };

  const handlePausePolling = () => {
    if (controls.pausePollingUntil) {
      routerSimulator.resumePolling();
      triggerSuccess('Polling resumed');
    } else {
      routerSimulator.pausePollingFiveMinutes();
      triggerSuccess(t.pausePolling);
    }
  };

  return (
    <div className="space-y-6">
      {/* Toast Alert */}
      {successToast && (
        <div className="flex items-center gap-2 p-3.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-medium animate-fadeIn">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{t.actionSuccess} ({successToast})</span>
        </div>
      )}

      <div>
        <h2 className="text-base font-bold text-white">{t.controlsTitle}</h2>
        <p className="text-xs text-slate-400">{t.controlsDesc}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Mobile Data Switch */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex items-center justify-between hover:border-slate-700 transition">
          <div className="flex items-center gap-3.5">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
              controls.mobileDataEnabled ? 'bg-emerald-500/15 text-emerald-400' : 'bg-slate-800 text-slate-500'
            }`}>
              <Signal className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white">{t.mobileData}</h4>
              <p className="text-xs text-slate-400">{t.mobileDataDesc}</p>
            </div>
          </div>
          <button
            onClick={handleToggleMobileData}
            className={`w-12 h-6 rounded-full transition-colors relative cursor-pointer focus:outline-none ${
              controls.mobileDataEnabled ? 'bg-emerald-500' : 'bg-slate-700'
            }`}
          >
            <div
              className={`w-5 h-5 rounded-full bg-white transition-transform transform absolute top-0.5 ${
                controls.mobileDataEnabled ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Master Wi-Fi Switch */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex items-center justify-between hover:border-slate-700 transition">
          <div className="flex items-center gap-3.5">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
              controls.wifiMasterEnabled ? 'bg-sky-500/15 text-sky-400' : 'bg-slate-800 text-slate-500'
            }`}>
              <Wifi className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white">{t.wifiMaster}</h4>
              <p className="text-xs text-slate-400">{t.wifiMasterDesc}</p>
            </div>
          </div>
          <button
            onClick={handleToggleWifiMaster}
            className={`w-12 h-6 rounded-full transition-colors relative cursor-pointer focus:outline-none ${
              controls.wifiMasterEnabled ? 'bg-sky-500' : 'bg-slate-700'
            }`}
          >
            <div
              className={`w-5 h-5 rounded-full bg-white transition-transform transform absolute top-0.5 ${
                controls.wifiMasterEnabled ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* 2.4 GHz Wi-Fi Radio */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex items-center justify-between hover:border-slate-700 transition">
          <div className="flex items-center gap-3.5">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
              controls.wifi2gEnabled && controls.wifiMasterEnabled ? 'bg-sky-500/15 text-sky-400' : 'bg-slate-800 text-slate-500'
            }`}>
              <Wifi className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white">{t.wifi2g}</h4>
              <p className="text-xs text-slate-400">{t.wifi2gDesc}</p>
            </div>
          </div>
          <button
            disabled={!controls.wifiMasterEnabled}
            onClick={handleToggleWifi2g}
            className={`w-12 h-6 rounded-full transition-colors relative cursor-pointer focus:outline-none disabled:opacity-40 ${
              controls.wifi2gEnabled && controls.wifiMasterEnabled ? 'bg-sky-500' : 'bg-slate-700'
            }`}
          >
            <div
              className={`w-5 h-5 rounded-full bg-white transition-transform transform absolute top-0.5 ${
                controls.wifi2gEnabled && controls.wifiMasterEnabled ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* 5 GHz Wi-Fi Radio */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex items-center justify-between hover:border-slate-700 transition">
          <div className="flex items-center gap-3.5">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
              controls.wifi5gEnabled && controls.wifiMasterEnabled ? 'bg-cyan-500/15 text-cyan-400' : 'bg-slate-800 text-slate-500'
            }`}>
              <Wifi className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white">{t.wifi5g}</h4>
              <p className="text-xs text-slate-400">{t.wifi5gDesc}</p>
            </div>
          </div>
          <button
            disabled={!controls.wifiMasterEnabled}
            onClick={handleToggleWifi5g}
            className={`w-12 h-6 rounded-full transition-colors relative cursor-pointer focus:outline-none disabled:opacity-40 ${
              controls.wifi5gEnabled && controls.wifiMasterEnabled ? 'bg-cyan-500' : 'bg-slate-700'
            }`}
          >
            <div
              className={`w-5 h-5 rounded-full bg-white transition-transform transform absolute top-0.5 ${
                controls.wifi5gEnabled && controls.wifiMasterEnabled ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* ODU Status LEDs */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex items-center justify-between hover:border-slate-700 transition">
          <div className="flex items-center gap-3.5">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
              controls.oduLedEnabled ? 'bg-amber-500/15 text-amber-400' : 'bg-slate-800 text-slate-500'
            }`}>
              <Lightbulb className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white">{t.oduLed}</h4>
              <p className="text-xs text-slate-400">{t.oduLedDesc}</p>
            </div>
          </div>
          <button
            onClick={handleToggleOduLed}
            className={`w-12 h-6 rounded-full transition-colors relative cursor-pointer focus:outline-none ${
              controls.oduLedEnabled ? 'bg-amber-500' : 'bg-slate-700'
            }`}
          >
            <div
              className={`w-5 h-5 rounded-full bg-white transition-transform transform absolute top-0.5 ${
                controls.oduLedEnabled ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* Pause Polling Switch */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex items-center justify-between hover:border-slate-700 transition">
          <div className="flex items-center gap-3.5">
            <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
              controls.pausePollingUntil ? 'bg-amber-500/15 text-amber-400 animate-pulse' : 'bg-slate-800 text-slate-500'
            }`}>
              <Clock className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-white">{t.pausePolling}</h4>
              <p className="text-xs text-slate-400">{t.pausePollingDesc}</p>
            </div>
          </div>
          <button
            onClick={handlePausePolling}
            className={`w-12 h-6 rounded-full transition-colors relative cursor-pointer focus:outline-none ${
              controls.pausePollingUntil ? 'bg-amber-500' : 'bg-slate-700'
            }`}
          >
            <div
              className={`w-5 h-5 rounded-full bg-white transition-transform transform absolute top-0.5 ${
                controls.pausePollingUntil ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>
      </div>

      {/* Reboot Router Card */}
      <div className="bg-rose-950/20 border border-rose-800/40 rounded-xl p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-lg bg-rose-500/20 flex items-center justify-center text-rose-400">
            <Power className="w-5 h-5" />
          </div>
          <div>
            <h4 className="text-sm font-bold text-white">{t.restartRouter}</h4>
            <p className="text-xs text-rose-300/80">
              Sends `zwrt_mc.device.manager.device_reboot` UBUS RPC to the router.
            </p>
          </div>
        </div>
        <button
          onClick={onReboot}
          className="px-4 py-2 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold transition shadow flex items-center gap-1.5 shrink-0"
        >
          <RotateCw className="w-3.5 h-3.5" />
          {t.restartRouter}
        </button>
      </div>
    </div>
  );
};
