import React, { useEffect, useState, useRef, useCallback } from 'react';
import { Navbar } from './components/Navbar';
import { DownloadCard } from './components/DownloadCard';
import { ActiveDownloads } from './components/ActiveDownloads';
import { VideoGrid } from './components/VideoGrid';
import { VideoPlayerModal } from './components/VideoPlayerModal';
import { ChunkEngineExplainer } from './components/ChunkEngineExplainer';
import { FolderPickerModal } from './components/FolderPickerModal';
import { VideoStitchModal } from './components/VideoStitchModal';
import { MediaToolsModal } from './components/MediaToolsModal';
import { fetchVideos, getSystemSettings } from './api';
import { VideoItem, SystemSettings } from './types';

export const App: React.FC = () => {
  const [videos, setVideos] = useState<VideoItem[]>([]);
  const [settings, setSettings] = useState<SystemSettings | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [playingVideo, setPlayingVideo] = useState<VideoItem | null>(null);
  const [showExplainer, setShowExplainer] = useState(false);
  const [showFolderPicker, setShowFolderPicker] = useState(false);
  const [stitchModalVideos, setStitchModalVideos] = useState<VideoItem[] | null>(null);
  const [mediaToolsTarget, setMediaToolsTarget] = useState<{ video: VideoItem; initialTab: 'audio' | 'compress' | 'gif' | 'trim' } | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const loadVideos = useCallback(async () => {
    try {
      const data = await fetchVideos();
      setVideos(data);
    } catch (err) {
      console.error('Failed to load videos', err);
    }
  }, []);

  const loadSettings = useCallback(async () => {
    try {
      const data = await getSystemSettings();
      setSettings(data);
    } catch (err) {
      console.error('Failed to load settings', err);
    }
  }, []);

  useEffect(() => {
    loadVideos();
    loadSettings();
  }, [loadVideos, loadSettings]);

  // WebSocket connection management
  useEffect(() => {
    let reconnectTimeout: any;

    const connectWs = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/downloads`;
      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setWsConnected(true);
      };

      ws.onclose = () => {
        setWsConnected(false);
        reconnectTimeout = setTimeout(connectWs, 2500);
      };

      ws.onerror = () => {
        ws.close();
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.event === 'progress') {
            setVideos((prev) =>
              prev.map((v) => {
                if (v.id === data.video_id) {
                  return {
                    ...v,
                    status: data.status || v.status,
                    progress: data.progress !== undefined ? data.progress : v.progress,
                    speed: data.speed !== undefined ? data.speed : v.speed,
                    eta: data.eta !== undefined ? data.eta : v.eta,
                    chunks_total: data.chunks_total || v.chunks_total,
                    chunks_completed: data.chunks_completed || v.chunks_completed,
                  };
                }
                return v;
              })
            );
          } else if (data.event === 'video_created') {
            setVideos((prev) => [data.video, ...prev.filter((v) => v.id !== data.video.id)]);
          } else if (data.event === 'completed' || data.event === 'failed') {
            loadVideos();
            loadSettings();
          }
        } catch (e) {
          // ignore ping/pong
        }
      };

      wsRef.current = ws;
    };

    connectWs();

    const pingInterval = setInterval(() => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send('ping');
      }
    }, 15000);

    return () => {
      clearInterval(pingInterval);
      clearTimeout(reconnectTimeout);
      if (wsRef.current) wsRef.current.close();
    };
  }, [loadVideos, loadSettings]);

  const activeDownloads = videos.filter((v) =>
    ['queued', 'downloading', 'merging'].includes(v.status)
  );

  const totalStorage = videos.reduce((acc, v) => acc + (v.file_size || 0), 0);
  const completedVideos = videos.filter((v) => v.status === 'completed');

  return (
    <div className="min-h-screen bg-[#0B0F19] text-slate-100 flex flex-col font-sans">
      <Navbar
        wsConnected={wsConnected}
        totalVideos={completedVideos.length}
        totalStorage={totalStorage}
        activeCount={activeDownloads.length}
        settings={settings}
        onOpenExplainer={() => setShowExplainer(true)}
        onOpenFolderPicker={() => setShowFolderPicker(true)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Download Action Card */}
        <DownloadCard
          currentFolder={settings?.download_folder}
          onDownloadStarted={() => {
            loadVideos();
            loadSettings();
          }}
          onOpenFolderPicker={() => setShowFolderPicker(true)}
        />

        {/* Active Realtime Downloads */}
        <ActiveDownloads downloads={activeDownloads} />

        {/* Video Gallery / History */}
        <VideoGrid
          videos={videos}
          onPlayVideo={(video) => setPlayingVideo(video)}
          onRefresh={loadVideos}
          onOpenStitchModal={(selected) => setStitchModalVideos(selected)}
          onOpenMediaTools={(video, initialTab = 'audio') => setMediaToolsTarget({ video, initialTab })}
        />
      </main>

      {/* Video Player Modal */}
      <VideoPlayerModal
        video={playingVideo}
        onClose={() => setPlayingVideo(null)}
      />

      {/* Media Studio & Converter Modal (Audio, Compress, GIF, Trim) */}
      {mediaToolsTarget && (
        <MediaToolsModal
          video={mediaToolsTarget.video}
          initialTab={mediaToolsTarget.initialTab}
          onClose={() => setMediaToolsTarget(null)}
          onSuccess={() => {
            setMediaToolsTarget(null);
            loadVideos();
            loadSettings();
          }}
        />
      )}

      {/* Video Stitching Modal */}
      {stitchModalVideos && (
        <VideoStitchModal
          selectedVideos={stitchModalVideos}
          onClose={() => setStitchModalVideos(null)}
          onStitchSuccess={() => {
            setStitchModalVideos(null);
            loadVideos();
            loadSettings();
          }}
        />
      )}

      {/* Chunking Architecture Explainer Modal */}
      {showExplainer && (
        <ChunkEngineExplainer onClose={() => setShowExplainer(false)} />
      )}

      {/* Folder Picker Modal */}
      {showFolderPicker && (
        <FolderPickerModal
          currentFolder={settings?.download_folder || ''}
          settings={settings}
          onClose={() => setShowFolderPicker(false)}
          onFolderSelected={(newFolder) => {
            setSettings((prev) => prev ? { ...prev, download_folder: newFolder } : null);
            loadSettings();
          }}
        />
      )}
    </div>
  );
};
