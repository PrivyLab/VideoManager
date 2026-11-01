import React, { useState, useEffect } from 'react';
import {
  Download, Search, Settings2, Sparkles, CheckCircle2, AlertCircle,
  Layers, Split, Folder, Shield, Globe, Cookie, Wifi, WifiOff, Loader2,
  ExternalLink
} from 'lucide-react';
import { inspectUrl, startDownload, formatDuration, getTorStatus } from '../api';
import { InspectResult, TorStatus } from '../types';

interface DownloadCardProps {
  currentFolder?: string;
  onDownloadStarted: () => void;
  onOpenFolderPicker: () => void;
}

export const DownloadCard: React.FC<DownloadCardProps> = ({
  currentFolder,
  onDownloadStarted,
  onOpenFolderPicker,
}) => {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [inspecting, setInspecting] = useState(false);
  const [inspectData, setInspectData] = useState<InspectResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Core options
  const [quality, setQuality] = useState('best');
  const [downloaderType, setDownloaderType] = useState<'auto' | 'ytdlp' | 'chunked' | 'segments'>('auto');
  const [numChunks, setNumChunks] = useState(4);
  const [segmentUrlsText, setSegmentUrlsText] = useState('');
  const [customTitle, setCustomTitle] = useState('');
  const [customFolderOverride, setCustomFolderOverride] = useState('');

  // Anti-blocking options
  const [referer, setReferer] = useState('');
  const [useTor, setUseTor] = useState(false);
  const [customProxy, setCustomProxy] = useState('');
  const [cookiesFromBrowser, setCookiesFromBrowser] = useState('');
  const [torStatus, setTorStatus] = useState<TorStatus | null>(null);
  const [checkingTor, setCheckingTor] = useState(false);

  // UI state
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showAntiBlock, setShowAntiBlock] = useState(false);

  const checkTorStatus = async () => {
    setCheckingTor(true);
    try {
      const status = await getTorStatus();
      setTorStatus(status);
    } catch {
      setTorStatus(null);
    } finally {
      setCheckingTor(false);
    }
  };

  // Auto-check Tor when anti-block panel opens
  useEffect(() => {
    if (showAntiBlock && !torStatus) {
      checkTorStatus();
    }
  }, [showAntiBlock]);

  // Auto-fill Referer from inspected page
  const handleInspect = async () => {
    if (!url.trim()) return;
    setInspecting(true);
    setError(null);
    try {
      const data = await inspectUrl(url.trim());
      setInspectData(data);
      if (data.info.title) setCustomTitle(data.info.title);
    } catch (err: any) {
      setError(err.message || 'Failed to inspect URL');
    } finally {
      setInspecting(false);
    }
  };

  const handleDownload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim() && downloaderType !== 'segments') return;
    if (downloaderType === 'segments' && !segmentUrlsText.trim()) {
      setError('Please provide at least one segment URL');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const segmentUrls = downloaderType === 'segments'
        ? segmentUrlsText.split('\n').map(s => s.trim()).filter(Boolean)
        : undefined;

      await startDownload({
        url: url.trim(),
        quality,
        downloader_type: downloaderType === 'segments' ? 'chunked' : downloaderType,
        custom_chunks: numChunks,
        chunk_urls: segmentUrls,
        custom_title: customTitle.trim() || undefined,
        download_folder: customFolderOverride.trim() || currentFolder || undefined,
        // Anti-blocking
        referer: referer.trim() || undefined,
        use_tor: useTor,
        custom_proxy: customProxy.trim() || undefined,
        cookies_from_browser: cookiesFromBrowser || undefined,
      });

      setUrl('');
      setInspectData(null);
      setSegmentUrlsText('');
      setCustomTitle('');
      onDownloadStarted();
    } catch (err: any) {
      setError(err.message || 'Failed to start download');
    } finally {
      setLoading(false);
    }
  };

  const torColor = torStatus?.running
    ? torStatus.is_tor ? 'text-brand-400' : 'text-amber-400'
    : 'text-slate-500';
  const torBg = torStatus?.running
    ? torStatus.is_tor ? 'bg-brand-500/10 border-brand-500/30' : 'bg-amber-500/10 border-amber-500/30'
    : 'bg-dark-700/40 border-dark-600';

  return (
    <div className="bg-dark-800/90 border border-dark-700 rounded-2xl p-6 shadow-xl relative overflow-hidden">
      <div className="absolute -top-24 -right-24 w-60 h-60 bg-brand-500/10 rounded-full blur-3xl pointer-events-none" />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <div>
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-brand-400" />
            Download Any Video
          </h2>
          <p className="text-xs text-slate-400">
            Universal streaming platform downloader & multi-chunk parallel engine.
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap justify-end">
          {/* Destination Folder Pill */}
          <button
            type="button"
            onClick={onOpenFolderPicker}
            className="flex items-center space-x-1.5 text-xs text-slate-300 hover:text-white bg-dark-900/90 hover:bg-dark-700 border border-dark-600 px-3 py-1.5 rounded-xl transition-all max-w-[200px] truncate group"
            title={`Download Destination: ${currentFolder}`}
          >
            <Folder className="h-3.5 w-3.5 text-brand-400 shrink-0" />
            <span className="truncate font-mono text-[11px]">
              {currentFolder ? currentFolder.split('/').pop() || currentFolder : 'Select Folder'}
            </span>
            <span className="text-[10px] text-brand-400 font-semibold bg-brand-500/10 px-1.5 py-0.5 rounded border border-brand-500/20 shrink-0">
              Change
            </span>
          </button>

          {/* Anti-Block Toggle */}
          <button
            type="button"
            onClick={() => setShowAntiBlock(!showAntiBlock)}
            className={`text-xs px-3 py-1.5 rounded-xl flex items-center gap-1.5 transition-all border ${
              showAntiBlock || useTor || referer || cookiesFromBrowser || customProxy
                ? 'bg-purple-500/20 text-purple-400 border-purple-500/40'
                : 'bg-dark-700/60 text-slate-400 hover:text-white border-dark-600'
            }`}
            title="Anti-blocking options: cookies, Tor proxy, Referer"
          >
            <Shield className="h-3.5 w-3.5" />
            <span>Anti-Block</span>
            {(useTor || cookiesFromBrowser || customProxy) && (
              <span className="h-1.5 w-1.5 rounded-full bg-purple-400 animate-pulse" />
            )}
          </button>

          {/* Advanced Engine Toggle */}
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className={`text-xs px-3 py-1.5 rounded-xl flex items-center gap-1.5 transition-all border ${
              showAdvanced
                ? 'bg-brand-500/20 text-brand-400 border-brand-500/40'
                : 'bg-dark-700/60 text-slate-400 hover:text-white border-dark-600'
            }`}
          >
            <Settings2 className="h-3.5 w-3.5" />
            <span>Options</span>
          </button>
        </div>
      </div>

      <form onSubmit={handleDownload} className="space-y-4">
        {/* Main URL Input or Segment List */}
        {downloaderType !== 'segments' ? (
          <div className="flex flex-col sm:flex-row gap-2">
            <div className="relative flex-1">
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="Paste video URL here (YouTube, Vimeo, direct MP4, streaming site...)"
                className="w-full bg-dark-900/90 border border-dark-600 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 text-slate-200 placeholder-slate-500 text-sm rounded-xl px-4 py-3 outline-none transition-all pr-24"
                required
              />
              {url && (
                <button
                  type="button"
                  onClick={handleInspect}
                  disabled={inspecting}
                  className="absolute right-2 top-2 bottom-2 px-3 bg-dark-700 hover:bg-dark-600 text-slate-300 text-xs font-medium rounded-lg flex items-center gap-1 transition-all"
                >
                  <Search className="h-3 w-3" />
                  {inspecting ? 'Inspecting...' : 'Inspect'}
                </button>
              )}
            </div>
            <button
              type="submit"
              disabled={loading || !url.trim()}
              className="bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white font-medium text-sm px-6 py-3 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-brand-600/30 transition-all shrink-0 cursor-pointer"
            >
              <Download className="h-4 w-4" />
              <span>{loading ? 'Starting...' : 'Download'}</span>
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
              <Split className="h-4 w-4 text-brand-400" />
              Direct Segment URLs (one URL per line):
            </label>
            <textarea
              value={segmentUrlsText}
              onChange={(e) => setSegmentUrlsText(e.target.value)}
              rows={4}
              placeholder="https://example.com/seg-1.ts&#10;https://example.com/seg-2.ts"
              className="w-full bg-dark-900 border border-dark-600 focus:border-brand-500 text-slate-200 text-xs rounded-xl p-3 font-mono outline-none"
            />
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={loading || !segmentUrlsText.trim()}
                className="bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white font-medium text-sm px-6 py-2.5 rounded-xl flex items-center gap-2"
              >
                <Layers className="h-4 w-4" />
                Fetch Chunks & Merge
              </button>
            </div>
          </div>
        )}

        {/* Inspection Result */}
        {inspectData && (
          <div className="bg-dark-900/80 border border-brand-500/30 rounded-xl p-4 flex flex-col sm:flex-row gap-4 items-start">
            {inspectData.info.thumbnail && (
              <img
                src={inspectData.info.thumbnail}
                alt="thumbnail"
                className="w-full sm:w-36 h-24 object-cover rounded-lg border border-dark-700 shrink-0"
              />
            )}
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-xs bg-brand-500/20 text-brand-400 px-2 py-0.5 rounded font-mono uppercase">
                  {inspectData.source}
                </span>
                {inspectData.info.duration > 0 && (
                  <span className="text-xs text-slate-400">
                    Duration: {formatDuration(inspectData.info.duration)}
                  </span>
                )}
                {inspectData.info.probe?.accept_ranges && (
                  <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-0.5 rounded flex items-center gap-1">
                    <CheckCircle2 className="h-3 w-3" /> Range Chunking Supported
                  </span>
                )}
              </div>
              <h3 className="text-sm font-semibold text-white mt-1 truncate">{inspectData.info.title}</h3>
              {inspectData.info.uploader && (
                <p className="text-xs text-slate-400 mt-0.5">By {inspectData.info.uploader}</p>
              )}
            </div>
          </div>
        )}

        {/* ── ANTI-BLOCKING PANEL ── */}
        {showAntiBlock && (
          <div className="bg-dark-900/70 border border-purple-500/20 rounded-xl p-4 space-y-4">
            <p className="text-[11px] font-semibold text-purple-400 uppercase tracking-widest flex items-center gap-1.5">
              <Shield className="h-3.5 w-3.5" /> Anti-Blocking & Bypass Options
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Referer */}
              <div>
                <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5 mb-1.5">
                  <Globe className="h-3.5 w-3.5 text-purple-400" />
                  Referer URL
                  <span className="text-[10px] text-slate-500">(webpage embedding the video)</span>
                </label>
                <input
                  type="url"
                  value={referer}
                  onChange={(e) => setReferer(e.target.value)}
                  placeholder="https://example.com/watch/video-page"
                  className="w-full bg-dark-800 border border-dark-600 focus:border-purple-500 text-slate-200 text-xs rounded-lg px-3 py-2 outline-none font-mono text-[11px]"
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  Paste the page URL where you found the video. Bypasses CDN anti-hotlink checks.
                </p>
              </div>

              {/* Cookies from Browser */}
              <div>
                <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5 mb-1.5">
                  <Cookie className="h-3.5 w-3.5 text-purple-400" />
                  Cookies from Browser
                </label>
                <select
                  value={cookiesFromBrowser}
                  onChange={(e) => setCookiesFromBrowser(e.target.value)}
                  className="w-full bg-dark-800 border border-dark-600 focus:border-purple-500 text-slate-200 text-xs rounded-lg px-3 py-2 outline-none"
                >
                  <option value="">None (No Cookies)</option>
                  <option value="chrome">Chrome</option>
                  <option value="firefox">Firefox</option>
                  <option value="safari">Safari</option>
                  <option value="edge">Microsoft Edge</option>
                  <option value="brave">Brave</option>
                </select>
                <p className="text-[10px] text-slate-500 mt-1">
                  Passes your real browser session cookies. Required for age-restricted or login-gated content.
                </p>
              </div>

              {/* Custom Proxy */}
              <div>
                <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5 mb-1.5">
                  <ExternalLink className="h-3.5 w-3.5 text-purple-400" />
                  Custom Proxy (optional)
                  <span className="text-[10px] text-slate-500">overrides Tor if set</span>
                </label>
                <input
                  type="text"
                  value={customProxy}
                  onChange={(e) => setCustomProxy(e.target.value)}
                  placeholder="socks5://127.0.0.1:9050  or  http://user:pass@host:port"
                  className="w-full bg-dark-800 border border-dark-600 focus:border-purple-500 text-slate-200 text-xs rounded-lg px-3 py-2 outline-none font-mono text-[10px]"
                />
                <p className="text-[10px] text-slate-500 mt-1">
                  Supports http://, https://, socks4://, socks5://. Leave blank to use Tor toggle below.
                </p>
              </div>

              {/* Tor Toggle */}
              <div>
                <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5 mb-1.5">
                  <Shield className="h-3.5 w-3.5 text-purple-400" />
                  Route Through Tor
                </label>

                {/* Tor Status Badge */}
                <div className={`border rounded-xl p-2.5 mb-2 text-xs ${torBg}`}>
                  <div className={`flex items-center justify-between ${torColor}`}>
                    <div className="flex items-center gap-1.5">
                      {checkingTor ? (
                        <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      ) : torStatus?.running ? (
                        <Wifi className="h-3.5 w-3.5" />
                      ) : (
                        <WifiOff className="h-3.5 w-3.5" />
                      )}
                      <span className="font-mono text-[11px]">
                        {checkingTor ? 'Checking Tor...'
                          : torStatus?.running
                            ? torStatus.is_tor
                              ? `✅ ${torStatus.source || 'Tor'} Active (Exit IP: ${torStatus.exit_ip})`
                              : `✅ ${torStatus.source || 'Tor'} Ready (${torStatus.proxy})`
                            : '❌ Tor not detected'}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={checkTorStatus}
                      className="text-[10px] text-slate-400 hover:text-slate-200 underline"
                    >
                      Re-check
                    </button>
                  </div>
                  {torStatus && !torStatus.running && torStatus.install_hint && (
                    <div className="mt-1.5 font-mono text-[10px] text-slate-400 bg-dark-900/60 px-2 py-1 rounded">
                      {torStatus.install_hint}
                    </div>
                  )}
                </div>

                <label className="flex items-center gap-2 cursor-pointer">
                  <div
                    onClick={() => setUseTor(!useTor)}
                    className={`relative w-10 h-5 rounded-full transition-colors cursor-pointer ${
                      useTor ? 'bg-purple-600' : 'bg-dark-600'
                    }`}
                  >
                    <div className={`absolute top-0.5 h-4 w-4 bg-white rounded-full shadow transition-all ${
                      useTor ? 'left-5' : 'left-0.5'
                    }`} />
                  </div>
                  <span className="text-xs text-slate-300">
                    {useTor ? `On — routing via ${torStatus?.proxy || 'socks5://127.0.0.1:9150'}` : 'Off'}
                  </span>
                </label>
              </div>
            </div>
          </div>
        )}

        {/* ── ENGINE / ADVANCED OPTIONS ── */}
        {showAdvanced && (
          <div className="bg-dark-900/60 border border-dark-700/80 rounded-xl p-4 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1.5">Downloader Engine</label>
                <select
                  value={downloaderType}
                  onChange={(e: any) => setDownloaderType(e.target.value)}
                  className="w-full bg-dark-800 border border-dark-600 text-slate-200 text-xs rounded-lg px-3 py-2 outline-none focus:border-brand-500"
                >
                  <option value="auto">Auto Select (Best Match)</option>
                  <option value="ytdlp">Universal Engine (yt-dlp)</option>
                  <option value="chunked">Parallel Range Chunk Engine</option>
                  <option value="segments">Explicit Segment List (Stitcher)</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1.5">Quality Preference</label>
                <select
                  value={quality}
                  onChange={(e) => setQuality(e.target.value)}
                  className="w-full bg-dark-800 border border-dark-600 text-slate-200 text-xs rounded-lg px-3 py-2 outline-none focus:border-brand-500"
                >
                  <option value="best">Best Available</option>
                  <option value="1080p">1080p Full HD</option>
                  <option value="720p">720p HD</option>
                  <option value="480p">480p SD</option>
                  <option value="audio">Audio Only</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1.5">
                  Chunk Segments Count ({numChunks})
                </label>
                <input
                  type="range" min="2" max="16" step="2" value={numChunks}
                  onChange={(e) => setNumChunks(parseInt(e.target.value))}
                  className="w-full accent-brand-500"
                />
                <div className="flex justify-between text-[10px] text-slate-400 mt-0.5">
                  <span>2</span><span>4</span><span>8</span><span>16</span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">Custom Output Title</label>
                <input
                  type="text"
                  value={customTitle}
                  onChange={(e) => setCustomTitle(e.target.value)}
                  placeholder="Leave blank to detect automatically"
                  className="w-full bg-dark-800 border border-dark-600 text-slate-200 text-xs rounded-lg px-3 py-2 outline-none focus:border-brand-500"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">Destination Folder Override</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={customFolderOverride}
                    onChange={(e) => setCustomFolderOverride(e.target.value)}
                    placeholder={currentFolder || "Default folder"}
                    className="flex-1 bg-dark-800 border border-dark-600 text-slate-200 text-xs rounded-lg px-3 py-2 outline-none focus:border-brand-500 font-mono text-[11px]"
                  />
                  <button
                    type="button"
                    onClick={onOpenFolderPicker}
                    className="px-3 bg-dark-700 hover:bg-dark-600 text-slate-300 rounded-lg text-xs flex items-center gap-1"
                  >
                    <Folder className="h-3 w-3" />
                    Browse
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 px-3 py-2 rounded-lg">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </form>
    </div>
  );
};
