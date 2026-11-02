import React from 'react';
import { RouterModel, Language } from '../types';
import { translations } from '../services/translations';
import { routerSimulator } from '../services/routerSimulator';
import {
  Wifi,
  Radio,
  Server,
  Languages,
  Clock,
  RotateCw,
  Cpu,
  ShieldCheck,
} from 'lucide-react';

interface HeaderProps {
  lang: Language;
  onLanguageChange: (lang: Language) => void;
  selectedModel: RouterModel;
  onModelChange: (model: RouterModel) => void;
  isSimulated: boolean;
  onModeToggle: () => void;
  onReboot: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  lang,
  onLanguageChange,
  selectedModel,
  onModelChange,
  isSimulated,
  onModeToggle,
  onReboot,
}) => {
  const t = translations[lang];
  const controls = routerSimulator.controls;
  const isRebooting = routerSimulator.isRebooting;

  const pauseRemainingSeconds = controls.pausePollingUntil
    ? Math.max(0, Math.round((controls.pausePollingUntil - Date.now()) / 1000))
    : 0;

  return (
    <header className="border-b border-slate-800 bg-slate-900/95 backdrop-blur sticky top-0 z-40 px-4 lg:px-8 py-3.5 shadow-lg">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
        {/* Brand & Model */}
        <div className="flex items-center gap-3.5">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-sky-600 to-cyan-500 flex items-center justify-center shadow-lg shadow-sky-500/20 text-white font-black text-xl tracking-wider">
            ZTE
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
                {t.appTitle}
              </h1>
              <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-sky-950 text-sky-400 border border-sky-800/60">
                Home Assistant
              </span>
            </div>
            <p className="text-xs text-slate-400 flex items-center gap-1.5">
              <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              {isRebooting ? t.rebooting : isSimulated ? t.simulatorDesc : t.liveModeDesc}
            </p>
          </div>
        </div>

        {/* Center / Right controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Pause Polling indicator if active */}
          {pauseRemainingSeconds > 0 && (
            <div className="flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-300 animate-pulse">
              <Clock className="w-3.5 h-3.5" />
              <span>
                {t.pollingPaused}: {Math.floor(pauseRemainingSeconds / 60)}:
                {(pauseRemainingSeconds % 60).toString().padStart(2, '0')}
              </span>
            </div>
          )}

          {/* Model Selector */}
          <div className="flex items-center bg-slate-800/80 border border-slate-700 rounded-lg px-2.5 py-1 text-xs">
            <Radio className="w-3.5 h-3.5 text-sky-400 mr-1.5" />
            <select
              value={selectedModel}
              onChange={(e) => onModelChange(e.target.value as RouterModel)}
              className="bg-transparent text-slate-200 outline-none cursor-pointer font-medium"
            >
              <option value="ZTE G5TS" className="bg-slate-900">ZTE G5TS (Wi-Fi 6)</option>
              <option value="ZTE G5TC" className="bg-slate-900">ZTE G5TC (5G FWA)</option>
              <option value="ZTE G5C" className="bg-slate-900">ZTE G5C</option>
              <option value="ZTE G5 Max" className="bg-slate-900">ZTE G5 Max</option>
              <option value="ZTE G5 Ultra" className="bg-slate-900">ZTE G5 Ultra</option>
              <option value="ZTE MC801A" className="bg-slate-900">ZTE MC801A</option>
              <option value="ZTE MC888" className="bg-slate-900">ZTE MC888</option>
            </select>
          </div>

          {/* Mode Switcher */}
          <button
            onClick={onModeToggle}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border transition ${
              isSimulated
                ? 'bg-sky-500/10 border-sky-500/30 text-sky-400 hover:bg-sky-500/20'
                : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20'
            }`}
            title="Toggle between Interactive Simulator and Real Router IP connection"
          >
            <Server className="w-3.5 h-3.5" />
            <span>{isSimulated ? t.simulatorActive : t.liveModeActive}</span>
          </button>

          {/* Language Toggle */}
          <div className="flex items-center bg-slate-800/80 border border-slate-700 rounded-lg p-0.5">
            <button
              onClick={() => onLanguageChange('de')}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition ${
                lang === 'de'
                  ? 'bg-sky-600 text-white shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              🇩🇪 DE
            </button>
            <button
              onClick={() => onLanguageChange('en')}
              className={`px-2.5 py-1 text-xs font-medium rounded-md transition ${
                lang === 'en'
                  ? 'bg-sky-600 text-white shadow'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              🇬🇧 EN
            </button>
          </div>

          {/* Reboot Button */}
          <button
            onClick={onReboot}
            disabled={isRebooting}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 hover:bg-rose-500/20 disabled:opacity-50 transition"
            title={t.restartRouter}
          >
            <RotateCw className={`w-3.5 h-3.5 ${isRebooting ? 'animate-spin' : ''}`} />
            <span>{isRebooting ? t.rebooting : t.restartRouter}</span>
          </button>
        </div>
      </div>
    </header>
  );
};
