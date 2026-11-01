import {
  VideoItem,
  InspectResult,
  DownloadRequestPayload,
  SystemSettings,
  FolderBrowseResponse,
  TorStatus,
  StitchRequestPayload,
  StitchPreviewResponse
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
