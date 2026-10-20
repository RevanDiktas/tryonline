// Minify src/*.js into the extension's assets and fail if any asset is over Shopify's 10 KB
// app-block script limit. Run: npm run build (deploy.sh runs it first).
import { execFileSync } from 'node:child_process';
import { readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const LIMIT = 10 * 1024;
const here = new URL('.', import.meta.url).pathname;
const assets = join(here, 'extensions/size-widget/assets');

for (const f of readdirSync(join(here, 'src')).filter((f) => f.endsWith('.js'))) {
  execFileSync('npx', ['--yes', 'terser@5', join(here, 'src', f), '-c', '-m', '-o', join(assets, f)], { stdio: 'inherit' });
}
let over = false;
for (const f of readdirSync(assets).filter((f) => f.endsWith('.js'))) {
  const size = statSync(join(assets, f)).size;
  console.log(`${f}: ${size} B`);
  if (size > LIMIT) { console.error(`  over the ${LIMIT} B limit`); over = true; }
}
process.exit(over ? 1 : 0);
