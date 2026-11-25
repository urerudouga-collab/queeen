// make_ogp.py から呼ばれ、HTMLを 1200x630 の画像にします
const { chromium } = require('playwright');
const jobs = require(process.argv[2]);
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1200, height: 630 } });
  for (const j of jobs) {
    await p.goto('file://' + j.html, { waitUntil: 'networkidle' });
    await p.evaluate(() => document.fonts.ready);
    await p.waitForTimeout(300);
    await p.screenshot({ path: j.out, type: 'jpeg', quality: 88 });
  }
  await b.close();
})();
