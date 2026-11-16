// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

// Package snmptest provides a lightweight localhost UDP SNMPv2c responder for unit tests.
package snmptest

import (
	"io"
	"log"
	"net"
	"strings"
	"sync"
	"testing"

	"github.com/gosnmp/gosnmp"
)

// SetRecord captures a single SNMP SET request handled by MockAgent.
type SetRecord struct {
	OID   string
	Value interface{}
}

// MockAgent serves deterministic SNMPv2c GET/SET responses over a localhost UDP socket.
type MockAgent struct {
	Port int

	conn net.PacketConn

	mu   sync.RWMutex
	oids map[string]gosnmp.SnmpPDU
	sets []SetRecord
	done chan struct{}
	wg   sync.WaitGroup
}

// StartMockAgent binds an ephemeral UDP port on 127.0.0.1 and registers cleanup with t.Cleanup.
func StartMockAgent(t *testing.T, initial map[string]gosnmp.SnmpPDU) *MockAgent {
	t.Helper()

	conn, err := net.ListenPacket("udp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("failed to bind mock SNMP UDP socket: %v", err)
	}

	copied := make(map[string]gosnmp.SnmpPDU, len(initial))
	for k, v := range initial {
		norm := strings.TrimPrefix(k, ".")
		v.Name = "." + norm
		copied[norm] = v
	}

	agent := &MockAgent{
		Port: conn.LocalAddr().(*net.UDPAddr).Port,
		conn: conn,
		oids: copied,
		done: make(chan struct{}),
	}

	agent.wg.Add(1)
	go agent.serve()

	t.Cleanup(func() {
		agent.Close()
	})
	return agent
}

// Close shuts down the mock SNMP listener and waits for the serve goroutine to exit.
func (m *MockAgent) Close() {
	select {
	case <-m.done:
		return
	default:
		close(m.done)
	}
	_ = m.conn.Close()
	m.wg.Wait()
}

// Sets returns a snapshot copy of all recorded SET requests.
func (m *MockAgent) Sets() []SetRecord {
	m.mu.RLock()
	defer m.mu.RUnlock()
	out := make([]SetRecord, len(m.sets))
	copy(out, m.sets)
	return out
}

// WaitForSet waits or checks sets cleanly; SetPDU updates an OID at runtime.
func (m *MockAgent) SetPDU(oid string, pdu gosnmp.SnmpPDU) {
	norm := strings.TrimPrefix(oid, ".")
	pdu.Name = "." + norm
	m.mu.Lock()
	m.oids[norm] = pdu
	m.mu.Unlock()
}

func (m *MockAgent) serve() {
	defer m.wg.Done()

	decoder := &gosnmp.GoSNMP{
		Version: gosnmp.Version2c,
		Logger:  gosnmp.NewLogger(log.New(io.Discard, "", 0)),
	}
	buf := make([]byte, 4096)

	for {
		n, addr, err := m.conn.ReadFrom(buf)
		if err != nil {
			select {
			case <-m.done:
				return
			default:
				continue
			}
		}

		pkt, err := decoder.SnmpDecodePacket(buf[:n])
		if err != nil || pkt == nil {
			continue
		}

		resp := m.buildResponse(pkt)
		raw, err := resp.MarshalMsg()
		if err != nil {
			continue
		}
		_, _ = m.conn.WriteTo(raw, addr)
	}
}

func (m *MockAgent) buildResponse(req *gosnmp.SnmpPacket) *gosnmp.SnmpPacket {
	respVars := make([]gosnmp.SnmpPDU, 0, len(req.Variables))

	if req.PDUType == gosnmp.SetRequest {
		m.mu.Lock()
		for _, v := range req.Variables {
			norm := strings.TrimPrefix(v.Name, ".")
			m.sets = append(m.sets, SetRecord{OID: norm, Value: v.Value})
			m.oids[norm] = v
			respVars = append(respVars, v)
		}
		m.mu.Unlock()
	} else {
		m.mu.RLock()
		for _, v := range req.Variables {
			norm := strings.TrimPrefix(v.Name, ".")
			if val, ok := m.oids[norm]; ok {
				out := val
				out.Name = v.Name
				respVars = append(respVars, out)
			} else {
				respVars = append(respVars, gosnmp.SnmpPDU{
					Name:  v.Name,
					Type:  gosnmp.NoSuchObject,
					Value: nil,
				})
			}
		}
		m.mu.RUnlock()
	}

	return &gosnmp.SnmpPacket{
		Version:   req.Version,
		Community: req.Community,
		PDUType:   gosnmp.GetResponse,
		RequestID: req.RequestID,
		MsgID:     req.MsgID,
		Variables: respVars,
		Logger:    gosnmp.NewLogger(log.New(io.Discard, "", 0)),
	}
}
