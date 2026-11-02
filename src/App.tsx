import React, { useState, useEffect } from 'react';
import { Language, RouterModel, RouterConfig } from './types';
import { translations } from './services/translations';
import { routerSimulator } from './services/routerSimulator';
import { Header } from './components/Header';
import { OverviewTab } from './components/OverviewTab';
import { ControlsTab } from './components/ControlsTab';
import { CellLockTab } from './components/CellLockTab';
import { NetworkClientsTab } from './components/NetworkClientsTab';
import { SmsTab } from './components/SmsTab';
import { DiagnosticsTab } from './components/DiagnosticsTab';
import { IntegrationDocsTab } from './components/IntegrationDocsTab';
import { SettingsTab } from './components/SettingsTab';
import {
  Signal,
  Sliders,
  Lock,
  Users,
  Mail,
  Activity,
  Layers,
  Settings,
  RotateCw,
} from 'lucide-react';

export function App() {
  const [lang, setLang] = useState<Language>('de');
  const [selectedModel, setSelectedModel] = useState<RouterModel>('ZTE G5TS');
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [isSimulated, setIsSimulated] = useState<boolean>(true);
  const [tick, setTick] = useState(0);

  const [config, setConfig] = useState<RouterConfig>({
    host: 'http://192.168.0.1',
    password: '',
    verifyTls: false,
    slowScanInterval: 60,
    fastScanInterval: 5,
    trackClients: true,
    clientConsiderHome: 180,
    mode: 'simulator',
  });

  // Subscribe to live router engine
  useEffect(() => {
    const unsub = routerSimulator.subscribe(() => {
      setTick((t) => t + 1);
    });
    return unsub;
  }, []);

  const t = translations[lang];

  const handleReboot = () => {
    if (window.confirm(t.restartConfirm)) {
      routerSimulator.rebootRouter(() => {
        alert(lang === 'de' ? 'Router wurde erfolgreich neu gestartet!' : 'Router successfully rebooted!');
      });
    }
  };

  const tabs = [
    { id: 'overview', label: t.tabOverview, icon: <Signal className="w-4 h-4" /> },
    { id: 'controls', label: t.tabControls, icon: <Sliders className="w-4 h-4" /> },
    { id: 'celllock', label: t.tabCellLock, icon: <Lock className="w-4 h-4" /> },
    {
      id: 'clients',
      label: t.tabClients,
      icon: <Users className="w-4 h-4" />,
      badge: routerSimulator.clients.length,
    },
    {
      id: 'sms',
      label: t.tabSms,
      icon: <Mail className="w-4 h-4" />,
      badge: routerSimulator.smsStorage.unreadCount > 0 ? routerSimulator.smsStorage.unreadCount : undefined,
      badgeColor: 'bg-amber-500',
    },
    { id: 'diagnostics', label: t.tabDiagnostics, icon: <Activity className="w-4 h-4" /> },
    { id: 'ha_docs', label: t.tabHaIntegration, icon: <Layers className="w-4 h-4 text-sky-400" /> },
    { id: 'settings', label: t.tabSettings, icon: <Settings className="w-4 h-4" /> },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Header */}
      <Header
        lang={lang}
        onLanguageChange={setLang}
        selectedModel={selectedModel}
        onModelChange={setSelectedModel}
        isSimulated={isSimulated}
        onModeToggle={() => setIsSimulated(!isSimulated)}
        onReboot={handleReboot}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 lg:px-8 py-6 space-y-6">
        {/* Navigation Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-2 border-b border-slate-800 scrollbar-none">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition shrink-0 cursor-pointer ${
                  isActive
                    ? 'bg-sky-600 text-white shadow-md shadow-sky-600/20'
                    : 'text-slate-400 hover:text-white hover:bg-slate-900'
                }`}
              >
                {tab.icon}
                <span>{tab.label}</span>
                {tab.badge !== undefined && (
                  <span
                    className={`px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
                      tab.badgeColor ? `${tab.badgeColor} text-white` : 'bg-slate-800 text-slate-200'
                    }`}
                  >
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>

        {/* Tab Content */}
        <div className="animate-fadeIn">
          {activeTab === 'overview' && (
            <OverviewTab
              radio={routerSimulator.radio}
              wan={routerSimulator.wanTraffic}
              lang={lang}
            />
          )}

          {activeTab === 'controls' && (
            <ControlsTab
              controls={routerSimulator.controls}
              lang={lang}
              onReboot={handleReboot}
            />
          )}

          {activeTab === 'celllock' && (
            <CellLockTab
              controls={routerSimulator.controls}
              radio={routerSimulator.radio}
              lang={lang}
            />
          )}

          {activeTab === 'clients' && (
            <NetworkClientsTab
              clients={routerSimulator.clients}
              lang={lang}
            />
          )}

          {activeTab === 'sms' && (
            <SmsTab
              messages={routerSimulator.smsMessages}
              storage={routerSimulator.smsStorage}
              lang={lang}
            />
          )}

          {activeTab === 'diagnostics' && (
            <DiagnosticsTab
              hardware={routerSimulator.hardware}
              lang={lang}
            />
          )}

          {activeTab === 'ha_docs' && (
            <IntegrationDocsTab lang={lang} />
          )}

          {activeTab === 'settings' && (
            <SettingsTab
              config={config}
              onConfigSave={(newConf) => setConfig(newConf)}
              lang={lang}
            />
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/80 py-4 text-center text-xs text-slate-500">
        <p>
          ZTE NG Router Home Assistant Custom Integration (G5TS / G5TC / G5C / G5 Max / G5 Ultra / MC801A / MC888) • Apache-2.0
        </p>
      </footer>
    </div>
  );
}

export default App;
