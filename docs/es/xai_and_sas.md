# 🔍 Inteligencia Artificial Explicable (XAI) y SAS

Este documento detalla el motor de explicabilidad matemática de CARINA: el uso de Google Captum Integrated Gradients, las 5 ecuaciones matemáticas formales y la generación automatizada de informes periciales en formato Word (`.docx`).

⬅️ [Centro de Documentación](../README.md) | 🏛️ [Arquitectura](architecture.md)

---

## 1. Explicabilidad Matemática Determinista
Para auditorías de transporte público, las decisiones de IA deben ser completamente trazables. CARINA calcula la atribución porcentual de cada variable observada (longitud de colas, ocupación, velocidades de aproximación) mediante gradientes integrados.

---

## 2. Las 5 Ecuaciones Formales del Informe
1. **Convolución Causal Dilatada (TCN):** Procesamiento temporal de series de tráfico.
2. **Atención en Grafos (ST-GATv2 Lite):** Coordinación dinámica de ondas verdes arteriales.
3. **Fusión por Atención Cruzada:** Ponderación multimodal de estados.
4. **Valor Q Dueling (Guardian D3QN):** Estimación del riesgo de desbordamiento vehicular.
5. **Gradientes Integrados de Captum:** Verificación del axioma de completitud matemática.
