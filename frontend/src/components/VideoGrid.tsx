import React, { useState } from 'react';
import {
  Play,
  Download,
  Trash2,
  RotateCcw,
  Clock,
  HardDrive,
  Video,
  Layers,
  Search,
  Check,
  CheckSquare,
  Square,
  X,
  Music,
  Scissors,
  Sparkles,
  Minimize2,
  Smartphone,
  Loader2
} from 'lucide-react';
import { VideoItem } from '../types';
import { formatBytes, formatDuration, deleteVideo, retryDownload, bulkDeleteVideos } from '../api';

interface VideoGridProps {
  videos: VideoItem[];
  onPlayVideo: (video: VideoItem) => void;
  onRefresh: () => void;
  onOpenStitchModal: (selected: VideoItem[]) => void;
  onOpenMediaTools: (video: VideoItem, initialTab?: 'audio' | 'compress' | 'gif' | 'trim') => void;
  onOpenMobileStream: (video: VideoItem) => void;
}

export const VideoGrid: React.FC<VideoGridProps> = ({
  videos,
  onPlayVideo,
  onRefresh,
  onOpenStitchModal,
  onOpenMediaTools,
  onOpenMobileStream,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filter, setFilter] = useState<'all' | 'completed' | 'failed'>('all');
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const completedVideos = videos.filter((v) => v.status === 'completed');

  const filteredVideos = videos.filter((v) => {
    const matchesSearch = (v.title || v.url).toLowerCase().includes(searchTerm.toLowerCase());
    if (filter === 'completed') return matchesSearch && v.status === 'completed';
    if (filter === 'failed') return matchesSearch && (v.status === 'failed' || v.status === 'cancelled');
    return matchesSearch;
  });

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleSelectAll = () => {
    if (selectedIds.length === filteredVideos.length && filteredVideos.length > 0) {
      setSelectedIds([]);
    } else {
      setSelectedIds(filteredVideos.map((v) => v.id));
    }
  };

  const handleDelete = async (id: string) => {
    if (window.confirm('Are you sure you want to delete this video?')) {
      await deleteVideo(id);
      setSelectedIds((prev) => prev.filter((item) => item !== id));
      onRefresh();
    }
  };

  const handleBulkDelete = async () => {
    if (selectedIds.length === 0) return;
    const count = selectedIds.length;
    if (window.confirm(`Are you sure you want to permanently delete ${count} selected video${count > 1 ? 's' : ''} and all stored files from disk?`)) {
      try {
        setIsDeleting(true);
        await bulkDeleteVideos(selectedIds);
        setNotice(`Successfully deleted ${count} video${count > 1 ? 's' : ''} from library.`);
        setTimeout(() => setNotice(null), 3500);
        setSelectedIds([]);
        setIsSelectionMode(false);
        onRefresh();
      } catch (err: any) {
        setNotice(`Failed to delete videos: ${err.message || 'Unknown error'}`);
        setTimeout(() => setNotice(null), 4000);
      } finally {
        setIsDeleting(false);
      }
    }
  };

  const handleRetry = async (id: string) => {
    await retryDownload(id);
    onRefresh();
  };

  const selectedCompletedVideos = selectedIds
    .map((id) => videos.find((v) => v.id === id))
    .filter((v): v is VideoItem => Boolean(v && v.status === 'completed'));

  const handleLaunchStitch = () => {
    if (selectedCompletedVideos.length >= 2) {
      onOpenStitchModal(selectedCompletedVideos);
    }
  };

  return (
    <div className="space-y-4 relative pb-16">
      {/* Search, Filter & Bulk Actions Header */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2.5 self-start sm:self-auto flex-wrap">
          <h3 className="text-base font-semibold text-white flex items-center gap-2">
            <Video className="h-5 w-5 text-brand-400" />
            Video Library ({videos.length})
          </h3>

          {/* Select & Bulk Actions Toggle Button */}
          {videos.length > 0 && (
            <button
              onClick={() => {
                setIsSelectionMode(!isSelectionMode);
                if (isSelectionMode) setSelectedIds([]);
              }}
              className={`px-3 py-1.5 text-xs rounded-xl flex items-center gap-1.5 transition-all font-medium border shadow-sm ${
                isSelectionMode
                  ? 'bg-brand-500/20 text-brand-300 border-brand-500/50 shadow-brand-500/10'
                  : 'bg-dark-800 text-slate-200 border-dark-700 hover:text-white hover:border-brand-500/40 hover:bg-dark-700'
              }`}
              title="Select multiple videos for bulk deletion or stitching"
            >
              <CheckSquare className="h-3.5 w-3.5 text-brand-400" />
              <span>{isSelectionMode ? 'Cancel Selection' : 'Select / Bulk Delete'}</span>
              {selectedIds.length > 0 && isSelectionMode && (
                <span className="text-[10px] bg-brand-500/20 text-brand-400 px-1.5 py-0.2 rounded-full font-mono">
                  {selectedIds.length} selected
                </span>
              )}
            </button>
          )}

          {/* Stitch Mode Shortcut Button */}
          {completedVideos.length >= 2 && !isSelectionMode && (
            <button
              onClick={() => {
                setIsSelectionMode(true);
                setSelectedIds(completedVideos.slice(0, 2).map((v) => v.id));
              }}
              className="px-3 py-1.5 text-xs rounded-xl flex items-center gap-1.5 transition-all font-medium border shadow-sm bg-dark-800 text-slate-200 border-dark-700 hover:text-white hover:border-brand-500/40 hover:bg-dark-700"
              title="Select multiple videos and stitch them together"
            >
              <Layers className="h-3.5 w-3.5 text-brand-400" />
              <span>Stitch Videos</span>
              <span className="text-[10px] bg-brand-500/20 text-brand-400 px-1.5 py-0.2 rounded-full font-mono">
                {completedVideos.length} ready
              </span>
            </button>
          )}
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          {/* Search bar */}
          <div className="relative flex-1 sm:w-64">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search library..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full bg-dark-800 border border-dark-700 text-slate-200 text-xs rounded-lg pl-9 pr-3 py-2 outline-none focus:border-brand-500"
            />
          </div>

          {/* Filter Pills */}
          <div className="flex bg-dark-800 p-0.5 rounded-lg border border-dark-700 text-xs">
            <button
              onClick={() => setFilter('all')}
              className={`px-3 py-1.5 rounded-md transition-all ${
                filter === 'all' ? 'bg-dark-700 text-white font-medium' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setFilter('completed')}
              className={`px-3 py-1.5 rounded-md transition-all ${
                filter === 'completed' ? 'bg-dark-700 text-brand-400 font-medium' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Ready
            </button>
            <button
              onClick={() => setFilter('failed')}
              className={`px-3 py-1.5 rounded-md transition-all ${
                filter === 'failed' ? 'bg-dark-700 text-rose-400 font-medium' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Failed
            </button>
          </div>
        </div>
      </div>

      {notice && (
        <div className="p-3 bg-brand-500/10 border border-brand-500/30 rounded-xl text-brand-300 text-xs flex items-center justify-between animate-in fade-in duration-200">
          <span>{notice}</span>
          <button onClick={() => setNotice(null)} className="text-slate-400 hover:text-white p-1">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* Grid or Empty State */}
      {filteredVideos.length === 0 ? (
        <div className="bg-dark-800/40 border border-dashed border-dark-700 rounded-2xl p-12 text-center">
          <div className="h-12 w-12 rounded-full bg-dark-700/60 flex items-center justify-center mx-auto mb-3 text-slate-500">
            <Video className="h-6 w-6" />
          </div>
          <h4 className="text-sm font-medium text-slate-300">No videos found</h4>
          <p className="text-xs text-slate-500 mt-1">
            {searchTerm ? 'Try a different search term.' : 'Paste a video URL above to download your first video.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredVideos.map((video) => {
            const isCompleted = video.status === 'completed';
            const isSelected = selectedIds.includes(video.id);
            const selectionIndex = selectedIds.indexOf(video.id) + 1;

            return (
              <div
                key={video.id}
                onClick={() => {
                  if (isSelectionMode) {
                    toggleSelect(video.id);
                  }
                }}
                className={`group bg-dark-800/90 border rounded-2xl overflow-hidden shadow-lg transition-all flex flex-col relative ${
                  isSelected
                    ? 'border-brand-500/80 ring-2 ring-brand-500/20 bg-dark-800'
                    : isSelectionMode
                    ? 'border-dark-600 hover:border-brand-500/50 cursor-pointer'
                    : 'border-dark-700 hover:border-dark-600 hover:shadow-xl hover:shadow-brand-500/5'
                }`}
              >
                {/* Media Thumbnail Container */}
                <div className="relative aspect-video bg-dark-900 overflow-hidden flex items-center justify-center">
                  {video.file_format === 'mp3' || video.downloader_type === 'audio' ? (
                    <div className="flex flex-col items-center justify-center gap-1.5 text-brand-400 bg-gradient-to-br from-brand-950/80 to-dark-900 w-full h-full">
                      <div className="h-12 w-12 rounded-full bg-brand-500/20 flex items-center justify-center">
                        <Music className="h-6 w-6 text-brand-400" />
                      </div>
                      <span className="text-[10px] font-mono tracking-wider text-brand-300 uppercase font-semibold">
                        Audio Track
                      </span>
                    </div>
                  ) : video.thumbnail_url ? (
                    <img
                      src={video.thumbnail_url}
                      alt={video.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                      loading="lazy"
                    />
                  ) : (
                    <div className="flex flex-col items-center gap-1 text-slate-600">
                      <Video className="h-10 w-10" />
                      <span className="text-[10px] font-mono uppercase">{video.file_format || 'MP4'}</span>
                    </div>
                  )}

                  {/* Selection Mode Checkbox Badge */}
                  {isSelectionMode && (
                    <div className="absolute top-2 right-2 z-10">
                      {isSelected ? (
                        <div className="h-6 w-6 rounded-lg bg-brand-500 text-white font-mono text-xs font-bold flex items-center justify-center shadow-lg border border-brand-400">
                          {selectionIndex}
                        </div>
                      ) : (
                        <div className="h-6 w-6 rounded-lg bg-black/60 border border-white/40 backdrop-blur-sm flex items-center justify-center text-transparent hover:border-white">
                          <Check className="h-3.5 w-3.5" />
                        </div>
                      )}
                    </div>
                  )}

                  {/* Status or duration badge */}
                  {isCompleted && (
                    <>
                      {video.duration > 0 && (
                        <span className="absolute bottom-2 right-2 bg-black/80 backdrop-blur-sm text-slate-200 text-[11px] px-2 py-0.5 rounded font-mono flex items-center gap-1">
                          <Clock className="h-3 w-3 text-brand-400" />
                          {formatDuration(video.duration)}
                        </span>
                      )}

                      {/* Quick Play Hover Button (only when not in selection mode) */}
                      {!isSelectionMode && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onPlayVideo(video);
                          }}
                          className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity backdrop-blur-[2px]"
                          title="Play Video"
                        >
                          <div className="h-12 w-12 rounded-full bg-brand-500 text-white flex items-center justify-center shadow-lg transform group-hover:scale-110 transition-transform">
                            <Play className="h-6 w-6 ml-1 fill-white" />
                          </div>
                        </button>
                      )}
                    </>
                  )}

                  {video.status === 'failed' && (
                    <div className="absolute inset-0 bg-rose-950/60 flex items-center justify-center p-3 text-center">
                      <span className="text-xs text-rose-300">Download Failed</span>
                    </div>
                  )}

                  {/* Top Badges */}
                  <div className="absolute top-2 left-2 flex items-center gap-1.5 flex-wrap">
                    <span className="bg-dark-900/80 backdrop-blur-sm text-slate-300 text-[10px] font-mono uppercase px-2 py-0.5 rounded border border-dark-700">
                      {video.file_format || 'mp4'}
                    </span>
                    {video.downloader_type === 'chunked' && (
                      <span className="bg-blue-900/80 backdrop-blur-sm text-blue-300 text-[10px] px-1.5 py-0.5 rounded flex items-center gap-1 font-mono border border-blue-700/60">
                        <Layers className="h-2.5 w-2.5" /> Chunk Engine
                      </span>
                    )}
                    {video.downloader_type === 'stitch' && (
                      <span className="bg-purple-900/80 backdrop-blur-sm text-purple-300 text-[10px] px-1.5 py-0.5 rounded flex items-center gap-1 font-mono border border-purple-700/60">
                        <Layers className="h-2.5 w-2.5" /> Stitched
                      </span>
                    )}
                    {video.downloader_type === 'audio' && (
                      <span className="bg-amber-900/80 backdrop-blur-sm text-amber-300 text-[10px] px-1.5 py-0.5 rounded flex items-center gap-1 font-mono border border-amber-700/60">
                        <Music className="h-2.5 w-2.5" /> Audio Track
                      </span>
                    )}
                    {video.downloader_type === 'compress' && (
                      <span className="bg-emerald-900/80 backdrop-blur-sm text-emerald-300 text-[10px] px-1.5 py-0.5 rounded flex items-center gap-1 font-mono border border-emerald-700/60">
                        <Minimize2 className="h-2.5 w-2.5" /> Compressed
                      </span>
                    )}
                    {video.downloader_type === 'gif' && (
                      <span className="bg-pink-900/80 backdrop-blur-sm text-pink-300 text-[10px] px-1.5 py-0.5 rounded flex items-center gap-1 font-mono border border-pink-700/60">
                        <Sparkles className="h-2.5 w-2.5" /> Animated GIF
                      </span>
                    )}
                    {video.downloader_type === 'trim' && (
                      <span className="bg-teal-900/80 backdrop-blur-sm text-teal-300 text-[10px] px-1.5 py-0.5 rounded flex items-center gap-1 font-mono border border-teal-700/60">
                        <Scissors className="h-2.5 w-2.5" /> Clip
                      </span>
                    )}
                  </div>
                </div>

                {/* Video Info Section */}
                <div className="p-4 flex-1 flex flex-col justify-between space-y-3">
                  <div>
                    <h4
                      className={`text-sm font-semibold text-white line-clamp-2 transition-colors ${
                        isSelectionMode ? '' : 'hover:text-brand-400 cursor-pointer'
                      }`}
                      onClick={() => {
                        if (!isSelectionMode && isCompleted) onPlayVideo(video);
                      }}
                      title={video.title || video.url}
                    >
                      {video.title || video.url}
                    </h4>
                    {video.error_message && (
                      <p className="text-xs text-rose-400 mt-1 line-clamp-2" title={video.error_message}>
                        {video.error_message}
                      </p>
                    )}
                  </div>

                  {/* Metadata & Actions */}
                  <div className="pt-2 border-t border-dark-700/80 flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs text-slate-400">
                      <span className="flex items-center gap-1">
                        <HardDrive className="h-3 w-3 text-slate-500" />
                        {formatBytes(video.file_size)}
                      </span>
                      {video.resolution && (
                        <span className="text-[11px] font-mono text-slate-500">
                          {video.resolution}
                        </span>
                      )}
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-1">
                      {isCompleted ? (
                        <>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onPlayVideo(video);
                            }}
                            className="p-1.5 text-slate-400 hover:text-brand-400 hover:bg-dark-700 rounded-lg transition-colors"
                            title="Stream & Play"
                          >
                            <Play className="h-4 w-4" />
                          </button>
                          {video.file_format !== 'mp3' && video.downloader_type !== 'audio' && (
                            <>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onOpenMediaTools(video, 'audio');
                                }}
                                className="p-1.5 text-slate-400 hover:text-amber-400 hover:bg-dark-700 rounded-lg transition-colors"
                                title="Extract Audio (MP3 / M4A)"
                              >
                                <Music className="h-4 w-4" />
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onOpenMediaTools(video, 'compress');
                                }}
                                className="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-dark-700 rounded-lg transition-colors"
                                title="Compress / Shrink File"
                              >
                                <Minimize2 className="h-4 w-4" />
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onOpenMediaTools(video, 'gif');
                                }}
                                className="p-1.5 text-slate-400 hover:text-pink-400 hover:bg-dark-700 rounded-lg transition-colors"
                                title="Convert to GIF / Trim"
                              >
                                <Scissors className="h-4 w-4" />
                              </button>
                            </>
                          )}
                          <a
                            href={`/api/videos/${video.id}/download`}
                            download
                            onClick={(e) => e.stopPropagation()}
                            className="p-1.5 text-slate-400 hover:text-white hover:bg-dark-700 rounded-lg transition-colors"
                            title="Save to Computer"
                          >
                            <Download className="h-4 w-4" />
                          </a>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              onOpenMobileStream(video);
                            }}
                            className="p-1.5 text-slate-400 hover:text-emerald-400 hover:bg-dark-700 rounded-lg transition-colors"
                            title="Watch on Phone (Wi-Fi QR Code)"
                          >
                            <Smartphone className="h-4 w-4" />
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRetry(video.id);
                          }}
                          className="p-1.5 text-slate-400 hover:text-amber-400 hover:bg-dark-700 rounded-lg transition-colors"
                          title="Retry Download"
                        >
                          <RotateCcw className="h-4 w-4" />
                        </button>
                      )}

                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDelete(video.id);
                        }}
                        className="p-1.5 text-slate-400 hover:text-rose-400 hover:bg-dark-700 rounded-lg transition-colors"
                        title="Delete Video"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Floating Bulk Actions Toolbar */}
      {isSelectionMode && (
        <div className="fixed bottom-6 left-1/2 transform -translate-x-1/2 z-40 bg-dark-900/95 border border-brand-500/40 backdrop-blur-md rounded-2xl shadow-2xl px-5 py-3 flex items-center gap-3 sm:gap-4 animate-in slide-in-from-bottom-5 duration-200 max-w-[95vw] overflow-x-auto">
          <div className="flex items-center gap-2 text-xs text-slate-200 whitespace-nowrap">
            <span className="h-6 w-6 rounded-full bg-brand-500/20 text-brand-400 flex items-center justify-center font-bold text-xs">
              {selectedIds.length}
            </span>
            <span className="font-medium">
              {selectedIds.length === 1
                ? '1 video selected'
                : `${selectedIds.length} videos selected`}
            </span>
          </div>

          <div className="h-4 w-px bg-dark-700 shrink-0" />

          {/* Select All / Clear All */}
          <button
            onClick={handleSelectAll}
            className="text-xs text-slate-300 hover:text-white transition-colors flex items-center gap-1.5 whitespace-nowrap px-2 py-1 rounded-lg hover:bg-dark-800"
          >
            {selectedIds.length === filteredVideos.length && filteredVideos.length > 0 ? (
              <>
                <Square className="h-3.5 w-3.5 text-slate-400" />
                <span>Clear All</span>
              </>
            ) : (
              <>
                <CheckSquare className="h-3.5 w-3.5 text-brand-400" />
                <span>Select All ({filteredVideos.length})</span>
              </>
            )}
          </button>

          {/* Bulk Delete Button */}
          <button
            onClick={handleBulkDelete}
            disabled={selectedIds.length === 0 || isDeleting}
            className="px-3.5 py-1.5 rounded-xl bg-rose-500/20 border border-rose-500/40 hover:bg-rose-600 hover:border-rose-600 disabled:opacity-40 text-rose-300 hover:text-white text-xs font-medium shadow-md shadow-rose-500/10 flex items-center gap-1.5 transition-all whitespace-nowrap"
            title="Permanently delete all selected videos from library and disk"
          >
            {isDeleting ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                <span>Deleting...</span>
              </>
            ) : (
              <>
                <Trash2 className="h-3.5 w-3.5" />
                <span>Delete Selected ({selectedIds.length})</span>
              </>
            )}
          </button>

          {/* Stitch Shortcut Button (if >= 2 completed videos selected) */}
          {selectedCompletedVideos.length >= 2 && (
            <button
              onClick={handleLaunchStitch}
              className="px-3.5 py-1.5 rounded-xl bg-brand-500 hover:bg-brand-600 text-white text-xs font-medium shadow-md shadow-brand-500/20 flex items-center gap-1.5 transition-all whitespace-nowrap"
            >
              <Layers className="h-3.5 w-3.5" />
              <span>Stitch ({selectedCompletedVideos.length})</span>
            </button>
          )}

          <button
            onClick={() => {
              setIsSelectionMode(false);
              setSelectedIds([]);
            }}
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-dark-800 transition-colors ml-1"
            title="Exit selection mode"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}
    </div>
  );
};
