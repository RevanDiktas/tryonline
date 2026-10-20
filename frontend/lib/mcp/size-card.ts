/**
 * The size card shown inside the chat (an MCP App, ui://tryon/size-card.html) for
 * recommend_size. Plain HTML + the official MCP Apps client (public/mcp-assets, pinned copy of
 * @modelcontextprotocol/ext-apps app-with-deps.js, served from tryon.global so nothing loads
 * from a third-party CDN). Our own bundle, not tryon.global in a frame: hosts reject frames.
 *
 * It renders the tool's structuredContent (SizeCardData in app/mcp/route.ts). Buttons go
 * through the host: openLink for the product, callServerTool for save_to_wishlist.
 */
export const SIZE_CARD_URI = 'ui://tryon/size-card.html';
export const EXT_APPS_URL = 'https://tryon.global/mcp-assets/ext-apps-2.0.3.js';

export const SIZE_CARD_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>TryOn size</title>
<style>
  :root { --ink:#0A0A0A; --dim:#6F6C66; --line:#E6E2D8; --card:#FFFFFF; --soft:#F6F4EF; --accent:#0040FF; --good:#1E7F4F; --warn:#9A5B00; }
  :root[data-theme="dark"] { --ink:#F2F1EC; --dim:#9A9891; --line:#2A2A2A; --card:#141414; --soft:#1C1C1C; --accent:#5B82FF; --good:#4CC38A; --warn:#E3A44B; }
  * { box-sizing: border-box; }
  html, body { margin:0; background:transparent; color:var(--ink); font: 14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }
  .card { background:var(--card); border:1px solid var(--line); border-radius:16px; padding:16px; display:grid; gap:14px; }
  .top { display:flex; gap:14px; align-items:center; }
  .img { width:72px; height:90px; border-radius:10px; background:var(--soft) center/cover no-repeat; flex:none; }
  .title { font-weight:600; font-size:15px; margin:0; }
  .store { color:var(--dim); font-size:13px; margin:2px 0 0; }
  .result { display:flex; align-items:center; gap:16px; }
  .ring { --p:0; width:92px; height:92px; border-radius:50%; flex:none; display:grid; place-items:center;
          background: conic-gradient(var(--accent) calc(var(--p)*1%), var(--soft) 0); }
  .ring > div { width:76px; height:76px; border-radius:50%; background:var(--card); display:grid; place-items:center; text-align:center; }
  .size { font-size:24px; font-weight:700; line-height:1; }
  .pct { font-size:10px; color:var(--dim); margin-top:3px; white-space:nowrap; }
  .lead { font-size:12px; text-transform:uppercase; letter-spacing:.05em; color:var(--dim); margin:0 0 4px; }
  .why { margin:0; }
  .note { margin:0; color:var(--warn); font-size:13px; }
  .sizes { display:flex; flex-wrap:wrap; gap:6px; }
  .chip { border:1px solid var(--line); border-radius:999px; padding:4px 10px; font-size:12px; color:var(--dim); }
  .chip b { color:var(--ink); font-weight:600; margin-right:4px; }
  .chip.best { border-color:var(--accent); color:var(--accent); }
  .chip.best b { color:var(--accent); }
  .chip.out { text-decoration:line-through; opacity:.6; }
  .actions { display:flex; gap:8px; flex-wrap:wrap; }
  button { font:inherit; font-weight:600; border-radius:10px; padding:9px 14px; cursor:pointer; border:1px solid var(--line); background:transparent; color:var(--ink); }
  button.primary { background:var(--accent); border-color:var(--accent); color:#fff; }
  button:disabled { opacity:.6; cursor:default; }
  .foot { color:var(--dim); font-size:12px; margin:0; }
  .empty { color:var(--dim); margin:0; }
</style>
</head>
<body>
<div class="card" id="card"><p class="empty">Working out your size…</p></div>
<script type="module">
import { App, applyDocumentTheme } from '${EXT_APPS_URL}';

const card = document.getElementById('card');
const esc = (v) => String(v == null ? '' : v).replace(/[&<>"']/g, (c) => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
const up = (s) => String(s).toUpperCase();
let data = null;

const app = new App({ name: 'TryOn size card', version: '1.0.0' }, {});

function theme(ctx) {
  const t = ctx && ctx.theme;
  if (t === 'dark' || t === 'light') { document.documentElement.dataset.theme = t; try { applyDocumentTheme(t); } catch (e) {} }
}

function render(d) {
  data = d;
  if (!d || !d.answer) {
    card.innerHTML = '<p class="empty">' + esc((d && d.message) || 'No size to show.') + '</p>';
    return;
  }
  const a = d.answer, p = d.product || {};
  const order = (p.sizes || []).map((s) => s.label);
  const chips = (p.sizes || []).map((s) => {
    const score = Math.round((a.scores || {})[s.label] || 0);
    const cls = ['chip', s.label === a.size ? 'best' : '', s.available ? '' : 'out'].join(' ');
    return '<span class="' + cls + '"><b>' + esc(up(s.label)) + '</b>' + score + '%</span>';
  }).join('');
  let note = '';
  if (a.soldOut) note = up(a.size) + ' is sold out.' + (a.nextInStock ? ' Next best in stock: ' + up(a.nextInStock) + ' (' + Math.round(a.scores[a.nextInStock] || 0) + '% match).' : ' None of the sizes in stock is likely to fit you.');
  else if (a.between) note = 'You are between ' + up(a.size) + ' and ' + up(a.between) + '.';
  card.innerHTML =
    '<div class="top">' +
      '<div class="img" style="' + (p.image ? "background-image:url('" + esc(p.image) + "')" : '') + '"></div>' +
      '<div><p class="title">' + esc(p.title) + '</p><p class="store">' + esc(p.storeName || p.host || '') + (p.price ? ' · ' + esc(p.price) + ' ' + esc(p.currency || '') : '') + '</p></div>' +
    '</div>' +
    '<div class="result">' +
      '<div class="ring" style="--p:' + Math.round(a.match || 0) + '"><div><div><div class="size">' + esc(up(a.size)) + '</div><div class="pct">' + Math.round(a.match || 0) + '% match</div></div></div></div>' +
      '<div><p class="lead">' + (a.basis === 'measured' ? 'Your size, from your fit passport' : 'Your estimated size') + '</p><p class="why">' + esc(a.reasoning) + '</p></div>' +
    '</div>' +
    (note ? '<p class="note">' + esc(note) + '</p>' : '') +
    (chips ? '<div class="sizes">' + chips + '</div>' : '') +
    '<div class="actions">' +
      '<button class="primary" id="open">Open product</button>' +
      '<button id="save">Save to wishlist</button>' +
    '</div>' +
    '<p class="foot">' + (a.basis === 'measured' ? 'Sized from your measured fit passport.' : 'Estimated from your answers. A photo fit passport on tryon.global makes it exact.') + ' TryOn</p>';
  document.getElementById('open').onclick = () => app.openLink({ url: p.url }).catch(() => {});
  const save = document.getElementById('save');
  save.onclick = async () => {
    save.disabled = true;
    try {
      const r = await app.callServerTool({ name: 'save_to_wishlist', arguments: { product_url: p.url } });
      save.textContent = r && r.isError ? 'Could not save' : 'Saved';
    } catch (e) { save.textContent = 'Could not save'; save.disabled = false; }
  };
}

app.ontoolresult = (params) => {
  if (params && params.isError) { render({ message: ((params.content || [])[0] || {}).text || 'Something went wrong.' }); return; }
  render(params && params.structuredContent);
};
app.onhostcontextchanged = (ctx) => theme(ctx);
await app.connect();
theme(app.getHostContext());
</script>
</body>
</html>`;
