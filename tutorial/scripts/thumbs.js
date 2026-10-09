// Render templates/thumbs.html to thumb_a/b/c.png (+ _zones proofs).
//
//   node thumbs.js <dir> [--zones]
//
// Needs puppeteer: npm install puppeteer
const puppeteer = require('puppeteer');

(async () => {
  const dir = process.argv[2];
  const zones = process.argv.includes('--zones');
  const b = await puppeteer.launch({
    args: ['--allow-file-access-from-files', '--font-render-hinting=none'],
  });
  const p = await b.newPage();
  await p.setViewport({ width: 1280, height: 720, deviceScaleFactor: 1 });
  await p.goto('file://' + dir + '/thumbs.html', { waitUntil: 'networkidle0' });

  for (const id of ['a', 'b', 'c']) {
    const el = await p.$('#' + id);
    await el.screenshot({ path: `${dir}/thumb_${id}.png` });
  }

  if (zones) {
    await p.evaluate(() => document.body.classList.add('zones'));
    for (const id of ['a', 'b', 'c']) {
      const el = await p.$('#' + id);
      await el.screenshot({ path: `${dir}/thumb_${id}_zones.png` });
    }
  }
  await b.close();
  console.log('wrote thumb_a/b/c.png' + (zones ? ' + _zones proofs' : '') + ' in ' + dir);
})();
