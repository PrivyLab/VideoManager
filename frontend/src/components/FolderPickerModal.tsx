import React, { useState, useEffect } from 'react';
import { X, Folder, ChevronRight, ArrowUp, HardDrive, Check, Loader2, RefreshCw } from 'lucide-react';
import { browseFolders, updateSystemSettings, formatBytes } from '../api';
import { FolderBrowseResponse, SystemSettings } from '../types';

interface FolderPickerModalProps {
  currentFolder: string;
  settings?: SystemSettings | null;
  onClose: () => void;
  onFolderSelected: (folderPath: string) => void;
}

export const FolderPickerModal: React.FC<FolderPickerModalProps> = ({
  currentFolder,
  settings,
  onClose,
  onFolderSelected,
}) => {
  const [loading, setLoading] = useState(false);
  const [browseData, setBrowseData] = useState<FolderBrowseResponse | null>(null);
  const [selectedPath, setSelectedPath] = useState(currentFolder);
  const [manualInput, setManualInput] = useState(currentFolder);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDirectory = async (path?: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await browseFolders(path);
      setBrowseData(data);
      setSelectedPath(data.current_path);
      setManualInput(data.current_path);
    } catch (err: any) {
      setError(err.message || 'Failed to list folders');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDirectory(currentFolder);
  }, [currentFolder]);

  const handleSelectFolder = async () => {
    const pathToSave = manualInput.trim() || selectedPath;
    setSaving(true);
    setError(null);
    try {
      await updateSystemSettings(pathToSave);
      onFolderSelected(pathToSave);
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to update folder destination');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="bg-dark-900 border border-dark-700 rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="p-4 sm:p-5 border-b border-dark-700 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-brand-500/10 border border-brand-500/20 rounded-xl text-brand-400">
              <Folder className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Select Download Directory</h3>
              <p className="text-xs text-slate-400">Choose where completed video files will be stored</p>
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
        <div className="p-4 sm:p-6 space-y-4 flex-1 overflow-y-auto">
          {/* Path input */}
          <div>
            <label className="text-xs font-medium text-slate-300 block mb-1.5">
              Target Folder Path:
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={manualInput}
                onChange={(e) => setManualInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && loadDirectory(manualInput)}
                placeholder="/path/to/downloads"
                className="flex-1 bg-dark-800 border border-dark-600 focus:border-brand-500 text-slate-200 text-xs rounded-xl px-3 py-2.5 font-mono outline-none"
              />
              <button
                type="button"
                onClick={() => loadDirectory(manualInput)}
                className="bg-dark-700 hover:bg-dark-600 text-slate-200 px-3 py-2 rounded-xl text-xs flex items-center gap-1 font-medium transition-colors"
                title="Navigate to path"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
                Go
              </button>
            </div>
          </div>

          {/* Navigation Bar */}
          <div className="flex items-center justify-between bg-dark-800/80 border border-dark-700 px-3 py-2 rounded-xl text-xs">
            <div className="flex items-center space-x-2 truncate">
              {browseData?.parent_path && (
                <button
                  onClick={() => loadDirectory(browseData.parent_path!)}
                  className="p-1 hover:bg-dark-700 text-brand-400 rounded-lg flex items-center gap-1 transition-colors"
                  title="Go to parent directory"
                >
                  <ArrowUp className="h-3.5 w-3.5" />
                  <span className="text-[11px]">Up</span>
                </button>
              )}
              <span className="text-slate-400 font-mono text-[11px] truncate">
                {browseData?.current_path || selectedPath}
              </span>
            </div>

            {settings?.disk_free_bytes && (
              <div className="flex items-center space-x-1 text-slate-400 text-[11px] shrink-0 font-mono">
                <HardDrive className="h-3 w-3 text-brand-400" />
                <span>{formatBytes(settings.disk_free_bytes)} free</span>
              </div>
            )}
          </div>

          {/* Folder Listing */}
          <div className="bg-dark-950/60 border border-dark-700 rounded-xl p-2 h-64 overflow-y-auto space-y-1">
            {loading ? (
              <div className="h-full flex items-center justify-center text-slate-500 text-xs gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-brand-400" />
                <span>Loading folders...</span>
              </div>
            ) : browseData?.folders.length === 0 ? (
              <div className="h-full flex items-center justify-center text-slate-500 text-xs">
                No accessible subfolders in this directory
              </div>
            ) : (
              browseData?.folders.map((folder) => (
                <button
                  key={folder.path}
                  onClick={() => loadDirectory(folder.path)}
                  className="w-full text-left px-3 py-2 rounded-lg text-xs hover:bg-dark-800/90 text-slate-300 hover:text-white flex items-center justify-between group transition-colors"
                >
                  <div className="flex items-center space-x-2.5 truncate">
                    <Folder className="h-4 w-4 text-brand-400/80 group-hover:text-brand-400 shrink-0" />
                    <span className="truncate">{folder.name}</span>
                  </div>
                  <ChevronRight className="h-3.5 w-3.5 text-slate-600 group-hover:text-slate-400 shrink-0" />
                </button>
              ))
            )}
          </div>

          {error && (
            <div className="text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 px-3 py-2 rounded-xl">
              {error}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-dark-700 bg-dark-800/60 flex items-center justify-between">
          <span className="text-xs text-slate-400 truncate max-w-[280px] sm:max-w-md font-mono">
            Selected: <span className="text-slate-200">{manualInput || selectedPath}</span>
          </span>
          <div className="flex items-center space-x-2 shrink-0">
            <button
              onClick={onClose}
              className="px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200 bg-dark-700 rounded-xl"
            >
              Cancel
            </button>
            <button
              onClick={handleSelectFolder}
              disabled={saving}
              className="px-4 py-1.5 text-xs font-medium text-white bg-brand-600 hover:bg-brand-500 disabled:opacity-50 rounded-xl flex items-center gap-1.5 transition-all shadow-md shadow-brand-600/30"
            >
              <Check className="h-3.5 w-3.5" />
              <span>{saving ? 'Saving...' : 'Set as Download Folder'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

