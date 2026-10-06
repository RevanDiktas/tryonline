import { ImageResponse } from 'next/og';
import { DEFAULT_TITLE } from '@/lib/seo';

// The share card for every page: monochrome, with cobalt only on the button, like the site.
export const runtime = 'edge';
export const alt = DEFAULT_TITLE;
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

const INK = '#0A0A0A';
const PAPER = '#FAFAF8';
const MUTE = '#6E6E6E';
const LINE = 'rgba(10,10,10,0.10)';
const COBALT = '#0040FF';
const SCORES = [
  { size: 'M', score: 31 },
  { size: 'L', score: 96, best: true },
  { size: 'XL', score: 23 },
];

const HEADLINE = 'Your size in 30 seconds.';
const SUB = 'On every product. No account. 3D try-on where you can.';
const CTA = 'Find my size →';
// Every character the card draws, so Google Fonts serves one small subset per weight.
const GLYPHS = `TryOn${HEADLINE}${SUB}${CTA}Your size96% match${SCORES.map((s) => `${s.size}${s.score}%`).join('')}YOUR SIZE`;

// Inter from Google Fonts (woff, which the renderer reads); if it can't be fetched the card
// still renders in the default font.
async function inter(weight: number): Promise<ArrayBuffer | null> {
  try {
    const q = new URLSearchParams({ family: `Inter:wght@${weight}`, text: Array.from(new Set(GLYPHS)).join('') });
    const css = await (await fetch(`https://fonts.googleapis.com/css2?${q.toString()}`, {
      headers: { 'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/534.30 (KHTML, like Gecko) Safari/534.30' },
    })).text();
    const url = css.match(/src: url\((.+?)\) format\('(?:woff|truetype|opentype)'\)/)?.[1];
    return url ? await (await fetch(url)).arrayBuffer() : null;
  } catch {
    return null;
  }
}

export default async function Image() {
  const [w500, w800] = await Promise.all([inter(500), inter(800)]);
  const fonts = [
    ...(w500 ? [{ name: 'Inter', data: w500, weight: 500 as const, style: 'normal' as const }] : []),
    ...(w800 ? [{ name: 'Inter', data: w800, weight: 800 as const, style: 'normal' as const }] : []),
  ];

  return new ImageResponse(
    (
      <div style={{
        width: '100%', height: '100%', display: 'flex', background: PAPER, color: INK,
        fontFamily: 'Inter', padding: '64px 72px', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <div style={{ display: 'flex', flexDirection: 'column', width: 600 }}>
          <div style={{ fontSize: 34, fontWeight: 800, letterSpacing: '-0.03em', marginBottom: 56 }}>TryOn</div>
          <div style={{ fontSize: 84, fontWeight: 800, letterSpacing: '-0.045em', lineHeight: 0.98, marginBottom: 28 }}>
            {HEADLINE}
          </div>
          <div style={{ fontSize: 28, fontWeight: 500, color: MUTE, lineHeight: 1.35, marginBottom: 40 }}>
            {SUB}
          </div>
          <div style={{ display: 'flex' }}>
            <div style={{
              display: 'flex', background: COBALT, color: '#FFFFFF', borderRadius: 9999,
              padding: '16px 30px', fontSize: 24, fontWeight: 500,
            }}>{CTA}</div>
          </div>
        </div>

        <div style={{
          display: 'flex', flexDirection: 'column', width: 380, background: '#FFFFFF',
          border: `1px solid ${LINE}`, borderRadius: 28, padding: '34px 34px 30px',
          boxShadow: '0 24px 60px rgba(0,0,0,0.10)',
        }}>
          <div style={{ fontSize: 16, fontWeight: 500, color: MUTE, letterSpacing: '0.1em', textTransform: 'uppercase' }}>Your size</div>
          <div style={{ display: 'flex', alignItems: 'flex-end', margin: '8px 0 28px' }}>
            <div style={{ fontSize: 96, fontWeight: 800, letterSpacing: '-0.04em', lineHeight: 1 }}>L</div>
            <div style={{ fontSize: 24, fontWeight: 500, color: MUTE, marginLeft: 16, marginBottom: 12 }}>96% match</div>
          </div>
          {SCORES.map((s) => (
            <div key={s.size} style={{ display: 'flex', alignItems: 'center', marginBottom: 16 }}>
              <div style={{ width: 48, fontSize: 22, fontWeight: s.best ? 800 : 500 }}>{s.size}</div>
              <div style={{ display: 'flex', flex: 1, height: 10, borderRadius: 5, background: LINE }}>
                <div style={{ width: `${s.score}%`, height: 10, borderRadius: 5, background: s.best ? INK : MUTE }} />
              </div>
              <div style={{ width: 64, textAlign: 'right', fontSize: 22, fontWeight: 500, color: s.best ? INK : MUTE, justifyContent: 'flex-end', display: 'flex' }}>{s.score}%</div>
            </div>
          ))}
        </div>
      </div>
    ),
    { ...size, fonts: fonts.length ? fonts : undefined },
  );
}
