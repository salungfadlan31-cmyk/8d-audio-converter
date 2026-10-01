"use client";

interface Step {
  label: string;
  icon:  string;
  detail: string;
}

const STEPS: Step[] = [
  { label: "Uploading",          icon: "📤", detail: "Sending file to server..." },
  { label: "Applying 8D Effect", icon: "🔄", detail: "Creating surround movement..." },
  { label: "Slowing Down",       icon: "🐢", detail: "Adjusting playback speed..." },
  { label: "Adding Reverb",      icon: "🏛️", detail: "Adding room reverb effect..." },
  { label: "Finished!",          icon: "✅", detail: "Your 8D audio is ready." },
];

interface Props {
  currentStep: number; // 0 = uploading, 1-3 = processing, 4 = done
}

export default function ProcessingStatus({ currentStep }: Props) {
  return (
    <div>
      {/* Header */}
      <div style={{ textAlign: "center", marginBottom: "32px" }}>
        {currentStep < 4 ? (
          <>
            {/* Animated waveform */}
            <div className="waveform" style={{ justifyContent: "center", marginBottom: "20px" }}>
              {Array.from({ length: 20 }).map((_, i) => (
                <div
                  key={i}
                  className="waveform-bar"
                  style={{
                    height: `${Math.random() * 30 + 10}px`,
                    animationDelay: `${(i * 0.06).toFixed(2)}s`,
                    animationDuration: `${0.8 + Math.random() * 0.8}s`,
                  }}
                />
              ))}
            </div>
            <p
              style={{
                fontWeight: 700,
                fontSize: "1.2rem",
                color: "var(--text-primary)",
                marginBottom: "6px",
              }}
            >
              Processing Your Audio
            </p>
            <p style={{ fontSize: "14px", color: "var(--text-secondary)" }}>
              This may take a minute depending on file size…
            </p>
          </>
        ) : (
          <div
            style={{
              fontSize: "48px",
              marginBottom: "12px",
              animation: "fadeIn 0.5s ease",
            }}
          >
            🎉
          </div>
        )}
      </div>

      {/* Steps list */}
      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        {STEPS.map((step, i) => {
          const isDone    = i < currentStep;
          const isActive  = i === currentStep;
          const isPending = i > currentStep;

          return (
            <div
              key={i}
              className={`step-item ${isDone ? "done" : isActive ? "active" : "pending"}`}
              style={{ opacity: isPending ? 0.4 : 1 }}
            >
              {/* Step dot */}
              <div className={`step-dot ${isDone ? "done" : isActive ? "active" : "pending"}`}>
                {isDone ? (
                  <span style={{ color: "white" }}>✓</span>
                ) : isActive ? (
                  <div className="spinner" />
                ) : (
                  <span style={{ color: "var(--text-muted)", fontSize: "12px" }}>{i + 1}</span>
                )}
              </div>

              {/* Step info */}
              <div style={{ flex: 1 }}>
                <p
                  style={{
                    fontWeight: 600,
                    fontSize: "14px",
                    color: isDone
                      ? "#34d399"
                      : isActive
                      ? "var(--text-primary)"
                      : "var(--text-muted)",
                    marginBottom: "2px",
                  }}
                >
                  {step.icon} {step.label}
                </p>
                {(isActive || isDone) && (
                  <p style={{ fontSize: "12px", color: "var(--text-secondary)" }}>
                    {step.detail}
                  </p>
                )}
              </div>

              {/* Status badge */}
              {isDone && (
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 600,
                    color: "#34d399",
                    background: "rgba(16,185,129,0.1)",
                    padding: "3px 8px",
                    borderRadius: "100px",
                  }}
                >
                  Done
                </span>
              )}
              {isActive && currentStep < 4 && (
                <span
                  style={{
                    fontSize: "11px",
                    fontWeight: 600,
                    color: "#a78bfa",
                    background: "rgba(139,92,246,0.1)",
                    padding: "3px 8px",
                    borderRadius: "100px",
                  }}
                >
                  Running
                </span>
              )}
            </div>
          );
        })}
      </div>

      {/* Overall progress bar */}
      <div
        style={{
          marginTop: "24px",
          background: "rgba(255,255,255,0.06)",
          borderRadius: "100px",
          height: "6px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${(currentStep / (STEPS.length - 1)) * 100}%`,
            background: "var(--gradient-main)",
            borderRadius: "100px",
            transition: "width 0.8s cubic-bezier(0.4, 0, 0.2, 1)",
          }}
        />
      </div>
      <p
        style={{
          textAlign: "right",
          fontSize: "12px",
          color: "var(--text-muted)",
          marginTop: "6px",
        }}
      >
        {Math.round((currentStep / (STEPS.length - 1)) * 100)}%
      </p>
    </div>
  );
}
