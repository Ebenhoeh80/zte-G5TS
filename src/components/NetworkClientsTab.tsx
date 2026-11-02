import React, { useState } from 'react';
import { NetworkClientDevice, Language } from '../types';
import { translations } from '../services/translations';
import {
  Users,
  Wifi,
  Laptop,
  Smartphone,
  Tv,
  Server,
  Filter,
  CheckCircle,
  Clock,
} from 'lucide-react';

interface NetworkClientsTabProps {
  clients: NetworkClientDevice[];
  lang: Language;
}

export const NetworkClientsTab: React.FC<NetworkClientsTabProps> = ({ clients, lang }) => {
  const t = translations[lang];
  const [filter, setFilter] = useState<'all' | 'wifi' | 'lan'>('all');

  const filteredClients = clients.filter((c) => {
    if (filter === 'wifi') return c.interface.startsWith('wifi');
    if (filter === 'lan') return c.interface === 'lan';
    return true;
  });

  const wifiCount = clients.filter((c) => c.interface.startsWith('wifi')).length;
  const lanCount = clients.filter((c) => c.interface === 'lan').length;

  const getDeviceIcon = (hostname: string, iface: string) => {
    const h = hostname.toLowerCase();
    if (h.includes('iphone') || h.includes('phone') || h.includes('pixel') || h.includes('galaxy')) {
      return <Smartphone className="w-4 h-4 text-sky-400" />;
    }
    if (h.includes('macbook') || h.includes('laptop') || h.includes('pc') || h.includes('thinkpad')) {
      return <Laptop className="w-4 h-4 text-emerald-400" />;
    }
    if (h.includes('tv') || h.includes('bravia') || h.includes('samsung') || h.includes('lg')) {
      return <Tv className="w-4 h-4 text-purple-400" />;
    }
    return <Server className="w-4 h-4 text-cyan-400" />;
  };

  return (
    <div className="space-y-6">
      {/* Overview Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-400 font-medium">{t.totalClients}</span>
            <div className="text-2xl font-black text-white mt-0.5">{clients.length}</div>
          </div>
          <div className="w-10 h-10 rounded-lg bg-sky-500/10 flex items-center justify-center text-sky-400">
            <Users className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-400 font-medium">{t.wifiClients}</span>
            <div className="text-2xl font-black text-sky-400 mt-0.5">{wifiCount}</div>
          </div>
          <div className="w-10 h-10 rounded-lg bg-sky-500/10 flex items-center justify-center text-sky-400">
            <Wifi className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-400 font-medium">{t.lanClients}</span>
            <div className="text-2xl font-black text-emerald-400 mt-0.5">{lanCount}</div>
          </div>
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center text-emerald-400">
            <Server className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Filter and Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-bold text-white">{t.clientsTitle}</h2>
          <p className="text-xs text-slate-400">{t.clientsDesc}</p>
        </div>

        <div className="flex items-center bg-slate-900 border border-slate-800 rounded-lg p-1 self-start">
          <button
            onClick={() => setFilter('all')}
            className={`px-3 py-1 text-xs font-medium rounded-md transition ${
              filter === 'all' ? 'bg-sky-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Alle ({clients.length})
          </button>
          <button
            onClick={() => setFilter('wifi')}
            className={`px-3 py-1 text-xs font-medium rounded-md transition ${
              filter === 'wifi' ? 'bg-sky-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            WLAN ({wifiCount})
          </button>
          <button
            onClick={() => setFilter('lan')}
            className={`px-3 py-1 text-xs font-medium rounded-md transition ${
              filter === 'lan' ? 'bg-sky-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            LAN ({lanCount})
          </button>
        </div>
      </div>

      {/* Clients Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/70 border-b border-slate-800 text-slate-400 font-semibold uppercase tracking-wider text-[11px]">
              <tr>
                <th className="py-3 px-4">{t.hostname}</th>
                <th className="py-3 px-4">{t.ipAddress}</th>
                <th className="py-3 px-4">{t.macAddress}</th>
                <th className="py-3 px-4">{t.connectionType}</th>
                <th className="py-3 px-4">{t.status}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {filteredClients.map((client) => (
                <tr key={client.mac} className="hover:bg-slate-800/30 transition">
                  <td className="py-3.5 px-4 font-sans font-medium text-white flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center shrink-0">
                      {getDeviceIcon(client.hostname, client.interface)}
                    </div>
                    <div>
                      <div className="text-slate-200">{client.hostname}</div>
                      {client.vendor && <div className="text-[10px] text-slate-400 font-mono">{client.vendor}</div>}
                    </div>
                  </td>
                  <td className="py-3.5 px-4 text-slate-300">
                    {client.ip}
                  </td>
                  <td className="py-3.5 px-4 text-slate-400">
                    {client.mac}
                  </td>
                  <td className="py-3.5 px-4 font-sans">
                    <span className={`px-2 py-0.5 rounded text-[11px] font-medium ${
                      client.interface === 'lan'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                        : client.interface === 'wifi_5g'
                        ? 'bg-sky-500/10 text-sky-400 border border-sky-500/30'
                        : 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/30'
                    }`}>
                      {client.interface === 'lan' ? 'Ethernet (LAN)' : client.interface === 'wifi_5g' ? 'Wi-Fi 5 GHz' : 'Wi-Fi 2.4 GHz'}
                      {client.signal ? ` (${client.signal} dBm)` : ''}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 font-sans">
                    <div className="flex items-center gap-1.5 text-emerald-400 text-xs">
                      <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                      <span>{t.online}</span>
                    </div>
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
