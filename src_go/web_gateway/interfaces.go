// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package web_gateway

// EventDispatcher defines the contract for dispatching domain events to external processes/pipes (DIP).
type EventDispatcher interface {
	Dispatch(event interface{})
}

// Broadcaster defines the contract for broadcasting messages to multiple connected clients (ISP).
type Broadcaster interface {
	Broadcast(data []byte)
}

// TelemetryIngestionService defines the business logic for parsing and validating emergency vehicle pings.
type TelemetryIngestionService interface {
	Ingest(payload map[string]interface{}, pathVehicleID string) error
}

// CCOStreamingService defines the contract for managing active CCO videowall streams.
type CCOStreamingService interface {
	Broadcast(payload interface{}) error
	RegisterClient(ch chan []byte)
	UnregisterClient(ch chan []byte)
	ClientCount() int
}

