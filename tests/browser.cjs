/* Real browser, real readers, real local model. No intercepted API responses. */
const { chromium } = require('playwright');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const base = process.env.RFQ_BASE_URL || 'http://127.0.0.1:8765';
(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.RFQ_BROWSER ? {channel: process.env.RFQ_BROWSER} : {}) });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 }, acceptDownloads: true });
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  const reports = [], created = [];
  try {
    await page.goto(base);
    await page.waitForFunction(() => document.getElementById('history').textContent.length > 0);
    await page.getByRole('button', { name: /Extract product/ }).click();
    assert.match(await page.locator('#message').textContent(), /Select a document/);
    for (const filename of ['scan.pdf', 'broken.pdf']) {
      await page.locator('#file').setInputFiles(path.join(root, 'data/browser-inputs', filename));
      await page.getByRole('button', { name: /Extract product/ }).click();
      await page.waitForFunction(() => !document.getElementById('analyze').disabled);
      const text = await page.locator('#message').textContent();
      assert.match(text, filename === 'scan.pdf' ? /OCR/ : /corrupted/);
      reports.push({ filename, error: text });
    }
    for (const extension of ['txt', 'pdf', 'docx', 'xlsx']) {
      await page.locator('#file').setInputFiles(path.join(root, 'data/browser-inputs', `requirement.${extension}`));
      const response = page.waitForResponse(res => res.url() === `${base}/api/analyze` && res.request().method() === 'POST', { timeout: 260000 });
      await page.getByRole('button', { name: /Extract product/ }).click();
      const res = await response;
      const record = await res.json();
      assert.equal(res.status(), 201, JSON.stringify(record));
      created.push(record.id);
      await page.waitForFunction(() => !document.getElementById('analyze').disabled);
      assert.equal(await page.locator('.line').count(), 4);
      assert.equal(record.status, 'needs_review');
      for (const [i, line] of record.lines.entries()) {
        assert.equal(line.line_number, String(i + 1));
        assert.equal(line.quantity, [120, 200, 40, null][i]);
        assert.equal(line.unit, ['pcs', 'm', 'pcs', null][i]);
        assert.equal(line.category, ['Fasteners', 'Electrical', 'Pipes and fittings', 'Fasteners'][i]);
        assert.equal(line.approved, false);
      }
      reports.push({ extension, id: record.id, elapsed_seconds: record.analysis.elapsed_seconds, checked_positions: 4, findings: record.analysis.validation_findings });
    }
    const latestId = created.at(-1);
    const cards = page.locator('.line');
    // The source's missing quantity must prevent approval, then permit a human correction.
    await cards.nth(3).locator('[data-key=approved]').check();
    await page.getByRole('button', { name: 'Save review', exact: true }).click();
    await page.waitForFunction(() => !document.getElementById('save').disabled);
    assert.match(await page.locator('#message').textContent(), /positive quantity/);
    await cards.nth(3).locator('[data-key=quantity]').fill('25');
    await cards.nth(3).locator('[data-key=unit]').fill('pcs');
    for (let i = 0; i < 4; i++) await cards.nth(i).locator('[data-key=approved]').check();
    await page.getByRole('button', { name: 'Save review', exact: true }).click();
    await page.waitForFunction(() => document.getElementById('status').textContent === 'REVIEWED');
    await page.reload();
    await page.waitForFunction(() => document.querySelectorAll('.history-item').length > 0);
    await page.locator('.history-item').first().click();
    await page.waitForFunction(() => document.getElementById('status').textContent === 'REVIEWED');
    assert.equal(await page.locator('.line').nth(3).locator('[data-key=quantity]').inputValue(), '25');
    const downloadPromise = page.waitForEvent('download');
    await page.getByText('Download saved JSON', { exact: true }).click();
    const download = await downloadPromise;
    const downloadedPath = path.join(root, 'data', 'browser-review-export.json');
    await download.saveAs(downloadedPath);
    const saved = JSON.parse(fs.readFileSync(downloadedPath, 'utf8'));
    assert.equal(saved.id, latestId);
    assert.equal(saved.status, 'reviewed');
    assert.equal(saved.lines[3].quantity, 25);
    // Add a source-backed missing position without modifying original IDs.
    await page.getByRole('button', { name: 'Add a missed line' }).click();
    const added = page.locator('.line').last();
    await added.locator('[data-key=line_number]').fill('5');
    await added.locator('[data-key=description]').fill('Manually split cable position');
    await added.locator('[data-key=source_quote]').fill('2. Copper cable 4mm2, 200 m.');
    await page.getByRole('button', { name: 'Save review', exact: true }).click();
    await page.waitForFunction(() => !document.getElementById('save').disabled);
    assert.match(await page.locator('#message').textContent(), /Review saved/);
    assert.equal(await page.locator('.line').count(), 5);
    assert.equal(await page.locator('#status').textContent(), 'NEEDS REVIEW');
    await page.screenshot({path: path.join(root, 'data', 'review-desktop.png'), fullPage: true});
    await page.setViewportSize({width: 390, height: 844});
    assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), true, 'Mobile overflow');
    await page.screenshot({path: path.join(root, 'data', 'review-mobile.png'), fullPage: true});
    assert.deepEqual(errors, []);
    const config = await (await page.request.get(`${base}/api/config`)).json();
    const denied = await page.request.post(`${base}/api/analyze`, {data: {text:'1. Bolt 2 pcs'}});
    assert.equal(denied.status(), 403);
    for (const id of created) {
      const deletion = await page.request.post(`${base}/api/requirements/${id}/delete`, {headers: {'X-Workbench-Token': config.token, Origin: base}, data: {}});
      assert.equal(deletion.status(), 200);
    }
    const missing = await page.request.get(`${base}/api/requirements/${latestId}`);
    assert.equal(missing.status(), 404);
    fs.writeFileSync(path.join(root, 'data', 'browser-test-report.json'), JSON.stringify({passed:true, reports, review_save_reload_export_manual_add_delete:true, mobile_overflow:false, page_errors:errors}, null, 2));
    console.log(JSON.stringify({passed:true, reports, review_save_reload_export_manual_add_delete:true, mobile_overflow:false}, null, 2));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
