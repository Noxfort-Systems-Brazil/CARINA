// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

const fs = require('fs');
const path = require('path');
const { chromium } = require('/home/gabriel-moraes/Documentos/SYNAPSE_CORE/node_modules/playwright');

const SCREENSHOT_DIR = '/tmp/carina_test_coords';

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

  // 1. Diagnostics Tab (x=400, y=90)
  console.log('Switching to Diagnostics tab...');
  await page.mouse.click(400, 90);
  await page.waitForTimeout(2000);

  // 2. MFD: Sub-tab 0 is active by default. Click "Gerar Relatório de Otimização MFD" (x=155, y=242)
  console.log('Clicking Gerar Relatório MFD (x=155, y=242)...');
  await page.mouse.click(155, 242);
  await page.waitForTimeout(3000); // Wait for mock generation
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '01_mfd_chart_loaded.png') });

  // View MFD SLM Text Report (x=300, y=335)
  console.log('Viewing MFD SLM Text Report (x=300, y=335)...');
  await page.mouse.click(300, 335);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '02_mfd_text_loaded.png') });

  // 3. Switch to XAI sub-tab (x=295, y=165)
  console.log('Switching to XAI sub-tab (x=295, y=165)...');
  await page.mouse.click(295, 165);
  await page.waitForTimeout(2000);

  // Click "Executar Análise XAI" (x=480, y=248)
  console.log('Clicking Executar Análise XAI (x=480, y=248)...');
  await page.mouse.click(480, 248);
  await page.waitForTimeout(3500); // Wait for mock generation
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '03_xai_chart_loaded.png') });

  // View XAI Text Report (x=350, y=355)
  console.log('Viewing XAI Text Report (x=350, y=355)...');
  await page.mouse.click(350, 355);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '04_xai_text_loaded.png') });

  // 4. Switch to Audit Logs sub-tab (x=490, y=165)
  console.log('Switching to Audit Logs sub-tab (x=490, y=165)...');
  await page.mouse.click(490, 165);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '05_audit_table_loaded.png') });

  // 5. Open Settings Dialog via gear icon (x=1890, y=25)
  console.log('Opening Settings Dialog (x=1890, y=25)...');
  await page.mouse.click(1890, 25);
  await page.waitForTimeout(2500);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '06_settings_general.png') });

  // Click Advanced (IA) tab inside Settings (x=730, y=185)
  console.log('Clicking Avançado (IA) in Settings (x=730, y=185)...');
  await page.mouse.click(730, 185);
  await page.waitForTimeout(1500);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '07_settings_advanced.png') });

  // Close Settings dialog
  await page.keyboard.press('Escape');
  await page.waitForTimeout(1500);

  // 6. Return to Dashboard (x=50, y=95)
  console.log('Returning to Dashboard Operacional (x=50, y=95)...');
  await page.mouse.click(50, 95);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(SCREENSHOT_DIR, '08_dashboard_return.png') });

  await browser.close();
  console.log('✅ Coordinate and tab verification successfully completed!');
}

test().catch(err => {
  console.error('Error during test:', err);
  process.exit(1);
});
