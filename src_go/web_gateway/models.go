// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package web_gateway

// EVPPushEvent represents the NDJSON event sent over stdout to Python core.
type EVPPushEvent struct {
	Type      string                 `json:"type"`       // "event"
	EventType string                 `json:"event_type"` // "evp_telemetry"
	Payload   map[string]interface{} `json:"payload"`
}

// VehicleTelemetry represents the GPS/siren telemetry packet emitted by emergency vehicles.
type VehicleTelemetry struct {
	VehicleID   string  `json:"vehicle_id"`
	Corporation string  `json:"corporation"`
	Latitude    float64 `json:"latitude"`
	Longitude   float64 `json:"longitude"`
	SpeedKmh    float64 `json:"speed_kmh"`
	HeadingDeg  float64 `json:"heading_deg"`
	SirenActive bool    `json:"siren_active"`
	Timestamp   int64   `json:"timestamp,omitempty"`
}

// CCOBroadcastMessage represents real-time narrative or telemetry payloads pushed to CCO videowalls.
type CCOBroadcastMessage struct {
	Text      string `json:"text,omitempty"`
	Subtitle  string `json:"subtitle,omitempty"`
	Category  string `json:"category,omitempty"`
	TimeStr   string `json:"time_str,omitempty"`
	Timestamp int64  `json:"timestamp,omitempty"`
}

// HealthStatus represents the gateway operational status diagnostic payload.
type HealthStatus struct {
	Status         string `json:"status"`
	Service        string `json:"service"`
	Port           int    `json:"port"`
	GatewayEnabled bool   `json:"gateway_enabled"`
	Timestamp      int64  `json:"timestamp"`
}
