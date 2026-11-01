import React, { useState } from 'react';
import {
  X,
  Music,
  Minimize2,
  Image as ImageIcon,
  Scissors,
  Clock,
  HardDrive,
  Loader2,
  AlertTriangle,
  Sparkles
} from 'lucide-react';
import { VideoItem } from '../types';
import { formatBytes, formatDuration, extractAudio, compressVideo, createGif, trimVideo } from '../api';

interface MediaToolsModalProps {
  video: VideoItem;
  initialTab?: 'audio' | 'compress' | 'gif' | 'trim';
  onClose: () => void;
  onSuccess: (newVideo: VideoItem) => void;
}

export const MediaToolsModal: React.FC<MediaToolsModalProps> = ({
  video,
  initialTab = 'audio',
  onClose,
  onSuccess,
}) => {
  const [activeTab, setActiveTab] = useState<'audio' | 'compress' | 'gif' | 'trim'>(initialTab);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Audio state
  const [audioFormat, setAudioFormat] = useState<'mp3' | 'm4a' | 'aac' | 'wav'>('mp3');
  const [audioBitrate, setAudioBitrate] = useState('192k');
  const [audioTitle, setAudioTitle] = useState(`${video.title || 'video'}_audio`);

  // Compress state
  const [compressPreset, setCompressPreset] = useState<'light' | 'balanced' | 'discord'>('balanced');
  const [compressRes, setCompressRes] = useState<'same' | '1080p' | '720p' | '480p'>('same');
  const [compressTitle, setCompressTitle] = useState(`${video.title || 'video'}_compressed`);

  // GIF state
  const [gifStart, setGifStart] = useState(0);
  const [gifDuration, setGifDuration] = useState(Math.min(video.duration || 5, 5));
  const [gifFps, setGifFps] = useState(15);
  const [gifWidth, setGifWidth] = useState(480);
  const [gifTitle, setGifTitle] = useState(`${video.title || 'video'}_gif`);

  // Trim state
  const [trimStart, setTrimStart] = useState(0);
  const [trimEnd, setTrimEnd] = useState(video.duration || 10);
  const [trimMode, setTrimMode] = useState<'fast' | 'reencode'>('fast');
  const [trimTitle, setTrimTitle] = useState(`${video.title || 'video'}_clip`);

  const handleExtractAudio = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await extractAudio(video.id, {
        format: audioFormat,
        bitrate: audioBitrate,
        title: audioTitle.trim() || undefined,
      });
      onSuccess(res.video);
    } catch (err: any) {
      setError(err.message || 'Failed to extract audio');
      setLoading(false);
    }
  };

  const handleCompress = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await compressVideo(video.id, {
        preset: compressPreset,
        resolution: compressRes,
        title: compressTitle.trim() || undefined,
      });
      onSuccess(res.video);
    } catch (err: any) {
      setError(err.message || 'Failed to compress video');
      setLoading(false);
    }
  };

  const handleCreateGif = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await createGif(video.id, {
        start_time: Number(gifStart),
        duration: Number(gifDuration),
        fps: Number(gifFps),
        width: Number(gifWidth),
        title: gifTitle.trim() || undefined,
      });
      onSuccess(res.video);
    } catch (err: any) {
      setError(err.message || 'Failed to generate GIF');
      setLoading(false);
    }
  };

  const handleTrim = async () => {
    if (trimEnd <= trimStart) {
      setError('End time must be greater than start time.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await trimVideo(video.id, {
        start_time: Number(trimStart),
        end_time: Number(trimEnd),
        mode: trimMode,
        title: trimTitle.trim() || undefined,
      });
      onSuccess(res.video);
    } catch (err: any) {
      setError(err.message || 'Failed to trim video');
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-dark-900 border border-dark-700 w-full max-w-2xl rounded-2xl shadow-2xl flex flex-col max-h-[92vh] overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-dark-800 bg-dark-800/40">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Media Studio & Converter</h3>
              <p className="text-xs text-slate-400 truncate max-w-md">
                {video.title || video.url}
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

        {/* Feature Tabs */}
        <div className="flex border-b border-dark-800 bg-dark-900/80 px-5 pt-3 gap-2 overflow-x-auto">
          <button
            onClick={() => setActiveTab('audio')}
            className={`pb-3 px-3 text-xs font-medium flex items-center gap-1.5 transition-all border-b-2 ${
              activeTab === 'audio'
                ? 'border-brand-500 text-brand-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Music className="h-4 w-4" />
            <span>Extract Audio</span>
          </button>

          <button
            onClick={() => setActiveTab('compress')}
            className={`pb-3 px-3 text-xs font-medium flex items-center gap-1.5 transition-all border-b-2 ${
              activeTab === 'compress'
                ? 'border-brand-500 text-brand-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Minimize2 className="h-4 w-4" />
            <span>Compress Video</span>
          </button>

          <button
            onClick={() => setActiveTab('gif')}
            className={`pb-3 px-3 text-xs font-medium flex items-center gap-1.5 transition-all border-b-2 ${
              activeTab === 'gif'
                ? 'border-brand-500 text-brand-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <ImageIcon className="h-4 w-4" />
            <span>Convert to GIF</span>
          </button>

          <button
            onClick={() => setActiveTab('trim')}
            className={`pb-3 px-3 text-xs font-medium flex items-center gap-1.5 transition-all border-b-2 ${
              activeTab === 'trim'
                ? 'border-brand-500 text-brand-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Scissors className="h-4 w-4" />
            <span>Trim Clip</span>
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 space-y-5 overflow-y-auto flex-1">
          {error && (
            <div className="p-3.5 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-xs flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Quick Source Info */}
          <div className="flex items-center gap-4 bg-dark-800/60 border border-dark-700/80 rounded-xl p-3 text-xs text-slate-300">
            <span className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5 text-brand-400" />
              {formatDuration(video.duration)}
            </span>
            <span>•</span>
            <span className="flex items-center gap-1">
              <HardDrive className="h-3.5 w-3.5 text-brand-400" />
              {formatBytes(video.file_size)}
            </span>
            {video.resolution && (
              <>
                <span>•</span>
                <span className="font-mono text-slate-400">{video.resolution}</span>
              </>
            )}
          </div>

          {/* TAB 1: EXTRACT AUDIO */}
          {activeTab === 'audio' && (
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1.5">Output Audio Format</label>
                <div className="grid grid-cols-4 gap-2">
                  {(['mp3', 'm4a', 'aac', 'wav'] as const).map((fmt) => (
                    <button
                      key={fmt}
                      type="button"
                      onClick={() => setAudioFormat(fmt)}
                      className={`p-2.5 rounded-xl border text-center font-mono text-xs uppercase transition-all ${
                        audioFormat === fmt
                          ? 'border-brand-500 bg-brand-500/10 text-brand-300 font-semibold shadow-sm'
                          : 'border-dark-700 bg-dark-800/60 text-slate-400 hover:border-dark-600'
                      }`}
                    >
                      .{fmt}
                    </button>
                  ))}
                </div>
              </div>

              {audioFormat !== 'wav' && (
                <div>
                  <label className="text-xs font-medium text-slate-300 block mb-1.5">Audio Bitrate / Quality</label>
                  <select
                    value={audioBitrate}
                    onChange={(e) => setAudioBitrate(e.target.value)}
                    className="w-full bg-dark-800 border border-dark-700 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none focus:border-brand-500"
                  >
                    <option value="320k">320 kbps (High Fidelity Studio)</option>
                    <option value="192k">192 kbps (Standard High Quality - Recommended)</option>
                    <option value="128k">128 kbps (Compact Audio)</option>
                    <option value="96k">96 kbps (Speech / Audiobook)</option>
                  </select>
                </div>
              )}

              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1.5">Audio Track Title</label>
                <input
                  type="text"
                  value={audioTitle}
                  onChange={(e) => setAudioTitle(e.target.value)}
                  className="w-full bg-dark-800 border border-dark-700 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none focus:border-brand-500"
                />
              </div>
            </div>
          )}

          {/* TAB 2: COMPRESS VIDEO */}
          {activeTab === 'compress' && (
            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1.5">Compression Preset</label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                  <button
                    type="button"
                    onClick={() => setCompressPreset('balanced')}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      compressPreset === 'balanced'
                        ? 'border-brand-500 bg-brand-500/10 text-white shadow-sm'
                        : 'border-dark-700 bg-dark-800/60 text-slate-300 hover:border-dark-600'
                    }`}
                  >
                    <span className="text-xs font-semibold block">⚡ Balanced (~50% smaller)</span>
                    <span className="text-[11px] text-slate-400 mt-1 block">Best balance of high quality and halved file size.</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setCompressPreset('discord')}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      compressPreset === 'discord'
                        ? 'border-brand-500 bg-brand-500/10 text-white shadow-sm'
                        : 'border-dark-700 bg-dark-800/60 text-slate-300 hover:border-dark-600'
                    }`}
                  >
                    <span className="text-xs font-semibold block">💬 WhatsApp / Discord (~80%)</span>
                    <span className="text-[11px] text-slate-400 mt-1 block">Shrinks 1GB+ files down to lightweight mobile size.</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setCompressPreset('light')}
                    className={`p-3 rounded-xl border text-left transition-all ${
                      compressPreset === 'light'
                        ? 'border-brand-500 bg-brand-500/10 text-white shadow-sm'
                        : 'border-dark-700 bg-dark-800/60 text-slate-300 hover:border-dark-600'
                    }`}
                  >
                    <span className="text-xs font-semibold block">💎 Near-Lossless (~30%)</span>
                    <span className="text-[11px] text-slate-400 mt-1 block">Maximum video sharpness with slight size reduction.</span>
                  </button>
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1.5">Max Target Resolution</label>
                <select
                  value={compressRes}
                  onChange={(e) => setCompressRes(e.target.value as any)}
                  className="w-full bg-dark-800 border border-dark-700 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none focus:border-brand-500"
                >
                  <option value="same">Keep Original Resolution ({video.resolution || 'original'})</option>
                  <option value="1080p">Scale to 1080p (Full HD)</option>
                  <option value="720p">Scale to 720p (HD - Best for sharing)</option>
                  <option value="480p">Scale to 480p (SD - Ultra compact)</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1.5">Compressed Video Title</label>
                <input
                  type="text"
                  value={compressTitle}
                  onChange={(e) => setCompressTitle(e.target.value)}
                  className="w-full bg-dark-800 border border-dark-700 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none focus:border-brand-500"
                />
              </div>
            </div>
          )}

          {/* TAB 3: CREATE GIF */}
          {activeTab === 'gif' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-slate-300 block mb-1.5">
                    Start Offset: <span className="font-mono text-brand-400">{formatDuration(gifStart)}</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max={Math.max(0, (video.duration || 10) - 1)}
                    step="0.5"
                    value={gifStart}
                    onChange={(e) => setGifStart(parseFloat(e.target.value))}
                    className="w-full accent-brand-500"
                  />
                </div>

                <div>
                  <label className="text-xs font-medium text-slate-300 block mb-1.5">
                    GIF Duration: <span className="font-mono text-brand-400">{gifDuration}s</span>
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="15"
                    step="1"
                    value={gifDuration}
                    onChange={(e) => setGifDuration(parseFloat(e.target.value))}
                    className="w-full accent-brand-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-slate-300 block mb-1.5">Framerate (FPS)</label>
                  <select
                    value={gifFps}
                    onChange={(e) => setGifFps(parseInt(e.target.value))}
                    className="w-full bg-dark-800 border border-dark-700 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none focus:border-brand-500"
                  >
                    <option value="12">12 fps (Lightweight)</option>
                    <option value="15">15 fps (Recommended)</option>
                    <option value="24">24 fps (Smooth Cinematic)</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs font-medium text-slate-300 block mb-1.5">GIF Width</label>
                  <select
                    value={gifWidth}
                    onChange={(e) => setGifWidth(parseInt(e.target.value))}
                    className="w-full bg-dark-800 border border-dark-700 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none focus:border-brand-500"
                  >
                    <option value="320">320px (Compact sticker)</option>
                    <option value="480">480px (Standard - Recommended)</option>
                    <option value="640">640px (High-res preview)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1.5">GIF Title</label>
                <input
                  type="text"
                  value={gifTitle}
                  onChange={(e) => setGifTitle(e.target.value)}
                  className="w-full bg-dark-800 border border-dark-700 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none focus:border-brand-500"
                />
              </div>
            </div>
          )}

          {/* TAB 4: TRIM CLIP */}
          {activeTab === 'trim' && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-slate-300 block mb-1.5">
                    Start Time: <span className="font-mono text-brand-400">{formatDuration(trimStart)}</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max={Math.max(0, (video.duration || 10) - 1)}
                    step="0.5"
                    value={trimStart}
                    onChange={(e) => setTrimStart(parseFloat(e.target.value))}
                    className="w-full accent-brand-500"
                  />
                </div>

                <div>
                  <label className="text-xs font-medium text-slate-300 block mb-1.5">
                    End Time: <span className="font-mono text-brand-400">{formatDuration(trimEnd)}</span>
                  </label>
                  <input
                    type="range"
                    min="1"
                    max={video.duration || 10}
                    step="0.5"
                    value={trimEnd}
                    onChange={(e) => setTrimEnd(parseFloat(e.target.value))}
                    className="w-full accent-brand-500"
                  />
                </div>
              </div>

              <div className="p-3 bg-dark-800/80 border border-dark-700 rounded-xl flex items-center justify-between text-xs">
                <span className="text-slate-400">Resulting Clip Length:</span>
                <span className="font-mono font-bold text-brand-400">
                  {formatDuration(Math.max(0, trimEnd - trimStart))}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setTrimMode('fast')}
                  className={`p-2.5 rounded-xl border text-left transition-all ${
                    trimMode === 'fast'
                      ? 'border-brand-500 bg-brand-500/10 text-white font-medium'
                      : 'border-dark-700 bg-dark-800/60 text-slate-300 hover:border-dark-600'
                  }`}
                >
                  <span className="text-xs block">⚡ Instant Stream Copy</span>
                  <span className="text-[10px] text-slate-400 mt-0.5 block">0.1s execution without re-encoding.</span>
                </button>

                <button
                  type="button"
                  onClick={() => setTrimMode('reencode')}
                  className={`p-2.5 rounded-xl border text-left transition-all ${
                    trimMode === 'reencode'
                      ? 'border-brand-500 bg-brand-500/10 text-white font-medium'
                      : 'border-dark-700 bg-dark-800/60 text-slate-300 hover:border-dark-600'
                  }`}
                >
                  <span className="text-xs block">🎯 Frame-Accurate Cut</span>
                  <span className="text-[10px] text-slate-400 mt-0.5 block">Precise cut with clean I-frame keyframes.</span>
                </button>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1.5">Clip Title</label>
                <input
                  type="text"
                  value={trimTitle}
                  onChange={(e) => setTrimTitle(e.target.value)}
                  className="w-full bg-dark-800 border border-dark-700 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none focus:border-brand-500"
                />
              </div>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-dark-800 bg-dark-800/40 flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white hover:bg-dark-800 transition-colors"
          >
            Cancel
          </button>

          {activeTab === 'audio' && (
            <button
              onClick={handleExtractAudio}
              disabled={loading}
              className="px-5 py-2.5 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-xs font-medium shadow-lg shadow-brand-500/20 disabled:opacity-40 flex items-center gap-2 transition-all"
            >
              {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Music className="h-3.5 w-3.5" />}
              <span>Extract .{audioFormat.toUpperCase()} Audio</span>
            </button>
          )}

          {activeTab === 'compress' && (
            <button
              onClick={handleCompress}
              disabled={loading}
              className="px-5 py-2.5 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-xs font-medium shadow-lg shadow-brand-500/20 disabled:opacity-40 flex items-center gap-2 transition-all"
            >
              {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Minimize2 className="h-3.5 w-3.5" />}
              <span>Compress Video</span>
            </button>
          )}

          {activeTab === 'gif' && (
            <button
              onClick={handleCreateGif}
              disabled={loading}
              className="px-5 py-2.5 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-xs font-medium shadow-lg shadow-brand-500/20 disabled:opacity-40 flex items-center gap-2 transition-all"
            >
              {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ImageIcon className="h-3.5 w-3.5" />}
              <span>Generate GIF</span>
            </button>
          )}

          {activeTab === 'trim' && (
            <button
              onClick={handleTrim}
              disabled={loading}
              className="px-5 py-2.5 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-xs font-medium shadow-lg shadow-brand-500/20 disabled:opacity-40 flex items-center gap-2 transition-all"
            >
              {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Scissors className="h-3.5 w-3.5" />}
              <span>Cut & Save Clip</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
