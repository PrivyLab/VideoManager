import {
  VideoItem,
  InspectResult,
  DownloadRequestPayload,
  SystemSettings,
  FolderBrowseResponse,
  TorStatus,
  StitchRequestPayload,
  StitchPreviewResponse,
  NetworkStatusResponse,
  ExtractAudioPayload,
  CompressVideoPayload,
  CreateGifPayload,
  TrimVideoPayload,
  BatchDownloadPayload,
  PlaylistInspectResponse,
} from './types';

const API_BASE = '/api';

export async function fetchVideos(): Promise<VideoItem[]> {
  const res = await fetch(`${API_BASE}/videos`);
  if (!res.ok) throw new Error('Failed to fetch videos');
  const data = await res.json();
  return data.videos;
}

export async function inspectUrl(url: string): Promise<InspectResult> {
  const res = await fetch(`${API_BASE}/downloads/inspect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) throw new Error('Failed to inspect URL');
  return res.json();
}

export async function startDownload(payload: DownloadRequestPayload): Promise<{ video_id: string }> {
  const res = await fetch(`${API_BASE}/downloads`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to start download');
  }
  return res.json();
}

export async function startBatchDownload(payload: BatchDownloadPayload): Promise<{ success: boolean; count: number; video_ids: string[] }> {
  const res = await fetch(`${API_BASE}/downloads/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to queue batch download');
  }
  return res.json();
}

export async function inspectPlaylist(
  url: string,
  options?: { referer?: string; routing_mode?: string; cookies_from_browser?: string; custom_proxy?: string; max_entries?: number }
): Promise<PlaylistInspectResponse> {
  const res = await fetch(`${API_BASE}/downloads/playlist/inspect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url, ...options }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to inspect playlist');
  }
  return res.json();
}

export async function cancelDownload(videoId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/downloads/${videoId}/cancel`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to cancel download');
}

export async function retryDownload(videoId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/downloads/${videoId}/retry`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to retry download');
}

export async function deleteVideo(videoId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/videos/${videoId}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete video');
}

export async function bulkDeleteVideos(videoIds: string[]): Promise<{ success: boolean; deleted_count: number; deleted_ids: string[] }> {
  const res = await fetch(`${API_BASE}/videos/bulk-delete`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ video_ids: videoIds }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to delete videos in bulk');
  }
  return res.json();
}

export async function cancelAllDownloads(): Promise<{ success: boolean; cancelled_count: number; cancelled_ids: string[] }> {
  const res = await fetch(`${API_BASE}/downloads/cancel-all`, { method: 'POST' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to cancel all downloads');
  }
  return res.json();
}

export async function getSystemSettings(): Promise<SystemSettings> {
  const res = await fetch(`${API_BASE}/system/settings`);
  if (!res.ok) throw new Error('Failed to fetch system settings');
  return res.json();
}

export async function updateSystemSettings(download_folder: string): Promise<{ success: boolean; download_folder: string }> {
  const res = await fetch(`${API_BASE}/system/settings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ download_folder }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to update folder settings');
  }
  return res.json();
}

export async function browseFolders(path?: string): Promise<FolderBrowseResponse> {
  const url = path ? `${API_BASE}/system/browse-folders?path=${encodeURIComponent(path)}` : `${API_BASE}/system/browse-folders`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to browse folders');
  return res.json();
}

export async function getTorStatus(): Promise<TorStatus> {
  const res = await fetch(`${API_BASE}/system/tor-status`);
  if (!res.ok) throw new Error('Failed to check Tor status');
  return res.json();
}

export async function getNetworkStatus(): Promise<NetworkStatusResponse> {
  const res = await fetch(`${API_BASE}/system/network-status`);
  if (!res.ok) throw new Error('Failed to check network status');
  return res.json();
}

export async function stitchVideos(payload: StitchRequestPayload): Promise<{ success: boolean; video_id: string }> {
  const res = await fetch(`${API_BASE}/videos/stitch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to stitch videos');
  }
  return res.json();
}

export async function previewStitch(payload: StitchRequestPayload): Promise<StitchPreviewResponse> {
  const res = await fetch(`${API_BASE}/videos/stitch/preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to generate stitch preview');
  }
  return res.json();
}

export async function extractAudio(videoId: string, payload: ExtractAudioPayload): Promise<{ success: boolean; video: VideoItem }> {
  const res = await fetch(`${API_BASE}/videos/${videoId}/extract-audio`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to extract audio');
  }
  return res.json();
}

export async function compressVideo(videoId: string, payload: CompressVideoPayload): Promise<{ success: boolean; video: VideoItem }> {
  const res = await fetch(`${API_BASE}/videos/${videoId}/compress`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to compress video');
  }
  return res.json();
}

export async function createGif(videoId: string, payload: CreateGifPayload): Promise<{ success: boolean; video: VideoItem }> {
  const res = await fetch(`${API_BASE}/videos/${videoId}/gif`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to create GIF');
  }
  return res.json();
}

export async function trimVideo(videoId: string, payload: TrimVideoPayload): Promise<{ success: boolean; video: VideoItem }> {
  const res = await fetch(`${API_BASE}/videos/${videoId}/trim`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to trim video');
  }
  return res.json();
}

export interface VideoShareLink {
  video_id: string;
  title: string;
  local_ip: string;
  port: number;
  watch_url: string;
  stream_url: string;
  qr_url: string;
  token?: string;
  pin?: string;
  pin_enabled?: boolean;
  encrypted?: boolean;
  duration: number;
  file_size: number;
  file_format: string;
}

export async function getVideoShareLink(videoId: string, port?: number): Promise<VideoShareLink> {
  const p = port || 8000;
  const res = await fetch(`${API_BASE}/videos/${videoId}/share-link?port=${p}`);
  if (!res.ok) throw new Error('Failed to get video share link');
  return res.json();
}

export async function regeneratePin(videoId: string): Promise<{ pin: string; token: string }> {
  const res = await fetch(`${API_BASE}/videos/${videoId}/regenerate-pin`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to regenerate PIN');
  return res.json();
}

export async function updatePinConfig(
  videoId: string,
  payload: { pin?: string; pin_enabled?: boolean }
): Promise<{ pin: string; pin_enabled: boolean; token: string }> {
  const res = await fetch(`${API_BASE}/videos/${videoId}/security-pin`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Failed to update PIN security config');
  return res.json();
}

export interface DiscoveredVideoLink {
  url: string;
  title: string;
  type: string;
  format: string;
  source: string;
  thumbnail?: string;
  resolution?: string;
}

export interface FindLinksResponse {
  page_url: string;
  page_title: string;
  total_found: number;
  links: DiscoveredVideoLink[];
  stealth_used: boolean;
  proxy_used?: string | null;
}

export async function findVideoLinks(payload: {
  url: string;
  routing_mode?: string;
  custom_proxy?: string;
  cookies_from_browser?: string;
  use_stealth?: boolean;
}): Promise<FindLinksResponse> {
  const res = await fetch(`${API_BASE}/downloads/find-links`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to find video links' }));
    throw new Error(err.detail || 'Failed to scan webpage for video links');
  }
  return res.json();
}

export function formatBytes(bytes: number): string {
  if (!bytes || bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
}

export function formatDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return '0:00';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  const h = Math.floor(m / 60);
  if (h > 0) {
    const remM = m % 60;
    return `${h}:${remM < 10 ? '0' : ''}${remM}:${s < 10 ? '0' : ''}${s}`;
  }
  return `${m}:${s < 10 ? '0' : ''}${s}`;
}
