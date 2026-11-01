import React, { useEffect, useState } from 'react';
import { X, Download, HardDrive, Clock, ExternalLink, AlertTriangle, Terminal, RefreshCw } from 'lucide-react';
import { VideoItem } from '../types';
import { formatBytes, formatDuration } from '../api';

interface VideoPlayerModalProps {
  video: VideoItem | null;
  onClose: () => void;
}

interface FileInfo {
  detected_content_type: string;
  detected_extension: string;
  streamable_in_browser: boolean;
  needs_remux: boolean;
  stated_format: string;
}

export const VideoPlayerModal: React.FC<VideoPlayerModalProps> = ({ video, onClose }) => {
  const [fileInfo, setFileInfo] = useState<FileInfo | null>(null);
  const [infoLoading, setInfoLoading] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  useEffect(() => {
    if (!video) return;
    setFileInfo(null);
    setInfoLoading(true);
    fetch(`/api/videos/${video.id}/info`)
      .then(r => r.json())
      .then(setFileInfo)
      .catch(() => setFileInfo(null))
      .finally(() => setInfoLoading(false));
  }, [video]);

  if (!video) return null;

  const streamUrl = `/api/videos/${video.id}/stream`;
  const downloadUrl = `/api/videos/${video.id}/download`;
  const isTs = fileInfo?.needs_remux || fileInfo?.detected_extension === 'ts';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-md">
      <div className="bg-dark-900 border border-dark-700 rounded-2xl w-full max-w-4xl overflow-hidden shadow-2xl flex flex-col">
        {/* Header */}
        <div className="p-4 border-b border-dark-700 flex items-center justify-between gap-4">
          <div className="min-w-0">
            <h3 className="text-base font-semibold text-white truncate">{video.title}</h3>
            <div className="flex items-center gap-3 text-xs text-slate-400 mt-0.5 flex-wrap">
              <span className="flex items-center gap-1 font-mono">
                <HardDrive className="h-3 w-3 text-brand-400" />
                {formatBytes(video.file_size)}
              </span>
              {video.duration > 0 && (
                <span className="flex items-center gap-1 font-mono">
                  <Clock className="h-3 w-3 text-brand-400" />
                  {formatDuration(video.duration)}
                </span>
              )}
              {/* Real detected format badge */}
              {fileInfo && (
                <span className={`font-mono uppercase px-1.5 py-0.5 rounded text-[10px] border ${
                  isTs
                    ? 'bg-rose-500/20 text-rose-400 border-rose-500/30'
                    : 'bg-dark-800 text-slate-300 border-dark-700'
                }`}>
                  {fileInfo.detected_extension} · {fileInfo.detected_content_type}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <a
              href={downloadUrl}
              download
              className="p-2 text-slate-400 hover:text-white bg-dark-800 hover:bg-dark-700 rounded-lg transition-colors flex items-center gap-1 text-xs"
              title="Save to Computer"
            >
              <Download className="h-4 w-4" />
              <span className="hidden sm:inline">Save</span>
            </a>
            <button
              onClick={onClose}
              className="p-2 text-slate-400 hover:text-white bg-dark-800 hover:bg-dark-700 rounded-lg transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Player Area */}
        <div className="relative bg-black aspect-video flex items-center justify-center">
          {infoLoading ? (
            <div className="flex flex-col items-center gap-2 text-slate-500">
              <RefreshCw className="h-6 w-6 animate-spin text-brand-400" />
              <span className="text-xs">Detecting media format...</span>
            </div>
          ) : isTs ? (
            /* ── MPEG-TS Unplayable Warning ── */
            <div className="flex flex-col items-center gap-4 px-6 py-8 text-center max-w-md">
              <div className="p-3 bg-amber-500/15 border border-amber-500/30 rounded-2xl">
                <AlertTriangle className="h-8 w-8 text-amber-400" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-white mb-1">
                  Raw MPEG-TS Stream — Cannot Play in Browser
                </h4>
                <p className="text-xs text-slate-400 leading-relaxed">
                  This file is a raw <span className="text-amber-400 font-mono">.ts</span> transport stream.
                  Browsers only play <span className="text-brand-400 font-mono">.mp4</span> and <span className="text-brand-400 font-mono">.webm</span>.
                  <br /><br />
                  yt-dlp needs <strong className="text-white">ffmpeg</strong> to remux HLS segments into a proper MP4 container after downloading.
                </p>
              </div>

              {/* Install Command */}
              <div className="w-full bg-dark-900/90 border border-dark-600 rounded-xl p-3 text-left">
                <p className="text-[10px] text-slate-500 uppercase font-semibold tracking-wider mb-2 flex items-center gap-1">
                  <Terminal className="h-3 w-3" /> Fix — Install ffmpeg, then re-download:
                </p>
                <div className="space-y-1.5">
                  <code className="block text-xs text-brand-400 font-mono bg-dark-800 px-2 py-1 rounded">
                    brew install ffmpeg
                  </code>
                  <code className="block text-xs text-brand-400 font-mono bg-dark-800 px-2 py-1 rounded">
                    # Docker: already included (ffmpeg pre-installed)
                  </code>
                </div>
              </div>

              <div className="flex gap-3 w-full">
                <a
                  href={downloadUrl}
                  download
                  className="flex-1 py-2 bg-dark-700 hover:bg-dark-600 text-slate-300 text-xs rounded-xl text-center flex items-center justify-center gap-1.5 transition-colors"
                >
                  <Download className="h-3.5 w-3.5" />
                  Download Raw .ts File
                </a>
                <button
                  onClick={onClose}
                  className="flex-1 py-2 bg-brand-600 hover:bg-brand-500 text-white text-xs rounded-xl font-medium transition-colors"
                >
                  Close & Install ffmpeg
                </button>
              </div>
            </div>
          ) : (
            /* ── Normal Video Player ── */
            <video
              key={video.id}
              src={streamUrl}
              controls
              autoPlay
              className="w-full h-full max-h-[70vh] object-contain"
              onError={(e) => {
                console.error('Video playback error:', e);
              }}
            >
              Your browser does not support the video tag.
            </video>
          )}
        </div>

        {/* Footer */}
        <div className="p-3 bg-dark-800/60 border-t border-dark-700 flex items-center justify-between text-xs text-slate-400">
          <div className="flex items-center gap-2 truncate">
            <span className="text-slate-500 shrink-0">Source:</span>
            <a
              href={video.url}
              target="_blank"
              rel="noreferrer"
              className="truncate text-brand-400 hover:underline flex items-center gap-1"
            >
              {video.url}
              <ExternalLink className="h-3 w-3 inline shrink-0" />
            </a>
          </div>
          <span className="text-slate-500 text-[11px] shrink-0 hidden sm:block">Esc to close</span>
        </div>
      </div>
    </div>
  );
};
