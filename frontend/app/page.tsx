"use client";

import { useState } from "react";
import AudioUploader from "@/components/AudioUploader";
import ProcessingStatus from "@/components/ProcessingStatus";
import AudioPlayer from "@/components/AudioPlayer";

export type AppState = "idle" | "uploading" | "processing" | "done" | "error";

export interface ProcessResult {
  fileUrl: string;
  fileName: string;
  original: string;
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export default function HomePage() {
  const [appState, setAppState] = useState<AppState>("idle");
  const [result, setResult]     = useState<ProcessResult | null>(null);
  const [error, setError]       = useState<string>("");
  const [progress, setProgress] = useState<number>(0); // 0-4 step index

  const handleFileSelected = async (file: File) => {
    setError("");
    setResult(null);

    // ── Step 0: Uploading ──────────────────────────────────────
    setAppState("uploading");
    setProgress(0);

    const formData = new FormData();
    formData.append("file", file);

    try {
      // ── Step 1: Processing ──────────────────────────────────
      setAppState("processing");
      setProgress(1);

      // Simulate sub-step progress while waiting for backend
      const stepTimer1 = setTimeout(() => setProgress(2), 4000);
      const stepTimer2 = setTimeout(() => setProgress(3), 9000);

      const response = await fetch(`${BACKEND_URL}/api/process`, {
        method: "POST",
        body: formData,
      });

      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);

      if (!response.ok) {
        let detail = "Processing failed. Please try again.";
        try {
          const json = await response.json();
          detail = json.detail || detail;
        } catch (_) {}
        throw new Error(detail);
      }

      const data = await response.json();

      // ── Step 4: Done ────────────────────────────────────────
      setProgress(4);
      setResult({
        fileUrl:  `${BACKEND_URL}${data.file_url}`,
        fileName: data.file_name,
        original: data.original,
      });
      setAppState("done");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "An unexpected error occurred.";
      setError(msg);
      setAppState("error");
    }
  };

  const handleReset = () => {
    setAppState("idle");
    setResult(null);
    setError("");
    setProgress(0);
  };

  return (
    <main
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "24px 16px 64px",
      }}
    >
      {/* ── Header ───────────────────────────────────────────── */}
      <header style={{ textAlign: "center", marginBottom: "56px", paddingTop: "48px" }}>
        {/* Logo badge */}
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "8px",
            background: "rgba(139,92,246,0.12)",
            border: "1px solid rgba(139,92,246,0.25)",
            borderRadius: "100px",
            padding: "6px 16px",
            marginBottom: "24px",
            fontSize: "13px",
            fontWeight: 600,
            color: "#a78bfa",
            letterSpacing: "0.5px",
          }}
        >
          <span style={{ fontSize: "16px" }}>🎧</span>
          8D AUDIO ENGINE
        </div>

        <h1
          style={{
            fontSize: "clamp(2.2rem, 6vw, 4rem)",
            fontWeight: 900,
            lineHeight: 1.1,
            letterSpacing: "-0.03em",
            marginBottom: "16px",
            fontFamily: "'Outfit', 'Inter', sans-serif",
          }}
        >
          Transform Your Music{" "}
          <span className="gradient-text" style={{ display: "block" }}>
            Into 8D Experience
          </span>
        </h1>

        <p
          style={{
            fontSize: "clamp(1rem, 2.5vw, 1.2rem)",
            color: "var(--text-secondary)",
            maxWidth: "480px",
            margin: "0 auto",
            lineHeight: 1.6,
          }}
        >
          Convert your songs into immersive{" "}
          <strong style={{ color: "#a78bfa" }}>8D</strong>,{" "}
          <strong style={{ color: "#ec4899" }}>slow</strong> and{" "}
          <strong style={{ color: "#38bdf8" }}>reverb</strong> audio.
        </p>

        {/* Feature pills */}
        <div
          style={{
            display: "flex",
            gap: "8px",
            justifyContent: "center",
            flexWrap: "wrap",
            marginTop: "24px",
          }}
        >
          {[
            { icon: "bi bi-music-note-beamed", text: "MP3 & WAV" },
            { icon: "bi bi-lightning-fill", text: "Fast Processing" },
            { icon: "bi bi-cloud-arrow-down-fill", text: "Free Download" },
            { icon: "bi bi-person-fill-slash", text: "No Account Needed" },
          ].map((item) => (
            <span
              key={item.text}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "5px 12px",
                borderRadius: "100px",
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
                fontSize: "12px",
                color: "var(--text-secondary)",
                fontWeight: 500,
              }}
            >
              <i className={item.icon} style={{ color: "var(--accent-purple)" }}></i>
              <span>{item.text}</span>
            </span>
          ))}
        </div>
      </header>

      {/* ── Main Card ────────────────────────────────────────── */}
      <div
        className="glass-card"
        style={{
          width: "100%",
          maxWidth: "680px",
          padding: "clamp(24px, 5vw, 48px)",
        }}
      >
        {/* IDLE – show uploader */}
        {(appState === "idle" || appState === "error") && (
          <div className="fade-in">
            <AudioUploader onFileSelected={handleFileSelected} />
            {error && (
              <div
                style={{
                  marginTop: "20px",
                  padding: "16px",
                  borderRadius: "12px",
                  background: "rgba(239,68,68,0.1)",
                  border: "1px solid rgba(239,68,68,0.25)",
                  color: "#f87171",
                  fontSize: "14px",
                  display: "flex",
                  gap: "10px",
                  alignItems: "flex-start",
                }}
              >
                <span style={{ fontSize: "18px", flexShrink: 0 }}>⚠️</span>
                <div>
                  <strong style={{ display: "block", marginBottom: "4px" }}>
                    Processing Failed
                  </strong>
                  {error}
                </div>
              </div>
            )}
          </div>
        )}

        {/* UPLOADING / PROCESSING – show progress */}
        {(appState === "uploading" || appState === "processing") && (
          <div className="fade-in">
            <ProcessingStatus currentStep={progress} />
          </div>
        )}

        {/* DONE – show player */}
        {appState === "done" && result && (
          <div className="fade-in">
            <AudioPlayer result={result} backendUrl={BACKEND_URL} />
            <div
              style={{
                display: "flex",
                gap: "12px",
                marginTop: "24px",
                flexWrap: "wrap",
              }}
            >
              <button
                className="btn-gradient"
                onClick={handleReset}
                style={{ flex: 1, padding: "14px 24px", fontSize: "15px" }}
                id="convert-another-btn"
              >
                🔄 Convert Another Audio
              </button>
              <a
                href={result.fileUrl}
                download={result.fileName}
                style={{ flex: 1, textDecoration: "none" }}
              >
                <button
                  className="btn-ghost"
                  style={{
                    width: "100%",
                    padding: "14px 24px",
                    fontSize: "15px",
                  }}
                  id="download-result-btn"
                >
                  📥 Download MP3
                </button>
              </a>
            </div>
          </div>
        )}
      </div>

      {/* ── How it works ─────────────────────────────────────── */}
      {appState === "idle" && (
        <div
          className="fade-in"
          style={{
            marginTop: "56px",
            width: "100%",
            maxWidth: "680px",
          }}
        >
          <h2
            style={{
              textAlign: "center",
              fontSize: "1.1rem",
              fontWeight: 700,
              color: "var(--text-secondary)",
              marginBottom: "24px",
              textTransform: "uppercase",
              letterSpacing: "0.1em",
            }}
          >
            How It Works
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "16px" }}>
            {[
              { icon: "📁", title: "Upload", desc: "Drop your MP3 or WAV file" },
              { icon: "⚙️", title: "Process", desc: "8D + slow + reverb applied" },
              { icon: "🎧", title: "Enjoy", desc: "Play & download your 8D audio" },
            ].map((item, i) => (
              <div
                key={i}
                className="glass-card"
                style={{ padding: "20px 16px", textAlign: "center" }}
              >
                <div style={{ fontSize: "28px", marginBottom: "10px" }}>{item.icon}</div>
                <div
                  style={{
                    fontWeight: 700,
                    fontSize: "15px",
                    marginBottom: "6px",
                    color: "var(--text-primary)",
                  }}
                >
                  {item.title}
                </div>
                <div style={{ fontSize: "13px", color: "var(--text-secondary)" }}>{item.desc}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Footer ───────────────────────────────────────────── */}
      <footer
        style={{
          marginTop: "64px",
          textAlign: "center",
          fontSize: "13px",
          color: "var(--text-muted)",
        }}
      >
        Built with 🎵 Python + FastAPI + Next.js &nbsp;·&nbsp; Powered by 8D Audio Engine
      </footer>
    </main>
  );
}
