// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package web_gateway

import (
	"errors"
	"time"
)

// EVPIngestionUseCase encapsulates the business logic for processing and enriching emergency vehicle telemetry.
// Implements TelemetryIngestionService.
type EVPIngestionUseCase struct {
	dispatcher   EventDispatcher
	ccoStreaming CCOStreamingService
}

// NewEVPIngestionUseCase creates an instance of the EVP ingestion application service.
func NewEVPIngestionUseCase(dispatcher EventDispatcher, ccoStreaming ...CCOStreamingService) *EVPIngestionUseCase {
	var cco CCOStreamingService
	if len(ccoStreaming) > 0 {
		cco = ccoStreaming[0]
	}
	return &EVPIngestionUseCase{
		dispatcher:   dispatcher,
		ccoStreaming: cco,
	}
}

// Ingest validates, enriches and dispatches vehicle telemetry to the configured EventDispatcher.
func (s *EVPIngestionUseCase) Ingest(payload map[string]interface{}, pathVehicleID string) error {
	if payload == nil {
		return errors.New("empty telemetry payload")
	}

	// 1. Resolve and enrich vehicle ID
	vid, ok := payload["vehicle_id"].(string)
	if !ok || vid == "" {
		if pathVehicleID != "" {
			payload["vehicle_id"] = pathVehicleID
		} else {
			payload["vehicle_id"] = "VIATURA_DESCONHECIDA"
		}
	}

	// 2. Ensure timestamp exists
	if _, ok := payload["timestamp"]; !ok {
		payload["timestamp"] = time.Now().UnixMilli()
	}

	// 3. Dispatch domain event to pipe/stdout
	if s.dispatcher != nil {
		s.dispatcher.Dispatch(EVPPushEvent{
			Type:      "event",
			EventType: "evp_telemetry",
			Payload:   payload,
		})
	}

	// 4. Broadcast directly to connected CCO SSE clients
	if s.ccoStreaming != nil {
		_ = s.ccoStreaming.Broadcast(map[string]interface{}{
			"type":    "evp_telemetry",
			"vehicle": payload,
		})
	}

	return nil
}
