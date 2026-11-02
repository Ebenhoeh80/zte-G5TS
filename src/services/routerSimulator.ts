import {
  RadioMetrics,
  WanAndTraffic,
  RouterControls,
  NetworkClientDevice,
  SmsMessage,
  SmsStorageInfo,
  SystemHardware,
} from '../types';

export class RouterStateEngine {
  private listeners: (() => void)[] = [];
  
  public radio: RadioMetrics = {
    networkType: '5G_NSA',
    provider: 'Telekom.de',
    signalBars: 4,
    rmcc: '262',
    rmnc: '01',
    activeBands: 'B3 + B20 + n78',
    totalBandwidthMHz: 90,
    
    // 4G primary
    ltePci: 124,
    lteEarfcn: 1300,
    lteBand: 'B3 (1800 MHz)',
    lteRsrp: -86,
    lteRsrq: -9.5,
    lteSinr: 16.4,
    lteRssi: -58,
    
    // 5G secondary
    nrPci: 488,
    nrArfcn: 641666,
    nrBand: 'n78 (3.5 GHz)',
    nrRsrp: -79,
    nrRsrq: -8.0,
    nrSinr: 24.2,
    nrRssi: -51,
    nrCellId: '003B2A10',
  };

  public wanTraffic: WanAndTraffic = {
    ipv4: '10.184.212.87',
    ipv6: '2a01:598:a102:400::1/64',
    wanStatus: 'ipv4_ipv6_connected',
    linkState: 'up',
    connectedSince: new Date(Date.now() - 3600 * 1000 * 48).toISOString(),
    uptimeSeconds: 172800,
    
    downloadSpeedBps: 420_000_000, // ~420 Mbit/s
    uploadSpeedBps: 68_000_000,   // ~68 Mbit/s
    
    dailyDownloadBytes: 14_850_000_000, // 14.85 GB
    dailyUploadBytes: 2_150_000_000,    // 2.15 GB
    monthlyDownloadBytes: 284_000_000_000, // 284 GB
    monthlyUploadBytes: 42_000_000_000,    // 42 GB
    
    dataLimitEnabled: false,
    dataLimitType: 'data_volume',
    dataLimitValue: '1000',
    warningThresholdPercent: 80,
    limitExceeded: false,
    autoReset: true,
    resetDay: 1,
    
    rxErrors: 0,
    txErrors: 0,
    rxDrops: 12,
    txDrops: 0,
  };

  public controls: RouterControls = {
    mobileDataEnabled: true,
    wifiMasterEnabled: true,
    wifi2gEnabled: true,
    wifi5gEnabled: true,
    oduLedEnabled: true,
    pausePollingUntil: null,
    cellLock4gEnabled: false,
    cellLock4gValue: '124,1300',
    cellLock5gEnabled: false,
    cellLock5gValue: '488,641666,78',
  };

  public clients: NetworkClientDevice[] = [
    {
      mac: 'F4:D4:88:51:2B:1A',
      ip: '192.168.0.102',
      hostname: 'iPhone-16-Pro',
      interface: 'wifi_5g',
      connected: true,
      lastSeen: new Date().toISOString(),
      signal: -48,
      vendor: 'Apple Inc.',
    },
    {
      mac: '3C:06:30:A4:1F:C8',
      ip: '192.168.0.105',
      hostname: 'MacBook-Pro-M3',
      interface: 'wifi_5g',
      connected: true,
      lastSeen: new Date().toISOString(),
      signal: -54,
      vendor: 'Apple Inc.',
    },
    {
      mac: 'DC:A6:32:8B:71:4E',
      ip: '192.168.0.110',
      hostname: 'Home-Assistant-Green',
      interface: 'lan',
      connected: true,
      lastSeen: new Date().toISOString(),
      vendor: 'Raspberry Pi / Nabu Casa',
    },
    {
      mac: 'A4:C1:38:29:EE:12',
      ip: '192.168.0.120',
      hostname: 'Sony-Bravia-OLED',
      interface: 'lan',
      connected: true,
      lastSeen: new Date().toISOString(),
      vendor: 'Sony Interactive',
    },
    {
      mac: '50:EC:50:81:4A:2D',
      ip: '192.168.0.145',
      hostname: 'Philips-Hue-Bridge',
      interface: 'wifi_2g',
      connected: true,
      lastSeen: new Date().toISOString(),
      signal: -62,
      vendor: 'Signify Netherlands B.V.',
    },
  ];

  public smsMessages: SmsMessage[] = [
    {
      id: '101',
      number: 'Telekom',
      date: '2026-11-01 10:14:22',
      content: 'Lieber Kunde, Ihr monatliches Inklusiv-Highspeed-Volumen steht Ihnen weiterhin ungedrosselt zur Verfügung. Ihr Team.',
      unread: false,
      storage: 'nv',
    },
    {
      id: '102',
      number: '+491705551234',
      date: '2026-11-02 08:32:10',
      content: 'ZTE Router Alert: 5G Carrier Aggregation active on Cell 003B2A10.',
      unread: true,
      storage: 'nv',
    },
    {
      id: '103',
      number: 'Speedtest.net',
      date: '2026-10-29 18:05:00',
      content: 'Ihr Verifizierungscode für den Router-Durchsatztest lautet: 849201.',
      unread: false,
      storage: 'sim',
    },
  ];

  public smsStorage: SmsStorageInfo = {
    unreadCount: 1,
    totalCount: 3,
    simTotal: 20,
    simUsed: 1,
    nvTotal: 200,
    nvUsed: 2,
  };

  public hardware: SystemHardware = {
    model: 'ZTE G5TS',
    hardwareVersion: 'G5TSHW1.0',
    firmwareVersion: 'BD_G5TSV1.0.0B08',
    cpuUsage: 14,
    ramUsage: 42,
    cpuTemp: 44,
    modemTemp: 41,
    paTempLevel: 'Normal',
    tjTempLevel: 'Normal',
    firmwareStatus: 'up_to_date',
    gnssFix: true,
    gnssLatitude: 48.137154,
    gnssLongitude: 11.576124,
  };

  private timer: any = null;
  public isRebooting = false;

  constructor() {
    this.startLiveSimulation();
  }

  public subscribe(listener: () => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  private notify(): void {
    this.listeners.forEach((l) => l());
  }

  private startLiveSimulation(): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = setInterval(() => {
      if (this.isRebooting) return;

      // Small realistic fluctuations in signal & throughput
      if (this.controls.mobileDataEnabled) {
        const jitter = (Math.random() - 0.5) * 40_000_000;
        this.wanTraffic.downloadSpeedBps = Math.max(120_000_000, Math.min(680_000_000, 420_000_000 + jitter));
        this.wanTraffic.uploadSpeedBps = Math.max(25_000_000, Math.min(95_000_000, 68_000_000 + (Math.random() - 0.5) * 15_000_000));
        
        // Add to daily traffic
        const bytesDelta = Math.floor(this.wanTraffic.downloadSpeedBps / 8);
        this.wanTraffic.dailyDownloadBytes += bytesDelta;
        this.wanTraffic.monthlyDownloadBytes += bytesDelta;
      } else {
        this.wanTraffic.downloadSpeedBps = 0;
        this.wanTraffic.uploadSpeedBps = 0;
      }

      // Fluctuations in RF metrics
      this.radio.nrRsrp = Math.round(-79 + (Math.random() - 0.5) * 3);
      this.radio.nrSinr = Math.round((24.2 + (Math.random() - 0.5) * 2) * 10) / 10;
      this.radio.lteRsrp = Math.round(-86 + (Math.random() - 0.5) * 2);

      // Hardware CPU / RAM
      this.hardware.cpuUsage = Math.max(8, Math.min(38, Math.round(14 + (Math.random() - 0.5) * 8)));
      this.hardware.ramUsage = Math.max(38, Math.min(48, Math.round(42 + (Math.random() - 0.5) * 2)));

      // Check pause polling expiration
      if (this.controls.pausePollingUntil && Date.now() > this.controls.pausePollingUntil) {
        this.controls.pausePollingUntil = null;
      }

      this.notify();
    }, 1500);
  }

  // Action methods
  public toggleMobileData(): void {
    this.controls.mobileDataEnabled = !this.controls.mobileDataEnabled;
    this.wanTraffic.wanStatus = this.controls.mobileDataEnabled ? 'ipv4_ipv6_connected' : 'disconnected';
    this.notify();
  }

  public toggleWifiMaster(): void {
    this.controls.wifiMasterEnabled = !this.controls.wifiMasterEnabled;
    this.notify();
  }

  public toggleWifi2g(): void {
    this.controls.wifi2gEnabled = !this.controls.wifi2gEnabled;
    this.notify();
  }

  public toggleWifi5g(): void {
    this.controls.wifi5gEnabled = !this.controls.wifi5gEnabled;
    this.notify();
  }

  public toggleOduLed(): void {
    this.controls.oduLedEnabled = !this.controls.oduLedEnabled;
    this.notify();
  }

  public pausePollingFiveMinutes(): void {
    this.controls.pausePollingUntil = Date.now() + 5 * 60 * 1000;
    this.notify();
  }

  public resumePolling(): void {
    this.controls.pausePollingUntil = null;
    this.notify();
  }

  public rebootRouter(onComplete?: () => void): void {
    this.isRebooting = true;
    this.wanTraffic.wanStatus = 'disconnected';
    this.wanTraffic.downloadSpeedBps = 0;
    this.wanTraffic.uploadSpeedBps = 0;
    this.notify();

    setTimeout(() => {
      this.isRebooting = false;
      this.wanTraffic.wanStatus = 'ipv4_ipv6_connected';
      this.wanTraffic.connectedSince = new Date().toISOString();
      this.wanTraffic.uptimeSeconds = 0;
      this.notify();
      if (onComplete) onComplete();
    }, 4000);
  }

  public toggleCellLock4g(value?: string): void {
    if (value) this.controls.cellLock4gValue = value;
    this.controls.cellLock4gEnabled = !this.controls.cellLock4gEnabled;
    this.notify();
  }

  public toggleCellLock5g(value?: string): void {
    if (value) this.controls.cellLock5gValue = value;
    this.controls.cellLock5gEnabled = !this.controls.cellLock5gEnabled;
    this.notify();
  }

  public sendSms(number: string, content: string): boolean {
    if (!number.trim() || !content.trim()) return false;
    const newMsg: SmsMessage = {
      id: String(Date.now()),
      number: number.trim(),
      date: new Date().toISOString().replace('T', ' ').substring(0, 19),
      content: content.trim(),
      unread: false,
      storage: 'nv',
    };
    this.smsMessages.unshift(newMsg);
    this.smsStorage.totalCount += 1;
    this.smsStorage.nvUsed += 1;
    this.notify();
    return true;
  }

  public markSmsRead(id: string): void {
    const msg = this.smsMessages.find((m) => m.id === id);
    if (msg && msg.unread) {
      msg.unread = false;
      this.smsStorage.unreadCount = Math.max(0, this.smsStorage.unreadCount - 1);
      this.notify();
    }
  }

  public checkFirmware(): void {
    this.hardware.firmwareStatus = 'checking';
    this.notify();
    setTimeout(() => {
      this.hardware.firmwareStatus = 'up_to_date';
      this.notify();
    }, 2500);
  }
}

export const routerSimulator = new RouterStateEngine();
