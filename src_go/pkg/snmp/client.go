// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture) is an open-source AI ecosystem for real-time, adaptive control of urban traffic light networks.
// Copyright (C) 2026 Gabriel Moraes - Noxfort Systems
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as
// published by the Free Software Foundation, either version 3 of the
// License, or (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program. If not, see <https://www.gnu.org/licenses/>.

// File: src_go/pkg/snmp/client.go
// Author: Gabriel Moraes
// Date: September 2026

package snmp

import (
	"fmt"
	"strconv"
	"sync"
	"time"

	"github.com/gosnmp/gosnmp"
)

// Client manages direct SNMPv2c communication over UDP with traffic light controllers.
type Client struct {
	IPAddress string
	Port      uint16
	Community string
	Timeout   time.Duration
	Retries   int

	mu     sync.Mutex
	client *gosnmp.GoSNMP
}

// NewClient instantiates a new configured SNMP client.
func NewClient(ip string, port int, community string, timeoutSec int, retries int) *Client {
	if timeoutSec <= 0 {
		timeoutSec = 2
	}
	if retries < 0 {
		retries = 1
	}
	if community == "" {
		community = "public"
	}

	return &Client{
		IPAddress: ip,
		Port:      uint16(port),
		Community: community,
		Timeout:   time.Duration(timeoutSec) * time.Second,
		Retries:   retries,
	}
}

func (c *Client) ensureConnected() error {
	if c.client != nil && c.client.Conn != nil {
		return nil
	}

	snmpObj := &gosnmp.GoSNMP{
		Target:    c.IPAddress,
		Port:      c.Port,
		Community: c.Community,
		Version:   gosnmp.Version2c,
		Timeout:   c.Timeout,
		Retries:   c.Retries,
	}

	if err := snmpObj.Connect(); err != nil {
		return fmt.Errorf("falha ao conectar socket SNMP em %s:%d: %w", c.IPAddress, c.Port, err)
	}

	c.client = snmpObj
	return nil
}

// Close terminates the SNMP socket connection.
func (c *Client) Close() {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.client != nil && c.client.Conn != nil {
		_ = c.client.Conn.Close()
		c.client = nil
	}
}

// Get executes a synchronous SNMP GET request for the given OID.
func (c *Client) Get(oid string) (interface{}, error) {
	c.mu.Lock()
	defer c.mu.Unlock()

	if err := c.ensureConnected(); err != nil {
		return nil, err
	}

	pkt, err := c.client.Get([]string{oid})
	if err != nil {
		// Attempt reconnection once if socket was broken
		_ = c.client.Conn.Close()
		c.client = nil
		if errConn := c.ensureConnected(); errConn == nil {
			pkt, err = c.client.Get([]string{oid})
		}
	}

	if err != nil {
		return nil, fmt.Errorf("snmp get %s failed: %w", oid, err)
	}

	if len(pkt.Variables) == 0 {
		return nil, fmt.Errorf("snmp get %s returned empty variables", oid)
	}

	pdu := pkt.Variables[0]
	switch pdu.Type {
	case gosnmp.OctetString:
		bytes, ok := pdu.Value.([]byte)
		if ok {
			return string(bytes), nil
		}
		return fmt.Sprintf("%v", pdu.Value), nil
	case gosnmp.Integer, gosnmp.Counter32, gosnmp.Gauge32, gosnmp.TimeTicks, gosnmp.Counter64:
		return gosnmp.ToBigInt(pdu.Value).Int64(), nil
	default:
		return pdu.Value, nil
	}
}

// GetInt executes a GET request and converts the return value to an integer (int64).
func (c *Client) GetInt(oid string) (int64, error) {
	val, err := c.Get(oid)
	if err != nil {
		return 0, err
	}

	switch v := val.(type) {
	case int64:
		return v, nil
	case int:
		return int64(v), nil
	case uint64:
		return int64(v), nil
	case string:
		i, err := strconv.ParseInt(v, 10, 64)
		if err != nil {
			return 0, err
		}
		return i, nil
	default:
		return 0, fmt.Errorf("tipo não numérico retornado para OID %s: %T (%v)", oid, val, val)
	}
}

// Set executes an SNMP SET request for the given OID.
func (c *Client) Set(oid string, value interface{}) error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if err := c.ensureConnected(); err != nil {
		return err
	}

	pdu := gosnmp.SnmpPDU{
		Name: oid,
	}

	switch v := value.(type) {
	case int:
		pdu.Type = gosnmp.Integer
		pdu.Value = v
	case int32:
		pdu.Type = gosnmp.Integer
		pdu.Value = int(v)
	case int64:
		pdu.Type = gosnmp.Integer
		pdu.Value = int(v)
	case float64:
		pdu.Type = gosnmp.Integer
		pdu.Value = int(v)
	case string:
		pdu.Type = gosnmp.OctetString
		pdu.Value = []byte(v)
	case []byte:
		pdu.Type = gosnmp.OctetString
		pdu.Value = v
	default:
		return fmt.Errorf("tipo não suportado para SNMP SET: %T", value)
	}

	pkt, err := c.client.Set([]gosnmp.SnmpPDU{pdu})
	if err != nil {
		// Attempt reconnection and resend once
		_ = c.client.Conn.Close()
		c.client = nil
		if errConn := c.ensureConnected(); errConn == nil {
			pkt, err = c.client.Set([]gosnmp.SnmpPDU{pdu})
		}
	}

	if err != nil {
		return fmt.Errorf("snmp set %s failed: %w", oid, err)
	}

	if pkt.Error != gosnmp.NoError {
		return fmt.Errorf("snmp set status error %v at index %d", pkt.Error, pkt.ErrorIndex)
	}

	return nil
}
