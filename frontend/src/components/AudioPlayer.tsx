import React, { useEffect, useRef, useState } from 'react';

interface AudioPlayerProps {
  url: string;
  languageCode: string;
}

const LANGUAGE_LABELS: Record<string, string> = {
  'kn-IN': 'ಕನ್ನಡ',
  'hi-IN': 'हिन्दी',
  'ta-IN': 'தமிழ்',
  'te-IN': 'తెలుగు',
  'mr-IN': 'मराठी',
  'en-IN': 'English',
};

export default function AudioPlayer({ url, languageCode }: AudioPlayerProps) {
  const audioRef     = useRef<HTMLAudioElement>(null);
  const [isPlaying,  setIsPlaying]  = useState(false);
  const [progress,   setProgress]   = useState(0);
  const [duration,   setDuration]   = useState(0);
  const [currentTime, setCurrentTime] = useState(0);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const onTimeUpdate     = () => {
      setCurrentTime(audio.currentTime);
      if (audio.duration > 0) setProgress((audio.currentTime / audio.duration) * 100);
    };
    const onDurationChange = () => setDuration(audio.duration);
    const onEnded          = () => setIsPlaying(false);

    audio.addEventListener('timeupdate',     onTimeUpdate);
    audio.addEventListener('durationchange', onDurationChange);
    audio.addEventListener('ended',          onEnded);
    return () => {
      audio.removeEventListener('timeupdate',     onTimeUpdate);
      audio.removeEventListener('durationchange', onDurationChange);
      audio.removeEventListener('ended',          onEnded);
    };
  }, []);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;
    isPlaying ? audio.pause() : audio.play();
    setIsPlaying(!isPlaying);
  };

  const seek = (e: React.MouseEvent<HTMLDivElement>) => {
    const audio = audioRef.current;
    if (!audio || !audio.duration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    audio.currentTime = ((e.clientX - rect.left) / rect.width) * audio.duration;
  };

  const formatTime = (s: number) => {
    if (isNaN(s)) return '0:00';
    return `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
  };

  return (
    <div className="glass-card">
      <audio ref={audioRef} src={url} preload="metadata" />

      <div className="flex items-center gap-4">
        {/* Play/Pause */}
        <button
          onClick={togglePlay}
          className="flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center
                     transition-all active:scale-95"
          style={{
            background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
            boxShadow: isPlaying
              ? '0 0 0 4px rgba(99,102,241,0.20), 0 4px 15px rgba(99,102,241,0.35)'
              : '0 4px 15px rgba(99,102,241,0.30)',
          }}
          aria-label={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying ? (
            <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 text-white">
              <rect x="6" y="4" width="4" height="16" rx="1" />
              <rect x="14" y="4" width="4" height="16" rx="1" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5 text-white ml-0.5">
              <path d="M8 5v14l11-7z" />
            </svg>
          )}
        </button>

        {/* Progress area */}
        <div className="flex-1 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-slate-800 dark:text-slate-200">
              🎙️ Teacher Narration — {LANGUAGE_LABELS[languageCode] || languageCode}
            </span>
            <span className="text-xs text-slate-500 dark:text-slate-400 tabular-nums">
              {formatTime(currentTime)} / {formatTime(duration)}
            </span>
          </div>

          {/* Seek bar */}
          <div
            onClick={seek}
            className="h-1.5 rounded-full cursor-pointer relative overflow-hidden"
            style={{ background: 'var(--glass-border)' }}
          >
            <div
              className="h-full rounded-full transition-all duration-100"
              style={{
                width: `${progress}%`,
                background: 'linear-gradient(90deg, #6366f1, #8b5cf6)',
              }}
            />
          </div>
        </div>
      </div>

      {/* Download */}
      <a
        href={url}
        download
        className="mt-3 inline-flex items-center gap-1.5 text-xs text-slate-400 dark:text-slate-500
                   hover:text-indigo-600 dark:hover:text-indigo-400 transition-colors"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5m0 0l5-5m-5 5V4" />
        </svg>
        Download audio
      </a>
    </div>
  );
}
