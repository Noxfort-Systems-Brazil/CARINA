// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package snmp

import (
	"fmt"
	"sync"
	"time"

	"github.com/gosnmp/gosnmp"
)

// Client manages direct SNMPv2c / SNMPv3 communication over UDP with traffic light controllers.
type Client struct {
	IPAddress string
	Port      uint16
	Community string
	Config    SNMPConfig
	Timeout   time.Duration
	Retries   int

	mu     sync.Mutex
	client *gosnmp.GoSNMP
}

// NewClient instantiates a new configured SNMPv2c client.
func NewClient(ip string, port int, community string, timeoutSec int, retries int) *Client {
	return NewClientWithConfig(ip, port, SNMPConfig{
		Version:   "2c",
		Community: community,
	}, timeoutSec, retries)
}

// NewClientWithConfig instantiates a new SNMP client supporting SNMPv2c and SNMPv3.
func NewClientWithConfig(ip string, port int, cfg SNMPConfig, timeoutSec int, retries int) *Client {
	if timeoutSec <= 0 {
		timeoutSec = 2
	}
	if retries < 0 {
		retries = 1
	}
	norm := cfg.Normalized()
	return &Client{
		IPAddress: ip,
		Port:      uint16(port),
		Community: norm.Community,
		Config:    norm,
		Timeout:   time.Duration(timeoutSec) * time.Second,
		Retries:   retries,
	}
}

func (c *Client) ensureConnected() error {
	if c.client != nil && c.client.Conn != nil {
		return nil
	}

	snmpObj, err := BuildGoSNMP(c.IPAddress, c.Port, c.Config, c.Timeout, c.Retries)
	if err != nil {
		return err
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
	c.closeLocked()
}

func (c *Client) closeLocked() {
	if c.client != nil && c.client.Conn != nil {
		_ = c.client.Conn.Close()
	}
	c.client = nil
}

// executeWithReconnect acquires the client mutex, ensures a live socket, and retries once after reconnect on error.
func (c *Client) executeWithReconnect(op func(*gosnmp.GoSNMP) (*gosnmp.SnmpPacket, error)) (*gosnmp.SnmpPacket, error) {
	c.mu.Lock()
	defer c.mu.Unlock()

	if err := c.ensureConnected(); err != nil {
		return nil, err
	}

	pkt, err := op(c.client)
	if err != nil {
		c.closeLocked()
		if errConn := c.ensureConnected(); errConn == nil {
			pkt, err = op(c.client)
		}
	}
	return pkt, err
}

func (c *Client) getVariable(oid string) (gosnmp.SnmpPDU, error) {
	pkt, err := c.executeWithReconnect(func(cli *gosnmp.GoSNMP) (*gosnmp.SnmpPacket, error) {
		return cli.Get([]string{oid})
	})
	if err != nil {
		return gosnmp.SnmpPDU{}, fmt.Errorf("snmp get %s failed: %w", oid, err)
	}
	if pkt == nil || len(pkt.Variables) == 0 {
		return gosnmp.SnmpPDU{}, fmt.Errorf("snmp get %s returned empty variables", oid)
	}

	pdu := pkt.Variables[0]
	if pdu.Type == gosnmp.NoSuchObject || pdu.Type == gosnmp.NoSuchInstance || pdu.Type == gosnmp.EndOfMibView {
		return gosnmp.SnmpPDU{}, fmt.Errorf("snmp get %s returned MIB exception %v", oid, pdu.Type)
	}
	return pdu, nil
}

// Get executes a synchronous SNMP GET request for the given OID.
func (c *Client) Get(oid string) (interface{}, error) {
	pdu, err := c.getVariable(oid)
	if err != nil {
		return nil, err
	}
	return decodeGenericPDUValue(pdu), nil
}

// GetBitmask queries an OID expecting either a numeric integer or binary OCTET STRING bitmask (NTCIP 1202).
func (c *Client) GetBitmask(oid string) (int64, error) {
	pdu, err := c.getVariable(oid)
	if err != nil {
		return 0, err
	}
	return DecodeBitmaskPDU(pdu, true)
}

// GetInt executes a GET request and converts the return value to an integer (int64).
func (c *Client) GetInt(oid string) (int64, error) {
	pdu, err := c.getVariable(oid)
	if err != nil {
		return 0, err
	}
	return DecodeBitmaskPDU(pdu, false)
}

// Set executes an SNMP SET request for the given OID.
func (c *Client) Set(oid string, value interface{}) error {
	pdu, err := buildSetPDU(oid, value)
	if err != nil {
		return err
	}

	pkt, err := c.executeWithReconnect(func(cli *gosnmp.GoSNMP) (*gosnmp.SnmpPacket, error) {
		return cli.Set([]gosnmp.SnmpPDU{pdu})
	})
	if err != nil {
		return fmt.Errorf("snmp set %s failed: %w", oid, err)
	}
	if pkt != nil && pkt.Error != gosnmp.NoError {
		return fmt.Errorf("snmp set status error %v at index %d", pkt.Error, pkt.ErrorIndex)
	}
	return nil
}
