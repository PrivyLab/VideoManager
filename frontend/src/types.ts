export interface VideoItem {
  id: string;
  url: string;
  title: string;
  duration: number;
  file_path: string;
  file_size: number;
  file_format: string;
  thumbnail_url?: string;
  resolution?: string;
  status: 'queued' | 'downloading' | 'merging' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  speed?: string;
  eta?: string;
  error_message?: string;
  downloader_type: 'ytdlp' | 'chunked' | 'direct' | 'auto' | 'stitch';
  chunks_total?: number;
  chunks_completed?: number;
  created_at: string;
  completed_at?: string;
}

export interface VideoFormat {
  format_id: string;
  ext: string;
  resolution: string;
  filesize?: number;
}

export interface InspectResult {
  source: 'ytdlp' | 'direct';
  info: {
    title: string;
    duration: number;
    thumbnail?: string;
    description?: string;
    uploader?: string;
    formats?: VideoFormat[];
    probe?: {
      content_length: number;
      accept_ranges: boolean;
      content_type: string;
    };
  };
  ytdlp_error?: string;
}

export interface DownloadRequestPayload {
  url: string;
  quality?: string;
  downloader_type?: string;
  custom_chunks?: number;
  chunk_urls?: string[];
  custom_title?: string;
  download_folder?: string;
  // Anti-blocking
  cookies_from_browser?: string;
  referer?: string;
  use_tor?: boolean;
  custom_proxy?: string;
}

export interface TorStatus {
  running: boolean;
  proxy: string;
  source?: string;
  is_tor?: boolean | null;
  exit_ip?: string | null;
  message: string;
  install_hint?: string;
}

export interface SystemSettings {
  download_folder: string;
  default_folder: string;
  disk_free_bytes: number;
  disk_total_bytes: number;
}

export interface FolderBrowseItem {
  name: string;
  path: string;
  is_dir: boolean;
}

export interface FolderBrowseResponse {
  current_path: string;
  parent_path?: string | null;
  folders: FolderBrowseItem[];
}

export interface StitchRequestPayload {
  video_ids: string[];
  title?: string;
  mode?: 'auto' | 'fast' | 'reencode';
}

export interface StitchClipInfo {
  id: string;
  title: string;
  duration: number;
  size: number;
  resolution: string;
  video_codec?: string;
  has_audio?: boolean;
  thumbnail_url?: string;
}

export interface StitchPreviewResponse {
  clips: StitchClipInfo[];
  total_clips: number;
  total_duration: number;
  total_size: number;
  compatible_for_fast: boolean;
}
