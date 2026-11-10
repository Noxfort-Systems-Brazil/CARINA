// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

const fs = require('fs');
const path = require('path');
const { chromium } = require('/home/gabriel-moraes/Documentos/SYNAPSE_CORE/node_modules/playwright');

const SCREENSHOT_DIR = '/tmp/carina_test_street';

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

  // 1. Click traffic light at (775, 315)
  console.log('Clicking semaphore at (775, 315)...');
  await page.mouse.click(775, 315);
  await page.waitForTimeout(2000);

  // Click Alert Mode (Colocar em Alerta) (1620, 940)
  console.log('Clicking Colocar em Alerta at (1620, 940)...');
  await page.mouse.click(1620, 940);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01_semaphore_alert.png') });

  // Click Deactivate Traffic Light (Desativar Semáforo) (1810, 940)
  console.log('Clicking Desativar Semáforo at (1810, 940)...');
  await page.mouse.click(1810, 940);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_semaphore_disabled.png') });

  // Close semaphore panel (1760, 995)
  console.log('Closing semaphore panel at (1760, 995)...');
  await page.mouse.click(1760, 995);
  await page.waitForTimeout(1500);

  // 2. Click road at (900, 595) or (838, 600)
  console.log('Clicking street at (900, 595)...');
  await page.mouse.click(900, 595);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_street_clicked.png') });

  // 3. Switch to Planning (290, 105)
  console.log('Switching to Planning (290, 105)...');
  await page.mouse.click(290, 105);
  await page.waitForTimeout(3000);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '04_planning_switched.png') });

  // 4. Switch to Diagnostics (490, 105)
  console.log('Switching to Diagnostics (490, 105)...');
  await page.mouse.click(490, 105);
  await page.waitForTimeout(3000);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '05_diagnostics_switched.png') });

  await browser.close();
  console.log('Test street click finished successfully!');
}

test().catch(err => {
  console.error(err);
  process.exit(1);
});
