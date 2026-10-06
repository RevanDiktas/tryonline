'use client';

import React, { useEffect, useRef, useState } from 'react';
import type { Palette } from './marketing';

/**
 * The real Find my size card (public/size-finder.html), running in a phone frame. This page
 * plays the store: it answers the card's TRYON_SIZE_READY with the product and opens it,
 * exactly as the Shopify block does. No shop is passed, so nothing is tracked as a store's
 * analytics. "Add to cart" shows a demo toast instead of a cart.
 */
const SIZES = ['XS', 'S', 'M', 'L', 'XL'];
const SOLD_OUT = 'L';

export default function LiveSizeDemo({ C }: { C: Palette }) {
  const frame = useRef<HTMLIFrameElement>(null);
  const [run, setRun] = useState(0);          // bump to restart the card
  const [closed, setClosed] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const opened = useRef(-1);   // the run the card was last opened for

  // Hand the card its product and open it, once per run. Called on the card's READY and on
  // the frame's load: READY can fire before this page has hydrated and is listening.
  const openCard = () => {
    const f = frame.current;
    if (!f || !f.contentWindow || opened.current === run) return;
    opened.current = run;
    const post = (type: string, payload?: unknown) => f.contentWindow?.postMessage(payload ? { type, payload } : { type }, '*');
    post('TRYON_SIZE_PRODUCT', {
      sizes: SIZES.map((label) => ({ label, available: label !== SOLD_OUT })),
      image: `${window.location.origin}/redesign/zipup_demo.webp`,
      hasTryon: false,
    });
    post('TRYON_SIZE_OPEN');
    setClosed(false);
  };
  const openRef = useRef(openCard);
  openRef.current = openCard;

  useEffect(() => {
    const onMessage = (e: MessageEvent) => {
      const f = frame.current;
      if (!f || e.source !== f.contentWindow || !e.data) return;
      if (e.data.type === 'TRYON_SIZE_READY') openRef.current();
      if (e.data.type === 'TRYON_SIZE_CLOSE') setClosed(true);
      if (e.data.type === 'TRYON_SIZE_ADD_TO_CART' && e.data.payload) {
        setClosed(true);
        setToast(`Demo: ${String(e.data.payload.size).toUpperCase()} added to cart`);
        window.setTimeout(() => setToast(null), 2600);
      }
    };
    window.addEventListener('message', onMessage);
    return () => window.removeEventListener('message', onMessage);
  }, []);

  // The frame may have finished loading before this page hydrated (then neither READY nor
  // onLoad reached React): open it now if its document is already complete (same origin).
  useEffect(() => {
    try {
      if (frame.current?.contentDocument?.readyState === 'complete') openRef.current();
    } catch { /* not readable: READY or onLoad will do it */ }
  }, [run]);

  const src = `/size-finder.html?product_name=${encodeURIComponent('Originals zip-up')}&brand_name=${encodeURIComponent('Your store')}&v=${run}`;

  return (
    <div style={{ display: 'grid', justifyItems: 'center', gap: 14 }}>
      <div style={{
        position: 'relative', width: 'min(100%, 360px)', aspectRatio: '9 / 18.5',
        borderRadius: 46, padding: 10, background: C.ink,
        boxShadow: '0 30px 80px rgba(0,0,0,0.18)',
      }}>
        <div style={{ position: 'relative', width: '100%', height: '100%', borderRadius: 36, overflow: 'hidden', background: '#FFFFFF' }}>
          {/* The store's product page under the card. */}
          <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column' }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/redesign/zipup_demo.webp" alt="" style={{ width: '100%', height: '62%', objectFit: 'cover', background: '#F2F2F2' }} />
            <div style={{ padding: '14px 16px', fontFamily: 'var(--display)', color: '#0A0A0A' }}>
              <div style={{ fontSize: 15, fontWeight: 600 }}>Originals zip-up</div>
              <div style={{ fontSize: 13, color: '#6E6E6E', marginTop: 2 }}>€49.00</div>
              <div style={{ display: 'flex', gap: 6, marginTop: 12 }}>
                {SIZES.map((s) => (
                  <span key={s} style={{
                    flex: 1, textAlign: 'center', padding: '7px 0', fontSize: 12, borderRadius: 8,
                    border: '1px solid rgba(10,10,10,0.14)', color: s === SOLD_OUT ? '#B0B0B0' : '#0A0A0A',
                    textDecoration: s === SOLD_OUT ? 'line-through' : 'none',
                  }}>{s}</span>
                ))}
              </div>
              <button
                type="button"
                onClick={() => { setRun((r) => r + 1); }}
                style={{
                  marginTop: 12, width: '100%', padding: '11px 0', borderRadius: 10, border: '1px solid #0A0A0A',
                  background: '#FFFFFF', color: '#0A0A0A', fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600, cursor: 'pointer',
                }}
              >Find my size</button>
            </div>
          </div>
          <iframe
            key={run}
            ref={frame}
            src={src}
            title="Find my size, live demo"
            onLoad={() => openRef.current()}
            style={{
              position: 'absolute', inset: 0, width: '100%', height: '100%', border: 0, background: 'transparent',
              pointerEvents: closed ? 'none' : 'auto', opacity: closed ? 0 : 1, transition: 'opacity .25s ease',
            }}
          />
          {toast && (
            <div role="status" style={{
              position: 'absolute', left: 16, right: 16, top: 16, padding: '11px 14px', borderRadius: 14,
              background: '#0A0A0A', color: '#FFFFFF', fontFamily: 'var(--display)', fontSize: 13, fontWeight: 600, textAlign: 'center',
            }}>{toast}</div>
          )}
        </div>
      </div>
      <p style={{ fontFamily: 'var(--display)', fontSize: 12.5, color: C.mute, margin: 0, textAlign: 'center' }}>
        The real Find my size card. Size L is sold out in this demo.
        {closed && <> <button type="button" onClick={() => setRun((r) => r + 1)} style={{ background: 'none', border: 0, padding: 0, color: C.ink, textDecoration: 'underline', cursor: 'pointer', font: 'inherit' }}>Open it again</button></>}
      </p>
    </div>
  );
}
