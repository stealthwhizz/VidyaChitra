import React, { useCallback, useRef, useState } from 'react';

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

interface PDFUploaderProps {
  onUploadSuccess: (meta: UploadMeta) => void;
}

export default function PDFUploader({ onUploadSuccess }: PDFUploaderProps) {
  const [file,        setFile]        = useState<File | null>(null);
  const [isDragging,  setIsDragging]  = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error,       setError]       = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFile = (f: File) => {
    if (!f.name.toLowerCase().endsWith('.pdf')) { setError('Please upload a PDF file.'); return; }
    if (f.size > 50 * 1024 * 1024)             { setError('File size must be under 50 MB.'); return; }
    setError('');
    setFile(f);
  };

  const onDragOver  = useCallback((e: React.DragEvent) => { e.preventDefault(); setIsDragging(true); }, []);
  const onDragLeave = useCallback(() => setIsDragging(false), []);
  const onDrop      = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) handleFile(f);
  }, []);

  const handleSubmit = async () => {
    if (!file) { setError('Please select a PDF file first.'); return; }
    setIsUploading(true);
    setError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const resp = await fetch('/api/upload', { method: 'POST', body: formData });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: 'Upload failed.' }));
        throw new Error(err.detail || 'Upload failed.');
      }
      const data = await resp.json();
      onUploadSuccess({
        sessionId:   data.session_id,
        chapterName: data.chapter_name,
        numPages:    data.num_pages,
        numDiagrams: data.num_diagrams,
        pdfUrl:      data.pdf_url ?? '',
        language:    data.language ?? 'en-IN',
        board:       data.board ?? '',
        classLevel:  data.class_level ?? '10',
      });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'An unexpected error occurred.');
    } finally {
      setIsUploading(false);
    }
  };

  /* Drop-zone state colours */
  const dzBorder = isDragging
    ? 'border-indigo-400 dark:border-indigo-400'
    : file
    ? 'border-emerald-400 dark:border-emerald-400'
    : 'border-slate-300/50 dark:border-white/12';

  const dzGlow = isDragging
    ? '0 0 0 4px rgba(99,102,241,0.15), var(--glass-shadow)'
    : file
    ? '0 0 0 4px rgba(52,211,153,0.12), var(--glass-shadow)'
    : 'var(--glass-shadow)';

  return (
    <div
      className="w-full max-w-xl mx-auto rounded-2xl overflow-hidden"
      style={{
        background: 'var(--glass-bg)',
        backdropFilter: 'blur(28px) saturate(180%)',
        WebkitBackdropFilter: 'blur(28px) saturate(180%)',
        border: '1px solid var(--glass-border)',
        boxShadow: 'var(--glass-shadow-lg)',
      }}
    >
      {/* Top highlight stripe */}
      <div
        className="h-px w-full"
        style={{ background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.5), transparent)' }}
      />

      <div className="p-6 space-y-5">

        {/* Drop zone */}
        <div
          onClick={() => fileInputRef.current?.click()}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          className={`border-2 border-dashed rounded-xl py-10 px-6 text-center
                      cursor-pointer transition-all duration-200 ${dzBorder}`}
          style={{
            background: isDragging
              ? 'rgba(99,102,241,0.07)'
              : file
              ? 'rgba(52,211,153,0.06)'
              : 'rgba(255,255,255,0.04)',
            boxShadow: dzGlow,
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,application/pdf"
            className="hidden"
            onChange={e => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
          />

          {file ? (
            <div className="space-y-1.5">
              <div className="text-3xl">📄</div>
              <p className="font-semibold text-emerald-600 dark:text-emerald-400 text-sm truncate px-4">
                {file.name}
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {(file.size / 1024 / 1024).toFixed(2)} MB · tap to change
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="text-5xl select-none">📄</div>
              <p className="font-semibold text-slate-800 dark:text-slate-200 text-sm">
                Drop your NCERT or State Board PDF here
              </p>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Language, board & class are auto-detected · max 50 MB
              </p>
            </div>
          )}
        </div>

        {/* Error */}
        {error && (
          <div
            className="rounded-xl px-4 py-2.5 text-sm text-red-600 dark:text-red-300 border"
            style={{ background: 'rgba(239,68,68,0.08)', borderColor: 'rgba(239,68,68,0.25)' }}
          >
            ⚠ {error}
          </div>
        )}

        {/* CTA button */}
        <button
          onClick={handleSubmit}
          disabled={!file || isUploading}
          className="btn-primary w-full text-[15px]"
        >
          {isUploading ? (
            <span className="flex items-center justify-center gap-3">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24" fill="none">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
              </svg>
              Analysing with AI…
            </span>
          ) : (
            '✨  Generate Study Materials'
          )}
        </button>

        <p className="text-center text-[11px] text-slate-400 dark:text-slate-500">
          Powered by Gemini 2.5 Flash · All NCERT & State Board textbooks
        </p>
      </div>
    </div>
  );
}
