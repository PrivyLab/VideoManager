import React from 'react';
import { Film, HardDrive, Layers, Folder } from 'lucide-react';
import { formatBytes } from '../api';
import { SystemSettings } from '../types';

interface NavbarProps {
  wsConnected: boolean;
  totalVideos: number;
  totalStorage: number;
  activeCount: number;
  settings?: SystemSettings | null;
  onOpenExplainer: () => void;
  onOpenFolderPicker: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  wsConnected,
  totalVideos,
  totalStorage,
  activeCount,
  settings,
  onOpenExplainer,
  onOpenFolderPicker,
}) => {
  return (
    <header className="border-b border-dark-700 bg-dark-900/80 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center space-x-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-brand-600 to-emerald-400 flex items-center justify-center shadow-lg shadow-brand-500/20">
            <Film className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              VideoManager
              <span className="text-[10px] font-semibold bg-brand-500/20 text-brand-400 border border-brand-500/30 px-2 py-0.5 rounded-full uppercase tracking-wider">
                v1.0
              </span>
            </h1>
            <p className="text-xs text-slate-400">Universal Downloader & Chunk Stream Engine</p>
          </div>
        </div>

        {/* Stats & Actions */}
        <div className="flex items-center space-x-3">
          {/* Destination Folder button */}
          <button
            onClick={onOpenFolderPicker}
            className="hidden lg:flex items-center space-x-1.5 text-xs text-slate-300 hover:text-white bg-dark-800 hover:bg-dark-700 border border-dark-600 px-3 py-1.5 rounded-lg transition-all"
            title={settings ? `Current save folder: ${settings.download_folder}` : 'Choose download folder'}
          >
            <Folder className="h-3.5 w-3.5 text-brand-400" />
            <span className="truncate max-w-[140px] font-mono text-[11px]">
              {settings?.download_folder ? settings.download_folder.split('/').pop() : 'Destination'}
            </span>
          </button>

          <button
            onClick={onOpenExplainer}
            className="hidden md:flex items-center space-x-1.5 text-xs text-slate-300 hover:text-white bg-dark-800 hover:bg-dark-700 border border-dark-600 px-3 py-1.5 rounded-lg transition-all"
            title="Learn how Chunking & Merging works"
          >
            <Layers className="h-3.5 w-3.5 text-brand-400" />
            <span>Chunk Engine Docs</span>
          </button>

          <div className="hidden sm:flex items-center space-x-3 text-xs bg-dark-800/80 border border-dark-700 px-3 py-1.5 rounded-lg text-slate-400">
            <div className="flex items-center space-x-1">
              <HardDrive className="h-3.5 w-3.5 text-slate-400" />
              <span>{totalVideos} videos</span>
              <span className="text-slate-600">•</span>
              <span className="text-slate-200 font-medium">{formatBytes(totalStorage)}</span>
            </div>
          </div>

          {/* Active status */}
          <div className="flex items-center space-x-2 text-xs bg-dark-800 border border-dark-700 px-3 py-1.5 rounded-lg">
            <span className={`h-2 w-2 rounded-full ${wsConnected ? 'bg-brand-500 animate-pulse' : 'bg-amber-500'}`} />
            <span className="text-slate-300">
              {activeCount > 0 ? (
                <span className="text-brand-400 font-semibold">{activeCount} Downloading</span>
              ) : (
                wsConnected ? 'Live Ready' : 'Connecting...'
              )}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};
