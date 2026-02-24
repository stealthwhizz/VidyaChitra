import React, { useState } from 'react';
import type { MCQ, QuestionsData, ShortAnswer } from '../hooks/useSSEStream';

interface MCQBlockProps { questions: QuestionsData; }

/* ── MCQ item ─────────────────────────────────────────────────────── */
function MCQItem({ mcq, index }: { mcq: MCQ; index: number }) {
  const [selected, setSelected] = useState<number | null>(null);
  const isAnswered = selected !== null;
  const isCorrect  = selected === mcq.correct_index;

  const optionStyle = (i: number): React.CSSProperties & { className: string } => {
    if (!isAnswered) {
      return {
        className: 'border text-slate-700 dark:text-slate-200 cursor-pointer hover:border-indigo-400 dark:hover:border-indigo-400',
        background: 'var(--glass-bg)',
        borderColor: 'var(--glass-border)',
      } as any;
    }
    if (i === mcq.correct_index) {
      return {
        className: 'border cursor-default text-emerald-700 dark:text-emerald-300',
        background: 'rgba(52,211,153,0.10)',
        borderColor: 'rgba(52,211,153,0.45)',
      } as any;
    }
    if (i === selected) {
      return {
        className: 'border cursor-default text-red-600 dark:text-red-300',
        background: 'rgba(239,68,68,0.08)',
        borderColor: 'rgba(239,68,68,0.40)',
      } as any;
    }
    return {
      className: 'border cursor-default text-slate-400 dark:text-slate-500',
      background: 'transparent',
      borderColor: 'var(--glass-border)',
    } as any;
  };

  return (
    <div
      className="mb-4 rounded-2xl p-5"
      style={{
        background: 'var(--glass-bg)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        border: '1px solid var(--glass-border)',
      }}
    >
      {/* Badges */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <span
          className="text-xs font-bold px-2 py-0.5 rounded-md text-indigo-600 dark:text-indigo-300"
          style={{ background: 'rgba(99,102,241,0.10)', border: '1px solid rgba(99,102,241,0.20)' }}
        >
          Q{index + 1}
        </span>
        {mcq.prev_year_hint && (
          <span
            className="text-xs font-medium px-2 py-0.5 rounded-md text-amber-600 dark:text-amber-300"
            style={{ background: 'rgba(251,191,36,0.10)', border: '1px solid rgba(251,191,36,0.25)' }}
          >
            ⭐ Likely exam question
          </span>
        )}
        {mcq.is_diagram_based && (
          <span
            className="text-xs font-medium px-2 py-0.5 rounded-md text-purple-600 dark:text-purple-300"
            style={{ background: 'rgba(168,85,247,0.10)', border: '1px solid rgba(168,85,247,0.25)' }}
          >
            📐 Diagram-based
          </span>
        )}
      </div>

      <p className="text-slate-900 dark:text-slate-100 font-medium mb-4 leading-relaxed">
        {mcq.question}
      </p>

      <div className="space-y-2">
        {mcq.options.map((option, i) => {
          const s = optionStyle(i);
          return (
            <button
              key={i}
              className={`w-full text-left px-4 py-3 rounded-xl text-sm transition-all duration-200 ${s.className}`}
              style={{ background: s.background, borderColor: s.borderColor, border: '1px solid' } as any}
              onClick={() => !isAnswered && setSelected(i)}
              disabled={isAnswered}
            >
              <span className="font-semibold mr-2">{String.fromCharCode(65 + i)}.</span>
              {option.replace(/^[A-D]\.\s*/, '')}
              {isAnswered && i === mcq.correct_index && <span className="ml-2">✓</span>}
              {isAnswered && i === selected && i !== mcq.correct_index && <span className="ml-2">✗</span>}
            </button>
          );
        })}
      </div>

      {isAnswered && (
        <div
          className={`mt-4 p-3 rounded-xl text-sm ${
            isCorrect ? 'text-emerald-700 dark:text-emerald-300' : 'text-slate-600 dark:text-slate-300'
          }`}
          style={{
            background: isCorrect ? 'rgba(52,211,153,0.08)' : 'var(--glass-bg)',
            border: `1px solid ${isCorrect ? 'rgba(52,211,153,0.30)' : 'var(--glass-border)'}`,
          }}
        >
          <span className="font-semibold">{isCorrect ? '✓ Correct! ' : '✗ Incorrect. '}</span>
          {mcq.explanation}
        </div>
      )}
    </div>
  );
}

/* ── Short answer item ────────────────────────────────────────────── */
function ShortAnswerItem({ qa, index }: { qa: ShortAnswer; index: number }) {
  const [revealed, setRevealed] = useState(false);

  return (
    <div
      className="mb-4 rounded-2xl p-5"
      style={{
        background: 'var(--glass-bg)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        border: '1px solid var(--glass-border)',
      }}
    >
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className="text-xs font-bold px-2 py-0.5 rounded-md text-indigo-600 dark:text-indigo-300"
            style={{ background: 'rgba(99,102,241,0.10)', border: '1px solid rgba(99,102,241,0.20)' }}
          >
            SA{index + 1}
          </span>
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {qa.marks} mark{qa.marks !== 1 ? 's' : ''}
          </span>
          {qa.is_diagram_based && (
            <span
              className="text-xs px-2 py-0.5 rounded-md text-purple-600 dark:text-purple-300"
              style={{ background: 'rgba(168,85,247,0.10)', border: '1px solid rgba(168,85,247,0.22)' }}
            >
              📐 Diagram
            </span>
          )}
        </div>
        <span className="text-xs text-slate-400 dark:text-slate-500 flex-shrink-0">
          ~{qa.word_count_target} words
        </span>
      </div>

      <p className="text-slate-900 dark:text-slate-100 font-medium mb-3 leading-relaxed">
        {qa.question}
      </p>

      {!revealed ? (
        <button onClick={() => setRevealed(true)} className="btn-secondary text-sm">
          Reveal Model Answer
        </button>
      ) : (
        <div
          className="rounded-xl p-4 text-sm leading-relaxed text-slate-700 dark:text-slate-300"
          style={{ background: 'var(--glass-bg)', border: '1px solid var(--glass-border)' }}
        >
          <p className="text-xs font-bold text-slate-400 dark:text-slate-500 mb-2 uppercase tracking-widest">
            Model Answer
          </p>
          {qa.model_answer}
        </div>
      )}
    </div>
  );
}

/* ── MCQBlock ─────────────────────────────────────────────────────── */
export default function MCQBlock({ questions }: MCQBlockProps) {
  const [activeTab, setActiveTab] = useState<'mcq' | 'short' | 'hot'>('mcq');

  const tabBase = 'px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200';

  return (
    <div>
      {/* Tab bar */}
      <div
        className="flex gap-2 mb-5 p-1 rounded-2xl"
        style={{ background: 'var(--glass-bg)', border: '1px solid var(--glass-border)' }}
      >
        <button
          onClick={() => setActiveTab('mcq')}
          className={`${tabBase} flex-1 ${
            activeTab === 'mcq'
              ? 'text-white shadow-md'
              : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
          }`}
          style={activeTab === 'mcq' ? {
            background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
          } : {}}
        >
          MCQs ({questions.mcqs.length})
        </button>
        <button
          onClick={() => setActiveTab('short')}
          className={`${tabBase} flex-1 ${
            activeTab === 'short'
              ? 'text-white shadow-md'
              : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'
          }`}
          style={activeTab === 'short' ? {
            background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
          } : {}}
        >
          Short Answers ({questions.short_answers.length})
        </button>
        {questions.hot_question?.question && (
          <button
            onClick={() => setActiveTab('hot')}
            className={`${tabBase} flex-1 ${
              activeTab === 'hot'
                ? 'text-white shadow-md'
                : 'text-amber-600 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-300'
            }`}
            style={activeTab === 'hot' ? {
              background: 'linear-gradient(135deg, #f59e0b 0%, #ef4444 100%)',
            } : {}}
          >
            🔥 HOT
          </button>
        )}
      </div>

      {/* MCQ tab */}
      {activeTab === 'mcq' && (
        <div>
          {questions.mcqs.map((mcq, i) => <MCQItem key={i} mcq={mcq} index={i} />)}
        </div>
      )}

      {/* Short answer tab */}
      {activeTab === 'short' && (
        <div>
          {questions.short_answers.map((qa, i) => <ShortAnswerItem key={i} qa={qa} index={i} />)}
        </div>
      )}

      {/* HOT question tab */}
      {activeTab === 'hot' && questions.hot_question && (
        <div
          className="rounded-2xl p-5"
          style={{
            background: 'rgba(251,191,36,0.07)',
            backdropFilter: 'blur(16px)',
            WebkitBackdropFilter: 'blur(16px)',
            border: '1px solid rgba(251,191,36,0.22)',
          }}
        >
          <div className="flex items-center gap-3 mb-4">
            <span className="text-2xl">🔥</span>
            <div>
              <p className="font-bold text-amber-600 dark:text-amber-400">Higher Order Thinking</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {questions.hot_question.marks} marks
              </p>
            </div>
          </div>
          <p className="text-slate-900 dark:text-slate-100 font-medium mb-4 leading-relaxed">
            {questions.hot_question.question}
          </p>
          {questions.hot_question.hint && (
            <details className="mb-4">
              <summary className="cursor-pointer text-sm text-indigo-600 dark:text-indigo-400 hover:opacity-80">
                💡 Show hint
              </summary>
              <p
                className="mt-2 text-slate-700 dark:text-slate-300 text-sm rounded-xl p-3"
                style={{ background: 'var(--glass-bg)', border: '1px solid var(--glass-border)' }}
              >
                {questions.hot_question.hint}
              </p>
            </details>
          )}
          <details>
            <summary className="cursor-pointer text-sm text-emerald-600 dark:text-emerald-400 hover:opacity-80">
              Reveal Model Answer
            </summary>
            <div
              className="mt-3 rounded-xl p-4 text-slate-700 dark:text-slate-300 text-sm leading-relaxed"
              style={{ background: 'var(--glass-bg)', border: '1px solid var(--glass-border)' }}
            >
              {questions.hot_question.model_answer}
            </div>
          </details>
        </div>
      )}
    </div>
  );
}
