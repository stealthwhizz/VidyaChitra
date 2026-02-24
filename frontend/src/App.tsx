import React, { useEffect, useState } from 'react';
import ChatInterface from './components/ChatInterface';
import PDFUploader from './components/PDFUploader';
import PDFViewer from './components/PDFViewer';
import StreamOutput from './components/StreamOutput';
import { useSSEStream } from './hooks/useSSEStream';

/* ── Dark-mode hook ───────────────────────────────────────────────── */
function useDarkMode(): [boolean, React.Dispatch<React.SetStateAction<boolean>>] {
  const [dark, setDark] = useState<boolean>(() => {
    const saved = localStorage.getItem('vc-theme');
    if (saved) return saved === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    const root = document.documentElement;
    if (dark) {
      root.classList.add('dark');
      localStorage.setItem('vc-theme', 'dark');
    } else {
      root.classList.remove('dark');
      localStorage.setItem('vc-theme', 'light');
    }
  }, [dark]);

  return [dark, setDark];
}

/* ── Theme toggle ─────────────────────────────────────────────────── */
function ThemeToggle({ dark, onToggle }: { dark: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
      className="w-9 h-9 rounded-full flex items-center justify-center transition-all duration-200 active:scale-90 hover:scale-110"
      style={{
        background: 'var(--glass-bg)',
        border: '1px solid var(--glass-border)',
        backdropFilter: 'blur(10px)',
        WebkitBackdropFilter: 'blur(10px)',
      }}
    >
      {dark ? (
        <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 text-amber-400">
          <path d="M12 2.25a.75.75 0 01.75.75v2.25a.75.75 0 01-1.5 0V3a.75.75 0 01.75-.75zM7.5 12a4.5 4.5 0 119 0 4.5 4.5 0 01-9 0zM18.894 6.166a.75.75 0 00-1.06-1.06l-1.591 1.59a.75.75 0 101.06 1.061l1.591-1.59zM21.75 12a.75.75 0 01-.75.75h-2.25a.75.75 0 010-1.5H21a.75.75 0 01.75.75zM17.834 18.894a.75.75 0 001.06-1.06l-1.59-1.591a.75.75 0 10-1.061 1.06l1.59 1.591zM12 18a.75.75 0 01.75.75V21a.75.75 0 01-1.5 0v-2.25A.75.75 0 0112 18zM7.758 17.303a.75.75 0 00-1.061-1.06l-1.591 1.59a.75.75 0 001.06 1.061l1.592-1.591zM6 12a.75.75 0 01-.75.75H3a.75.75 0 010-1.5h2.25A.75.75 0 016 12zM6.697 7.757a.75.75 0 001.06-1.06l-1.59-1.591a.75.75 0 00-1.061 1.06l1.591 1.591z" />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 text-slate-500">
          <path fillRule="evenodd" d="M9.528 1.718a.75.75 0 01.162.819A8.97 8.97 0 009 6a9 9 0 009 9 8.97 8.97 0 003.463-.69.75.75 0 01.981.98 10.503 10.503 0 01-9.694 6.46c-5.799 0-10.5-4.701-10.5-10.5 0-4.368 2.667-8.112 6.46-9.694a.75.75 0 01.818.162z" clipRule="evenodd" />
        </svg>
      )}
    </button>
  );
}

/* ── Decorative background blobs ──────────────────────────────────── */
function BackgroundBlobs() {
  return (
    <div className="fixed inset-0 pointer-events-none -z-10 overflow-hidden" aria-hidden>
      <div style={{
        position: 'absolute',
        top: '-15%', left: '50%', transform: 'translateX(-50%)',
        width: '800px', height: '700px',
        background: 'radial-gradient(circle, rgba(99,102,241,0.28) 0%, transparent 65%)',
        filter: 'blur(80px)',
      }} />
      <div style={{
        position: 'absolute',
        bottom: '-10%', right: '-5%',
        width: '550px', height: '550px',
        background: 'radial-gradient(circle, rgba(168,85,247,0.22) 0%, transparent 65%)',
        filter: 'blur(80px)',
      }} />
      <div style={{
        position: 'absolute',
        top: '40%', left: '-8%',
        width: '420px', height: '420px',
        background: 'radial-gradient(circle, rgba(59,130,246,0.16) 0%, transparent 65%)',
        filter: 'blur(70px)',
      }} />
    </div>
  );
}

/* ── Types ────────────────────────────────────────────────────────── */
interface UploadMeta {
  sessionId: string;
  chapterName: string;
  numPages: number;
  numDiagrams: number;
  pdfUrl: string;
  language: string;
  board: string;
  classLevel: string;
}
type Screen = 'upload' | 'results';
type MobileTab = 'pdf' | 'study';

/* ── App ──────────────────────────────────────────────────────────── */
export default function App() {
  const [dark, setDark] = useDarkMode();
  const [screen, setScreen] = useState<Screen>('upload');
  const [sessionId, setSessionId] = useState('');
  const [board, setBoard] = useState('');
  const [language, setLanguage] = useState('en-IN');
  const [meta, setMeta] = useState<UploadMeta | null>(null);
  const [mobileTab, setMobileTab] = useState<MobileTab>('study');
  const { state, connect, reset } = useSSEStream();

  const handleUploadSuccess = (uploadMeta: UploadMeta) => {
    setMeta(uploadMeta);
    setSessionId(uploadMeta.sessionId);
    setBoard(uploadMeta.board);
    setLanguage(uploadMeta.language);
    setMobileTab('study');
    const params = new URLSearchParams({
      session_id:  uploadMeta.sessionId,
      board:       uploadMeta.board,
      language:    uploadMeta.language,
      class_level: uploadMeta.classLevel,
    });
    connect(`/api/generate?${params.toString()}`);
    setScreen('results');
  };

  const handleReset = () => {
    reset();
    setScreen('upload');
    setMeta(null);
    setSessionId('');
    setBoard('');
  };

  return (
    <div className="min-h-screen">
      <BackgroundBlobs />

      {/* ── Glass Navbar ─────────────────────────────────────────── */}
      <header
        className="sticky top-0 z-30 border-b transition-colors duration-300"
        style={{
          background: 'var(--nav-bg)',
          backdropFilter: 'blur(28px) saturate(180%)',
          WebkitBackdropFilter: 'blur(28px) saturate(180%)',
          borderColor: 'var(--glass-border)',
        }}
      >
        <div className="max-w-[1400px] mx-auto px-4 h-14 flex items-center justify-between">
          <button
            onClick={handleReset}
            className="flex items-center gap-2.5 hover:opacity-75 transition-opacity"
          >
            <div
              className="w-8 h-8 rounded-xl flex items-center justify-center text-base flex-shrink-0"
              style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}
            >
              📖
            </div>
            <span className="font-bold text-slate-900 dark:text-white text-[17px] tracking-tight">
              VidyaChitra
            </span>
          </button>

          <div className="flex items-center gap-2">
            {screen === 'results' && meta?.pdfUrl && (
              /* Mobile tab switcher — only visible below lg */
              <div
                className="flex lg:hidden rounded-lg overflow-hidden"
                style={{ border: '1px solid var(--glass-border)', background: 'var(--glass-bg)' }}
              >
                {([['pdf', '📄 PDF'], ['study', '📚 Study']] as [MobileTab, string][]).map(([tab, label]) => (
                  <button
                    key={tab}
                    onClick={() => setMobileTab(tab)}
                    className={`px-3 py-1.5 text-xs font-semibold transition-all ${
                      mobileTab === tab
                        ? 'text-white'
                        : 'text-slate-500 dark:text-slate-400'
                    }`}
                    style={mobileTab === tab ? {
                      background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                    } : {}}
                  >
                    {label}
                  </button>
                ))}
              </div>
            )}
            {screen === 'results' && (
              <button onClick={handleReset} className="btn-secondary text-sm">
                ← New Chapter
              </button>
            )}
            <ThemeToggle dark={dark} onToggle={() => setDark(d => !d)} />
          </div>
        </div>
      </header>

      {/* ── Main ─────────────────────────────────────────────────── */}
      {screen === 'upload' ? (

        <main className="max-w-4xl mx-auto px-4 py-10">
          <div className="flex flex-col items-center justify-center min-h-[calc(100vh-8rem)]">

            {/* Hero */}
            <div className="mb-8 text-center animate-in">
              <div className="relative inline-block mb-5">
                <div
                  className="absolute inset-0 rounded-full blur-2xl opacity-50"
                  style={{ background: 'radial-gradient(circle, rgba(99,102,241,0.6) 0%, transparent 70%)' }}
                />
                <span className="relative text-6xl select-none animate-float inline-block">📚</span>
              </div>

              <h1 className="text-5xl font-black tracking-tight text-slate-900 dark:text-white mb-1">
                विद्याचित्र
              </h1>
              <p className="text-lg font-semibold text-indigo-600 dark:text-indigo-400 mb-4">
                VidyaChitra — AI Study Companion
              </p>

              <div className="flex flex-wrap gap-2 justify-center">
                {[
                  { icon: '🌐', label: '6 Languages' },
                  { icon: '📐', label: 'Animated Diagrams' },
                  { icon: '🎙️', label: 'Audio Narration' },
                  { icon: '❓', label: 'Exam Questions' },
                  { icon: '💬', label: 'AI Chat' },
                ].map(({ icon, label }) => (
                  <span
                    key={label}
                    className="text-xs px-3 py-1.5 rounded-full font-medium
                               text-slate-600 dark:text-slate-300"
                    style={{
                      background: 'var(--glass-bg)',
                      border: '1px solid var(--glass-border)',
                      backdropFilter: 'blur(10px)',
                      WebkitBackdropFilter: 'blur(10px)',
                    }}
                  >
                    {icon} {label}
                  </span>
                ))}
              </div>
            </div>

            <div className="w-full animate-in" style={{ animationDelay: '120ms' }}>
              <PDFUploader onUploadSuccess={handleUploadSuccess} />
            </div>
          </div>
        </main>

      ) : (

        /* ── Results — split pane ──────────────────────────────── */
        <div className="max-w-[1400px] mx-auto px-4 pt-4 pb-10">

          {/* Chapter meta strip */}
          {meta && (
            <div className="mb-4 flex items-center gap-3 text-sm text-slate-500 dark:text-slate-400 animate-in">
              <span>📄 {meta.numPages} pages</span>
              {meta.numDiagrams > 0 && <span>📐 {meta.numDiagrams} diagrams</span>}
            </div>
          )}

          {/* Desktop: side-by-side | Mobile: tabs */}
          <div className="lg:grid lg:grid-cols-[2fr_3fr] lg:gap-5 lg:items-start animate-in">

            {/* ── PDF panel ── */}
            {meta?.pdfUrl && (
              <div
                className={`lg:block lg:sticky lg:top-[4.5rem] rounded-2xl overflow-hidden
                            ${mobileTab === 'pdf' ? 'block' : 'hidden lg:block'}`}
                style={{
                  height: 'calc(100vh - 5.5rem)',
                  background: 'var(--glass-bg)',
                  backdropFilter: 'blur(24px) saturate(180%)',
                  WebkitBackdropFilter: 'blur(24px) saturate(180%)',
                  border: '1px solid var(--glass-border)',
                  boxShadow: 'var(--glass-shadow-lg)',
                }}
              >
                <PDFViewer url={meta.pdfUrl} />
              </div>
            )}

            {/* ── Study materials panel ── */}
            <div className={mobileTab === 'study' ? 'block' : 'hidden lg:block'}>
              <StreamOutput state={state} language={language} board={board} />
            </div>

          </div>
        </div>

      )}

      {screen === 'results' && sessionId && (
        <ChatInterface
          sessionId={sessionId}
          language={language}
          chapterName={meta?.chapterName ?? 'This Chapter'}
        />
      )}
    </div>
  );
}
