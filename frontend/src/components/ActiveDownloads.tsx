import React from 'react';
import { Loader2, XCircle, ArrowDownCircle, Layers, Zap } from 'lucide-react';
import { VideoItem } from '../types';
import { cancelDownload } from '../api';

interface ActiveDownloadsProps {
  downloads: VideoItem[];
}

export const ActiveDownloads: React.FC<ActiveDownloadsProps> = ({ downloads }) => {
  if (downloads.length === 0) return null;

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-white flex items-center gap-2">
        <ArrowDownCircle className="h-4 w-4 text-brand-400 animate-bounce" />
        Active Downloads ({downloads.length})
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {downloads.map((item) => (
          <div
            key={item.id}
            className="bg-dark-800/90 border border-dark-700 hover:border-dark-600 rounded-xl p-4 shadow-lg space-y-3 relative overflow-hidden transition-all"
          >
            {/* Top row */}
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded font-semibold ${
                      item.status === 'merging'
                        ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                        : item.status === 'downloading'
                        ? 'bg-brand-500/20 text-brand-400 border border-brand-500/30'
                        : 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                    }`}
                  >
                    {item.status === 'merging' ? 'Merging Streams' : item.status}
                  </span>

                  {item.downloader_type === 'chunked' && (
                    <span className="text-[10px] bg-blue-500/20 text-blue-400 border border-blue-500/30 px-1.5 py-0.5 rounded flex items-center gap-1 font-mono">
                      <Layers className="h-2.5 w-2.5" />
                      {item.chunks_completed}/{item.chunks_total || 4} chunks
                    </span>
                  )}
                </div>

                <h4 className="text-sm font-medium text-white truncate" title={item.title || item.url}>
                  {item.title || item.url}
                </h4>
              </div>

              <button
                onClick={() => cancelDownload(item.id)}
                className="text-slate-500 hover:text-rose-400 p-1 rounded-lg hover:bg-dark-700 transition-colors"
                title="Cancel Download"
              >
                <XCircle className="h-4 w-4" />
              </button>
            </div>

            {/* Progress bar */}
            <div>
              <div className="flex justify-between text-xs text-slate-400 mb-1 font-mono">
                <span className="flex items-center gap-1.5 text-brand-400 font-semibold">
                  {item.status === 'merging' ? (
                    <>
                      <Loader2 className="h-3 w-3 animate-spin text-purple-400" />
                      <span className="text-purple-400">Assembling & Storing...</span>
                    </>
                  ) : (
                    <>
                      <Zap className="h-3 w-3 text-brand-400" />
                      {item.progress.toFixed(1)}%
                    </>
                  )}
                </span>
                <div className="flex items-center gap-2">
                  {item.speed && <span className="text-slate-300">{item.speed}</span>}
                  {item.eta && <span className="text-slate-500">ETA: {item.eta}</span>}
                </div>
              </div>

              <div className="w-full bg-dark-900 rounded-full h-2 overflow-hidden border border-dark-700/60">
                <div
                  className={`h-full transition-all duration-300 rounded-full ${
                    item.status === 'merging'
                      ? 'bg-gradient-to-r from-purple-500 to-indigo-500 animate-pulse'
                      : 'bg-gradient-to-r from-brand-500 to-emerald-400'
                  }`}
                  style={{ width: `${Math.max(item.progress, 5)}%` }}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

