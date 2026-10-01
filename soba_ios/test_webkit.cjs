// Run after build.py with Playwright/WebKit installed. All remote requests fail.
const {webkit} = require('playwright');
const fs = require('node:fs'), http = require('node:http'), path = require('node:path'), assert = require('node:assert/strict');
const root = path.join(__dirname, 'Game');
const server = http.createServer((req, res) => {
  const file = path.join(root, req.url === '/' ? 'index.html' : req.url.split('?')[0]);
  if (!file.startsWith(root + path.sep)) { res.writeHead(403).end(); return; }
  try {
    const bytes = fs.readFileSync(file);
    res.setHeader('Content-Type', ({'.html':'text/html', '.js':'application/javascript', '.wasm':'application/wasm', '.json':'application/json'})[path.extname(file)] || 'application/octet-stream');
    res.end(bytes);
  } catch { res.writeHead(404).end(); }
});
(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const origin = `http://127.0.0.1:${server.address().port}`;
  const browser = await webkit.launch();
  const remote = [], failures = [];
  let snapshot = '';
  try {
    for (let iteration = 0; iteration < 2; iteration++) {
      const context = await browser.newContext({viewport:{width:844,height:390}, isMobile:true, hasTouch:true});
      const page = await context.newPage();
      await page.exposeFunction('captureNative', message => { if (message.kind === 'save') snapshot = message.snapshot; });
      await page.addInitScript(initial => {
        window.sobaIOSInitialSave = initial;
        window.webkit = {messageHandlers:{game:{postMessage:message => window.captureNative(message)}}};
      }, Buffer.from(snapshot).toString('base64'));
      await page.addInitScript(fs.readFileSync(path.join(__dirname, 'bridge.js'), 'utf8'));
      await page.route('**/*', route => {
        const url = route.request().url();
        if (!url.startsWith(origin + '/') && !url.startsWith('blob:')) {
          remote.push(url); return route.abort();
        }
        return route.continue();
      });
      page.on('pageerror', error => failures.push(String(error)));
      await page.goto(origin);
      await page.locator('#boot-start').click();
      await page.waitForFunction(() => document.querySelector('#boot-status').hidden, null, {timeout:90000});
      const canvas = page.locator('#canvas'), box = await canvas.boundingBox();
      assert(Math.abs(box.width / box.height - 1.6) < .01, 'Canvas must retain the game aspect ratio');
      if (iteration === 0) {
        // A real touch on the welcome button must reach pygame and save the world.
        await page.touchscreen.tap(box.x + box.width * .5, box.y + box.height * .794);
        for (let count = 0; count < 30 && !snapshot; count++) await page.waitForTimeout(100);
        assert(snapshot, 'Welcome touch must create a native save');
        const data = JSON.parse(snapshot);
        assert.equal(data.version, 10);
        assert.equal(data.cash, 10000000);
        // Persist a unique value to prove a fresh WebKit context reads the native save.
        data.cash = 9876543; snapshot = JSON.stringify(data);
        await page.getByRole('button', {name:'Phóng to', exact:true}).click();
        assert((await canvas.boundingBox()).width > box.width * 1.4);
        await page.getByRole('button', {name:'Xem toàn quán', exact:true}).click();
      } else {
        const restored = snapshot; snapshot = '';
        await page.evaluate(() => window.sobaIOSCommands.push({kind:'save'}));
        for (let count = 0; count < 30 && !snapshot; count++) await page.waitForTimeout(100);
        assert.equal(JSON.parse(snapshot).cash, JSON.parse(restored).cash, 'Restore must survive a new browser data store');
      }
      await context.close();
    }
    assert.deepEqual(remote, [], 'Offline game must not fetch any remote code or resources');
    assert.deepEqual(failures, []);
    console.log('PASS: offline WebKit boot, aspect ratio, real touch, zoom, native save and restore');
  } finally { await browser.close(); server.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; server.close(); });
