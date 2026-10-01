"use client";

import { useRef, useState, useEffect, useCallback } from "react";
import type { ProcessResult } from "@/app/page";

interface Props {
  result: ProcessResult;
}

export default function AudioPlayer({ result }: Props) {
  const audioRef           = useRef<HTMLAudioElement>(null);
  const progressBarRef     = useRef<HTMLDivElement>(null);
  const [isPlaying, setIsPlaying]       = useState(false);
  const [currentTime, setCurrentTime]   = useState(0);
  const [duration, setDuration]         = useState(0);
  const [volume, setVolume]             = useState(1);
  const [isMuted, setIsMuted]           = useState(false);

  // Auto-play when component mounts
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.play().catch(() => setIsPlaying(false));
  }, []);

  const handleTimeUpdate = () => {
    const audio = audioRef.current;
    if (!audio) return;
    setCurrentTime(audio.currentTime);
  };

  const handleLoadedMetadata = () => {
    const audio = audioRef.current;
    if (!audio) return;
    setDuration(audio.duration);
  };

  const handleEnded = () => setIsPlaying(false);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (isPlaying) {
      audio.pause();
    } else {
      audio.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleProgressClick = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const bar   = progressBarRef.current;
    const audio = audioRef.current;
    if (!bar || !audio || !duration) return;
    const rect  = bar.getBoundingClientRect();
    const ratio = (e.clientX - rect.left) / rect.width;
    audio.currentTime = ratio * duration;
  }, [duration]);

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setVolume(val);
    if (audioRef.current) audioRef.current.volume = val;
    setIsMuted(val === 0);
  };

  const toggleMute = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (isMuted) {
      audio.volume = volume || 1;
      setIsMuted(false);
    } else {
      audio.volume = 0;
      setIsMuted(true);
    }
  };

  const formatTime = (s: number) => {
    if (!isFinite(s)) return "0:00";
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
  };

  const progressPercent = duration ? (currentTime / duration) * 100 : 0;

  // Waveform bar heights (decorative, pre-computed)
  const barHeights = [
    6, 14, 20, 28, 36, 40, 36, 32, 28, 22, 18, 24, 32, 38, 40, 36, 28, 20, 14, 8,
    10, 18, 26, 34, 38, 40, 38, 30, 24, 16, 12, 20, 30, 36, 40, 34, 26, 18, 10, 6,
  ];

  return (
    <div>
      {/* Success badge */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "10px",
          padding: "12px 16px",
          borderRadius: "12px",
          background: "rgba(16,185,129,0.1)",
          border: "1px solid rgba(16,185,129,0.2)",
          marginBottom: "24px",
        }}
      >
        <span style={{ fontSize: "20px" }}>✅</span>
        <div style={{ flex: 1 }}>
          <p style={{ fontWeight: 700, fontSize: "14px", color: "#34d399", marginBottom: "2px" }}>
            8D Audio Ready!
          </p>
          <p
            style={{
              fontSize: "12px",
              color: "var(--text-secondary)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {result.original}
          </p>
        </div>
        {duration > 0 && (
          <span
            style={{
              fontSize: "12px",
              color: "var(--text-secondary)",
              background: "rgba(255,255,255,0.05)",
              padding: "4px 10px",
              borderRadius: "100px",
              flexShrink: 0,
            }}
          >
            {formatTime(duration)}
          </span>
        )}
      </div>

      {/* Hidden audio element */}
      <audio
        ref={audioRef}
        src={result.fileUrl}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={handleEnded}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        preload="auto"
        id="result-audio"
      />

      {/* Waveform visualizer (decorative) */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "2px",
          height: "60px",
          marginBottom: "20px",
          overflow: "hidden",
        }}
      >
        {barHeights.map((h, i) => {
          const barProgress = (i / barHeights.length) * 100;
          const isPast = barProgress <= progressPercent;
          return (
            <div
              key={i}
              style={{
                width: "4px",
                height: `${h}px`,
                borderRadius: "2px",
                background: isPast
                  ? "var(--gradient-main)"
                  : "rgba(255,255,255,0.12)",
                transition: "background 0.15s ease",
                ...(isPlaying && isPast
                  ? {
                      animation: `waveAnim ${0.8 + (i % 5) * 0.15}s ease-in-out infinite`,
                      animationDelay: `${(i * 0.04).toFixed(2)}s`,
                    }
                  : {}),
              }}
            />
          );
        })}
      </div>

      {/* Progress bar */}
      <div
        ref={progressBarRef}
        className="audio-progress-bar"
        onClick={handleProgressClick}
        role="slider"
        aria-label="Audio progress"
        aria-valuemin={0}
        aria-valuemax={duration}
        aria-valuenow={currentTime}
        id="audio-progress-bar"
        style={{ marginBottom: "8px", cursor: "pointer" }}
      >
        <div
          className="audio-progress-fill"
          style={{ width: `${progressPercent}%` }}
        />
        {duration > 0 && (
          <div
            className="audio-progress-thumb"
            style={{ left: `${progressPercent}%` }}
          />
        )}
      </div>

      {/* Time display */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          fontSize: "12px",
          color: "var(--text-muted)",
          marginBottom: "20px",
        }}
      >
        <span>{formatTime(currentTime)}</span>
        <span>{formatTime(duration)}</span>
      </div>

      {/* Controls */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "12px",
          flexWrap: "wrap",
        }}
      >
        {/* Play / Pause */}
        <button
          className="btn-gradient pulse-ring"
          id="play-pause-btn"
          onClick={togglePlay}
          style={{
            width: "56px",
            height: "56px",
            borderRadius: "50%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: "22px",
            flexShrink: 0,
            padding: 0,
          }}
          aria-label={isPlaying ? "Pause" : "Play"}
        >
          {isPlaying ? "⏸" : "▶"}
        </button>

        {/* Volume control */}
        <button
          id="mute-btn"
          onClick={toggleMute}
          aria-label="Toggle mute"
          style={{
            background: "transparent",
            border: "none",
            cursor: "pointer",
            fontSize: "18px",
            color: "var(--text-secondary)",
            padding: "8px",
            flexShrink: 0,
          }}
        >
          {isMuted ? "🔇" : volume > 0.5 ? "🔊" : "🔉"}
        </button>

        <input
          id="volume-slider"
          type="range"
          min={0}
          max={1}
          step={0.01}
          value={isMuted ? 0 : volume}
          onChange={handleVolumeChange}
          aria-label="Volume"
          style={{
            flex: 1,
            accentColor: "var(--accent-purple)",
            cursor: "pointer",
            minWidth: "60px",
          }}
        />

        {/* Download button */}
        <a
          href={result.fileUrl}
          download={result.fileName}
          style={{ textDecoration: "none", flexShrink: 0 }}
        >
          <button
            id="inline-download-btn"
            className="btn-ghost"
            style={{ padding: "10px 16px", fontSize: "13px" }}
          >
            📥 MP3
          </button>
        </a>
      </div>

      {/* File name chip */}
      <div
        style={{
          marginTop: "16px",
          padding: "8px 14px",
          borderRadius: "8px",
          background: "rgba(255,255,255,0.03)",
          border: "1px solid var(--border)",
          fontSize: "12px",
          color: "var(--text-muted)",
          display: "flex",
          gap: "8px",
          alignItems: "center",
          overflow: "hidden",
        }}
      >
        <span>🎵</span>
        <span
          style={{
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {result.fileName}
        </span>
      </div>
    </div>
  );
}
