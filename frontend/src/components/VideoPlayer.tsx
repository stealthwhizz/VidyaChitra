import React from 'react';

interface VideoPlayerProps { url: string; }

export default function VideoPlayer({ url }: VideoPlayerProps) {
  return (
    <>
      {/* Video */}
      <div className="relative aspect-video bg-black">
        <video
          src={url}
          controls
          className="w-full h-full"
          preload="metadata"
        >
          Your browser does not support the video tag.
        </video>
      </div>

      {/* Footer */}
      <div
        className="px-5 py-3 flex items-center justify-between border-t"
        style={{ borderColor: 'var(--glass-border)' }}
      >
        <p className="text-sm text-slate-500 dark:text-slate-400">
          🎬 Animated diagram explainer
        </p>
        <a
          href={url}
          download
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 dark:text-slate-500
                     hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5m0 0l5-5m-5 5V4" />
          </svg>
          Download MP4
        </a>
      </div>
    </>
  );
}
