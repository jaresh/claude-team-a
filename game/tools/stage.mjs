// Deploys the game to the local staging server and smoke-tests the deployed copy.
//
//   npm run stage -- <name>        e.g. npm run stage -- shop
//
// Copies game/ to $STAGING_DIR/<name>/game/ (default: <main checkout>-staging, shared by every
// worktree of the repo), makes
// sure a static server serves $STAGING_DIR on port $STAGING_PORT (default 8100; started in the
// background if nothing listens there), runs game/tools/smoke.mjs against the deployed URL and
// prints it. Exits 1 if the copy or the smoke test fails. Undo: rm -r $STAGING_DIR/<name>.
import { cp, mkdir, rm, writeFile } from 'node:fs/promises';
import { spawn, spawnSync } from 'node:child_process';
import { basename, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const name = process.argv[2];
if (!name || !/^[A-Za-z0-9._-]+$/.test(name)) {
  console.error('usage: npm run stage -- <name>   (letters, digits, . _ -)');
  process.exit(2);
}
const repo = fileURLToPath(new URL('../..', import.meta.url)).replace(/\/$/, '');
const common = spawnSync('git', ['-C', repo, 'rev-parse', '--path-format=absolute', '--git-common-dir'],
                         { encoding: 'utf8' }).stdout.trim();
const main = common ? dirname(common) : repo;   // the main checkout, for worktrees too
const dir = process.env.STAGING_DIR || join(dirname(main), basename(main) + '-staging');
const port = Number(process.env.STAGING_PORT || 8100);
const base = `http://127.0.0.1:${port}`;

const up = async () => fetch(base + '/').then(() => true, () => false);
await mkdir(dir, { recursive: true });
await writeFile(join(dir, '.staging-root'), dir);   // tells which directory a server serves
if (!(await up())) {
  // Detached, in its own session, so it outlives this command and the Claude session.
  spawn('python3', ['-m', 'http.server', String(port), '--bind', '127.0.0.1', '--directory', dir],
        { detached: true, stdio: 'ignore' }).unref();
  for (let i = 0; i < 50 && !(await up()); i++) await new Promise((ok) => setTimeout(ok, 100));
}
const served = await fetch(base + '/.staging-root').then((r) => (r.ok ? r.text() : ''), () => '');
if (served !== dir) {
  console.error(`Port ${port} serves another directory (${served || 'not a staging server'}), not ${dir}. `
    + 'Stop that server or set STAGING_PORT; nothing was deployed.');
  process.exit(1);
}
await rm(join(dir, name), { recursive: true, force: true });
await mkdir(join(dir, name), { recursive: true });
await cp(join(repo, 'game'), join(dir, name, 'game'), { recursive: true });
const url = `${base}/${name}/game/`;
const res = await fetch(url).catch(() => null);
if (!res || !res.ok) {
  console.error(`Staging server did not serve ${url}`);
  process.exit(1);
}
const smoke = spawnSync('node', [join(repo, 'game/tools/smoke.mjs'), join(dir, name, 'smoke.png'),
  '--url', url, ...process.argv.slice(3)], { encoding: 'utf8' });
const ok = smoke.status === 0;
console.log(`${ok ? 'Staged' : 'Staged, but the smoke test FAILED'}: ${url}`);
console.log(`Screenshot: ${join(dir, name, 'smoke.png')}. Undo: rm -r ${join(dir, name)}`);
if (!ok) console.log(smoke.stdout.slice(-800));
process.exit(ok ? 0 : 1);
