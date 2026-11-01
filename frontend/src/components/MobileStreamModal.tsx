import React, { useState, useEffect } from 'react';
import {
  X,
  Smartphone,
  Wifi,
  Copy,
  Check,
  ExternalLink,
  Sparkles,
  Info,
  Loader2,
  ShieldCheck,
  RefreshCw,
  Lock
} from 'lucide-react';
import { VideoItem } from '../types';
import {
  formatBytes,
  formatDuration,
  getVideoShareLink,
  VideoShareLink,
  regeneratePin,
  updatePinConfig
} from '../api';

interface MobileStreamModalProps {
  video: VideoItem;
  onClose: () => void;
}

export const MobileStreamModal: React.FC<MobileStreamModalProps> = ({ video, onClose }) => {
  const [loading, setLoading] = useState(true);
  const [shareData, setShareData] = useState<VideoShareLink | null>(null);
  const [customIp, setCustomIp] = useState('');
  const [customPort, setCustomPort] = useState('8000');
  const [pin, setPin] = useState('');
  const [pinEnabled, setPinEnabled] = useState(true);
  const [copied, setCopied] = useState(false);
  const [pinCopied, setPinCopied] = useState(false);
  const [regenerating, setRegenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getVideoShareLink(video.id)
      .then((data) => {
        setShareData(data);
        setCustomIp(data.local_ip);
        setCustomPort(String(data.port));
        setPin(data.pin || '');
        setPinEnabled(data.pin_enabled ?? true);
      })
      .catch((err) => {
        setError(err.message || 'Failed to detect network IP');
      })
      .finally(() => setLoading(false));
  }, [video.id]);

  const activeIp = customIp.trim() || shareData?.local_ip || '127.0.0.1';
  const activePort = customPort.trim() || '8000';

  const queryParams = new URLSearchParams();
  if (pinEnabled && pin) {
    queryParams.set('p', pin);
  }
  const authQuery = queryParams.toString() ? `?${queryParams.toString()}` : '';
  const streamUrl = `http://${activeIp}:${activePort}/watch/${video.id}${authQuery}`;

  const qrParams = new URLSearchParams({
    ip: activeIp,
    port: activePort,
  });
  if (pinEnabled && pin) {
    qrParams.set('p', pin);
  }
  const qrSvgUrl = `/api/videos/${video.id}/qr.svg?${qrParams.toString()}`;

  const handleCopy = () => {
    navigator.clipboard.writeText(streamUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const handleCopyPin = () => {
    if (!pin) return;
    navigator.clipboard.writeText(pin);
    setPinCopied(true);
    setTimeout(() => setPinCopied(false), 2500);
  };

  const handleRegeneratePin = async () => {
    setRegenerating(true);
    try {
      const res = await regeneratePin(video.id);
      setPin(res.pin);
    } catch (err: any) {
      setError(err.message || 'Failed to regenerate PIN');
    } finally {
      setRegenerating(false);
    }
  };

  const handleTogglePin = async () => {
    const nextState = !pinEnabled;
    setPinEnabled(nextState);
    try {
      const res = await updatePinConfig(video.id, { pin_enabled: nextState });
      setPinEnabled(res.pin_enabled);
    } catch (err: any) {
      setPinEnabled(!nextState);
      setError(err.message || 'Failed to update PIN config');
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-dark-900 border border-dark-700 w-full max-w-lg rounded-2xl shadow-2xl flex flex-col max-h-[92vh] overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-dark-800 bg-dark-800/40">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center text-white shadow-lg shadow-emerald-500/20">
              <Smartphone className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white flex items-center gap-2">
                Watch on Phone
                <span className="text-[10px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full font-mono uppercase flex items-center gap-1 font-semibold">
                  <ShieldCheck className="h-3 w-3" /> Encrypted Wi-Fi
                </span>
              </h3>
              <p className="text-xs text-slate-400 truncate max-w-xs">
                {video.title || 'Local Streaming'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-dark-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-5 text-center">
          {loading ? (
            <div className="py-12 flex flex-col items-center justify-center gap-3 text-slate-400">
              <Loader2 className="h-8 w-8 animate-spin text-emerald-400" />
              <span className="text-xs">Detecting local Wi-Fi address &amp; generating encryption keys...</span>
            </div>
          ) : (
            <>
              {/* QR Code Container */}
              <div className="flex flex-col items-center justify-center space-y-3">
                <div className="p-4 bg-white rounded-2xl shadow-2xl border border-slate-200 inline-block transition-transform hover:scale-105 duration-200">
                  <img
                    src={qrSvgUrl}
                    alt="Scan with phone"
                    className="w-64 h-64 object-contain block select-none"
                  />
                </div>

                <div className="space-y-1">
                  <p className="text-xs font-semibold text-white flex items-center justify-center gap-1.5">
                    <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
                    Scan with iPhone or Android Camera
                  </p>
                  <p className="text-[11px] text-slate-400 max-w-sm mx-auto leading-relaxed">
                    Point your camera at the QR code. The cryptographic signature automatically unlocks playback without manual typing.
                  </p>
                </div>
              </div>

              {/* Wi-Fi Security & PIN Box */}
              <div className="bg-dark-800/60 border border-dark-700/80 rounded-xl p-3 text-left space-y-2.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
                    <Lock className="h-3.5 w-3.5 text-emerald-400" />
                    <span>Wi-Fi Shield &amp; Stream PIN</span>
                  </div>
                  <button
                    type="button"
                    onClick={handleTogglePin}
                    className={`text-[10px] px-2 py-0.5 rounded-full font-mono font-medium transition-colors border ${pinEnabled
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20'
                        : 'bg-slate-800 text-slate-400 border-slate-700 hover:bg-slate-700'
                      }`}
                  >
                    {pinEnabled ? 'PIN Protection: ON' : 'PIN Protection: OFF'}
                  </button>
                </div>

                <div className="flex items-center justify-between bg-dark-900/90 border border-dark-700 rounded-lg p-2.5">
                  <div>
                    <span className="text-[10px] text-slate-400 block font-medium">Access PIN (for devices without QR):</span>
                    <span className="text-base font-mono font-bold tracking-widest text-emerald-400">
                      {pinEnabled ? pin : 'None (Open)'}
                    </span>
                  </div>
                  {pinEnabled && (
                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        onClick={handleCopyPin}
                        className="px-2 py-1 bg-dark-800 hover:bg-dark-700 text-slate-300 text-xs rounded-md font-medium flex items-center gap-1 transition-colors"
                        title="Copy PIN"
                      >
                        {pinCopied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                        <span>{pinCopied ? 'Copied' : 'Copy'}</span>
                      </button>
                      <button
                        type="button"
                        onClick={handleRegeneratePin}
                        disabled={regenerating}
                        className="p-1.5 bg-dark-800 hover:bg-dark-700 text-slate-300 hover:text-white rounded-md transition-colors"
                        title="Generate fresh 4-digit PIN"
                      >
                        <RefreshCw className={`h-3.5 w-3.5 ${regenerating ? 'animate-spin' : ''}`} />
                      </button>
                    </div>
                  )}
                </div>
                <p className="text-[10px] text-slate-400 leading-relaxed">
                  🛡️ <strong>Encrypted Access:</strong> Anyone on your Wi-Fi network who visits this link without your QR token or PIN is blocked with Access Denied.
                </p>
              </div>

              {/* Streaming URL Bar */}
              <div className="bg-dark-800/80 border border-dark-700 rounded-xl p-2.5 flex items-center justify-between gap-2 text-left">
                <div className="min-w-0 flex-1 px-1">
                  <span className="text-[10px] text-slate-400 block font-medium">Encrypted Wi-Fi Link:</span>
                  <span className="font-mono text-xs text-emerald-400 truncate block font-semibold select-all">
                    {streamUrl}
                  </span>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    type="button"
                    onClick={handleCopy}
                    className="px-2.5 py-1.5 bg-dark-700 hover:bg-dark-600 text-slate-200 text-xs rounded-lg font-medium flex items-center gap-1 transition-colors"
                  >
                    {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                    <span>{copied ? 'Copied' : 'Copy'}</span>
                  </button>
                  <a
                    href={streamUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="p-1.5 bg-dark-700 hover:bg-dark-600 text-slate-300 hover:text-white rounded-lg transition-colors"
                    title="Test Open Mobile Player Page"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                  </a>
                </div>
              </div>

              {/* Network IP / Port Editor */}
              <div className="bg-dark-800/40 border border-dark-700/80 rounded-xl p-3 text-left space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-[11px] font-medium text-slate-300 flex items-center gap-1">
                    <Wifi className="h-3 w-3 text-emerald-400" />
                    Detected Local IP &amp; Port:
                  </label>
                  <span className="text-[10px] text-slate-400">Same Wi-Fi Required</span>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div className="col-span-2">
                    <input
                      type="text"
                      value={customIp}
                      onChange={(e) => setCustomIp(e.target.value)}
                      placeholder="e.g. 192.168.1.44"
                      className="w-full bg-dark-900 border border-dark-700 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-200 outline-none focus:border-emerald-500"
                    />
                  </div>
                  <div>
                    <input
                      type="text"
                      value={customPort}
                      onChange={(e) => setCustomPort(e.target.value)}
                      placeholder="8000"
                      className="w-full bg-dark-900 border border-dark-700 rounded-lg px-2.5 py-1.5 text-xs font-mono text-slate-200 outline-none focus:border-emerald-500"
                    />
                  </div>
                </div>
              </div>

              {/* Wi-Fi Note */}
              <div className="flex items-start gap-2 p-3 bg-emerald-500/5 border border-emerald-500/20 rounded-xl text-left text-[11px] text-emerald-300/90 leading-relaxed">
                <Info className="h-4 w-4 shrink-0 text-emerald-400 mt-0.5" />
                <span>
                  <strong>Zero mobile data consumed:</strong> Video is streamed peer-to-peer across your home router. You can also save the video directly into your phone’s Photos or Files app from the mobile player page!
                </span>
              </div>
            </>
          )}

          {error && (
            <p className="text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 p-2.5 rounded-xl">
              {error}
            </p>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-dark-800 bg-dark-800/40 flex items-center justify-between">
          <span className="text-[11px] text-slate-400 font-mono">
            {formatBytes(video.file_size)} · {formatDuration(video.duration)}
          </span>
          <button
            onClick={onClose}
            className="px-5 py-2 bg-dark-700 hover:bg-dark-600 text-white rounded-xl text-xs font-medium transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
