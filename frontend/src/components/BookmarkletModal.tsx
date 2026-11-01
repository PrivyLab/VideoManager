import React, { useState } from 'react';
import {
  X,
  Bookmark,
  Copy,
  Check,
  Globe,
  Sparkles,
  Shield
} from 'lucide-react';

interface BookmarkletModalProps {
  onClose: () => void;
}

export const BookmarkletModal: React.FC<BookmarkletModalProps> = ({ onClose }) => {
  const [copied, setCopied] = useState(false);
  const [serverUrl, setServerUrl] = useState(() => {
    if (typeof window !== 'undefined') {
      return window.location.origin;
    }
    return 'http://localhost:5173';
  });
  const [activeBrowser, setActiveBrowser] = useState<'chrome' | 'safari' | 'firefox' | 'mobile'>('chrome');
  const [testStatus, setTestStatus] = useState<string | null>(null);

  // Minified bookmarklet script that will be executed in the user's browser
  const bookmarkletCode = `javascript:(function(){var u=window.location.href,t=document.title||'',s='${serverUrl}';var el=document.getElementById('vm-toast');if(!el){el=document.createElement('div');el.id='vm-toast';el.style.cssText='position:fixed;top:20px;right:20px;z-index:2147483647;background:#0f172a;color:#f8fafc;padding:12px 18px;border-radius:12px;border:1px solid #3b82f6;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;font-size:13px;box-shadow:0 10px 25px -5px rgba(0,0,0,0.5);display:flex;align-items:center;gap:10px;transition:all 0.3s ease;';document.body.appendChild(el);}el.innerHTML='⚡ <span>Sending to <b>VideoManager</b>...</span>';fetch(s+'/api/downloads',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:u,custom_title:t})}).then(function(r){if(!r.ok)throw new Error(r.status);return r.json();}).then(function(){el.style.borderColor='#10b981';el.style.background='#064e3b';el.innerHTML='✅ <span><b>Download Started!</b> Queued in VideoManager.</span> <a href=\"'+s+'\" target=\"_blank\" style=\"color:#6ee7b7;margin-left:8px;text-decoration:underline;\">Open</a>';setTimeout(function(){el.style.opacity='0';setTimeout(function(){el.remove();},400);},4000);}).catch(function(){el.style.borderColor='#f59e0b';el.innerHTML='🚀 <span>Opening <b>VideoManager</b>...</span>';setTimeout(function(){el.remove();window.open(s+'/?url='+encodeURIComponent(u)+'&autodownload=1&title='+encodeURIComponent(t),'_blank');},600);});})();`;

  const handleCopy = () => {
    navigator.clipboard.writeText(bookmarkletCode);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const runTest = () => {
    setTestStatus('Testing bookmarklet connection...');
    fetch(`${serverUrl}/api/videos`)
      .then((r) => {
        if (r.ok) {
          setTestStatus('✅ Connection successful! VideoManager is listening.');
        } else {
          setTestStatus(`⚠️ Server responded with status ${r.status}`);
        }
      })
      .catch((err) => {
        setTestStatus(`❌ Could not connect to ${serverUrl}: ${err.message}`);
      });
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-dark-900 border border-dark-700 w-full max-w-2xl rounded-2xl shadow-2xl flex flex-col max-h-[92vh] overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-dark-800 bg-dark-800/40">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-brand-600 to-emerald-500 flex items-center justify-center text-white shadow-lg shadow-brand-500/20">
              <Bookmark className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white flex items-center gap-2">
                Browser Bookmarklet
                <span className="text-[10px] bg-brand-500/20 text-brand-400 border border-brand-500/30 px-2 py-0.5 rounded-full font-mono uppercase">
                  1-Click Download
                </span>
              </h3>
              <p className="text-xs text-slate-400">
                Send any video directly to VideoManager without copy-pasting URLs.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white p-2 rounded-lg hover:bg-dark-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          {/* STEP 1: The Draggable Bookmarklet Button */}
          <div className="bg-gradient-to-b from-dark-800/90 to-dark-800/40 border border-dark-700 rounded-2xl p-6 text-center space-y-4 shadow-inner">
            <span className="text-[11px] font-semibold text-brand-400 uppercase tracking-widest block">
              Step 1: Install To Bookmarks Bar
            </span>

            <div className="flex flex-col items-center justify-center gap-3">
              <p className="text-xs text-slate-300 max-w-md">
                <strong>Drag and drop</strong> this button onto your Chrome, Safari, Firefox, or Edge bookmarks bar:
              </p>

              <a
                href={bookmarkletCode}
                onClick={(e) => {
                  e.preventDefault();
                  alert("👉 Drag this button to your browser's Bookmarks/Favorites bar! Clicking it directly inside this setup window does not install it.");
                }}
                className="px-6 py-3.5 bg-gradient-to-r from-brand-600 via-emerald-600 to-brand-500 hover:from-brand-500 hover:to-emerald-400 text-white font-bold text-sm rounded-xl shadow-xl shadow-brand-500/25 flex items-center gap-2.5 transition-all transform hover:scale-105 cursor-grab active:cursor-grabbing border border-white/20 select-none"
                title="Drag me to your Bookmarks Bar!"
              >
                <Sparkles className="h-4 w-4" />
                <span>🚀 Send to VideoManager</span>
              </a>

              <span className="text-[11px] text-slate-400">
                (Click &amp; drag the button up to your browser toolbar)
              </span>
            </div>

            {/* Manual Copy Option */}
            <div className="pt-3 border-t border-dark-700/60 flex items-center justify-center gap-3">
              <span className="text-xs text-slate-400">Or copy the code manually:</span>
              <button
                type="button"
                onClick={handleCopy}
                className="px-3 py-1.5 bg-dark-700 hover:bg-dark-600 text-slate-200 text-xs rounded-lg font-medium flex items-center gap-1.5 transition-all border border-dark-600"
              >
                {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                <span>{copied ? 'Copied to Clipboard!' : 'Copy Code'}</span>
              </button>
            </div>
          </div>

          {/* STEP 2: How It Works */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-brand-400" />
              How It Works
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="p-3 bg-dark-800/60 border border-dark-700 rounded-xl space-y-1">
                <span className="text-xs font-bold text-white flex items-center gap-1.5">
                  <span className="h-5 w-5 rounded-full bg-brand-500/20 text-brand-400 flex items-center justify-center text-[10px]">1</span>
                  Browse Any Video
                </span>
                <p className="text-[11px] text-slate-400">
                  Open YouTube, Vimeo, Reddit, Twitter, or any streaming webpage in your browser.
                </p>
              </div>

              <div className="p-3 bg-dark-800/60 border border-dark-700 rounded-xl space-y-1">
                <span className="text-xs font-bold text-white flex items-center gap-1.5">
                  <span className="h-5 w-5 rounded-full bg-brand-500/20 text-brand-400 flex items-center justify-center text-[10px]">2</span>
                  Click Bookmarklet
                </span>
                <p className="text-[11px] text-slate-400">
                  Click <strong>"Send to VideoManager"</strong> on your bookmarks bar.
                </p>
              </div>

              <div className="p-3 bg-dark-800/60 border border-dark-700 rounded-xl space-y-1">
                <span className="text-xs font-bold text-white flex items-center gap-1.5">
                  <span className="h-5 w-5 rounded-full bg-brand-500/20 text-brand-400 flex items-center justify-center text-[10px]">3</span>
                  Instant Download
                </span>
                <p className="text-[11px] text-slate-400">
                  A notification confirms the download started in the background without leaving your tab!
                </p>
              </div>
            </div>
          </div>

          {/* STEP 3: Server Host Configuration */}
          <div className="bg-dark-800/40 border border-dark-700 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                <Globe className="h-3.5 w-3.5 text-brand-400" />
                Target VideoManager Address
              </label>
              <button
                type="button"
                onClick={runTest}
                className="text-[11px] text-brand-400 hover:text-brand-300 underline font-medium"
              >
                Test Connection
              </button>
            </div>
            <input
              type="text"
              value={serverUrl}
              onChange={(e) => setServerUrl(e.target.value)}
              placeholder="http://localhost:5173 or http://localhost:8000"
              className="w-full bg-dark-900 border border-dark-600 text-slate-200 text-xs rounded-lg px-3 py-2 font-mono outline-none focus:border-brand-500"
            />
            {testStatus && (
              <p className="text-xs font-mono text-slate-300 bg-dark-900/80 px-2.5 py-1.5 rounded border border-dark-700">
                {testStatus}
              </p>
            )}
            <p className="text-[10px] text-slate-500">
              Change this if you run VideoManager on a home server, Docker port, or local network IP (e.g. <code>http://192.168.1.50:8000</code>).
            </p>
          </div>

          {/* Browser Specific Guides */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Browser Installation Guide
              </span>
              <div className="flex gap-1">
                {(['chrome', 'safari', 'firefox', 'mobile'] as const).map((b) => (
                  <button
                    key={b}
                    onClick={() => setActiveBrowser(b)}
                    className={`px-2.5 py-1 rounded text-[11px] font-medium capitalize transition-all ${
                      activeBrowser === b
                        ? 'bg-brand-500/20 text-brand-400 border border-brand-500/30'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {b === 'mobile' ? 'iOS / Android' : b}
                  </button>
                ))}
              </div>
            </div>

            <div className="p-4 bg-dark-900 border border-dark-700/80 rounded-xl text-xs text-slate-300 space-y-2">
              {activeBrowser === 'chrome' && (
                <ol className="list-decimal list-inside space-y-1.5 text-slate-300 leading-relaxed">
                  <li>Show the Bookmarks Bar by pressing <kbd className="px-1.5 py-0.5 bg-dark-800 rounded font-mono text-slate-200 border border-dark-700">Cmd + Shift + B</kbd> (Mac) or <kbd className="px-1.5 py-0.5 bg-dark-800 rounded font-mono text-slate-200 border border-dark-700">Ctrl + Shift + B</kbd> (Windows).</li>
                  <li>Click and drag the green <strong>"🚀 Send to VideoManager"</strong> button above into the bookmarks bar.</li>
                  <li>Done! You can now click it on any video webpage.</li>
                </ol>
              )}

              {activeBrowser === 'safari' && (
                <ol className="list-decimal list-inside space-y-1.5 text-slate-300 leading-relaxed">
                  <li>In Safari, press <kbd className="px-1.5 py-0.5 bg-dark-800 rounded font-mono text-slate-200 border border-dark-700">Cmd + Shift + B</kbd> to ensure the <em>Favorites Bar</em> is visible.</li>
                  <li>Drag the green <strong>"🚀 Send to VideoManager"</strong> button up into the Favorites bar.</li>
                  <li>Whenever you're watching a video, 1-click the bookmarklet to download it instantly.</li>
                </ol>
              )}

              {activeBrowser === 'firefox' && (
                <ol className="list-decimal list-inside space-y-1.5 text-slate-300 leading-relaxed">
                  <li>Press <kbd className="px-1.5 py-0.5 bg-dark-800 rounded font-mono text-slate-200 border border-dark-700">Ctrl + Shift + B</kbd> (or <kbd className="px-1.5 py-0.5 bg-dark-800 rounded font-mono text-slate-200 border border-dark-700">Cmd + Shift + B</kbd>) to show the Bookmarks Toolbar.</li>
                  <li>Drag the green button directly onto the Bookmarks Toolbar.</li>
                  <li>Click on any video page to trigger seamless download.</li>
                </ol>
              )}

              {activeBrowser === 'mobile' && (
                <ol className="list-decimal list-inside space-y-1.5 text-slate-300 leading-relaxed">
                  <li>Click <strong>"Copy Code"</strong> above.</li>
                  <li>Bookmark any page in your mobile browser and name it <em>"Send to VideoManager"</em>.</li>
                  <li>Edit the bookmark, delete the URL, and paste the copied code into the URL field.</li>
                </ol>
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-dark-800 bg-dark-800/40 flex items-center justify-between">
          <span className="text-[11px] text-slate-400 flex items-center gap-1.5">
            <Shield className="h-3.5 w-3.5 text-emerald-400" />
            100% private &amp; local — no third-party tracking.
          </span>
          <button
            onClick={onClose}
            className="px-5 py-2 bg-dark-700 hover:bg-dark-600 text-white rounded-xl text-xs font-medium transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
};
