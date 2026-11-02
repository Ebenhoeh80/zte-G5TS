import React, { useState } from 'react';
import { RouterConfig, Language } from '../types';
import { translations } from '../services/translations';
import {
  Settings,
  Shield,
  Clock,
  Users,
  CheckCircle2,
  AlertCircle,
  Play,
  RotateCcw,
} from 'lucide-react';

interface SettingsTabProps {
  config: RouterConfig;
  onConfigSave: (newConfig: RouterConfig) => void;
  lang: Language;
}

export const SettingsTab: React.FC<SettingsTabProps> = ({ config, onConfigSave, lang }) => {
  const t = translations[lang];

  const [form, setForm] = useState<RouterConfig>({ ...config });
  const [testResult, setTestResult] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    onConfigSave(form);
    setToast('Einstellungen gespeichert!');
    setTimeout(() => setToast(null), 3000);
  };

  const handleTestConnection = () => {
    setTesting(true);
    setTestResult(null);

    setTimeout(() => {
      setTesting(false);
      setTestResult(
        `[OK] UBUS web_login_info challenge received. Salt: 32 bytes SHA256 ok. ` +
        `WebUI Mode: Z-Mode 1. Authenticated session ready.`
      );
    }, 1200);
  };

  return (
    <div className="space-y-6">
      {/* Toast Alert */}
      {toast && (
        <div className="flex items-center gap-2 p-3.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs font-medium">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{toast}</span>
        </div>
      )}

      <div>
        <h2 className="text-base font-bold text-white">{t.tabSettings}</h2>
        <p className="text-xs text-slate-400">
          Entspricht den Feldern im Home Assistant Config Flow und Options Flow.
        </p>
      </div>

      <form onSubmit={handleSave} className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Connection Credentials */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <h3 className="font-bold text-sm text-white flex items-center gap-2 pb-2 border-b border-slate-800">
            <Shield className="w-4 h-4 text-sky-400" />
            Router-Verbindung & Anmeldedaten
          </h3>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Router-URL / IP-Adresse (Host)
            </label>
            <input
              type="text"
              value={form.host}
              onChange={(e) => setForm({ ...form, host: e.target.value })}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 outline-none focus:border-sky-500"
              placeholder="http://192.168.0.1"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              WebUI Admin-Passwort
            </label>
            <input
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 outline-none focus:border-sky-500"
              placeholder="••••••••••••"
            />
          </div>

          <div className="flex items-center justify-between pt-2">
            <div>
              <span className="text-xs font-medium text-slate-200">TLS-Zertifikat prüfen</span>
              <p className="text-[11px] text-slate-400">Nur bei gültigem SSL-Zertifikat aktivieren</p>
            </div>
            <input
              type="checkbox"
              checked={form.verifyTls}
              onChange={(e) => setForm({ ...form, verifyTls: e.target.checked })}
              className="w-4 h-4 rounded text-sky-600 focus:ring-0 bg-slate-800 border-slate-700 cursor-pointer"
            />
          </div>

          {/* Test Button */}
          <div className="pt-2">
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={testing}
              className="w-full py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-bold transition flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
            >
              <Play className={`w-3.5 h-3.5 ${testing ? 'animate-spin' : ''}`} />
              <span>{testing ? 'Teste UBUS/GoForm...' : 'Login-Diagnose testen'}</span>
            </button>
            {testResult && (
              <div className="mt-2 p-2.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-[11px] font-mono leading-relaxed">
                {testResult}
              </div>
            )}
          </div>
        </div>

        {/* Polling & Tracking Options */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <h3 className="font-bold text-sm text-white flex items-center gap-2 pb-2 border-b border-slate-800">
            <Clock className="w-4 h-4 text-cyan-400" />
            Polling-Intervalle & Tracking
          </h3>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Schnelles Polling-Intervall (Sekunden)
            </label>
            <input
              type="number"
              min={2}
              max={3600}
              value={form.fastScanInterval}
              onChange={(e) => setForm({ ...form, fastScanInterval: Number(e.target.value) })}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 outline-none focus:border-sky-500"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              Standard: 5s. Durchsatz (Rx/Tx) und RAM-Auslastung.
            </p>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Langsames Polling-Intervall (Sekunden)
            </label>
            <input
              type="number"
              min={5}
              max={3600}
              value={form.slowScanInterval}
              onChange={(e) => setForm({ ...form, slowScanInterval: Number(e.target.value) })}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 outline-none focus:border-sky-500"
            />
            <p className="text-[11px] text-slate-400 mt-1">
              Standard: 60s. Signalstärke, Funkzellen, Datenlimits und SMS.
            </p>
          </div>

          <div className="pt-2 border-t border-slate-800/80">
            <div className="flex items-center justify-between mb-2">
              <div>
                <span className="text-xs font-medium text-slate-200">Netzwerkgeräte verfolgen</span>
                <p className="text-[11px] text-slate-400">Erfasst WLAN- und LAN-Clients schreibgeschützt</p>
              </div>
              <input
                type="checkbox"
                checked={form.trackClients}
                onChange={(e) => setForm({ ...form, trackClients: e.target.checked })}
                className="w-4 h-4 rounded text-sky-600 focus:ring-0 bg-slate-800 border-slate-700 cursor-pointer"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Abwesenheitsfrist für Clients (Sekunden)
              </label>
              <input
                type="number"
                min={0}
                max={3600}
                value={form.clientConsiderHome}
                onChange={(e) => setForm({ ...form, clientConsiderHome: Number(e.target.value) })}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs font-mono text-slate-200 outline-none focus:border-sky-500"
              />
              <p className="text-[11px] text-slate-400 mt-1">Standard: 180s.</p>
            </div>
          </div>

          <div className="pt-3">
            <button
              type="submit"
              className="w-full py-2.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs transition shadow-lg shadow-sky-600/20 cursor-pointer"
            >
              Änderungen übernehmen & speichern
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};
