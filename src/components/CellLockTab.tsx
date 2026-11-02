import React, { useState } from 'react';
import { RouterControls, RadioMetrics, Language } from '../types';
import { translations } from '../services/translations';
import { routerSimulator } from '../services/routerSimulator';
import {
  Lock,
  Unlock,
  Radio,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Copy,
} from 'lucide-react';

interface CellLockTabProps {
  controls: RouterControls;
  radio: RadioMetrics;
  lang: Language;
}

export const CellLockTab: React.FC<CellLockTabProps> = ({ controls, radio, lang }) => {
  const t = translations[lang];

  // Local input state
  const [val4g, setVal4g] = useState(controls.cellLock4gValue);
  const [val5g, setVal5g] = useState(controls.cellLock5gValue);
  const [toast, setToast] = useState<string | null>(null);

  const suggested4g = `${radio.ltePci},${radio.lteEarfcn}`;
  // Extract number from nrBand e.g. "n78" -> "78"
  const bandNum5g = radio.nrBand.replace(/[^0-9]/g, '') || '78';
  const suggested5g = `${radio.nrPci},${radio.nrArfcn},${bandNum5g}`;

  const isValid4g = /^[0-9]+,[0-9]+$/.test(val4g.trim());
  const isValid5g = /^[0-9]+,[0-9]+,[0-9]+$/.test(val5g.trim());

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(null), 3000);
  };

  const handleToggle4g = () => {
    if (!controls.cellLock4gEnabled && !isValid4g) {
      showToast('Ungültiges Format für 4G Cell Lock (Erwartet: PCI,EARFCN)');
      return;
    }
    routerSimulator.toggleCellLock4g(val4g);
    showToast(`4G Cell Lock: ${!controls.cellLock4gEnabled ? 'Aktiviert' : 'Deaktiviert'}`);
  };

  const handleToggle5g = () => {
    if (!controls.cellLock5gEnabled && !isValid5g) {
      showToast('Ungültiges Format für 5G Cell Lock (Erwartet: PCI,ARFCN,BAND)');
      return;
    }
    routerSimulator.toggleCellLock5g(val5g);
    showToast(`5G Cell Lock: ${!controls.cellLock5gEnabled ? 'Aktiviert' : 'Deaktiviert'}`);
  };

  return (
    <div className="space-y-6">
      {/* Toast Alert */}
      {toast && (
        <div className="flex items-center gap-2 p-3.5 rounded-lg bg-sky-500/15 border border-sky-500/30 text-sky-300 text-xs font-medium">
          <CheckCircle2 className="w-4 h-4 text-sky-400 shrink-0" />
          <span>{toast}</span>
        </div>
      )}

      {/* Safety Notice Banner */}
      <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" />
        <div>
          <p className="font-semibold text-amber-100">{t.cellLockWarning}</p>
          <p className="mt-1 text-amber-300/80 leading-relaxed">
            Die Zellenfixierung bindet das Modem an einen spezifischen Antennensektor des Mobilfunkmastes.
            Nutze die vorgeschlagenen Werte der aktuellen Verbindung, um sicherzustellen, dass die Zelle empfangbar ist.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 4G Cell Lock Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-lg bg-blue-500/15 text-blue-400 flex items-center justify-center font-bold text-xs">
                4G
              </div>
              <div>
                <h3 className="font-bold text-sm text-white">{t.cellLock4gTitle}</h3>
                <p className="text-xs text-slate-400">{t.cellLock4gFormat}</p>
              </div>
            </div>
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
              controls.cellLock4gEnabled
                ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400'
                : 'bg-slate-800 border-slate-700 text-slate-400'
            }`}>
              {controls.cellLock4gEnabled ? 'LOCKED' : 'UNLOCKED'}
            </span>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              PCI, EARFCN
            </label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={val4g}
                onChange={(e) => setVal4g(e.target.value)}
                placeholder="124,1300"
                className={`w-full bg-slate-950 border rounded-lg px-3 py-2 text-xs font-mono text-slate-200 outline-none transition ${
                  isValid4g ? 'border-slate-700 focus:border-sky-500' : 'border-rose-500/60'
                }`}
              />
              <button
                onClick={handleToggle4g}
                className={`px-4 py-2 rounded-lg text-xs font-bold transition flex items-center gap-1.5 shrink-0 ${
                  controls.cellLock4gEnabled
                    ? 'bg-rose-600 hover:bg-rose-500 text-white'
                    : 'bg-sky-600 hover:bg-sky-500 text-white'
                }`}
              >
                {controls.cellLock4gEnabled ? <Unlock className="w-3.5 h-3.5" /> : <Lock className="w-3.5 h-3.5" />}
                {controls.cellLock4gEnabled ? t.releaseLock : t.applyLock}
              </button>
            </div>
          </div>

          {/* Suggestion */}
          <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3 text-xs flex items-center justify-between">
            <div>
              <span className="text-slate-400">{t.suggestedCell}</span>
              <p className="font-mono font-bold text-sky-400 mt-0.5">{suggested4g}</p>
            </div>
            <button
              onClick={() => setVal4g(suggested4g)}
              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-[11px] flex items-center gap-1 transition"
            >
              <Copy className="w-3 h-3" />
              {t.applySuggested}
            </button>
          </div>
        </div>

        {/* 5G Cell Lock Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-lg bg-sky-500/15 text-sky-400 flex items-center justify-center font-bold text-xs">
                5G
              </div>
              <div>
                <h3 className="font-bold text-sm text-white">{t.cellLock5gTitle}</h3>
                <p className="text-xs text-slate-400">{t.cellLock5gFormat}</p>
              </div>
            </div>
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold border ${
              controls.cellLock5gEnabled
                ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-400'
                : 'bg-slate-800 border-slate-700 text-slate-400'
            }`}>
              {controls.cellLock5gEnabled ? 'LOCKED' : 'UNLOCKED'}
            </span>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1.5">
              PCI, ARFCN, BAND
            </label>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={val5g}
                onChange={(e) => setVal5g(e.target.value)}
                placeholder="488,641666,78"
                className={`w-full bg-slate-950 border rounded-lg px-3 py-2 text-xs font-mono text-slate-200 outline-none transition ${
                  isValid5g ? 'border-slate-700 focus:border-sky-500' : 'border-rose-500/60'
                }`}
              />
              <button
                onClick={handleToggle5g}
                className={`px-4 py-2 rounded-lg text-xs font-bold transition flex items-center gap-1.5 shrink-0 ${
                  controls.cellLock5gEnabled
                    ? 'bg-rose-600 hover:bg-rose-500 text-white'
                    : 'bg-sky-600 hover:bg-sky-500 text-white'
                }`}
              >
                {controls.cellLock5gEnabled ? <Unlock className="w-3.5 h-3.5" /> : <Lock className="w-3.5 h-3.5" />}
                {controls.cellLock5gEnabled ? t.releaseLock : t.applyLock}
              </button>
            </div>
          </div>

          {/* Suggestion */}
          <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3 text-xs flex items-center justify-between">
            <div>
              <span className="text-slate-400">{t.suggestedCell}</span>
              <p className="font-mono font-bold text-sky-400 mt-0.5">{suggested5g}</p>
            </div>
            <button
              onClick={() => setVal5g(suggested5g)}
              className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-[11px] flex items-center gap-1 transition"
            >
              <Copy className="w-3 h-3" />
              {t.applySuggested}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
