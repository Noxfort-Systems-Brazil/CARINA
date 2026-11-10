// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');
const { chromium } = require('/home/gabriel-moraes/Documentos/SYNAPSE_CORE/node_modules/playwright');

const OUTPUT_DIR = path.join(__dirname, 'recordings');
const FINAL_MP4 = path.join(OUTPUT_DIR, 'carina_apresentacao.mp4');
const APP_URL = 'http://127.0.0.1:8550';

async function main() {
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  console.log('===============================================================');
  console.log('🚀 INICIANDO GRAVAÇÃO CINEMATOGRÁFICA DA CARINA (1080p @ 60FPS)');
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

  console.log(`🌐 Conectando à instância Flet em ${APP_URL}...`);
  await page.goto(APP_URL, { waitUntil: 'load' });

  // 1. Wait for WebGL/CanvasKit and road network initialization
  console.log('⏳ Sincronizando malha viária e buffers de renderização...');
  await page.waitForTimeout(3500);

  const SCENE_DIR = path.join(OUTPUT_DIR, 'scenes');
  if (!fs.existsSync(SCENE_DIR)) {
    fs.mkdirSync(SCENE_DIR, { recursive: true });
  }

  // -------------------------------------------------------------
  // SCENE 1: Operational Dashboard with Live Traffic
  // -------------------------------------------------------------
  console.log('\n📍 [CENA 1] Painel Operacional: Telemetria HFT e dinâmica semafórica autônoma...');
  await page.waitForTimeout(3500);
  await page.screenshot({ path: path.join(SCENE_DIR, '01_dashboard_live.png') });

  // -------------------------------------------------------------
  // SCENE 1.1: Live Emergency Fleet Preemption & Vehicle Cycling (EVP)
  // -------------------------------------------------------------
  console.log('\n🚨 [CENA 1.1] Monitoramento de Emergência (EVP): Viaturas sobre as linhas das vias...');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(SCENE_DIR, '01_evp_fleet_live.png') });

  console.log('🚑 [CENA 1.1] Inspecionando Viatura SAMU-01 (Ambulância UTI Móvel)...');
  await page.keyboard.press('v');
  await page.waitForTimeout(2500);
  await page.screenshot({ path: path.join(SCENE_DIR, '01_evp_inspect_samu.png') });

  console.log('🚒 [CENA 1.1] Ciclando para BOMBEIRO-01 (Auto-Bomba Salvamento na Av. São João)...');
  await page.keyboard.press('v');
  await page.waitForTimeout(2500);
  await page.screenshot({ path: path.join(SCENE_DIR, '01_evp_inspect_bombeiro.png') });

  console.log('🚓 [CENA 1.1] Ciclando para POLICIA-01 (Viatura Ronda Ostensiva na Av. Dom Pedro II)...');
  await page.keyboard.press('v');
  await page.waitForTimeout(2500);
  await page.screenshot({ path: path.join(SCENE_DIR, '01_evp_inspect_policia.png') });

  console.log('✖️ [CENA 1.1] Fechando card de inspeção de viatura...');
  await page.keyboard.press('Escape');
  await page.waitForTimeout(1000);

  // -------------------------------------------------------------
  // SCENE 2: Individual Traffic Light Control
  // -------------------------------------------------------------
  console.log('\n🚦 [CENA 2] Selecionando Semáforo (cruzamento 1116667894)...');
  await page.mouse.click(775, 315);
  await page.waitForTimeout(2000);

  console.log('⚠️ [CENA 2] Acionando modo "Colocar em Alerta" (Amarelo Intermitente)...');
  await page.mouse.click(1620, 940);
  await page.waitForTimeout(2000);

  console.log('🔌 [CENA 2] Acionando "Desativar Semáforo" (Corte emergencial de sinal)...');
  await page.mouse.click(1810, 940);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(SCENE_DIR, '02_semaphore_control.png') });

  console.log('🔄 [CENA 2] Restaurando semáforo para Operação Adaptativa Autônoma...');
  await page.mouse.click(1810, 940);
  await page.waitForTimeout(1500);

  console.log('✖️ [CENA 2] Fechando painel lateral de semáforo...');
  await page.mouse.click(1760, 995);
  await page.waitForTimeout(1000);
  await page.keyboard.press('Escape');

  // -------------------------------------------------------------
  // SCENE 3: Road Network Management - Street Closure
  // -------------------------------------------------------------
  console.log('\n🛣️ [CENA 3] Selecionando via arterial (Avenida Dom Pedro II)...');
  await page.mouse.click(900, 595);
  await page.waitForTimeout(2000);

  console.log('🚫 [CENA 3] Acionando "Desativar Fluxo" (Bloqueio viário por sinistro)...');
  await page.mouse.click(1715, 560);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(SCENE_DIR, '03_street_blocked.png') });

  console.log('✅ [CENA 3] Reativando fluxo viário...');
  await page.mouse.click(1715, 560);
  await page.waitForTimeout(1500);

  console.log('✖️ [CENA 3] Fechando painel de monitoramento da via...');
  await page.mouse.click(1715, 605);
  await page.waitForTimeout(1000);
  await page.keyboard.press('Escape');

  // -------------------------------------------------------------
  // SCENE 4: Tactical Planning and AI Optimization
  // -------------------------------------------------------------
  console.log('\n📐 [CENA 4] Alternando para aba "Planejamento e Otimização"...');
  await page.mouse.click(290, 105);
  await page.waitForTimeout(2000);

  console.log('🧠 [CENA 4] Disparando motor de IA "Analisar Infraestrutura"...');
  await page.mouse.click(108, 1042);
  await page.waitForTimeout(3000); // Processamento ST-GATv2

  console.log('✅ [CENA 4] IA concluiu: Métricas de atraso calculadas e planos semafóricos otimizados.');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(SCENE_DIR, '04_planning_analyzed.png') });

  console.log('🔍 [CENA 4] Alternando filtros na malha de planejamento ("Manter")...');
  await page.mouse.click(940, 415);
  await page.waitForTimeout(1500);

  console.log('🌐 [CENA 4] Alternando filtros para visão global ("Todos")...');
  await page.mouse.click(845, 415);
  await page.waitForTimeout(1500);

  // -------------------------------------------------------------
  // SCENE 5: Diagnostics - MFD
  // -------------------------------------------------------------
  console.log('\n🔧 [CENA 5] Alternando para aba "Diagnóstico e Sistema"...');
  await page.mouse.click(490, 105);
  await page.waitForTimeout(2000);

  console.log('📈 [CENA 5] Gerando Relatório Macroscópico de Otimização MFD...');
  await page.mouse.click(155, 242);
  await page.waitForTimeout(2000);

  console.log('📊 [CENA 5] Exibindo Curva MFD (Capacidade Máxima e Ponto Operacional Atual)...');
  await page.mouse.click(100, 335);
  await page.waitForTimeout(2500);
  await page.screenshot({ path: path.join(SCENE_DIR, '05_diagnostics_mfd.png') });

  console.log('📑 [CENA 5] Exibindo Laudo Estruturado (Relatório SLM de Regulação Macroscópica)...');
  await page.mouse.click(300, 335);
  await page.waitForTimeout(2500);

  // -------------------------------------------------------------
  // SCENE 6: Diagnostics - XAI Explainability
  // -------------------------------------------------------------
  console.log('\n🧠 [CENA 6] Alternando para sub-aba "Análise de Decisão (XAI)"...');
  await page.mouse.click(295, 165);
  await page.waitForTimeout(1500);

  console.log('⚡ [CENA 6] Executando Análise de Atribuição de Sensores (Integrated Gradients)...');
  await page.mouse.click(480, 248);
  await page.waitForTimeout(2000);

  console.log('📊 [CENA 6] Exibindo Gráfico de Importância dos Sensores...');
  await page.mouse.click(130, 355);
  await page.waitForTimeout(2500);
  await page.screenshot({ path: path.join(SCENE_DIR, '06_diagnostics_xai.png') });

  console.log('📜 [CENA 6] Exibindo Relatório Detalhado de Decisão Neural & Guardian Agent...');
  await page.mouse.click(350, 355);
  await page.waitForTimeout(2500);

  // -------------------------------------------------------------
  // SCENE 7: Diagnostics - Audit and Logs
  // -------------------------------------------------------------
  console.log('\n🛡️ [CENA 7] Alternando para sub-aba "Auditoria (Audit Logs)"...');
  await page.mouse.click(490, 165);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(SCENE_DIR, '07_diagnostics_audit.png') });

  console.log('📜 [CENA 7] Inspecionando histórico de rastreabilidade de eventos...');
  await page.mouse.move(960, 500);
  await page.mouse.wheel(0, 250);
  await page.waitForTimeout(1500);
  await page.mouse.wheel(0, -250);
  await page.waitForTimeout(1000);

  // -------------------------------------------------------------
  // SCENE 8: Global System Settings Modal
  // -------------------------------------------------------------
  console.log('\n⚙️ [CENA 8] Abrindo modal de Configurações do Sistema via AppBar...');
  await page.mouse.click(1890, 25);
  await page.waitForTimeout(1500);

  console.log('🎛️ [CENA 8] Exibindo parâmetros da aba "Gerais"...');
  await page.mouse.click(650, 185);
  await page.waitForTimeout(1500);

  console.log('🤖 [CENA 8] Exibindo parâmetros da aba "Avançado (IA)" (PPO, DQN, Escola de Pilotagem)...');
  await page.mouse.click(730, 185);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(SCENE_DIR, '08_settings_modal.png') });

  console.log('🔌 [CENA 8] Exibindo parâmetros da aba "Hardware / Conexões" (SNMP, NTCIP)...');
  await page.mouse.click(830, 185);
  await page.waitForTimeout(1500);

  console.log('🚑 [CENA 8] Exibindo parâmetros da aba "Preempção (EVP)" (Frota de Emergência, CONTRAN)...');
  await page.mouse.click(950, 185);
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(SCENE_DIR, '08_settings_evp_fleet.png') });

  console.log('✖️ [CENA 8] Fechando modal de Configurações...');
  await page.keyboard.press('Escape');
  await page.waitForTimeout(1000);

  // -------------------------------------------------------------
  // SCENE 9: Return to Operational Dashboard & Wrap-up
  // -------------------------------------------------------------
  console.log('\n🏁 [CENA 9] Retornando ao Dashboard Operacional para encerramento elegante...');
  await page.mouse.click(100, 105);
  await page.waitForTimeout(3000);
  await page.screenshot({ path: path.join(SCENE_DIR, '09_dashboard_return.png') });

  // Context teardown and video recording finish
  console.log('\n💾 Salvando buffer de vídeo...');
  const video = page.video();
  await page.close();
  await context.close();
  await browser.close();

  if (video) {
    const rawWebmPath = await video.path();
    console.log(`\n🎬 Gravação bruta capturada: ${rawWebmPath}`);
    console.log('⚙️ Codificando vídeo final em Full HD com aceleração por hardware (NVDEC + NVENC)...');

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
    console.log(`🎉 VÍDEO COMPLETO DE APRESENTAÇÃO GERADO COM SUCESSO!`);
    console.log(`📁 Arquivo final: ${FINAL_MP4}`);
    console.log(`===============================================================\n`);
  }
}

main().catch((err) => {
  console.error('❌ Erro durante a geração do vídeo:', err);
  process.exit(1);
});
