import React, { useState } from 'react';
import {
  X,
  Search,
  Shield,
  Globe,
  Radio,
  ExternalLink,
  Copy,
  Check,
  Download,
  Film,
  AlertCircle,
  Loader2,
  CheckSquare,
  Square
} from 'lucide-react';
import { findVideoLinks, DiscoveredVideoLink, startBatchDownload } from '../api';

interface LinkFinderModalProps {
  onClose: () => void;
  onDownloadQueued?: () => void;
}

export const LinkFinderModal: React.FC<LinkFinderModalProps> = ({
  onClose,
  onDownloadQueued
}) => {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [useStealth, setUseStealth] = useState(true);
  const [routingMode, setRoutingMode] = useState<'direct' | 'warp' | 'tor' | 'custom'>('direct');
  const [customProxy, setCustomProxy] = useState('');
  const [cookiesBrowser, setCookiesBrowser] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);

  const [scanResult, setScanResult] = useState<{
    page_title: string;
    page_url: string;
    total_found: number;
    links: DiscoveredVideoLink[];
  } | null>(null);

  const [selectedUrls, setSelectedUrls] = useState<Set<string>>(new Set());
  const [copiedUrl, setCopiedUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [downloadSuccess, setDownloadSuccess] = useState(false);

  const handleScan = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    const targetUrl = url.trim();
    if (!targetUrl) return;

    setError(null);
    setLoading(true);
    setScanResult(null);
    setDownloadSuccess(false);

    try {
      const res = await findVideoLinks({
        url: targetUrl,
        routing_mode: routingMode,
        custom_proxy: routingMode === 'custom' ? customProxy : undefined,
        cookies_from_browser: cookiesBrowser || undefined,
        use_stealth: useStealth
      });

      setScanResult(res);
      // Pre-select all direct/hls video links by default
      const preselected = new Set<string>();
      res.links.forEach((item) => {
        if (item.type !== 'embedded_player') {
          preselected.add(item.url);
        }
      });
      if (preselected.size === 0 && res.links.length > 0) {
        res.links.forEach((item) => preselected.add(item.url));
      }
      setSelectedUrls(preselected);
    } catch (err: any) {
      setError(err.message || 'Failed to scan website for video links');
    } finally {
      setLoading(false);
    }
  };

  const toggleSelectAll = () => {
    if (!scanResult) return;
    if (selectedUrls.size === scanResult.links.length) {
      setSelectedUrls(new Set());
    } else {
      setSelectedUrls(new Set(scanResult.links.map((l) => l.url)));
    }
  };

  const toggleSelect = (itemUrl: string) => {
    const next = new Set(selectedUrls);
    if (next.has(itemUrl)) {
      next.delete(itemUrl);
    } else {
      next.add(itemUrl);
    }
    setSelectedUrls(next);
  };

  const handleCopy = (linkUrl: string) => {
    navigator.clipboard.writeText(linkUrl);
    setCopiedUrl(linkUrl);
    setTimeout(() => setCopiedUrl(null), 2000);
  };

  const handleDownloadSelected = async () => {
    if (!scanResult || selectedUrls.size === 0) return;
    setDownloading(true);
    setError(null);

    const itemsToDownload = scanResult.links
      .filter((l) => selectedUrls.has(l.url))
      .map((l) => ({
        url: l.url,
        custom_title: l.title
      }));

    try {
      await startBatchDownload({
        items: itemsToDownload,
        routing_mode: routingMode,
        custom_proxy: routingMode === 'custom' ? customProxy : undefined,
        cookies_from_browser: cookiesBrowser || undefined,
        referer: scanResult.page_url
      });

      setDownloadSuccess(true);
      if (onDownloadQueued) onDownloadQueued();
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err: any) {
      setError(err.message || 'Failed to start batch download');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-dark-900 border border-dark-700 w-full max-w-2xl rounded-2xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-dark-800 bg-dark-800/40">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-brand-600 to-indigo-500 flex items-center justify-center text-white shadow-lg shadow-brand-500/20">
              <Search className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white flex items-center gap-2">
                Video Link Finder
                <span className="text-[10px] bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full font-mono uppercase flex items-center gap-1 font-semibold">
                  <Shield className="h-3 w-3" /> Stealth Active
                </span>
              </h3>
              <p className="text-xs text-slate-400">
                Inspect any website or article to extract embedded video streams without IP bans.
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
        <div className="p-5 overflow-y-auto space-y-4 flex-1">
          {/* URL Search Bar */}
          <form onSubmit={handleScan} className="space-y-3">
            <div className="relative">
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="Paste webpage URL (e.g. https://example.com/article)..."
                className="w-full bg-dark-800 border border-dark-600 focus:border-brand-500 rounded-xl px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-brand-500 pr-24 shadow-inner"
                disabled={loading}
                autoFocus
              />
              <button
                type="submit"
                disabled={loading || !url.trim()}
                className="absolute right-2 top-2 bottom-2 px-4 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white rounded-lg text-xs font-semibold flex items-center gap-1.5 transition-all shadow-md shadow-brand-600/30"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    <span>Scanning...</span>
                  </>
                ) : (
                  <>
                    <Search className="h-3.5 w-3.5" />
                    <span>Find Videos</span>
                  </>
                )}
              </button>
            </div>

            {/* Anti-Bot & Stealth Controls Pill Bar */}
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs pt-1">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setUseStealth(!useStealth)}
                  className={`px-2.5 py-1 rounded-lg border flex items-center gap-1.5 transition-colors font-medium ${
                    useStealth
                      ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30 hover:bg-emerald-500/25'
                      : 'bg-dark-800 text-slate-400 border-dark-700 hover:bg-dark-700'
                  }`}
                  title="Emulates complete modern desktop browser fingerprints (Chrome 124, Client Hints, Referer) so CDNs and WAFs don't block requests."
                >
                  <Shield className="h-3 w-3" />
                  <span>Browser Stealth Profile: {useStealth ? 'ON' : 'OFF'}</span>
                </button>

                <button
                  type="button"
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="px-2.5 py-1 rounded-lg bg-dark-800 hover:bg-dark-700 border border-dark-700 text-slate-400 hover:text-slate-200 transition-colors"
                >
                  {showAdvanced ? 'Hide IP & Proxy Options ▲' : 'IP & Proxy Options ▼'}
                </button>
              </div>

              <span className="text-[11px] text-slate-500">
                Supports MP4, WebM, HLS (.m3u8), DASH (.mpd), &amp; Embeds
              </span>
            </div>

            {/* Advanced Stealth & IP Shield Settings */}
            {showAdvanced && (
              <div className="p-3.5 bg-dark-800/80 border border-dark-700 rounded-xl space-y-3 text-xs animate-in fade-in duration-150">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-slate-300 font-medium mb-1 flex items-center gap-1.5">
                      <Radio className="h-3 w-3 text-brand-400" />
                      <span>Network IP Routing:</span>
                    </label>
                    <select
                      value={routingMode}
                      onChange={(e: any) => setRoutingMode(e.target.value)}
                      className="w-full bg-dark-900 border border-dark-600 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-brand-500"
                    >
                      <option value="direct">Direct Connection (Your Network)</option>
                      <option value="warp">Cloudflare WARP (Mask Home IP)</option>
                      <option value="tor">Tor SOCKS5 Network (Anonymized)</option>
                      <option value="custom">Custom Proxy...</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-slate-300 font-medium mb-1 flex items-center gap-1.5">
                      <Globe className="h-3 w-3 text-brand-400" />
                      <span>Browser Cookies (Bypass Paywalls/Logins):</span>
                    </label>
                    <select
                      value={cookiesBrowser}
                      onChange={(e) => setCookiesBrowser(e.target.value)}
                      className="w-full bg-dark-900 border border-dark-600 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-brand-500"
                    >
                      <option value="">None (Standard Anonymous)</option>
                      <option value="chrome">Google Chrome Session</option>
                      <option value="safari">Safari Session</option>
                      <option value="firefox">Mozilla Firefox Session</option>
                      <option value="brave">Brave Browser Session</option>
                      <option value="edge">Microsoft Edge Session</option>
                    </select>
                    <span className="text-[10px] text-slate-500 mt-1 block">
                      Leave as "None" for public videos. macOS requires Full Disk Access to read local browser databases.
                    </span>
                  </div>
                </div>

                {routingMode === 'custom' && (
                  <div>
                    <input
                      type="text"
                      value={customProxy}
                      onChange={(e) => setCustomProxy(e.target.value)}
                      placeholder="e.g. socks5://127.0.0.1:1080 or http://user:pass@host:port"
                      className="w-full bg-dark-900 border border-dark-600 rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-brand-500"
                    />
                  </div>
                )}
              </div>
            )}
          </form>

          {/* Error Notice */}
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400 text-xs flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Success Banner */}
          {downloadSuccess && (
            <div className="p-3 bg-emerald-500/15 border border-emerald-500/30 rounded-xl text-emerald-300 text-xs flex items-center gap-2">
              <Check className="h-4 w-4 text-emerald-400" />
              <span>Queued selected videos in VideoManager download queue!</span>
            </div>
          )}

          {/* Results Area */}
          {scanResult && (
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between border-b border-dark-800 pb-2">
                <div>
                  <h4 className="text-xs font-semibold text-white flex items-center gap-2">
                    <span>Discovered Videos</span>
                    <span className="bg-brand-500/20 text-brand-400 border border-brand-500/30 px-2 py-0.5 rounded-full text-[10px] font-mono">
                      {scanResult.total_found} Found
                    </span>
                  </h4>
                  <p className="text-[11px] text-slate-400 truncate max-w-md">
                    {scanResult.page_title}
                  </p>
                </div>

                {scanResult.links.length > 0 && (
                  <button
                    type="button"
                    onClick={toggleSelectAll}
                    className="text-xs text-brand-400 hover:text-brand-300 font-medium flex items-center gap-1"
                  >
                    {selectedUrls.size === scanResult.links.length ? (
                      <>
                        <CheckSquare className="h-3.5 w-3.5" />
                        <span>Deselect All</span>
                      </>
                    ) : (
                      <>
                        <Square className="h-3.5 w-3.5" />
                        <span>Select All</span>
                      </>
                    )}
                  </button>
                )}
              </div>

              {scanResult.links.length === 0 ? (
                <div className="p-8 text-center bg-dark-800/40 rounded-xl border border-dark-800">
                  <Film className="h-8 w-8 text-slate-500 mx-auto mb-2" />
                  <p className="text-sm font-medium text-slate-300">No video links detected on this page</p>
                  <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                    The page may load video dynamically via DRM, or require logging in. Try enabling browser cookies above.
                  </p>
                </div>
              ) : (
                <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                  {scanResult.links.map((link, idx) => {
                    const isSelected = selectedUrls.has(link.url);
                    const isCopied = copiedUrl === link.url;

                    return (
                      <div
                        key={idx}
                        onClick={() => toggleSelect(link.url)}
                        className={`p-3 rounded-xl border cursor-pointer transition-all flex items-center justify-between gap-3 ${
                          isSelected
                            ? 'bg-brand-950/40 border-brand-500/50 shadow-sm'
                            : 'bg-dark-800/40 border-dark-700/60 hover:bg-dark-800/80 hover:border-dark-600'
                        }`}
                      >
                        <div className="flex items-center gap-3 overflow-hidden flex-1">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => toggleSelect(link.url)}
                            onClick={(e) => e.stopPropagation()}
                            className="rounded border-dark-600 text-brand-600 focus:ring-0 focus:ring-offset-0 h-4 w-4 bg-dark-900 cursor-pointer"
                          />

                          {link.thumbnail ? (
                            <img
                              src={link.thumbnail}
                              alt=""
                              className="h-10 w-16 object-cover rounded-md bg-dark-900 shrink-0 border border-dark-700"
                              onError={(e) => {
                                (e.target as HTMLElement).style.display = 'none';
                              }}
                            />
                          ) : (
                            <div className="h-10 w-10 rounded-md bg-dark-800 border border-dark-700 flex items-center justify-center shrink-0 text-slate-400">
                              <Film className="h-5 w-5" />
                            </div>
                          )}

                          <div className="overflow-hidden flex-1">
                            <p className="text-xs font-semibold text-white truncate" title={link.title}>
                              {link.title}
                            </p>
                            <div className="flex items-center gap-2 mt-0.5">
                              <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-brand-500/20 text-brand-300 border border-brand-500/30">
                                {link.format}
                              </span>
                              <span className="text-[10px] text-slate-400 truncate">
                                Source: {link.source}
                              </span>
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
                          <button
                            type="button"
                            onClick={() => handleCopy(link.url)}
                            title="Copy Direct Link"
                            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-dark-700 transition-colors"
                          >
                            {isCopied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                          </button>
                          <a
                            href={link.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            title="Open Link"
                            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-dark-700 transition-colors"
                          >
                            <ExternalLink className="h-3.5 w-3.5" />
                          </a>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-dark-800 bg-dark-800/40 flex items-center justify-between">
          <div className="text-xs text-slate-400">
            {scanResult && scanResult.links.length > 0 && (
              <span>
                {selectedUrls.size} of {scanResult.links.length} video(s) selected
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-dark-800 hover:bg-dark-700 text-slate-300 text-xs font-medium rounded-xl transition-colors"
            >
              Close
            </button>

            {scanResult && scanResult.links.length > 0 && (
              <button
                type="button"
                onClick={handleDownloadSelected}
                disabled={selectedUrls.size === 0 || downloading}
                className="px-4 py-2 bg-brand-600 hover:bg-brand-500 disabled:opacity-50 text-white text-xs font-semibold rounded-xl flex items-center gap-1.5 transition-all shadow-md shadow-brand-600/30"
              >
                {downloading ? (
                  <>
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    <span>Queueing...</span>
                  </>
                ) : (
                  <>
                    <Download className="h-3.5 w-3.5" />
                    <span>Download Selected ({selectedUrls.size})</span>
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
