import React from 'react';
import { RadioMetrics, WanAndTraffic, Language } from '../types';
import { translations } from '../services/translations';
import {
  Signal,
  ArrowDownCircle,
  ArrowUpCircle,
  Globe,
  Radio,
  Clock,
  Layers,
  Database,
  AlertTriangle,
  Zap,
} from 'lucide-react';

interface OverviewTabProps {
  radio: RadioMetrics;
  wan: WanAndTraffic;
  lang: Language;
}

export const OverviewTab: React.FC<OverviewTabProps> = ({ radio, wan, lang }) => {
  const t = translations[lang];

  const formatBps = (bps: number) => {
    const mbps = (bps / 1_000_000).toFixed(1);
    return `${mbps} Mbit/s`;
  };

  const formatBytes = (bytes: number) => {
    const gb = (bytes / (1024 * 1024 * 1024)).toFixed(2);
    return `${gb} GB`;
  };

  // Signal color
  const getRsrpColor = (rsrp: number) => {
    if (rsrp >= -80) return 'text-emerald-400';
    if (rsrp >= -95) return 'text-cyan-400';
    if (rsrp >= -105) return 'text-amber-400';
    return 'text-rose-400';
  };

  return (
    <div className="space-y-6">
      {/* Top Banner: Signal & Real-time Throughput */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Signal & Provider Card */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
              <Signal className="w-4 h-4 text-sky-400" />
              {t.networkStatus}
            </span>
            <span className="text-xs font-mono font-bold text-sky-400">
              {radio.networkType}
            </span>
          </div>

          <div className="flex items-baseline justify-between mt-1">
            <div className="text-2xl font-black text-white tracking-tight">
              {radio.provider}
            </div>
            <div className="flex items-center gap-1">
              {[1, 2, 3, 4, 5].map((bar) => (
                <div
                  key={bar}
                  className={`w-2 rounded-full transition-all ${
                    bar <= radio.signalBars ? 'bg-sky-400' : 'bg-slate-700'
                  }`}
                  style={{ height: `${bar * 5 + 6}px` }}
                />
              ))}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-800 grid grid-cols-2 gap-2 text-xs">
            <div>
              <span className="text-slate-400">{t.activeBands}:</span>
              <p className="font-semibold text-slate-200 mt-0.5">{radio.activeBands}</p>
            </div>
            <div>
              <span className="text-slate-400">{t.bandwidthTotal}:</span>
              <p className="font-semibold text-sky-400 mt-0.5">{radio.totalBandwidthMHz} MHz CA</p>
            </div>
          </div>
        </div>

        {/* Real-time Download */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <ArrowDownCircle className="w-4 h-4 text-emerald-400" />
                {t.downloadRate}
              </span>
              <span className="text-xs text-emerald-400 font-mono flex items-center gap-1">
                <Zap className="w-3 h-3 animate-bounce" /> Fast Poll (5s)
              </span>
            </div>
            <div className="text-3xl font-black text-emerald-400 font-mono tracking-tight mt-1">
              {formatBps(wan.downloadSpeedBps)}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-800 text-xs text-slate-400 flex items-center justify-between">
            <span>{t.dailyTraffic}:</span>
            <span className="font-semibold text-slate-200">{formatBytes(wan.dailyDownloadBytes)}</span>
          </div>
        </div>

        {/* Real-time Upload */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
                <ArrowUpCircle className="w-4 h-4 text-cyan-400" />
                {t.uploadRate}
              </span>
              <span className="text-xs text-cyan-400 font-mono">Fast Poll (5s)</span>
            </div>
            <div className="text-3xl font-black text-cyan-400 font-mono tracking-tight mt-1">
              {formatBps(wan.uploadSpeedBps)}
            </div>
          </div>

          <div className="mt-4 pt-3 border-t border-slate-800 text-xs text-slate-400 flex items-center justify-between">
            <span>{t.dailyTraffic}:</span>
            <span className="font-semibold text-slate-200">{formatBytes(wan.dailyUploadBytes)}</span>
          </div>
        </div>
      </div>

      {/* Deep Radio Signal Telemetry (4G Primary + 5G NR Secondary) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* 5G NR Cell Metrics */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-sky-500/10 flex items-center justify-center text-sky-400 font-bold text-sm">
                5G
              </div>
              <div>
                <h3 className="font-semibold text-slate-200 text-sm">5G NR Secondary Cell</h3>
                <p className="text-xs text-slate-400">{radio.nrBand} • ARFCN {radio.nrArfcn}</p>
              </div>
            </div>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
              Cell ID: {radio.nrCellId}
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
              <span className="text-[11px] font-medium text-slate-400">RSRP</span>
              <div className={`text-lg font-bold font-mono mt-0.5 ${getRsrpColor(radio.nrRsrp)}`}>
                {radio.nrRsrp} <span className="text-xs font-normal">dBm</span>
              </div>
            </div>

            <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
              <span className="text-[11px] font-medium text-slate-400">SINR</span>
              <div className="text-lg font-bold font-mono text-emerald-400 mt-0.5">
                {radio.nrSinr} <span className="text-xs font-normal">dB</span>
              </div>
            </div>

            <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
              <span className="text-[11px] font-medium text-slate-400">RSRQ</span>
              <div className="text-lg font-bold font-mono text-slate-200 mt-0.5">
                {radio.nrRsrq} <span className="text-xs font-normal">dB</span>
              </div>
            </div>

            <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
              <span className="text-[11px] font-medium text-slate-400">PCI</span>
              <div className="text-lg font-bold font-mono text-slate-200 mt-0.5">
                {radio.nrPci}
              </div>
            </div>
          </div>
        </div>

        {/* 4G LTE Primary Cell Metrics */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400 font-bold text-sm">
                4G
              </div>
              <div>
                <h3 className="font-semibold text-slate-200 text-sm">4G LTE Primary Serving Cell</h3>
                <p className="text-xs text-slate-400">{radio.lteBand} • EARFCN {radio.lteEarfcn}</p>
              </div>
            </div>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
              MCC: {radio.rmcc} / MNC: {radio.rmnc}
            </span>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
              <span className="text-[11px] font-medium text-slate-400">RSRP</span>
              <div className={`text-lg font-bold font-mono mt-0.5 ${getRsrpColor(radio.lteRsrp)}`}>
                {radio.lteRsrp} <span className="text-xs font-normal">dBm</span>
              </div>
            </div>

            <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
              <span className="text-[11px] font-medium text-slate-400">SINR</span>
              <div className="text-lg font-bold font-mono text-emerald-400 mt-0.5">
                {radio.lteSinr} <span className="text-xs font-normal">dB</span>
              </div>
            </div>

            <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
              <span className="text-[11px] font-medium text-slate-400">RSRQ</span>
              <div className="text-lg font-bold font-mono text-slate-200 mt-0.5">
                {radio.lteRsrq} <span className="text-xs font-normal">dB</span>
              </div>
            </div>

            <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
              <span className="text-[11px] font-medium text-slate-400">PCI</span>
              <div className="text-lg font-bold font-mono text-slate-200 mt-0.5">
                {radio.ltePci}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* WAN IP & Connection Details */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm">
        <h3 className="font-semibold text-slate-200 text-sm mb-4 flex items-center gap-2">
          <Globe className="w-4 h-4 text-sky-400" />
          {t.wanIpAddresses} & {t.uptime}
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 text-xs">
          <div className="bg-slate-950/60 p-3.5 rounded-lg border border-slate-800">
            <span className="text-slate-400 font-medium">WAN IPv4</span>
            <p className="font-mono text-sm font-semibold text-slate-100 mt-1">{wan.ipv4}</p>
            <span className="text-[10px] text-emerald-400 mt-1 inline-block">● Dual-Stack Connected</span>
          </div>

          <div className="bg-slate-950/60 p-3.5 rounded-lg border border-slate-800">
            <span className="text-slate-400 font-medium">WAN IPv6</span>
            <p className="font-mono text-xs font-semibold text-slate-100 mt-1 truncate" title={wan.ipv6}>
              {wan.ipv6}
            </p>
            <span className="text-[10px] text-emerald-400 mt-1 inline-block">● Public Global Unicast</span>
          </div>

          <div className="bg-slate-950/60 p-3.5 rounded-lg border border-slate-800">
            <span className="text-slate-400 font-medium">{t.connectedDuration}</span>
            <p className="font-mono text-sm font-semibold text-slate-100 mt-1">48h 12m</p>
            <span className="text-[10px] text-slate-400 mt-1 inline-block">Stable session</span>
          </div>

          <div className="bg-slate-950/60 p-3.5 rounded-lg border border-slate-800">
            <span className="text-slate-400 font-medium">{t.packetStats}</span>
            <p className="font-mono text-xs text-slate-300 mt-1">
              Errors: {wan.rxErrors}/{wan.txErrors}
            </p>
            <p className="font-mono text-xs text-slate-400">
              Drops: {wan.rxDrops}/{wan.txDrops}
            </p>
          </div>
        </div>
      </div>

      {/* Home Assistant Live Entity Inspector */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Layers className="w-4 h-4 text-sky-400" />
            <h3 className="font-semibold text-slate-200 text-sm">
              {lang === 'de' ? 'Home Assistant Entitäten-Vorschau (Live)' : 'Home Assistant Live Entity State Preview'}
            </h3>
          </div>
          <span className="text-[11px] font-mono text-slate-400">has_entity_name: true · translation_key active</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 text-xs">
          <div className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-3 space-y-1">
            <span className="text-slate-400 font-mono text-[11px]">sensor.zte_g5ts_download_rate</span>
            <div className="text-slate-200 font-semibold flex items-center justify-between">
              <span>{lang === 'de' ? 'Download-Geschwindigkeit' : 'Download Rate'}</span>
              <span className="font-mono text-emerald-400">{(wan.downloadSpeedBps / 1_000_000).toFixed(1)} Mbit/s</span>
            </div>
            <div className="text-[10px] text-slate-500 font-mono">device_class: data_rate · state_class: measurement</div>
          </div>

          <div className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-3 space-y-1">
            <span className="text-slate-400 font-mono text-[11px]">sensor.zte_g5ts_signalbar</span>
            <div className="text-slate-200 font-semibold flex items-center justify-between">
              <span>{lang === 'de' ? 'Signalstärke' : 'Signal Strength'}</span>
              <span className="font-mono text-sky-400">{radio.signalBars} / 5</span>
            </div>
            <div className="text-[10px] text-slate-500 font-mono">icon: mdi:signal-cellular-outline</div>
          </div>

          <div className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-3 space-y-1">
            <span className="text-slate-400 font-mono text-[11px]">sensor.zte_g5ts_bands_summary</span>
            <div className="text-slate-200 font-semibold flex items-center justify-between">
              <span>{lang === 'de' ? 'Aktive Bänder (CA)' : 'Active Bands (CA)'}</span>
              <span className="font-mono text-slate-200">{radio.activeBands}</span>
            </div>
            <div className="text-[10px] text-slate-500 font-mono">total_bandwidth: {radio.totalBandwidthMHz} MHz</div>
          </div>

          <div className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-3 space-y-1">
            <span className="text-slate-400 font-mono text-[11px]">sensor.zte_g5ts_nr_rsrp</span>
            <div className="text-slate-200 font-semibold flex items-center justify-between">
              <span>5G NR RSRP</span>
              <span className="font-mono text-cyan-400">{radio.nrRsrp} dBm</span>
            </div>
            <div className="text-[10px] text-slate-500 font-mono">device_class: signal_strength · unit: dBm</div>
          </div>

          <div className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-3 space-y-1">
            <span className="text-slate-400 font-mono text-[11px]">switch.zte_g5ts_mobile_data</span>
            <div className="text-slate-200 font-semibold flex items-center justify-between">
              <span>{lang === 'de' ? 'Mobile Datenverbindung' : 'Mobile Cellular Data'}</span>
              <span className="font-mono text-emerald-400">on</span>
            </div>
            <div className="text-[10px] text-slate-500 font-mono">service: zwrt_data.set_wwaniface</div>
          </div>

          <div className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-3 space-y-1">
            <span className="text-slate-400 font-mono text-[11px]">switch.zte_g5ts_pause_polling</span>
            <div className="text-slate-200 font-semibold flex items-center justify-between">
              <span>{lang === 'de' ? 'Abfrage pausieren (5 Min.)' : 'Pause Polling (5 min)'}</span>
              <span className="font-mono text-slate-400">off</span>
            </div>
            <div className="text-[10px] text-slate-500 font-mono">protection: single_session_guard</div>
          </div>
        </div>
      </div>
    </div>
  );
};
