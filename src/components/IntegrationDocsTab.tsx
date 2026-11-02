import React from 'react';
import { Language } from '../types';
import { translations } from '../services/translations';
import {
  CheckCircle,
  FileCode,
  Layers,
  BookOpen,
  Download,
  ShieldCheck,
  Globe2,
  ExternalLink,
  Cpu,
  Check,
} from 'lucide-react';

interface IntegrationDocsTabProps {
  lang: Language;
}

export const IntegrationDocsTab: React.FC<IntegrationDocsTabProps> = ({ lang }) => {
  const t = translations[lang];

  const bestPractices = [
    {
      title: t.bp1Title,
      desc: t.bp1Desc,
      status: 'Implemented & Optimized',
    },
    {
      title: t.bp2Title,
      desc: t.bp2Desc,
      status: 'Implemented & Verified',
    },
    {
      title: t.bp3Title,
      desc: t.bp3Desc,
      status: 'Cryptographically Hardened',
    },
    {
      title: t.bp4Title,
      desc: t.bp4Desc,
      status: 'AES-GCM Authenticated',
    },
    {
      title: 'Modern Entity Registry & DeviceInfo',
      desc: 'Enriched DeviceInfo with model, hardware/software firmware revisions, configuration_url, and proper EntityCategory (Diagnostic/Config).',
      status: 'Quality Scale Platinum',
    },
    {
      title: 'Safe Absence Grace Period (180s)',
      desc: 'Client tracking requires confirmed consecutive absence snapshots before marking devices away, preventing false triggers during phone sleep.',
      status: 'Zero False-Positives',
    },
  ];

  const entityRegistry = [
    { domain: 'sensor', key: 'download_rate', nameDe: 'Download-Rate', nameEn: 'Download Rate', type: 'DataRate (bit/s)', poll: 'Fast (5s)' },
    { domain: 'sensor', key: 'upload_rate', nameDe: 'Upload-Rate', nameEn: 'Upload Rate', type: 'DataRate (bit/s)', poll: 'Fast (5s)' },
    { domain: 'sensor', key: 'lte_rsrp / nr_rsrp', nameDe: 'LTE / 5G RSRP', nameEn: 'LTE / 5G RSRP', type: 'Signal (dBm)', poll: 'Slow (60s)' },
    { domain: 'sensor', key: 'bands_summary', nameDe: 'Aktive Bänder', nameEn: 'Active Bands', type: 'Carrier Aggregation', poll: 'Slow (60s)' },
    { domain: 'sensor', key: 'daily_download', nameDe: 'Täglicher Download', nameEn: 'Daily Download', type: 'DataSize (Bytes)', poll: 'Fast (5s)' },
    { domain: 'sensor', key: 'ram_usage', nameDe: 'RAM-Auslastung', nameEn: 'RAM Usage', type: 'Percentage (%)', poll: 'Fast (5s)' },
    { domain: 'switch', key: 'mobile_data', nameDe: 'Mobilfunkdaten', nameEn: 'Mobile Data', type: 'Switch (WWAN)', poll: 'Immediate' },
    { domain: 'switch', key: 'wifi_master', nameDe: 'WLAN Hauptschalter', nameEn: 'Wi-Fi Master', type: 'Switch (2.4G+5G)', poll: 'Immediate' },
    { domain: 'switch', key: 'pause_polling', nameDe: 'Abfrage pausieren (5 Min.)', nameEn: 'Pause Polling (5 min)', type: 'Switch (Timer)', poll: 'Coordinator' },
    { domain: 'switch', key: 'cell_lock_4g / 5g', nameDe: '4G / 5G Zellenfixierung', nameEn: '4G / 5G Cell Lock', type: 'Switch (Radio Lock)', poll: 'Immediate' },
    { domain: 'button', key: 'restart', nameDe: 'Router neu starten', nameEn: 'Restart Router', type: 'Button (UBUS)', poll: 'Immediate' },
    { domain: 'button', key: 'send_sms', nameDe: 'SMS senden', nameEn: 'Send SMS', type: 'Button (SMS Action)', poll: 'Immediate' },
    { domain: 'text', key: 'cell_lock_4g / 5g_text', nameDe: 'Zellenfixierung Eingabe', nameEn: 'Cell Lock Config', type: 'Text (PCI,ARFCN,BAND)', poll: 'Entity' },
    { domain: 'device_tracker', key: 'wifi_client', nameDe: 'Netzwerkgerät (WLAN/LAN)', nameEn: 'Network Client Tracker', type: 'Device Tracker', poll: 'Slow (60s)' },
  ];

  return (
    <div className="space-y-6">
      {/* Banner */}
      <div className="bg-gradient-to-r from-sky-950/60 to-slate-900 border border-sky-800/40 rounded-xl p-6 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-sky-500/20 text-sky-400 border border-sky-500/30">
              {t.hacsCompliant}
            </span>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
              {t.qualityScale}
            </span>
          </div>
          <h2 className="text-xl font-bold text-white tracking-tight">{t.haTitle}</h2>
          <p className="text-xs text-slate-300 mt-1 max-w-2xl">{t.haSubtitle}</p>
        </div>

        <a
          href="/README.md"
          target="_blank"
          className="px-4 py-2.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs transition flex items-center gap-2 shadow-lg shadow-sky-600/20 shrink-0 self-start"
        >
          <BookOpen className="w-4 h-4" />
          <span>README.md / README.de.md</span>
        </a>
      </div>

      {/* Best Practices Checklist */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
        <h3 className="font-bold text-sm text-white flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          {t.bestPracticesTitle}
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {bestPractices.map((bp, i) => (
            <div key={i} className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 flex items-start gap-3">
              <div className="w-7 h-7 rounded-full bg-emerald-500/10 flex items-center justify-center text-emerald-400 shrink-0 mt-0.5">
                <Check className="w-4 h-4" />
              </div>
              <div>
                <div className="flex items-center justify-between gap-2">
                  <h4 className="text-xs font-bold text-white">{bp.title}</h4>
                  <span className="text-[10px] font-mono text-emerald-400 shrink-0">{bp.status}</span>
                </div>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">{bp.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Entity Registry Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
        <h3 className="font-bold text-sm text-white flex items-center gap-2">
          <Layers className="w-4 h-4 text-sky-400" />
          Home Assistant Entity Registry Matrix
        </h3>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/70 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-2.5 px-3">Plattform</th>
                <th className="py-2.5 px-3">Entity Key</th>
                <th className="py-2.5 px-3">Name (Deutsch)</th>
                <th className="py-2.5 px-3">Name (English)</th>
                <th className="py-2.5 px-3">Typ / Klasse</th>
                <th className="py-2.5 px-3">Polling Gruppe</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono text-xs">
              {entityRegistry.map((item, i) => (
                <tr key={i} className="hover:bg-slate-800/20">
                  <td className="py-2 px-3 font-sans">
                    <span className="px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 font-medium">
                      {item.domain}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-sky-400 font-semibold">{item.key}</td>
                  <td className="py-2 px-3 font-sans text-slate-200">{item.nameDe}</td>
                  <td className="py-2 px-3 font-sans text-slate-300">{item.nameEn}</td>
                  <td className="py-2 px-3 text-slate-400 font-sans text-[11px]">{item.type}</td>
                  <td className="py-2 px-3 font-sans">
                    <span className={`text-[11px] font-medium ${
                      item.poll.startsWith('Fast') ? 'text-emerald-400' : 'text-slate-400'
                    }`}>
                      {item.poll}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
