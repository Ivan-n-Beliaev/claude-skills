const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
  const [html, out, w, h, sf] = process.argv.slice(2);
  const width = parseInt(w, 10), height = parseInt(h, 10);
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.setViewport({ width, height, deviceScaleFactor: sf ? parseFloat(sf) : 1 });
  await page.goto('file://' + path.resolve(html), { waitUntil: 'networkidle0' });
  await page.screenshot({ path: out, type: 'png' });
  await browser.close();
  console.log('wrote', out);
})();
