import React, { useEffect, useRef, useState } from 'react';
import type { SSEStreamState } from '../hooks/useSSEStream';
import AudioPlayer from './AudioPlayer';
import MCQBlock from './MCQBlock';
import VideoPlayer from './VideoPlayer';

interface StreamOutputProps {
  state: SSEStreamState;
  language: string;
  board: string;
}

/* ── Animated typing text ─────────────────────────────────────────── */
function TypingText({ text }: { text: string }) {
  const [displayed, setDisplayed] = useState('');
  const indexRef = useRef(0);

  useEffect(() => {
    if (!text) return;
    indexRef.current = 0;
    setDisplayed('');
    const interval = setInterval(() => {
      if (indexRef.current < text.length) {
        setDisplayed(prev => prev + text[indexRef.current]);
        indexRef.current++;
      } else {
        clearInterval(interval);
      }
    }, 8);
    return () => clearInterval(interval);
  }, [text]);

  return (
    <p className="text-slate-700 dark:text-slate-300 leading-relaxed text-sm whitespace-pre-wrap">
      {displayed}
      {displayed.length < text.length && <span className="typing-cursor" />}
    </p>
  );
}

/* ── Progress bar ─────────────────────────────────────────────────── */
interface Step { key: string; label: string; icon: string; done: boolean; }

function ProgressBar({ steps }: { steps: Step[] }) {
  return (
    <div className="glass-card mb-6">
      <div className="grid grid-cols-4 gap-3">
        {steps.map(step => (
          <div key={step.key} className="flex flex-col items-center gap-2">
            <div
              className={`w-11 h-11 rounded-full flex items-center justify-center text-lg
                          transition-all duration-500 ${
                step.done
                  ? 'text-emerald-600 dark:text-emerald-400'
                  : 'shimmer'
              }`}
              style={step.done ? {
                background: 'rgba(52,211,153,0.12)',
                border: '2px solid rgba(52,211,153,0.50)',
                boxShadow: '0 0 14px rgba(52,211,153,0.25)',
              } : {
                border: '2px solid var(--glass-border)',
                borderRadius: '9999px',
              }}
            >
              {step.done ? '✓' : step.icon}
            </div>
            <span className={`text-xs text-center font-medium transition-colors ${
              step.done
                ? 'text-emerald-600 dark:text-emerald-400'
                : 'text-slate-400 dark:text-slate-500'
            }`}>
              {step.label}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Fade-in section wrapper ──────────────────────────────────────── */
function Section({ show, children, delay = 0 }: {
  show: boolean; children: React.ReactNode; delay?: number;
}) {
  return (
    <div
      className="transition-all duration-700"
      style={{
        opacity:          show ? 1 : 0,
        transform:        show ? 'translateY(0)' : 'translateY(14px)',
        transitionDelay:  `${delay}ms`,
        display:          show ? 'block' : 'none',
      }}
    >
      {children}
    </div>
  );
}

/* ── Main component ───────────────────────────────────────────────── */
export default function StreamOutput({ state, language, board }: StreamOutputProps) {
  const { summary, chapterName, questions, audioUrl, videoUrl, examTip, errors, isLoading } = state;

  const steps: Step[] = [
    { key: 'summary',   label: 'Summary',   icon: '📝', done: !!summary },
    { key: 'questions', label: 'Questions', icon: '❓', done: !!questions },
    { key: 'audio',     label: 'Audio',     icon: '🎙️', done: !!audioUrl },
    { key: 'video',     label: 'Video',     icon: '🎬', done: !!videoUrl },
  ];

  return (
    <div className="space-y-5 pb-40">

      {/* Chapter header */}
      {chapterName && (
        <div className="glass-card animate-in">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-1 uppercase tracking-widest font-semibold">
                {board}
              </p>
              <h2 className="text-xl font-bold text-slate-900 dark:text-slate-100">{chapterName}</h2>
            </div>
            {isLoading && (
              <div className="flex-shrink-0 flex items-center gap-2 text-sm text-indigo-600 dark:text-indigo-400">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                </svg>
                Generating…
              </div>
            )}
          </div>
        </div>
      )}

      {/* Progress */}
      <ProgressBar steps={steps} />

      {/* Errors */}
      {errors.map((err, i) => (
        <div
          key={i}
          className="border rounded-xl px-4 py-3 text-sm text-red-600 dark:text-red-300"
          style={{
            background: 'rgba(239,68,68,0.07)',
            borderColor: 'rgba(239,68,68,0.22)',
          }}
        >
          <span className="font-semibold">⚠ {err.branch} generation failed: </span>
          {err.msg}
        </div>
      ))}

      {/* Summary */}
      <Section show={!!summary}>
        <div className="glass-card">
          <h3 className="section-title"><span>📝</span> Chapter Summary</h3>
          <TypingText text={summary} />
        </div>
      </Section>

      {/* Video */}
      <Section show={!!videoUrl} delay={100}>
        <div className="glass-card p-0 overflow-hidden">
          <div className="px-5 pt-4 pb-3">
            <h3 className="section-title mb-0"><span>🎬</span> Animated Diagram Explainer</h3>
          </div>
          <VideoPlayer url={videoUrl!} />
        </div>
      </Section>

      {/* Audio */}
      <Section show={!!audioUrl} delay={150}>
        <AudioPlayer url={audioUrl!} languageCode={language} />
      </Section>

      {/* Exam tip */}
      <Section show={!!examTip} delay={200}>
        <div
          className="border rounded-2xl p-5"
          style={{
            background: 'rgba(251,191,36,0.07)',
            borderColor: 'rgba(251,191,36,0.25)',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
          }}
        >
          <p className="font-bold mb-2 flex items-center gap-2 text-amber-600 dark:text-amber-400">
            <span>💡</span> Exam Tip for {board}
          </p>
          <p className="text-amber-700 dark:text-amber-200 text-sm leading-relaxed">{examTip}</p>
        </div>
      </Section>

      {/* Questions */}
      <Section show={!!questions} delay={250}>
        <div className="glass-card">
          <h3 className="section-title mb-4">
            <span>❓</span> Practice Questions — {board} Pattern
          </h3>
          {questions && <MCQBlock questions={questions} />}
        </div>
      </Section>
    </div>
  );
}
