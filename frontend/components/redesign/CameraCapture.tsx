'use client';

import { useEffect, useRef, useState } from 'react';

type Props = {
  open: boolean;
  onClose: () => void;
  onCapture: (file: File, previewUrl: string) => void;
};

export function CameraCapture({ open, onClose, onCapture }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const [timerDuration, setTimerDuration] = useState(5);
  const [countdown, setCountdown] = useState<number | null>(null);
  const [flashActive, setFlashActive] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;

    (async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } },
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach(t => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play().catch(() => {});
        }
      } catch {
        setError('Could not access camera. Please use the gallery upload instead.');
      }
    })();

    return () => {
      cancelled = true;
      if (countdownRef.current) {
        clearInterval(countdownRef.current);
        countdownRef.current = null;
      }
      streamRef.current?.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    };
  }, [open]);

  if (!open) return null;

  const capture = () => {
    const video = videoRef.current;
    if (!video) return;
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);

    setFlashActive(true);
    setTimeout(() => setFlashActive(false), 200);

    canvas.toBlob((blob) => {
      if (!blob) return;
      const file = new File([blob], 'camera-photo.jpg', { type: 'image/jpeg' });
      const preview = URL.createObjectURL(blob);
      onCapture(file, preview);
      onClose();
    }, 'image/jpeg', 0.92);
  };

  const startCountdown = () => {
    setCountdown(timerDuration);
    let remaining = timerDuration;
    countdownRef.current = setInterval(() => {
      remaining -= 1;
      if (remaining <= 0) {
        if (countdownRef.current) clearInterval(countdownRef.current);
        countdownRef.current = null;
        setCountdown(null);
        capture();
      } else {
        setCountdown(remaining);
      }
    }, 1000);
  };

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: '#000', display: 'flex', flexDirection: 'column',
    }}>
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }}
        />

        {flashActive && (
          <div style={{ position: 'absolute', inset: 0, background: '#fff', zIndex: 30 }} />
        )}

        {countdown !== null && (
          <div style={{
            position: 'absolute', inset: 0, display: 'flex',
            alignItems: 'center', justifyContent: 'center', zIndex: 20,
          }}>
            <span style={{
              color: '#fff', fontFamily: 'var(--display)',
              fontSize: 120, fontWeight: 800,
              textShadow: '0 4px 24px rgba(0,0,0,0.5)',
            }}>{countdown}</span>
          </div>
        )}

        <button
          onClick={onClose}
          style={{
            position: 'absolute', top: 16, left: 16, zIndex: 20,
            width: 40, height: 40,
            background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(8px)',
            borderRadius: '50%', border: 'none', color: '#fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer',
          }}
          aria-label="Close camera"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {error && (
          <div style={{
            position: 'absolute', top: 16, left: '50%', transform: 'translateX(-50%)',
            background: 'rgba(0,0,0,0.7)', color: '#fff',
            padding: '10px 16px', borderRadius: 8,
            fontFamily: 'var(--display)', fontSize: 13,
            zIndex: 20,
          }}>{error}</div>
        )}

        {countdown === null && !error && (
          <div style={{
            position: 'absolute', top: 16, left: '50%', transform: 'translateX(-50%)',
            background: 'rgba(0,0,0,0.5)', backdropFilter: 'blur(8px)',
            padding: '8px 16px', borderRadius: 999,
            zIndex: 20,
          }}>
            <p style={{
              color: '#fff', fontFamily: 'var(--display)', fontSize: 12,
              margin: 0, textAlign: 'center',
            }}>Position in A-pose, then press start</p>
          </div>
        )}
      </div>

      {countdown === null && (
        <div style={{
          background: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(8px)',
          padding: '24px 24px 40px',
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: 12, fontFamily: 'var(--display)' }}>Timer:</span>
            {[3, 5, 10].map((t) => (
              <button
                key={t}
                onClick={() => setTimerDuration(t)}
                style={{
                  width: 40, height: 40, borderRadius: '50%',
                  background: timerDuration === t ? '#fff' : 'rgba(255,255,255,0.2)',
                  color: timerDuration === t ? '#000' : '#fff',
                  fontSize: 14, fontWeight: 600, fontFamily: 'var(--display)',
                  border: 'none', cursor: 'pointer',
                }}
              >{t}s</button>
            ))}
          </div>
          <button
            onClick={startCountdown}
            disabled={!!error}
            style={{
              width: 80, height: 80, borderRadius: '50%',
              border: '4px solid #fff', background: 'transparent',
              cursor: error ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
            aria-label="Capture photo"
          >
            <div style={{ width: 64, height: 64, borderRadius: '50%', background: '#fff' }} />
          </button>
        </div>
      )}
    </div>
  );
}
