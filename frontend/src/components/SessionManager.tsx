import React, { useState } from 'react';
import {
  FolderOpen, Plus, Pencil, Trash2, Check, X, ChevronDown, ChevronRight,
} from 'lucide-react';
import { Session } from '../types';
import { createSession, updateSession, deleteSession } from '../api';

const SESSION_COLORS = [
  '#6366f1', '#8b5cf6', '#ec4899', '#f59e0b',
  '#10b981', '#06b6d4', '#f97316', '#ef4444',
];

interface SessionManagerProps {
  sessions: Session[];
  activeSessionId: string | null;
  onSessionSelect: (id: string | null) => void;
  onSessionsChange: () => void;
}

export const SessionManager: React.FC<SessionManagerProps> = ({
  sessions,
  activeSessionId,
  onSessionSelect,
  onSessionsChange,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [newName, setNewName] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newColor, setNewColor] = useState(SESSION_COLORS[0]);
  const [editName, setEditName] = useState('');
  const [isBusy, setIsBusy] = useState(false);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setIsBusy(true);
    try {
      await createSession({ name: newName.trim(), description: newDesc.trim(), color: newColor });
      setNewName('');
      setNewDesc('');
      setNewColor(SESSION_COLORS[0]);
      setIsCreating(false);
      onSessionsChange();
    } catch (err) {
      console.error(err);
    } finally {
      setIsBusy(false);
    }
  };

  const handleUpdate = async (sessionId: string) => {
    if (!editName.trim()) return;
    setIsBusy(true);
    try {
      await updateSession(sessionId, { name: editName.trim() });
      setEditingId(null);
      onSessionsChange();
    } catch (err) {
      console.error(err);
    } finally {
      setIsBusy(false);
    }
  };

  const handleDelete = async (session: Session) => {
    if (!window.confirm(`Delete session "${session.name}"? Videos in it will become unassigned.`)) return;
    setIsBusy(true);
    try {
      await deleteSession(session.id);
      if (activeSessionId === session.id) onSessionSelect(null);
      onSessionsChange();
    } catch (err) {
      console.error(err);
    } finally {
      setIsBusy(false);
    }
  };

  return (
    <div className="bg-dark-800/60 border border-dark-700 rounded-2xl overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-dark-700/40 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <FolderOpen className="h-4.5 w-4.5 text-indigo-400" style={{ height: 18, width: 18 }} />
          <span className="text-sm font-semibold text-white">Sessions</span>
          <span className="text-[11px] bg-dark-700 text-slate-400 px-2 py-0.5 rounded-full font-mono">
            {sessions.length}
          </span>
          {activeSessionId && (
            <span className="text-[11px] bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-2 py-0.5 rounded-full">
              {sessions.find(s => s.id === activeSessionId)?.name || 'Session active'}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {activeSessionId && (
            <button
              onClick={(e) => { e.stopPropagation(); onSessionSelect(null); }}
              className="text-xs text-slate-400 hover:text-white px-2 py-0.5 rounded-lg hover:bg-dark-700 transition-colors"
            >
              Show All
            </button>
          )}
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-slate-400" />
          ) : (
            <ChevronRight className="h-4 w-4 text-slate-400" />
          )}
        </div>
      </button>

      {isExpanded && (
        <div className="px-3 pb-3 space-y-1.5">
          {/* All Videos pill */}
          <button
            onClick={() => onSessionSelect(null)}
            className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-all ${
              activeSessionId === null
                ? 'bg-indigo-500/20 text-indigo-200 border border-indigo-500/40'
                : 'text-slate-300 hover:bg-dark-700/60 hover:text-white'
            }`}
          >
            <div className="h-3 w-3 rounded-full bg-slate-500 flex-shrink-0" />
            <span className="flex-1 text-left font-medium text-xs">All Videos</span>
          </button>

          {/* Session list */}
          {sessions.map((session) => (
            <div key={session.id} className="group relative">
              {editingId === session.id ? (
                <div className="flex items-center gap-2 px-2 py-1.5">
                  <input
                    autoFocus
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleUpdate(session.id);
                      if (e.key === 'Escape') setEditingId(null);
                    }}
                    className="flex-1 bg-dark-700 border border-brand-500/50 text-white text-xs rounded-lg px-2.5 py-1.5 outline-none"
                  />
                  <button onClick={() => handleUpdate(session.id)} disabled={isBusy} className="text-emerald-400 hover:text-emerald-300 p-1">
                    <Check className="h-3.5 w-3.5" />
                  </button>
                  <button onClick={() => setEditingId(null)} className="text-slate-500 hover:text-slate-300 p-1">
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => onSessionSelect(session.id === activeSessionId ? null : session.id)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-all ${
                    activeSessionId === session.id
                      ? 'bg-dark-700 text-white border border-dark-600'
                      : 'text-slate-300 hover:bg-dark-700/60 hover:text-white'
                  }`}
                >
                  <div
                    className="h-3 w-3 rounded-full flex-shrink-0"
                    style={{ backgroundColor: session.color || '#6366f1' }}
                  />
                  <span className="flex-1 text-left font-medium text-xs truncate">{session.name}</span>
                  <span className="text-[10px] text-slate-500 font-mono flex-shrink-0">
                    {session.video_count || 0} videos
                  </span>
                  <div className="hidden group-hover:flex items-center gap-1 ml-1">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingId(session.id);
                        setEditName(session.name);
                      }}
                      className="text-slate-400 hover:text-white p-0.5 rounded"
                    >
                      <Pencil className="h-3 w-3" />
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDelete(session); }}
                      className="text-slate-400 hover:text-rose-400 p-0.5 rounded"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                </button>
              )}
            </div>
          ))}

          {/* Create new session */}
          {isCreating ? (
            <div className="bg-dark-700/60 border border-dark-600 rounded-xl p-3 space-y-2.5 mt-2">
              <input
                autoFocus
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleCreate(); if (e.key === 'Escape') setIsCreating(false); }}
                placeholder="Session name (e.g. Sports, Cars)"
                className="w-full bg-dark-800 border border-dark-600 text-white text-xs rounded-lg px-3 py-2 outline-none focus:border-indigo-500 placeholder-slate-600"
              />
              <input
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                placeholder="Description (optional)"
                className="w-full bg-dark-800 border border-dark-600 text-white text-xs rounded-lg px-3 py-2 outline-none focus:border-indigo-500 placeholder-slate-600"
              />
              {/* Color picker */}
              <div className="flex items-center gap-1.5">
                <span className="text-[10px] text-slate-500">Color:</span>
                {SESSION_COLORS.map((c) => (
                  <button
                    key={c}
                    onClick={() => setNewColor(c)}
                    className={`h-5 w-5 rounded-full transition-transform ${newColor === c ? 'ring-2 ring-white scale-110' : 'hover:scale-105'}`}
                    style={{ backgroundColor: c }}
                  />
                ))}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleCreate}
                  disabled={!newName.trim() || isBusy}
                  className="flex-1 py-1.5 bg-indigo-500 hover:bg-indigo-600 disabled:opacity-40 text-white text-xs font-medium rounded-lg transition-colors"
                >
                  Create Session
                </button>
                <button
                  onClick={() => { setIsCreating(false); setNewName(''); setNewDesc(''); }}
                  className="px-3 py-1.5 text-slate-400 hover:text-white text-xs rounded-lg hover:bg-dark-700 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setIsCreating(true)}
              className="w-full flex items-center gap-2 px-3 py-2 text-xs text-slate-400 hover:text-indigo-300 hover:bg-indigo-500/10 rounded-xl transition-all border border-dashed border-dark-600 hover:border-indigo-500/40 mt-1"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>New Session</span>
            </button>
          )}
        </div>
      )}
    </div>
  );
};
