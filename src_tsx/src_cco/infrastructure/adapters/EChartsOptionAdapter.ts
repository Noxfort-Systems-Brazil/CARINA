// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

import type { EChartsOption } from 'echarts';
import { MapTopology } from '../../domain/models/Topology';
import { TrafficLightPanelMap } from '../../domain/models/TrafficLight';
import { EmergencyVehicle } from '../../domain/models/EmergencyVehicle';
import { CongestionLevel } from '../../domain/models/CongestionLevel';

export class EChartsOptionAdapter {
  public static buildOption(
    topology: MapTopology | null,
    congestionMap: Record<string, number>,
    signals: TrafficLightPanelMap,
    emergencyVehicles: EmergencyVehicle[]
  ): EChartsOption {
    if (!topology || !topology.bounds) {
      return {
        backgroundColor: '#F7F7F7',
        title: {
          text: 'CARREGANDO TOPOLOGIA VIÁRIA...',
          left: 'center',
          top: 'center',
          textStyle: { color: '#546e7a', fontSize: 18, fontFamily: 'monospace' },
        },
      };
    }

    const { min_x, min_y, max_x, max_y } = topology.bounds;
    const padX = Math.max((max_x - min_x) * 0.05, 10);
    const padY = Math.max((max_y - min_y) * 0.05, 10);

    // 1. Road Lines (Streets with Congestion Gradient)
    const roadLines = topology.edges.map((edge) => {
      const rawCongestion = congestionMap[edge.id] ?? 0;
      const level = new CongestionLevel(rawCongestion);

      return {
        name: edge.name || edge.id,
        coords: edge.shape,
        lineStyle: {
          color: level.getColor(),
          width: level.getLineWidth(),
          opacity: 0.92,
          cap: 'round' as const,
          join: 'round' as const,
        },
      };
    });

    // 2. Traffic Lights / Signalized Intersections
    const trafficLightNodes = topology.nodes
      .filter((n) => n.type === 'traffic_light' || signals[n.id])
      .map((n) => {
        const sig = signals[n.id];
        const displayState = sig?.displayState || 'RED';

        let color = '#ef4444'; // Red default
        if (displayState === 'GREEN') color = '#10b981';
        else if (displayState === 'YELLOW' || displayState === 'FLASHING_YELLOW') color = '#facc15';

        return {
          name: `Semáforo ${n.id} (Fase ${sig?.phase ?? 1})`,
          value: [n.x, n.y],
          itemStyle: {
            color,
            borderColor: '#0f172a',
            borderWidth: 2,
            shadowColor: color,
            shadowBlur: 14,
          },
        };
      });

    // 3. Emergency Vehicles with Flashing Siren Effect (effectScatter)
    const evpScatterData = emergencyVehicles.map((vehicle) => {
      let color = '#3b82f6'; // Police
      if (vehicle.corporation === 'SAMU') color = '#ef4444';
      else if (vehicle.corporation === 'BOMBEIROS') color = '#f97316';

      return {
        name: `${vehicle.corporation}: ${vehicle.vehicleId}`,
        value: [vehicle.x, vehicle.y],
        itemStyle: {
          color,
          shadowColor: color,
          shadowBlur: 20,
        },
      };
    });

    return {
      backgroundColor: '#F7F7F7',
      animation: false,
      grid: {
        top: 20,
        bottom: 20,
        left: 20,
        right: 20,
      },
      xAxis: {
        type: 'value',
        min: min_x - padX,
        max: max_x + padX,
        show: false,
      },
      yAxis: {
        type: 'value',
        min: min_y - padY,
        max: max_y + padY,
        show: false,
        scale: true,
      },
      series: [
        // Layer 1: Traffic Roads
        {
          name: 'Vias Urbanas',
          type: 'lines',
          coordinateSystem: 'cartesian2d',
          polyline: true,
          silent: true,
          data: roadLines,
          progressive: 200,
          zlevel: 1,
        },
        // Layer 2: Physical Traffic Lights
        {
          name: 'Semáforos',
          type: 'scatter',
          coordinateSystem: 'cartesian2d',
          symbol: 'circle',
          symbolSize: 15,
          silent: true,
          data: trafficLightNodes,
          zlevel: 2,
        },
        // Layer 3: Moving Emergency Vehicles with Siren Effect
        {
          name: 'Viaturas de Emergência',
          type: 'effectScatter',
          coordinateSystem: 'cartesian2d',
          symbol: 'pin',
          symbolSize: 26,
          rippleEffect: {
            period: 1.8,
            scale: 3.2,
            brushType: 'stroke',
          },
          silent: true,
          data: evpScatterData,
          zlevel: 3,
        },
      ],
    };
  }
}
