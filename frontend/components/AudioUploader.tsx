"use client";

import { useState, useRef, useCallback } from "react";

interface Props {
  onFileSelected: (file: File) => void;
}

const MAX_SIZE_MB = 50;
const MAX_SIZE    = MAX_SIZE_MB * 1024 * 1024;
const ALLOWED     = ["audio/mpeg", "audio/mp3", "audio/wav", "audio/x-wav", "audio/wave"];
const ALLOWED_EXT = [".mp3", ".wav"];

export default function AudioUploader({ onFileSelected }: Props) {
  const [isDragOver, setIsDragOver]   = useState(false);
  const [fileError, setFileError]     = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateAndSet = useCallback((file: File) => {
    setFileError("");

    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    const validMime = ALLOWED.includes(file.type);
    const validExt  = ALLOWED_EXT.includes(ext);

    if (!validMime && !validExt) {
      setFileError("Invalid file type. Please upload an MP3 or WAV file.");
      return;
    }
    if (file.size > MAX_SIZE) {
      setFileError(`File too large. Maximum size is ${MAX_SIZE_MB} MB.`);
      return;
    }

    setSelectedFile(file);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) validateAndSet(file);
  }, [validateAndSet]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) validateAndSet(file);
  };

  const formatSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div>
      {/* Drop Zone */}
      <div
        id="audio-upload-zone"
        className={`upload-zone ${isDragOver ? "drag-over" : ""}`}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
        onDragLeave={() => setIsDragOver(false)}
        onDrop={handleDrop}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
        style={{
          padding: "clamp(40px, 8vw, 72px) 32px",
          textAlign: "center",
          userSelect: "none",
        }}
        aria-label="Upload audio file"
      >
        {/* Icon */}
        <div
          style={{
            width: "72px",
            height: "72px",
            borderRadius: "50%",
            background: "rgba(139,92,246,0.12)",
            border: "2px solid rgba(139,92,246,0.25)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            margin: "0 auto 20px",
            fontSize: "28px",
            transition: "all 0.3s ease",
            ...(isDragOver && {
              background: "rgba(139,92,246,0.25)",
              transform: "scale(1.1)",
            }),
          }}
        >
          {isDragOver ? "🎵" : "📁"}
        </div>

        <p
          style={{
            fontSize: "1.15rem",
            fontWeight: 700,
            color: "var(--text-primary)",
            marginBottom: "8px",
          }}
        >
          {isDragOver ? "Drop it here!" : "Drag & drop your audio file"}
        </p>
        <p style={{ fontSize: "14px", color: "var(--text-secondary)", marginBottom: "24px" }}>
          or{" "}
          <span className="gradient-text" style={{ fontWeight: 700, cursor: "pointer" }}>
            click to browse
          </span>
        </p>
        <p style={{ fontSize: "12px", color: "var(--text-muted)" }}>
          MP3 or WAV &nbsp;·&nbsp; Max {MAX_SIZE_MB} MB
        </p>

        <input
          ref={inputRef}
          type="file"
          accept=".mp3,.wav,audio/mpeg,audio/wav"
          style={{ display: "none" }}
          id="audio-file-input"
          onChange={handleInputChange}
        />
      </div>

      {/* File Error */}
      {fileError && (
        <div
          style={{
            marginTop: "12px",
            padding: "12px 16px",
            borderRadius: "10px",
            background: "rgba(239,68,68,0.1)",
            border: "1px solid rgba(239,68,68,0.25)",
            color: "#f87171",
            fontSize: "13px",
            display: "flex",
            gap: "8px",
            alignItems: "center",
          }}
        >
          <span>⚠️</span> {fileError}
        </div>
      )}

      {/* Selected File Preview */}
      {selectedFile && !fileError && (
        <div
          style={{
            marginTop: "20px",
            padding: "16px",
            borderRadius: "14px",
            background: "rgba(139,92,246,0.08)",
            border: "1px solid rgba(139,92,246,0.2)",
            display: "flex",
            alignItems: "center",
            gap: "14px",
          }}
        >
          {/* File icon */}
          <div
            style={{
              width: "44px",
              height: "44px",
              borderRadius: "10px",
              background: "var(--gradient-main)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: "20px",
              flexShrink: 0,
            }}
          >
            🎵
          </div>

          {/* File info */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <p
              style={{
                fontWeight: 600,
                fontSize: "14px",
                color: "var(--text-primary)",
                marginBottom: "2px",
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
            >
              {selectedFile.name}
            </p>
            <p style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
              {formatSize(selectedFile.size)}
            </p>
          </div>

          {/* Remove button */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              setSelectedFile(null);
              if (inputRef.current) inputRef.current.value = "";
            }}
            style={{
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "8px",
              color: "var(--text-secondary)",
              cursor: "pointer",
              padding: "6px 10px",
              fontSize: "12px",
              transition: "all 0.2s ease",
              flexShrink: 0,
            }}
            id="remove-file-btn"
            aria-label="Remove selected file"
          >
            ✕
          </button>
        </div>
      )}

      {/* Convert button */}
      {selectedFile && !fileError && (
        <button
          className="btn-gradient pulse-ring"
          id="convert-btn"
          onClick={() => onFileSelected(selectedFile)}
          style={{
            width: "100%",
            marginTop: "16px",
            padding: "16px 24px",
            fontSize: "16px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: "10px",
          }}
        >
          <span>🎧</span>
          Convert to 8D Audio
        </button>
      )}
    </div>
  );
}
