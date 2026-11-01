import React, { useState, useEffect } from 'react';
import {
  X,
  Layers,
  ArrowUp,
  ArrowDown,
  Trash2,
  Clock,
  HardDrive,
  Zap,
  RefreshCw,
  Video,
  CheckCircle2,
  AlertTriangle
} from 'lucide-react';
import { VideoItem, StitchPreviewResponse } from '../types';
import { formatBytes, formatDuration, previewStitch, stitchVideos } from '../api';

interface VideoStitchModalProps {
  selectedVideos: VideoItem[];
  onClose: () => void;
  onStitchSuccess: (jobId: string) => void;
}

export const VideoStitchModal: React.FC<VideoStitchModalProps> = ({
  selectedVideos: initialVideos,
  onClose,
  onStitchSuccess,
}) => {
  const [orderedVideos, setOrderedVideos] = useState<VideoItem[]>(initialVideos);
  const [outputTitle, setOutputTitle] = useState('');
  const [stitchMode, setStitchMode] = useState<'auto' | 'fast' | 'reencode'>('auto');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [preview, setPreview] = useState<StitchPreviewResponse | null>(null);

  // Auto-generate suggested title
  useEffect(() => {
    if (initialVideos.length > 0 && !outputTitle) {
      const firstTitle = initialVideos[0].title || 'Merged';
      const cleanTitle = firstTitle.replace(/[^a-zA-Z0-9_-]/g, '_').slice(0, 30);
      setOutputTitle(`${cleanTitle}_stitched`);
    }
  }, [initialVideos, outputTitle]);

  // Fetch preview when ordering changes
  useEffect(() => {
    if (orderedVideos.length >= 2) {
      previewStitch({ video_ids: orderedVideos.map((v) => v.id) })
        .then((res) => setPreview(res))
        .catch(() => setPreview(null));
    } else {
      setPreview(null);
    }
  }, [orderedVideos]);

  const moveUp = (index: number) => {
    if (index === 0) return;
    const newItems = [...orderedVideos];
    const temp = newItems[index - 1];
    newItems[index - 1] = newItems[index];
    newItems[index] = temp;
    setOrderedVideos(newItems);
  };

  const moveDown = (index: number) => {
    if (index === orderedVideos.length - 1) return;
    const newItems = [...orderedVideos];
    const temp = newItems[index + 1];
    newItems[index + 1] = newItems[index];
    newItems[index] = temp;
    setOrderedVideos(newItems);
  };

  const removeItem = (id: string) => {
    setOrderedVideos((prev) => prev.filter((v) => v.id !== id));
  };

  const handleStartStitch = async () => {
    if (orderedVideos.length < 2) {
      setError('You need at least 2 videos to merge.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await stitchVideos({
        video_ids: orderedVideos.map((v) => v.id),
        title: outputTitle.trim() || 'Stitched_Video',
        mode: stitchMode,
      });

      onStitchSuccess(res.video_id);
    } catch (err: any) {
      setError(err.message || 'Failed to start video stitching');
      setLoading(false);
    }
  };

  const totalDuration = preview
    ? preview.total_duration
    : orderedVideos.reduce((acc, v) => acc + (v.duration || 0), 0);
  const totalSize = preview
    ? preview.total_size
    : orderedVideos.reduce((acc, v) => acc + (v.file_size || 0), 0);

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-dark-900 border border-dark-700 w-full max-w-2xl rounded-2xl shadow-2xl flex flex-col max-h-[90vh] overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-dark-800 bg-dark-800/50">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center text-brand-400">
              <Layers className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">Stitch & Merge Videos</h3>
              <p className="text-xs text-slate-400">
                Arrange clips in playback order and merge them into a single continuous video.
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

        {/* Content body */}
        <div className="p-6 space-y-5 overflow-y-auto flex-1">
          {error && (
            <div className="p-3.5 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-400 text-xs flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Quick Metrics Bar */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-dark-800/60 border border-dark-700/80 rounded-xl p-3 flex flex-col">
              <span className="text-[11px] text-slate-400">Selected Clips</span>
              <span className="text-sm font-semibold text-white mt-0.5">{orderedVideos.length} clips</span>
            </div>
            <div className="bg-dark-800/60 border border-dark-700/80 rounded-xl p-3 flex flex-col">
              <span className="text-[11px] text-slate-400 flex items-center gap-1">
                <Clock className="h-3 w-3 text-brand-400" /> Total Duration
              </span>
              <span className="text-sm font-semibold text-white mt-0.5 font-mono">
                {formatDuration(totalDuration)}
              </span>
            </div>
            <div className="bg-dark-800/60 border border-dark-700/80 rounded-xl p-3 flex flex-col">
              <span className="text-[11px] text-slate-400 flex items-center gap-1">
                <HardDrive className="h-3 w-3 text-brand-400" /> Est. File Size
              </span>
              <span className="text-sm font-semibold text-white mt-0.5 font-mono">
                ~{formatBytes(totalSize)}
              </span>
            </div>
          </div>

          {/* Ordered Video Sequence List */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-medium text-slate-300">
              <span>Sequence Order ({orderedVideos.length})</span>
              <span className="text-slate-500 text-[11px]">Use arrows to reorder playback</span>
            </div>

            <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
              {orderedVideos.map((video, idx) => (
                <div
                  key={video.id}
                  className="bg-dark-800/80 border border-dark-700 rounded-xl p-3 flex items-center justify-between gap-3 hover:border-dark-600 transition-colors"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="h-6 w-6 rounded-md bg-brand-500/20 text-brand-400 text-xs font-mono font-bold flex items-center justify-center shrink-0">
                      {idx + 1}
                    </span>
                    <div className="h-9 w-12 rounded-lg bg-dark-900 border border-dark-700 shrink-0 overflow-hidden flex items-center justify-center">
                      {video.thumbnail_url ? (
                        <img src={video.thumbnail_url} alt="" className="w-full h-full object-cover" />
                      ) : (
                        <Video className="h-4 w-4 text-slate-600" />
                      )}
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-medium text-slate-200 truncate" title={video.title}>
                        {video.title || 'Untitled clip'}
                      </p>
                      <div className="flex items-center gap-2 text-[10px] text-slate-400 font-mono mt-0.5">
                        <span>{formatDuration(video.duration)}</span>
                        <span>•</span>
                        <span>{formatBytes(video.file_size)}</span>
                        {video.resolution && (
                          <>
                            <span>•</span>
                            <span>{video.resolution}</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-1 shrink-0">
                    <button
                      onClick={() => moveUp(idx)}
                      disabled={idx === 0}
                      className="p-1 text-slate-400 hover:text-white disabled:opacity-30 disabled:hover:text-slate-400 rounded hover:bg-dark-700 transition-colors"
                      title="Move Up"
                    >
                      <ArrowUp className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => moveDown(idx)}
                      disabled={idx === orderedVideos.length - 1}
                      className="p-1 text-slate-400 hover:text-white disabled:opacity-30 disabled:hover:text-slate-400 rounded hover:bg-dark-700 transition-colors"
                      title="Move Down"
                    >
                      <ArrowDown className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => removeItem(video.id)}
                      disabled={orderedVideos.length <= 2}
                      className="p-1 text-slate-500 hover:text-rose-400 disabled:opacity-20 disabled:hover:text-slate-500 rounded hover:bg-dark-700 transition-colors ml-1"
                      title="Remove clip from merge"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Output Title */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-slate-300">Merged Video Title</label>
            <input
              type="text"
              value={outputTitle}
              onChange={(e) => setOutputTitle(e.target.value)}
              placeholder="e.g. Full_Lecture_Part1_and_Part2"
              className="w-full bg-dark-800 border border-dark-700 rounded-xl px-3.5 py-2 text-xs text-slate-200 outline-none focus:border-brand-500 transition-colors"
            />
          </div>

          {/* Stitch Engine Mode */}
          <div className="space-y-2">
            <label className="text-xs font-medium text-slate-300">Merge Processing Mode</label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-left">
              {/* Auto */}
              <button
                type="button"
                onClick={() => setStitchMode('auto')}
                className={`p-3 rounded-xl border text-left transition-all ${
                  stitchMode === 'auto'
                    ? 'border-brand-500/80 bg-brand-500/10'
                    : 'border-dark-700 bg-dark-800/50 hover:border-dark-600'
                }`}
              >
                <div className="flex items-center gap-1.5 text-xs font-semibold text-white">
                  <Zap className="h-3.5 w-3.5 text-brand-400" />
                  <span>Smart Auto</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1 leading-snug">
                  Tries instant lossless concat first; auto-reencodes if codecs or dimensions differ.
                </p>
              </button>

              {/* Fast Copy */}
              <button
                type="button"
                onClick={() => setStitchMode('fast')}
                className={`p-3 rounded-xl border text-left transition-all ${
                  stitchMode === 'fast'
                    ? 'border-brand-500/80 bg-brand-500/10'
                    : 'border-dark-700 bg-dark-800/50 hover:border-dark-600'
                }`}
              >
                <div className="flex items-center gap-1.5 text-xs font-semibold text-white">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Fast Stream Copy</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1 leading-snug">
                  Direct bitstream join without re-encoding. Instant & lossless (same codec required).
                </p>
              </button>

              {/* Safe Reencode */}
              <button
                type="button"
                onClick={() => setStitchMode('reencode')}
                className={`p-3 rounded-xl border text-left transition-all ${
                  stitchMode === 'reencode'
                    ? 'border-brand-500/80 bg-brand-500/10'
                    : 'border-dark-700 bg-dark-800/50 hover:border-dark-600'
                }`}
              >
                <div className="flex items-center gap-1.5 text-xs font-semibold text-white">
                  <RefreshCw className="h-3.5 w-3.5 text-blue-400" />
                  <span>Safe Re-encode</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-1 leading-snug">
                  Normalizes all clips to standard 1080p MP4. Guarantees playback on all mixed formats.
                </p>
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-dark-800 bg-dark-800/40 flex items-center justify-end gap-3">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white hover:bg-dark-800 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={handleStartStitch}
            disabled={loading || orderedVideos.length < 2}
            className="px-5 py-2.5 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-xs font-medium shadow-lg shadow-brand-500/20 disabled:opacity-40 flex items-center gap-2 transition-all"
          >
            {loading ? (
              <>
                <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                <span>Starting Merge Engine...</span>
              </>
            ) : (
              <>
                <Layers className="h-3.5 w-3.5" />
                <span>Merge & Stitch Videos ({orderedVideos.length})</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

