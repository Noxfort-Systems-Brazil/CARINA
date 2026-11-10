// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package heartbeat

import (
	"errors"
	"sync"
	"sync/atomic"
	"testing"
	"time"
)

func TestManagerLifecycle(t *testing.T) {
	pulseCount := int32(0)
	mgr := NewManager(
		"tl_test1",
		"127.0.0.1",
		10*time.Millisecond,
		func() (bool, error) {
			atomic.AddInt32(&pulseCount, 1)
			return true, nil
		},
		nil,
		nil,
	)

	mgr.Start()
	// Calling Start again should be a safe no-op
	mgr.Start()

	time.Sleep(35 * time.Millisecond)
	mgr.Stop()
	// Calling Stop again should be safe
	mgr.Stop()

	count := atomic.LoadInt32(&pulseCount)
	if count < 2 {
		t.Fatalf("Expected at least 2 pulses, got %d", count)
	}
}

func TestHeartbeatLossAndRestore(t *testing.T) {
	var mu sync.Mutex
	shouldFail := true

	lossTriggered := make(chan string, 1)
	restoreTriggered := make(chan string, 1)

	mgr := NewManager(
		"tl_test2",
		"192.168.1.100",
		10*time.Millisecond,
		func() (bool, error) {
			mu.Lock()
			defer mu.Unlock()
			if shouldFail {
				return false, errors.New("timeout")
			}
			return true, nil
		},
		func(id string) {
			lossTriggered <- id
		},
		func(id string) {
			restoreTriggered <- id
		},
	)
	mgr.MaxConsecutiveFailures = 2

	mgr.Start()
	defer mgr.Stop()

	// Wait for loss notification
	select {
	case id := <-lossTriggered:
		if id != "tl_test2" {
			t.Fatalf("Expected loss for tl_test2, got %s", id)
		}
	case <-time.After(200 * time.Millisecond):
		t.Fatal("Timeout waiting for heartbeat loss notification")
	}

	// Now restore pulse
	mu.Lock()
	shouldFail = false
	mu.Unlock()

	// Wait for restore notification
	select {
	case id := <-restoreTriggered:
		if id != "tl_test2" {
			t.Fatalf("Expected restore for tl_test2, got %s", id)
		}
	case <-time.After(200 * time.Millisecond):
		t.Fatal("Timeout waiting for heartbeat restore notification")
	}
}
