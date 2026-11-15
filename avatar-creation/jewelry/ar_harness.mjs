// Drive ar-tryon.html in real Chrome with a fake camera feed; wait for tracking; screenshot.
import { chromium } from '/Volumes/SanDisk/fravash/node_modules/playwright-core/index.mjs';
const [,, url, y4m, out, waitMs = '90000'] = process.argv;
const browser = await chromium.launch({
  executablePath: '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  headless: true,
  args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist',
         '--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream',
         `--use-file-for-fake-video-capture=${y4m}`, '--autoplay-policy=no-user-gesture-required'],
});
const [vw, vh] = (process.env.VIEW || '450x900').split('x').map(Number);
const ctx = await browser.newContext({ viewport: { width: vw, height: vh }, deviceScaleFactor: 1, permissions: ['camera'] });
const page = await ctx.newPage();
const lines = [];
page.on('console', m => { const t = m.text(); if (!/GL Driver|gl_context|Graph success|OpenGL error/.test(t)) lines.push(`${m.type()}: ${t}`); });
page.on('pageerror', e => lines.push('pageerror: ' + e.message));
const t0 = Date.now();
await page.goto(url, { waitUntil: 'load' });
let state = 'timeout';
try {
  // tracking is logged, not written to the DOM; poll the console lines instead
  const deadline = t0 + +waitMs;
  while (Date.now() < deadline) {
    if (lines.some(l => /tracking|fatal/.test(l))) break;
    await page.waitForTimeout(500);
  }
  state = lines.some(l => /\] tracking/.test(l)) ? 'tracking' : lines.some(l => /fatal/.test(l)) ? 'fatal' : 'no-tracking';
} finally {
  await page.waitForTimeout(+(process.env.SETTLE || 2500));
  await page.screenshot({ path: out });
  // SHOTS=n: n more screenshots 350 ms apart, for clips where the subject moves.
  for (let i = 1; i <= +(process.env.SHOTS || 0); i++) { await page.waitForTimeout(350); await page.screenshot({ path: out.replace(/\.png$/, `_${i}.png`) }); }
  const dbg = await page.evaluate(() => ({ debug: document.getElementById('debug')?.textContent, hint: document.getElementById('hint')?.textContent,
    state: document.getElementById('state')?.className, video: [document.getElementById('cam')?.videoWidth, document.getElementById('cam')?.videoHeight, document.getElementById('cam')?.readyState], info: window.__arInfo }));
  if (process.env.DUMP) { const raw = await page.evaluate(() => window.__arRaw || null); (await import('node:fs')).writeFileSync(process.env.DUMP, JSON.stringify(raw)); }
  console.log('RESULT', state, 'after', ((Date.now() - t0) / 1000).toFixed(1) + 's', JSON.stringify(dbg));
  console.log(lines.slice(0, 40).join('\n'));
  await Promise.race([browser.close(), new Promise(r => setTimeout(r, 5000))]);
  process.exit(0);   // Chrome with a fake camera sometimes never finishes closing
}
