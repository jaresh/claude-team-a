// Browser smoke test (lead-only): serves the repo, opens the game at phone width in headless
// Chromium, presses keys and taps buttons, and checks the page. Exits 1 when a check fails.
//
//   node game/tools/smoke.mjs [screenshot.png]
//
// Needs playwright-core and its Chromium. Set PLAYWRIGHT_CORE to playwright-core's index.mjs if
// the default path below does not exist on this machine.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { extname, join, normalize } from 'node:path';
import { fileURLToPath } from 'node:url';

const PW = process.env.PLAYWRIGHT_CORE
  || '/root/.npm/_npx/da8a348eb3051058/node_modules/playwright-core/index.mjs';
const { chromium } = await import(PW);
const root = fileURLToPath(new URL('../..', import.meta.url));
const types = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript', '.css': 'text/css' };

const server = createServer(async (req, res) => {
  const path = normalize(join(root, decodeURIComponent(new URL(req.url, 'http://x').pathname)));
  const file = path.endsWith('/') ? join(path, 'index.html') : path;
  try {
    const body = await readFile(file);
    res.writeHead(200, { 'content-type': types[extname(file)] || 'application/octet-stream' });
    res.end(body);
  } catch {
    res.writeHead(404);
    res.end();
  }
});
await new Promise((ok) => server.listen(0, '127.0.0.1', ok));
const url = `http://127.0.0.1:${server.address().port}/game/?seed=42`;

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 360, height: 780 }, deviceScaleFactor: 2, hasTouch: true });
const errors = [];
page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()); });
page.on('pageerror', (e) => errors.push('page: ' + e.message));
page.on('requestfailed', (r) => errors.push('request: ' + r.url()));

await page.goto(url);
await page.waitForTimeout(400);
const turn = () => page.evaluate(() => (document.body.innerText.match(/TURN\s+(\d+)/i) || [])[1]);
const turnBefore = await turn();
for (const key of ['ArrowRight', 'ArrowRight', 'ArrowDown', 'l', 'j', 'u', '.', 'g', 'd', 's']) {
  await page.keyboard.press(key);
}
for (const button of (await page.$$('button')).slice(0, 4)) {
  await button.tap().catch((e) => errors.push('tap: ' + e.message));
}
await page.waitForTimeout(200);
const layout = await page.evaluate(() => {
  const canvas = document.querySelector('canvas');
  return {
    scrollWidth: document.documentElement.scrollWidth,
    innerWidth,
    canvas: canvas && { ...canvas.dataset, w: canvas.clientWidth, h: canvas.clientHeight },
    inventory: !!document.getElementById('inventory'),
  };
});
const turnAfter = await turn();
await page.screenshot({ path: process.argv[2] || 'smoke.png', fullPage: true });
await browser.close();
server.close();

const checks = {
  noErrors: errors.length === 0,
  noSideScroll: layout.scrollWidth <= layout.innerWidth,
  inputWorks: Number(turnAfter) > Number(turnBefore),
  cellAtLeast16: Number(layout.canvas?.cell) >= 16,
  inventoryPanel: layout.inventory,
};
console.log(JSON.stringify({ checks, errors, layout, turns: [turnBefore, turnAfter] }, null, 1));
process.exit(Object.values(checks).every(Boolean) ? 0 : 1);
