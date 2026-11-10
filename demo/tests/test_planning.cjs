// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

const fs = require('fs');
const path = require('path');
const { chromium } = require('/home/gabriel-moraes/Documentos/SYNAPSE_CORE/node_modules/playwright');

const SCREENSHOT_DIR = '/tmp/carina_test_planning';

async function test() {
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

  // Switch to Planning (x=290, y=105)
  console.log('Switching to Planning tab...');
  await page.mouse.click(290, 105);
  await page.waitForTimeout(3000);

  // Click "Analisar Infraestrutura" (x=108, y=1042)
  console.log('Clicking Analisar Infraestrutura at (x=108, y=1042)...');
  await page.mouse.click(108, 1042);
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_planning_calculating.png') });

  // Wait for AI response (feed takes ~2.5s)
  await page.waitForTimeout(3500);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_planning_analyzed.png') });

  await browser.close();
  console.log('Done test planning!');
}

test().catch(err => {
  console.error(err);
  process.exit(1);
});
