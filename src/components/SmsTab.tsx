import React, { useState } from 'react';
import { SmsMessage, SmsStorageInfo, Language } from '../types';
import { translations } from '../services/translations';
import { routerSimulator } from '../services/routerSimulator';
import {
  Mail,
  Send,
  HardDrive,
  Cpu,
  CheckCircle2,
  AlertCircle,
  Inbox,
  Clock,
  User,
} from 'lucide-react';

interface SmsTabProps {
  messages: SmsMessage[];
  storage: SmsStorageInfo;
  lang: Language;
}

export const SmsTab: React.FC<SmsTabProps> = ({ messages, storage, lang }) => {
  const t = translations[lang];

  const [destNumber, setDestNumber] = useState('');
  const [content, setContent] = useState('');
  const [toast, setToast] = useState<string | null>(null);

  const handleSendSms = (e: React.FormEvent) => {
    e.preventDefault();
    if (!destNumber.trim()) {
      setToast('Bitte Empfängernummer eingeben');
      return;
    }
    if (!content.trim()) {
      setToast('Nachrichtentext darf nicht leer sein');
      return;
    }

    const ok = routerSimulator.sendSms(destNumber, content);
    if (ok) {
      setToast(t.smsSentSuccess);
      setContent('');
      setTimeout(() => setToast(null), 3000);
    }
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

      {/* Storage Breakdown */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-400 font-medium">{t.totalSms}</span>
            <div className="text-2xl font-black text-white mt-0.5">{storage.totalCount}</div>
          </div>
          <div className="w-10 h-10 rounded-lg bg-sky-500/10 flex items-center justify-center text-sky-400">
            <Inbox className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-400 font-medium">{t.unread}</span>
            <div className="text-2xl font-black text-amber-400 mt-0.5">{storage.unreadCount}</div>
          </div>
          <div className="w-10 h-10 rounded-lg bg-amber-500/10 flex items-center justify-center text-amber-400">
            <Mail className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2">
            <span>{t.storageStatus}</span>
            <span className="font-mono text-slate-200">{storage.nvUsed}/{storage.nvTotal} NV</span>
          </div>
          <div className="w-full bg-slate-800 h-2.5 rounded-full overflow-hidden">
            <div
              className="bg-sky-500 h-full rounded-full transition-all"
              style={{ width: `${(storage.nvUsed / storage.nvTotal) * 100}%` }}
            />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Inbox List (2 columns on lg) */}
        <div className="lg:col-span-2 space-y-3">
          <h3 className="font-bold text-sm text-white flex items-center gap-2">
            <Mail className="w-4 h-4 text-sky-400" />
            {t.inbox} ({messages.length})
          </h3>

          <div className="space-y-2.5">
            {messages.map((msg) => (
              <div
                key={msg.id}
                onClick={() => routerSimulator.markSmsRead(msg.id)}
                className={`bg-slate-900 border rounded-xl p-4 transition cursor-pointer ${
                  msg.unread
                    ? 'border-sky-500/60 bg-sky-950/20 shadow-md shadow-sky-500/5'
                    : 'border-slate-800 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-full bg-slate-800 flex items-center justify-center text-slate-300">
                      <User className="w-3.5 h-3.5" />
                    </div>
                    <span className="font-bold text-xs text-white">{msg.number}</span>
                    {msg.unread && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-sky-500 text-white">
                        NEW
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
                    <span className="px-1.5 py-0.5 rounded bg-slate-800 text-[10px]">
                      {msg.storage.toUpperCase()}
                    </span>
                    <span className="flex items-center gap-1 text-[11px]">
                      <Clock className="w-3 h-3" />
                      {msg.date}
                    </span>
                  </div>
                </div>

                <p className="text-xs text-slate-300 leading-relaxed font-sans pl-8">
                  {msg.content}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Compose & Send Box */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 h-fit">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-800">
            <Send className="w-4 h-4 text-sky-400" />
            <h3 className="font-bold text-sm text-white">{t.composeTitle}</h3>
          </div>

          <form onSubmit={handleSendSms} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                {t.recipientNumber}
              </label>
              <input
                type="text"
                value={destNumber}
                onChange={(e) => setDestNumber(e.target.value)}
                placeholder={t.recipientPlaceholder}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 outline-none focus:border-sky-500 font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                {t.smsContent}
              </label>
              <textarea
                rows={4}
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="Hallo, Router-Testnachricht..."
                className="w-full bg-slate-950 border border-slate-700 rounded-lg p-3 text-xs text-slate-200 outline-none focus:border-sky-500 resize-none font-sans"
              />
              <div className="text-right text-[10px] text-slate-400 mt-1">
                {content.length}/160 Zeichen (GSM-7 / UCS-2 Auto)
              </div>
            </div>

            <button
              type="submit"
              className="w-full py-2.5 rounded-lg bg-sky-600 hover:bg-sky-500 text-white font-bold text-xs transition flex items-center justify-center gap-2 shadow-lg shadow-sky-600/20 cursor-pointer"
            >
              <Send className="w-3.5 h-3.5" />
              {t.sendSmsButton}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};
