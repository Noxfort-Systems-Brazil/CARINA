// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

const fs = require('fs');
const path = require('path');
const { chromium } = require('/home/gabriel-moraes/Documentos/SYNAPSE_CORE/node_modules/playwright');

const SCREENSHOT_DIR = '/tmp/carina_test_tabs';

async function test() {
  if (!fs.existsSync(SCREENSHOT_DIR)) {
    fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
  }

  const browser = await chromium.launch({
    headless: true,
    args: ['--hide-scrollbars', '--disable-gpu', '--no-sandbox']
  });

  const page = await browser.newPage({
    viewport: { width: 1920, height: 1080 }
  });

  console.log('Accessing CARINA...');
  await page.goto('http://127.0.0.1:8550', { waitUntil: 'load' });
  await page.waitForTimeout(6000);

  // Initial: should be on Dashboard
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01_dashboard.png') });
  console.log('Screenshot 01: Dashboard');

  // Switch to Planning (x=290, y=105)
  console.log('Switching to Planning tab at (x=290, y=105)...');
  await page.mouse.click(290, 105);
  await page.waitForTimeout(3000);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_planning.png') });
  console.log('Screenshot 02: Planning');

  // Switch to Diagnostics (x=490, y=105)
  console.log('Switching to Diagnostics tab at (x=490, y=105)...');
  await page.mouse.click(490, 105);
  await page.waitForTimeout(3000);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_diagnostics.png') });
  console.log('Screenshot 03: Diagnostics');

  // Switch back to Dashboard (x=100, y=105)
  console.log('Switching back to Dashboard at (x=100, y=105)...');
  await page.mouse.click(100, 105);
  await page.waitForTimeout(3000);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '04_dashboard_back.png') });
  console.log('Screenshot 04: Dashboard Back');

  await browser.close();
}

test().catch(err => {
  console.error(err);
  process.exit(1);
});
