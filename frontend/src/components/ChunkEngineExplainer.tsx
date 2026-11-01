import React from 'react';
import { X, Layers, Split, Merge, CheckCircle2, Cpu, Code2 } from 'lucide-react';

interface ChunkEngineExplainerProps {
  onClose: () => void;
}

export const ChunkEngineExplainer: React.FC<ChunkEngineExplainerProps> = ({ onClose }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="bg-dark-900 border border-dark-700 rounded-2xl w-full max-w-3xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="p-5 border-b border-dark-700 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-brand-500/10 border border-brand-500/20 rounded-xl text-brand-400">
              <Layers className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Video Chunking & Merging Architecture</h3>
              <p className="text-xs text-slate-400">Engineered for segmented streams & high-concurrency downloads</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white bg-dark-800 hover:bg-dark-700 rounded-lg transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto space-y-6 text-sm text-slate-300">
          {/* Visual Step-by-Step Pipeline */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="bg-dark-800 border border-dark-700 rounded-xl p-4 flex flex-col items-center text-center">
              <div className="p-3 bg-blue-500/10 border border-blue-500/20 text-blue-400 rounded-xl mb-3">
                <Split className="h-6 w-6" />
              </div>
              <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-1">1. Chunk Discovery</h4>
              <p className="text-xs text-slate-400">
                Probes HTTP `Range` headers or parses `.m3u8` playlists and CDN segments into N chunk URLs.
              </p>
            </div>

            <div className="bg-dark-800 border border-dark-700 rounded-xl p-4 flex flex-col items-center text-center">
              <div className="p-3 bg-brand-500/10 border border-brand-500/20 text-brand-400 rounded-xl mb-3">
                <Cpu className="h-6 w-6" />
              </div>
              <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-1">2. Async Parallel Fetch</h4>
              <p className="text-xs text-slate-400">
                Downloads chunks concurrently with bounded async workers, tracking progress & speed in real-time.
              </p>
            </div>

            <div className="bg-dark-800 border border-dark-700 rounded-xl p-4 flex flex-col items-center text-center">
              <div className="p-3 bg-purple-500/10 border border-purple-500/20 text-purple-400 rounded-xl mb-3">
                <Merge className="h-6 w-6" />
              </div>
              <h4 className="text-xs font-bold text-white uppercase tracking-wider mb-1">3. Binary Stream Merge</h4>
              <p className="text-xs text-slate-400">
                Streams and stitches chunk parts deterministically into the final container with zero RAM bloat.
              </p>
            </div>
          </div>

          {/* Code Extensibility Callout */}
          <div className="bg-dark-800/80 border border-dark-700 rounded-xl p-4 space-y-3">
            <div className="flex items-center gap-2 text-white font-semibold text-xs">
              <Code2 className="h-4 w-4 text-brand-400" />
              Extending for Complex Sites (Chunking Engine):
            </div>
            <p className="text-xs text-slate-400">
              In <code className="text-brand-300 font-mono">backend/app/services/chunk_engine.py</code>, you have dedicated methods:
            </p>
            <ul className="text-xs space-y-2 list-disc list-inside text-slate-300">
              <li>
                <span className="font-mono text-brand-400">download_with_chunking()</span>: Computes byte ranges (e.g. 0-25MB, 25-50MB, etc.) and fetches in parallel.
              </li>
              <li>
                <span className="font-mono text-brand-400">download_segment_list()</span>: Takes an array of arbitrary chunk URLs (from proprietary video player APIs or scraping scripts) and merges them sequentially.
              </li>
              <li>
                <span className="font-mono text-brand-400">merge_chunks()</span>: Buffered stream stitcher with automatic integrity checking and temp file cleanup.
              </li>
            </ul>
          </div>

          {/* Quick test instructions */}
          <div className="border border-brand-500/30 bg-brand-500/5 rounded-xl p-4">
            <h4 className="text-xs font-semibold text-brand-400 flex items-center gap-1.5 mb-1">
              <CheckCircle2 className="h-4 w-4" /> Ready for Live Use
            </h4>
            <p className="text-xs text-slate-400">
              You can test chunking immediately on any direct MP4 or video stream by toggling <strong className="text-slate-200">Chunking & Engine Options</strong> on the dashboard and selecting <strong className="text-brand-300">Parallel Range Chunk Engine</strong>!
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-dark-700 bg-dark-800/60 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-xl text-xs font-medium transition-all"
          >
            Got it, Let's Download!
          </button>
        </div>
      </div>
    </div>
  );
};

