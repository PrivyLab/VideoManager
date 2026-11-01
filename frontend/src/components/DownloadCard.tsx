import React, { useState, useEffect } from 'react';
import {
  Download, Search, Settings2, Sparkles, CheckCircle2, AlertCircle,
  Layers, Split, Folder, Shield, Globe, Cookie, Wifi, WifiOff, Loader2,
  ExternalLink, Zap, Scissors, ListFilter, ListOrdered, Film, ListPlus
} from 'lucide-react';
import {
  inspectUrl,
  startDownload,
  startBatchDownload,
  inspectPlaylist,
  formatDuration,
  getTorStatus,
  getNetworkStatus
} from '../api';
import {
  InspectResult,
  TorStatus,
  NetworkStatusResponse,
  PlaylistInspectResponse
} from '../types';

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

  // Pre-download section trimming
  const [trimEnabled, setTrimEnabled] = useState(false);
  const [trimStart, setTrimStart] = useState('');
  const [trimEnd, setTrimEnd] = useState('');

  // Anti-blocking options
  const [referer, setReferer] = useState('');
  const [useTor, setUseTor] = useState(false);
  const [customProxy, setCustomProxy] = useState('');
  const [cookiesFromBrowser, setCookiesFromBrowser] = useState('');
  const [torStatus, setTorStatus] = useState<TorStatus | null>(null);
  const [networkStatus, setNetworkStatus] = useState<NetworkStatusResponse | null>(null);
  const [routingMode, setRoutingMode] = useState<'direct' | 'warp' | 'tor'>('direct');
  const [checkingTor, setCheckingTor] = useState(false);

  // UI state
  const [downloadMode, setDownloadMode] = useState<'single' | 'batch' | 'playlist'>('single');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showAntiBlock, setShowAntiBlock] = useState(false);

  // Batch URLs state
  const [batchUrlsText, setBatchUrlsText] = useState('');

  // Playlist & Series state
  const [playlistUrl, setPlaylistUrl] = useState('');
  const [playlistLoading, setPlaylistLoading] = useState(false);
  const [playlistData, setPlaylistData] = useState<PlaylistInspectResponse | null>(null);
  const [selectedEpisodeIds, setSelectedEpisodeIds] = useState<Set<string>>(new Set());
  const [batchSuccessMsg, setBatchSuccessMsg] = useState<string | null>(null);

  const checkNetwork = async () => {
    setCheckingTor(true);
    try {
      const net = await getNetworkStatus();
      setNetworkStatus(net);
      setTorStatus({
        running: net.tor.is_active,
        proxy: net.tor.proxy,
        source: net.tor.source,
        message: net.tor.message,
      });
    } catch {
      // Fallback to basic tor status
      try {
        const status = await getTorStatus();
        setTorStatus(status);
      } catch {
        setTorStatus(null);
      }
    } finally {
      setCheckingTor(false);
    }
  };

  // Auto-check network status when anti-block panel opens
  useEffect(() => {
    if (showAntiBlock && !networkStatus) {
      checkNetwork();
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
        use_tor: routingMode === 'tor' || useTor,
        routing_mode: routingMode,
        custom_proxy: customProxy.trim() || undefined,
        cookies_from_browser: cookiesFromBrowser || undefined,
        // Pre-download section trimming
        trim_start: trimEnabled && trimStart.trim() ? trimStart.trim() : undefined,
        trim_end: trimEnabled && trimEnd.trim() ? trimEnd.trim() : undefined,
      });

      setUrl('');
      setInspectData(null);
      setSegmentUrlsText('');
      setCustomTitle('');
      if (trimEnabled) {
        setTrimStart('');
        setTrimEnd('');
        setTrimEnabled(false);
      }
      onDownloadStarted();
    } catch (err: any) {
      setError(err.message || 'Failed to start download');
    } finally {
      setLoading(false);
    }
  };

  // Batch URL handler
  const handleBatchDownload = async (e: React.FormEvent) => {
    e.preventDefault();
    const urls = batchUrlsText
      .split('\n')
      .map((u) => u.trim())
      .filter((u) => u.length > 0 && !u.startsWith('#'));

    if (urls.length === 0) {
      setError('Please enter at least one valid video URL');
      return;
    }

    setLoading(true);
    setError(null);
    setBatchSuccessMsg(null);
    try {
      const res = await startBatchDownload({
        urls,
        quality,
        downloader_type: downloaderType === 'segments' ? 'auto' : downloaderType,
        custom_chunks: numChunks,
        download_folder: customFolderOverride.trim() || currentFolder || undefined,
        referer: referer.trim() || undefined,
        use_tor: routingMode === 'tor' || useTor,
        routing_mode: routingMode,
        custom_proxy: customProxy.trim() || undefined,
        cookies_from_browser: cookiesFromBrowser || undefined,
      });

      setBatchUrlsText('');
      setBatchSuccessMsg(`Successfully queued ${res.count} videos for sequential download!`);
      setTimeout(() => setBatchSuccessMsg(null), 6000);
      onDownloadStarted();
    } catch (err: any) {
      setError(err.message || 'Failed to queue batch download');
    } finally {
      setLoading(false);
    }
  };

  // Playlist Inspection
  const handleInspectPlaylist = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!playlistUrl.trim()) return;
    setPlaylistLoading(true);
    setError(null);
    try {
      const data = await inspectPlaylist(playlistUrl.trim(), {
        referer: referer.trim() || undefined,
        routing_mode: routingMode,
        cookies_from_browser: cookiesFromBrowser || undefined,
        custom_proxy: customProxy.trim() || undefined,
      });
      setPlaylistData(data);
      const allIds = new Set(data.items.map((it) => it.id));
      setSelectedEpisodeIds(allIds);
    } catch (err: any) {
      setError(err.message || 'Failed to inspect playlist. Please make sure the URL is accessible.');
    } finally {
      setPlaylistLoading(false);
    }
  };

  // Playlist Queue
  const handleQueuePlaylist = async () => {
    if (!playlistData) return;
    const selectedItems = playlistData.items.filter((it) => selectedEpisodeIds.has(it.id));
    if (selectedItems.length === 0) {
      setError('Please select at least one video to download');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      const res = await startBatchDownload({
        items: selectedItems.map((it) => ({
          url: it.url,
          custom_title: it.title,
        })),
        quality,
        downloader_type: downloaderType === 'segments' ? 'auto' : downloaderType,
        custom_chunks: numChunks,
        download_folder: customFolderOverride.trim() || currentFolder || undefined,
        referer: referer.trim() || undefined,
        use_tor: routingMode === 'tor' || useTor,
        routing_mode: routingMode,
        custom_proxy: customProxy.trim() || undefined,
        cookies_from_browser: cookiesFromBrowser || undefined,
      });

      setPlaylistData(null);
      setPlaylistUrl('');
      setSelectedEpisodeIds(new Set());
      setBatchSuccessMsg(`Queued ${res.count} playlist episodes for sequential download!`);
      setTimeout(() => setBatchSuccessMsg(null), 6000);
      onDownloadStarted();
    } catch (err: any) {
      setError(err.message || 'Failed to queue playlist downloads');
    } finally {
      setLoading(false);
    }
  };

  const toggleEpisode = (id: string) => {
    setSelectedEpisodeIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const selectAllEpisodes = () => {
    if (!playlistData) return;
    setSelectedEpisodeIds(new Set(playlistData.items.map((it) => it.id)));
  };

  const deselectAllEpisodes = () => {
    setSelectedEpisodeIds(new Set());
  };

  const selectFirstN = (n: number) => {
    if (!playlistData) return;
    setSelectedEpisodeIds(new Set(playlistData.items.slice(0, n).map((it) => it.id)));
  };

  const isPlaylistLikeUrl = (val: string) => {
    const s = val.toLowerCase();
    return s.includes('playlist?list=') || s.includes('&list=') || s.includes('/sets/') || s.includes('/series/');
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

      {/* Mode Selection Tabs (Single | Batch | Playlist) */}
      <div className="flex items-center gap-2 mb-4 border-b border-dark-700/60 pb-3 overflow-x-auto">
        <button
          type="button"
          onClick={() => {
            setDownloadMode('single');
            setError(null);
          }}
          className={`px-3.5 py-1.5 rounded-xl text-xs font-medium flex items-center gap-1.5 transition-all ${
            downloadMode === 'single'
              ? 'bg-brand-500 text-white shadow-md shadow-brand-500/20'
              : 'bg-dark-900/60 text-slate-400 hover:text-slate-200 border border-dark-700/60'
          }`}
        >
          <Sparkles className="h-3.5 w-3.5" />
          <span>Single Video</span>
        </button>

        <button
          type="button"
          onClick={() => {
            setDownloadMode('batch');
            setError(null);
          }}
          className={`px-3.5 py-1.5 rounded-xl text-xs font-medium flex items-center gap-1.5 transition-all ${
            downloadMode === 'batch'
              ? 'bg-brand-500 text-white shadow-md shadow-brand-500/20'
              : 'bg-dark-900/60 text-slate-400 hover:text-slate-200 border border-dark-700/60'
          }`}
        >
          <ListFilter className="h-3.5 w-3.5" />
          <span>Bulk URL Input</span>
          {batchUrlsText.split('\n').filter((s) => s.trim().length > 0).length > 0 && (
            <span className="ml-1 bg-white/20 text-white text-[10px] px-1.5 py-0.2 rounded-full font-mono">
              {batchUrlsText.split('\n').filter((s) => s.trim().length > 0).length}
            </span>
          )}
        </button>

        <button
          type="button"
          onClick={() => {
            setDownloadMode('playlist');
            setError(null);
          }}
          className={`px-3.5 py-1.5 rounded-xl text-xs font-medium flex items-center gap-1.5 transition-all ${
            downloadMode === 'playlist'
              ? 'bg-brand-500 text-white shadow-md shadow-brand-500/20'
              : 'bg-dark-900/60 text-slate-400 hover:text-slate-200 border border-dark-700/60'
          }`}
        >
          <ListOrdered className="h-3.5 w-3.5" />
          <span>Playlist &amp; Series</span>
          {playlistData && (
            <span className="ml-1 bg-white/20 text-white text-[10px] px-1.5 py-0.2 rounded-full font-mono">
              {playlistData.items.length}
            </span>
          )}
        </button>
      </div>

      {/* Batch / Playlist Success Notice */}
      {batchSuccessMsg && (
        <div className="mb-4 flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs px-3.5 py-2.5 rounded-xl animate-in fade-in">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>{batchSuccessMsg}</span>
        </div>
      )}

      <div className="space-y-4">
        {/* MODE 1: SINGLE URL */}
        {downloadMode === 'single' && (
          <form onSubmit={handleDownload} className="space-y-3">
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
                    Fetch Chunks &amp; Merge
                  </button>
                </div>
              </div>
            )}

            {/* Smart notice if user pasted playlist link in single mode */}
            {url && isPlaylistLikeUrl(url) && (
              <div className="text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 px-3.5 py-2 rounded-xl flex items-center justify-between">
                <span>💡 This link appears to be a playlist or series.</span>
                <button
                  type="button"
                  onClick={() => {
                    setPlaylistUrl(url);
                    setDownloadMode('playlist');
                    setTimeout(() => handleInspectPlaylist(), 50);
                  }}
                  className="font-semibold underline hover:text-amber-300 transition-colors"
                >
                  Open in Playlist Mode →
                </button>
              </div>
            )}

            {/* Single Video Inspection Result */}
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
          </form>
        )}

        {/* MODE 2: BATCH URLS */}
        {downloadMode === 'batch' && (
          <form onSubmit={handleBatchDownload} className="space-y-3">
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                  <ListPlus className="h-4 w-4 text-brand-400" />
                  Paste Multiple Video URLs (10–20 links):
                </label>
                <span className="text-[11px] font-mono text-brand-400 font-semibold bg-brand-500/10 px-2 py-0.5 rounded border border-brand-500/20">
                  {batchUrlsText.split('\n').filter((s) => s.trim().length > 0).length} links ready
                </span>
              </div>
              <textarea
                value={batchUrlsText}
                onChange={(e) => setBatchUrlsText(e.target.value)}
                rows={5}
                placeholder={"https://www.youtube.com/watch?v=...\nhttps://www.youtube.com/watch?v=...\nhttps://vimeo.com/...\nhttps://example.com/video.mp4"}
                className="w-full bg-dark-900/90 border border-dark-600 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 text-slate-200 placeholder-slate-500 text-xs rounded-xl p-3.5 font-mono outline-none leading-relaxed"
              />
              <p className="text-[11px] text-slate-400 flex items-center gap-1.5">
                <span>💡 URLs are queued in VideoManager and downloaded sequentially without overloading your connection.</span>
              </p>
            </div>

            <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-2">
              <div className="flex items-center gap-2 w-full sm:w-auto">
                <select
                  value={quality}
                  onChange={(e) => setQuality(e.target.value)}
                  className="bg-dark-900 border border-dark-600 text-slate-200 text-xs rounded-lg px-2.5 py-2 outline-none focus:border-brand-500 w-full sm:w-auto"
                >
                  <option value="best">Quality: Best Available</option>
                  <option value="1080p">Quality: 1080p Full HD</option>
                  <option value="720p">Quality: 720p HD</option>
                  <option value="audio">Quality: Audio Only (MP3)</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={loading || batchUrlsText.split('\n').filter((s) => s.trim().length > 0).length === 0}
                className="w-full sm:w-auto bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white font-medium text-xs px-6 py-2.5 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-brand-600/30 transition-all cursor-pointer"
              >
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                <span>
                  {loading
                    ? 'Queueing...'
                    : `Queue All (${batchUrlsText.split('\n').filter((s) => s.trim().length > 0).length}) Downloads`}
                </span>
              </button>
            </div>
          </form>
        )}

        {/* MODE 3: PLAYLIST & SERIES */}
        {downloadMode === 'playlist' && (
          <div className="space-y-4">
            <form onSubmit={handleInspectPlaylist} className="flex flex-col sm:flex-row gap-2">
              <div className="relative flex-1">
                <input
                  type="url"
                  value={playlistUrl}
                  onChange={(e) => setPlaylistUrl(e.target.value)}
                  placeholder="Paste Playlist, Series, or Channel URL (e.g. https://www.youtube.com/playlist?list=...)"
                  className="w-full bg-dark-900/90 border border-dark-600 focus:border-brand-500 focus:ring-1 focus:ring-brand-500 text-slate-200 placeholder-slate-500 text-sm rounded-xl px-4 py-3 outline-none transition-all pr-12"
                />
              </div>
              <button
                type="submit"
                disabled={playlistLoading || !playlistUrl.trim()}
                className="bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white font-medium text-xs sm:text-sm px-5 py-3 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-brand-600/30 transition-all shrink-0 cursor-pointer"
              >
                {playlistLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ListOrdered className="h-4 w-4" />}
                <span>{playlistLoading ? 'Scanning...' : 'Fetch Playlist'}</span>
              </button>
            </form>

            {/* Playlist Preview & Episode Checkbox Selector */}
            {playlistData && (
              <div className="bg-dark-900/90 border border-dark-700 rounded-xl p-4 space-y-4 animate-in fade-in">
                {/* Playlist Info Header */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-dark-700/60">
                  <div>
                    <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                      <Film className="h-4 w-4 text-brand-400" />
                      {playlistData.title}
                    </h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      {playlistData.uploader ? `By ${playlistData.uploader} · ` : ''}
                      <span className="text-brand-400 font-mono font-medium">{playlistData.total_count} videos found</span>
                    </p>
                  </div>

                  {/* Quick Select Buttons */}
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <button
                      type="button"
                      onClick={selectAllEpisodes}
                      className="px-2.5 py-1 text-[11px] bg-dark-800 hover:bg-dark-700 text-slate-300 rounded-lg border border-dark-600 transition-colors"
                    >
                      Select All
                    </button>
                    <button
                      type="button"
                      onClick={deselectAllEpisodes}
                      className="px-2.5 py-1 text-[11px] bg-dark-800 hover:bg-dark-700 text-slate-300 rounded-lg border border-dark-600 transition-colors"
                    >
                      Deselect
                    </button>
                    <button
                      type="button"
                      onClick={() => selectFirstN(5)}
                      className="px-2.5 py-1 text-[11px] bg-dark-800 hover:bg-dark-700 text-slate-300 rounded-lg border border-dark-600 transition-colors"
                    >
                      First 5
                    </button>
                    <button
                      type="button"
                      onClick={() => selectFirstN(10)}
                      className="px-2.5 py-1 text-[11px] bg-dark-800 hover:bg-dark-700 text-slate-300 rounded-lg border border-dark-600 transition-colors"
                    >
                      First 10
                    </button>
                  </div>
                </div>

                {/* Episodes Scrollable List */}
                <div className="max-h-72 overflow-y-auto space-y-1.5 pr-1">
                  {playlistData.items.map((item) => {
                    const isSelected = selectedEpisodeIds.has(item.id);
                    return (
                      <div
                        key={item.id}
                        onClick={() => toggleEpisode(item.id)}
                        className={`flex items-center gap-3 p-2 rounded-xl border transition-all cursor-pointer ${
                          isSelected
                            ? 'bg-brand-500/10 border-brand-500/30 text-white'
                            : 'bg-dark-800/40 border-dark-700/60 text-slate-400 hover:bg-dark-800/80 hover:text-slate-200'
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => {}}
                          className="h-4 w-4 rounded border-dark-600 text-brand-500 focus:ring-brand-500 cursor-pointer shrink-0"
                        />
                        <span className="font-mono text-xs text-slate-500 w-6 shrink-0 text-right">
                          #{item.index}
                        </span>

                        {item.thumbnail ? (
                          <img
                            src={item.thumbnail}
                            alt=""
                            className="w-12 h-8 object-cover rounded-lg shrink-0 border border-dark-700"
                          />
                        ) : (
                          <div className="w-12 h-8 bg-dark-800 rounded-lg flex items-center justify-center shrink-0">
                            <Film className="h-3.5 w-3.5 text-slate-500" />
                          </div>
                        )}

                        <span className="text-xs truncate flex-1 font-medium">
                          {item.title}
                        </span>

                        {item.duration > 0 && (
                          <span className="font-mono text-[11px] text-slate-400 shrink-0">
                            {formatDuration(item.duration)}
                          </span>
                        )}

                        <a
                          href={item.url}
                          target="_blank"
                          rel="noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="p-1 text-slate-500 hover:text-slate-300 shrink-0"
                          title="Open original video"
                        >
                          <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                      </div>
                    );
                  })}
                </div>

                {/* Sticky Action Footer */}
                <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-3 border-t border-dark-700/60">
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-slate-300">
                      Selected: <strong className="text-brand-400 font-semibold">{selectedEpisodeIds.size}</strong> of {playlistData.total_count} videos
                    </span>
                    <select
                      value={quality}
                      onChange={(e) => setQuality(e.target.value)}
                      className="bg-dark-800 border border-dark-600 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 outline-none focus:border-brand-500"
                    >
                      <option value="best">Quality: Best Available</option>
                      <option value="1080p">Quality: 1080p</option>
                      <option value="720p">Quality: 720p</option>
                      <option value="audio">Quality: Audio Only (MP3)</option>
                    </select>
                  </div>

                  <button
                    type="button"
                    onClick={handleQueuePlaylist}
                    disabled={loading || selectedEpisodeIds.size === 0}
                    className="w-full sm:w-auto bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white font-medium text-xs px-5 py-2.5 rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-brand-600/30 transition-all cursor-pointer"
                  >
                    {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                    <span>Queue Selected ({selectedEpisodeIds.size}) Videos</span>
                  </button>
                </div>
              </div>
            )}
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

              {/* Network Routing / Tor / Cloudflare WARP */}
              {networkStatus?.in_docker ? (
                <div className="col-span-1 sm:col-span-2 space-y-3 pt-2 border-t border-dark-700/60">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
                      <Shield className="h-3.5 w-3.5 text-purple-400" />
                      Docker Network Routing
                    </label>
                    <span className="text-[10px] bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded-full font-mono flex items-center gap-1">
                      🐳 Docker Mode Active
                    </span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                    {/* Direct */}
                    <button
                      type="button"
                      onClick={() => {
                        setRoutingMode('direct');
                        setUseTor(false);
                      }}
                      className={`p-3 rounded-xl border text-left transition-all ${
                        routingMode === 'direct'
                          ? 'border-brand-500 bg-brand-500/10 text-white shadow-sm ring-1 ring-brand-500/30'
                          : 'border-dark-700 bg-dark-800/60 text-slate-300 hover:border-dark-600'
                      }`}
                    >
                      <div className="flex items-center gap-1.5 text-xs font-semibold">
                        <Zap className="h-3.5 w-3.5 text-brand-400" />
                        <span>Direct (Default)</span>
                      </div>
                      <p className="text-[10px] text-slate-400 mt-1 leading-snug">
                        Normal broadband speed. No proxy or tunneling overhead.
                      </p>
                    </button>

                    {/* Cloudflare WARP */}
                    <button
                      type="button"
                      onClick={() => {
                        setRoutingMode('warp');
                        setUseTor(false);
                      }}
                      className={`p-3 rounded-xl border text-left transition-all ${
                        routingMode === 'warp'
                          ? 'border-orange-500 bg-orange-500/10 text-white shadow-sm ring-1 ring-orange-500/30'
                          : 'border-dark-700 bg-dark-800/60 text-slate-300 hover:border-dark-600'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5 text-xs font-semibold">
                          <Globe className="h-3.5 w-3.5 text-orange-400" />
                          <span>Cloudflare WARP</span>
                        </div>
                        {networkStatus?.warp.available && (
                          <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400/50" />
                        )}
                      </div>
                      <p className="text-[10px] text-slate-400 mt-1 leading-snug">
                        Full gigabit speed. Masks IP via Cloudflare's global edge network.
                      </p>
                    </button>

                    {/* Tor Network */}
                    <button
                      type="button"
                      onClick={() => {
                        setRoutingMode('tor');
                        setUseTor(true);
                      }}
                      className={`p-3 rounded-xl border text-left transition-all ${
                        routingMode === 'tor'
                          ? 'border-purple-500 bg-purple-500/10 text-white shadow-sm ring-1 ring-purple-500/30'
                          : 'border-dark-700 bg-dark-800/60 text-slate-300 hover:border-dark-600'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1.5 text-xs font-semibold">
                          <Shield className="h-3.5 w-3.5 text-purple-400" />
                          <span>Tor Network</span>
                        </div>
                        {networkStatus?.tor.available && (
                          <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400/50" />
                        )}
                      </div>
                      <p className="text-[10px] text-slate-400 mt-1 leading-snug">
                        3-hop onion encryption. Maximum IP anonymity & bypass.
                      </p>
                    </button>
                  </div>

                  {/* Active routing status display */}
                  <div className="p-2.5 rounded-xl bg-dark-800/80 border border-dark-700 text-xs flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-slate-400">Current Routing:</span>
                      <span className="font-mono text-[11px] text-slate-200">
                        {routingMode === 'direct' && '⚡ Direct Connection (Fastest)'}
                        {routingMode === 'warp' && `🛡️ Cloudflare WARP (${networkStatus?.warp.proxy || 'socks5://warp:1080'})`}
                        {routingMode === 'tor' && `🧅 Tor Network (${networkStatus?.tor.proxy || 'socks5://tor:9050'})`}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={checkNetwork}
                      className="text-[10px] text-slate-400 hover:text-slate-200 underline"
                    >
                      {checkingTor ? 'Checking...' : 'Refresh'}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                    <Shield className="h-3.5 w-3.5 text-purple-400" />
                    Route Through Tor
                  </label>

                  {/* Tor Status Badge */}
                  <div className={`border rounded-xl p-2.5 text-xs ${torBg}`}>
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
                        onClick={checkNetwork}
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
                      onClick={() => {
                        const nextTor = !useTor;
                        setUseTor(nextTor);
                        setRoutingMode(nextTor ? 'tor' : 'direct');
                      }}
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

                  {/* Informative Docker mode note */}
                  <div className="p-2 bg-blue-500/5 border border-blue-500/20 rounded-xl text-[10px] text-blue-300/80 leading-relaxed">
                    💡 <strong>Docker Mode Bonus:</strong> Cloudflare WARP and Tor multi-proxy routing are both pre-configured side-by-side in Docker Compose (`docker compose up`).
                  </div>
                </div>
              )}
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

            {/* Pre-Download Clip / Section Trimmer */}
            <div className="pt-3 border-t border-dark-700/60">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Scissors className="h-4 w-4 text-emerald-400" />
                  <span className="text-xs font-semibold text-slate-200">
                    Download Specific Clip / Section (Trim)
                  </span>
                  <span className="text-[10px] text-emerald-400/90 bg-emerald-500/10 px-1.5 py-0.5 rounded font-mono">
                    Fast &amp; Bandwidth Saver
                  </span>
                </div>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={trimEnabled}
                    onChange={(e) => setTrimEnabled(e.target.checked)}
                    className="sr-only"
                  />
                  <div
                    onClick={() => setTrimEnabled(!trimEnabled)}
                    className={`relative w-8 h-4 rounded-full transition-colors cursor-pointer ${
                      trimEnabled ? 'bg-emerald-500' : 'bg-dark-600'
                    }`}
                  >
                    <div
                      className={`absolute top-0.5 h-3 w-3 bg-white rounded-full shadow transition-all ${
                        trimEnabled ? 'left-4' : 'left-0.5'
                      }`}
                    />
                  </div>
                  <span className="text-[11px] text-slate-400">
                    {trimEnabled ? 'Active' : 'Off'}
                  </span>
                </label>
              </div>

              {trimEnabled && (
                <div className="bg-dark-800/80 border border-emerald-500/20 rounded-xl p-3 space-y-2 mt-2">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-[11px] font-medium text-slate-300 block mb-1">
                        Start Time (e.g. 01:30 or 90)
                      </label>
                      <input
                        type="text"
                        value={trimStart}
                        onChange={(e) => setTrimStart(e.target.value)}
                        placeholder="00:00"
                        className="w-full bg-dark-900 border border-dark-600 text-slate-200 text-xs rounded-lg px-3 py-1.5 font-mono outline-none focus:border-emerald-500"
                      />
                    </div>
                    <div>
                      <label className="text-[11px] font-medium text-slate-300 block mb-1">
                        End Time (e.g. 05:45 or 345)
                      </label>
                      <input
                        type="text"
                        value={trimEnd}
                        onChange={(e) => setTrimEnd(e.target.value)}
                        placeholder={inspectData?.info?.duration ? formatDuration(inspectData.info.duration) : "End of video"}
                        className="w-full bg-dark-900 border border-dark-600 text-slate-200 text-xs rounded-lg px-3 py-1.5 font-mono outline-none focus:border-emerald-500"
                      />
                    </div>
                  </div>
                  <p className="text-[10px] text-slate-400 flex items-center justify-between">
                    <span>
                      💡 Downloads <strong className="text-emerald-300">only</strong> the requested range directly from the web source using frame-accurate keyframe slicing.
                    </span>
                    {inspectData?.info?.duration ? (
                      <span className="text-slate-400 font-mono">
                        Full duration: {formatDuration(inspectData.info.duration)}
                      </span>
                    ) : null}
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 px-3 py-2 rounded-lg">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}
      </div>
    </div>
  );
};
