export type Language = 'de' | 'en';

export type RouterModel = 'ZTE G5TS' | 'ZTE G5TC' | 'ZTE G5C' | 'ZTE G5 Max' | 'ZTE G5 Ultra' | 'ZTE MC801A' | 'ZTE MC888';

export interface RadioMetrics {
  networkType: string; // e.g. "5G_NSA" | "5G_SA" | "LTE"
  provider: string; // e.g. "Telekom.de", "Vodafone.de", "A1"
  signalBars: number; // 0 to 5
  rmcc: string; // e.g. "262"
  rmnc: string; // e.g. "01"
  activeBands: string; // e.g. "B3 + B20 + n78"
  totalBandwidthMHz: number; // e.g. 90
  
  // 4G LTE metrics
  ltePci: number;
  lteEarfcn: number;
  lteBand: string;
  lteRsrp: number; // dBm
  lteRsrq: number; // dB
  lteSinr: number; // dB
  lteRssi: number; // dBm
  
  // 5G NR metrics
  nrPci: number;
  nrArfcn: number;
  nrBand: string;
  nrRsrp: number; // dBm
  nrRsrq: number; // dB
  nrSinr: number; // dB
  nrRssi: number; // dBm
  nrCellId: string;
}

export interface WanAndTraffic {
  ipv4: string;
  ipv6: string;
  wanStatus: string; // "ipv4_ipv6_connected"
  linkState: string; // "up"
  connectedSince: string; // ISO timestamp
  uptimeSeconds: number;
  
  // Real-time rates
  downloadSpeedBps: number;
  uploadSpeedBps: number;
  
  // Daily & Monthly counters
  dailyDownloadBytes: number;
  dailyUploadBytes: number;
  monthlyDownloadBytes: number;
  monthlyUploadBytes: number;
  
  // Limits
  dataLimitEnabled: boolean;
  dataLimitType: 'data_volume' | 'connection_time';
  dataLimitValue: string; // e.g. "100" (GB)
  warningThresholdPercent: number; // e.g. 80
  limitExceeded: boolean;
  autoReset: boolean;
  resetDay: number; // 1-31
  
  // Packets
  rxErrors: number;
  txErrors: number;
  rxDrops: number;
  txDrops: number;
}

export interface RouterControls {
  mobileDataEnabled: boolean;
  wifiMasterEnabled: boolean;
  wifi2gEnabled: boolean;
  wifi5gEnabled: boolean;
  oduLedEnabled: boolean;
  pausePollingUntil: number | null; // timestamp ms
  cellLock4gEnabled: boolean;
  cellLock4gValue: string; // "PCI,EARFCN"
  cellLock5gEnabled: boolean;
  cellLock5gValue: string; // "PCI,ARFCN,BAND"
}

export interface NetworkClientDevice {
  mac: string;
  ip: string;
  ipv6?: string;
  hostname: string;
  interface: 'wifi_2g' | 'wifi_5g' | 'lan';
  connected: boolean;
  lastSeen: string;
  signal?: number; // for wifi clients
  vendor?: string;
  missingSince?: number; // timestamp
}

export interface SmsMessage {
  id: string;
  number: string;
  date: string;
  content: string;
  unread: boolean;
  storage: 'sim' | 'nv';
}

export interface SmsStorageInfo {
  unreadCount: number;
  totalCount: number;
  simTotal: number;
  simUsed: number;
  nvTotal: number;
  nvUsed: number;
}

export interface SystemHardware {
  model: RouterModel;
  hardwareVersion: string;
  firmwareVersion: string;
  cpuUsage: number; // percentage
  ramUsage: number; // percentage
  cpuTemp: number; // Celsius
  modemTemp: number; // Celsius
  paTempLevel: string; // "Normal"
  tjTempLevel: string; // "Normal"
  firmwareStatus: 'up_to_date' | 'checking' | 'update_available' | 'downloading';
  latestFirmwareVersion?: string;
  downloadProgress?: number;
  gnssFix: boolean;
  gnssLatitude?: number;
  gnssLongitude?: number;
}

export interface RouterConfig {
  host: string;
  password: string;
  verifyTls: boolean;
  slowScanInterval: number;
  fastScanInterval: number;
  trackClients: boolean;
  clientConsiderHome: number;
  mode: 'simulator' | 'live';
}
