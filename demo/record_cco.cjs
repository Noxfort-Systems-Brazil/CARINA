// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

let playwright;
try {
  playwright = require('playwright');
} catch (e) {
  playwright = require('/home/gabriel-moraes/Documentos/SYNAPSE_CORE/node_modules/playwright');
}
const { chromium } = playwright;

const OUTPUT_DIR = path.join(__dirname, 'recordings');
const FINAL_MP4 = path.join(OUTPUT_DIR, 'carina_cco_apresentacao.mp4');
const APP_URL = 'http://127.0.0.1:2201/cco/';

async function main() {
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  const SCENE_DIR = path.join(OUTPUT_DIR, 'scenes');
  if (!fs.existsSync(SCENE_DIR)) {
    fs.mkdirSync(SCENE_DIR, { recursive: true });
  }

  console.log('===============================================================');
  console.log('🚀 INICIANDO GRAVAÇÃO DO VIDEOWALL CCO CARINA (1080p @ 60FPS)');
  console.log('===============================================================');

  const browser = await chromium.launch({
    headless: true,
    args: ['--hide-scrollbars', '--disable-gpu', '--no-sandbox']
  });

  const context = await browser.newContext({
    recordVideo: {
      dir: OUTPUT_DIR,
      size: { width: 1920, height: 1080 }
    },
    viewport: { width: 1920, height: 1080 }
  });

  const page = await context.newPage();

  console.log(`🌐 Conectando ao Videowall CCO em ${APP_URL}...`);
  await page.goto(APP_URL, { waitUntil: 'load' });

  // 1. Wait for topology and SSE connection
  console.log('⏳ Sincronizando malha viária vetorial e conexão SSE...');
  await page.waitForTimeout(4000);

  // -------------------------------------------------------------
  // SCENE 1: Command Center Videowall Overview
  // -------------------------------------------------------------
  console.log('\n📍 [CENA 1] Centro de Controle Operacional: Visão Panorâmica do Videowall...');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: path.join(SCENE_DIR, 'cco_01_overview.png') });

  // -------------------------------------------------------------
  // SCENE 2: Live Emergency Fleet Telemetry & Siren Animation
  // -------------------------------------------------------------
  console.log('\n🚨 [CENA 2] Monitoramento de Frota de Emergência (EVP) e Corredores Verdes...');
  await page.waitForTimeout(3500);
  await page.screenshot({ path: path.join(SCENE_DIR, 'cco_02_fleet_in_action.png') });

  // -------------------------------------------------------------
  // SCENE 3: Quick Filter by Corporation (SAMU)
  // -------------------------------------------------------------
  console.log('\n🚑 [CENA 3] Filtrando viaturas por Corporação (SAMU)...');
  const samuBtn = page.locator('button[title="Filtrar viaturas do SAMU"]');
  if (await samuBtn.count() > 0) {
    await samuBtn.click();
    await page.waitForTimeout(2500);
    await page.screenshot({ path: path.join(SCENE_DIR, 'cco_03_filter_samu.png') });
    console.log('🔄 [CENA 3] Restaurando filtro global de todas as viaturas...');
    await samuBtn.click();
    await page.waitForTimeout(1500);
  } else {
    console.log('⚠️ [CENA 3] Botão de filtro SAMU não encontrado via seletor, mantendo visão ampla.');
  }

  // -------------------------------------------------------------
  // SCENE 4: Quick Search & Inspection Cycling (SAMU, BOMB, POLICIA)
  // -------------------------------------------------------------
  async function searchAndInspectVehicle(vId, label, screenshotName) {
    console.log(`\n🔍 [CENA 4] Busca Inteligente: Selecionando ${vId} (${label})...`);
    const searchBtn = page.locator('button[title="Busca Rápida de Viaturas e Cruzamentos"]');
    if (await searchBtn.count() > 0) {
      await searchBtn.click();
    } else {
      await page.keyboard.press('/');
    }
    await page.waitForTimeout(1000);

    const searchInput = page.locator('input[placeholder*="Buscar"]');
    if (await searchInput.count() > 0) {
      await searchInput.fill(vId);
      await page.waitForTimeout(1200);

      const searchResult = page.locator('div[class*="cursor-pointer"]').first();
      if (await searchResult.count() > 0) {
        console.log(`🎯 [CENA 4] Focando câmera (flyTo) e inspecionando ${vId}...`);
        await searchResult.click();
        await page.waitForTimeout(3000);
        await page.screenshot({ path: path.join(SCENE_DIR, screenshotName) });
      }
    }
  }

  // 1. Inspeciona SAMU-01
  await searchAndInspectVehicle('SAMU-01', 'Ambulância UTI Avançada', 'cco_04_inspect_samu.png');

  // 2. Inspeciona BOMBEIRO-01
  await searchAndInspectVehicle('BOMBEIRO-01', 'Auto-Bomba Salvamento', 'cco_04_inspect_bombeiro.png');

  // 3. Inspeciona POLICIA-01
  await searchAndInspectVehicle('POLICIA-01', 'Viatura Ronda Ostensiva', 'cco_04_inspect_policia.png');

  // -------------------------------------------------------------
  // SCENE 5: Vehicle Telemetry & Inspection Bottom Sheet Closure
  // -------------------------------------------------------------
  console.log('\n📋 [CENA 5] Fechando Bottom Sheet de inspeção para visão panorâmica...');
  await page.keyboard.press('Escape');
  await page.waitForTimeout(1500);

  // -------------------------------------------------------------
  // SCENE 6: Theme Toggle (Dark Command Center ↔ Cartographic Day Mode)
  // -------------------------------------------------------------
  console.log('\n🌓 [CENA 6] Alternando Tema do Videowall para Modo Diurno Cartográfico (#F7F7F7)...');
  const themeBtn = page.locator('button[title*="Tema"]');
  if (await themeBtn.count() > 0) {
    await themeBtn.click();
    await page.waitForTimeout(2500);
    await page.screenshot({ path: path.join(SCENE_DIR, 'cco_06_theme_light.png') });

    console.log('🌙 [CENA 6] Retornando ao Modo Noturno Sala de Comando (#020617)...');
    await themeBtn.click();
    await page.waitForTimeout(2000);
    await page.screenshot({ path: path.join(SCENE_DIR, 'cco_06_theme_dark.png') });
  }

  // -------------------------------------------------------------
  // SCENE 7: Map Exploration - Zoom In, Pan and Reset View
  // -------------------------------------------------------------
  console.log('\n🔭 [CENA 7] Explorando Malha Viária: Aproximação (Zoom In)...');
  const zoomInBtn = page.locator('button[title="Aproximar (+)"]');
  if (await zoomInBtn.count() > 0) {
    await zoomInBtn.click();
    await page.waitForTimeout(800);
    await zoomInBtn.click();
    await page.waitForTimeout(1500);
  }

  console.log('🧭 [CENA 7] Pan cinemático pelo corredor da Av. Dom Pedro II...');
  await page.mouse.move(960, 540);
  await page.mouse.down();
  await page.mouse.move(860, 480, { steps: 15 });
  await page.mouse.up();
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(SCENE_DIR, 'cco_07_zoom_pan.png') });

  console.log('🔄 [CENA 7] Recentralizando visualização global da cidade...');
  const resetBtn = page.locator('button[title="Recentralizar Vista (0)"]');
  if (await resetBtn.count() > 0) {
    await resetBtn.click();
    await page.waitForTimeout(2500);
  }

  // -------------------------------------------------------------
  // SCENE 8: Full Panoramic Wrap-up
  // -------------------------------------------------------------
  console.log('\n🏁 [CENA 8] Encerramento elegante do Videowall CCO com todas as camadas ativas...');
  await page.waitForTimeout(3000);
  await page.screenshot({ path: path.join(SCENE_DIR, 'cco_08_final_panoramic.png') });

  // Context teardown and video encoding
  console.log('\n💾 Salvando buffer de vídeo do Videowall CCO...');
  const video = page.video();
  await page.close();
  await context.close();
  await browser.close();

  if (video) {
    const rawWebmPath = await video.path();
    console.log(`\n🎬 Gravação bruta capturada: ${rawWebmPath}`);
    console.log('⚙️ Codificando vídeo final CCO em Full HD com aceleração por hardware (NVDEC + NVENC)...');

    try {
      execSync(
        `ffmpeg -y -c:v vp8_cuvid -i "${rawWebmPath}" -c:v h264_nvenc -pix_fmt yuv420p -preset p4 -cq 20 "${FINAL_MP4}"`,
        { stdio: 'inherit' }
      );
    } catch (err) {
      console.warn('⚠️ Falha com NVDEC/NVENC, aplicando fallback via CPU libx264 fast...');
      execSync(
        `ffmpeg -y -i "${rawWebmPath}" -c:v libx264 -preset veryfast -pix_fmt yuv420p -crf 22 "${FINAL_MP4}"`,
        { stdio: 'inherit' }
      );
    }

    console.log(`\n===============================================================`);
    console.log(`🎉 VÍDEO DO VIDEOWALL CCO GERADO COM SUCESSO!`);
    console.log(`📁 Arquivo final: ${FINAL_MP4}`);
    console.log(`===============================================================\n`);
  }
}

main().catch((err) => {
  console.error('❌ Erro durante a geração do vídeo CCO:', err);
  process.exit(1);
});
