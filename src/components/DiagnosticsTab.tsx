import React from 'react';
import { SystemHardware, Language } from '../types';
import { translations } from '../services/translations';
import { routerSimulator } from '../services/routerSimulator';
import {
  Cpu,
  Layers,
  Thermometer,
  ShieldCheck,
  RefreshCw,
  Navigation,
  HardDrive,
  Info,
} from 'lucide-react';

interface DiagnosticsTabProps {
  hardware: SystemHardware;
  lang: Language;
}

export const DiagnosticsTab: React.FC<DiagnosticsTabProps> = ({ hardware, lang }) => {
  const t = translations[lang];

  return (
    <div className="space-y-6">
      {/* Top Cards: CPU, RAM, Temperatures */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* CPU */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-slate-400">{t.cpuUsage}</span>
            <Cpu className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-2xl font-black text-white font-mono">{hardware.cpuUsage}%</div>
          <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden mt-3">
            <div
              className="bg-sky-500 h-full rounded-full transition-all"
              style={{ width: `${hardware.cpuUsage}%` }}
            />
          </div>
        </div>

        {/* RAM */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-slate-400">{t.ramUsage}</span>
            <Layers className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-black text-cyan-400 font-mono">{hardware.ramUsage}%</div>
          <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden mt-3">
            <div
              className="bg-cyan-500 h-full rounded-full transition-all"
              style={{ width: `${hardware.ramUsage}%` }}
            />
          </div>
        </div>

        {/* Modem Temp */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-slate-400">{t.modemTemp}</span>
            <Thermometer className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-black text-amber-400 font-mono">{hardware.modemTemp} °C</div>
          <p className="text-[11px] text-slate-400 mt-2">PA Level: {hardware.paTempLevel}</p>
        </div>

        {/* CPU Temp */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-slate-400">{t.cpuTemp}</span>
            <Thermometer className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-black text-emerald-400 font-mono">{hardware.cpuTemp} °C</div>
          <p className="text-[11px] text-slate-400 mt-2">TJ Level: {hardware.tjTempLevel}</p>
        </div>
      </div>

      {/* Firmware & Hardware Revisions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Hardware & Version Specs */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <h3 className="font-bold text-sm text-white flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-sky-400" />
            Hardware & Firmware Details
          </h3>

          <div className="space-y-3 text-xs">
            <div className="flex justify-between py-2 border-b border-slate-800/80">
              <span className="text-slate-400">Router Modell:</span>
              <span className="font-bold text-white">{hardware.model}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-800/80">
              <span className="text-slate-400">{t.hardwareVer}:</span>
              <span className="font-mono text-slate-200">{hardware.hardwareVersion}</span>
            </div>
            <div className="flex justify-between py-2 border-b border-slate-800/80">
              <span className="text-slate-400">{t.firmwareVer}:</span>
              <span className="font-mono text-slate-200">{hardware.firmwareVersion}</span>
            </div>
            <div className="flex justify-between py-2">
              <span className="text-slate-400">UBUS RPC API:</span>
              <span className="font-mono text-emerald-400">Aktiv (zwrt_web / zwrt_mc)</span>
            </div>
          </div>
        </div>

        {/* Firmware Update Controller */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 flex flex-col justify-between">
          <div>
            <h3 className="font-bold text-sm text-white flex items-center gap-2 mb-2">
              <RefreshCw className="w-4 h-4 text-sky-400" />
              {t.firmwareStatus}
            </h3>
            <p className="text-xs text-slate-400">
              Aktuell installierte Softwareversion ist auf dem neuesten Stand. Keine ausstehenden Sicherheitsupdates.
            </p>
          </div>

          <div className="bg-slate-950/60 p-4 rounded-lg border border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
              <span className="text-xs font-semibold text-slate-200">
                {hardware.firmwareStatus === 'checking' ? 'Prüfe Updates...' : 'Aktuell (Up to date)'}
              </span>
            </div>
            <button
              onClick={() => routerSimulator.checkFirmware()}
              disabled={hardware.firmwareStatus === 'checking'}
              className="px-3 py-1.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs transition flex items-center gap-1.5 cursor-pointer disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${hardware.firmwareStatus === 'checking' ? 'animate-spin' : ''}`} />
              {t.checkUpdate}
            </button>
          </div>
        </div>
      </div>

      {/* GNSS / GPS Coordinates */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h3 className="font-bold text-sm text-white flex items-center gap-2 mb-3">
          <Navigation className="w-4 h-4 text-emerald-400" />
          {t.gnssTitle}
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
          <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
            <span className="text-slate-400">{t.gnssStatus}:</span>
            <p className="font-bold text-emerald-400 mt-1 flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-400" /> 3D Satellite Fix (Current)
            </p>
          </div>

          <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
            <span className="text-slate-400">Breitengrad (Latitude):</span>
            <p className="font-mono font-bold text-slate-100 mt-1">{hardware.gnssLatitude}° N</p>
          </div>

          <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800">
            <span className="text-slate-400">Längengrad (Longitude):</span>
            <p className="font-mono font-bold text-slate-100 mt-1">{hardware.gnssLongitude}° E</p>
          </div>
        </div>
      </div>
    </div>
  );
};
