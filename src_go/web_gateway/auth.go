// CARINA (Controlled Artificial Road-traffic Intelligence Network Architecture)
// SPDX-FileCopyrightText: 2026 Noxfort Systems
// SPDX-License-Identifier: AGPL-3.0-or-later

package web_gateway

import (
	"crypto/subtle"
	"net/http"
	"os"
	"strings"
)

// ResolveAllowedOrigin selects explicit CORS origin config/env or returns "*" fallback.
func ResolveAllowedOrigin(configured string) string {
	trimmed := strings.TrimSpace(configured)
	if trimmed != "" {
		return trimmed
	}
	if envOrigin := strings.TrimSpace(os.Getenv("CARINA_CCO_ALLOWED_ORIGIN")); envOrigin != "" {
		return envOrigin
	}
	return "*"
}

// ExtractRequestToken reads authentication tokens from headers or optional query params (for SSE).
func ExtractRequestToken(r *http.Request, allowQueryParam bool) string {
	authHeader := strings.TrimSpace(r.Header.Get("Authorization"))
	if len(authHeader) > 7 && strings.EqualFold(authHeader[:7], "Bearer ") {
		if tok := strings.TrimSpace(authHeader[7:]); tok != "" {
			return tok
		}
	}
	for _, hdr := range []string{"X-EVP-Token", "X-CCO-Token", "X-Auth-Token"} {
		if tok := strings.TrimSpace(r.Header.Get(hdr)); tok != "" {
			return tok
		}
	}
	if allowQueryParam && r.URL != nil {
		if tok := strings.TrimSpace(r.URL.Query().Get("token")); tok != "" {
			return tok
		}
	}
	return ""
}

// TokensMatch performs constant-time comparison between two non-empty trimmed tokens.
func TokensMatch(received, expected string) bool {
	rBytes := []byte(strings.TrimSpace(received))
	eBytes := []byte(strings.TrimSpace(expected))
	if len(eBytes) == 0 {
		return true
	}
	return subtle.ConstantTimeCompare(rBytes, eBytes) == 1
}

// WrapTokenAuth enforces Bearer/header token authentication when tokenProvider returns a non-empty token.
func WrapTokenAuth(tokenProvider func() string, allowQueryParam bool, next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method == http.MethodOptions {
			next(w, r)
			return
		}
		if tokenProvider != nil {
			expected := strings.TrimSpace(tokenProvider())
			if expected != "" {
				received := ExtractRequestToken(r, allowQueryParam)
				if !TokensMatch(received, expected) {
					w.Header().Set("Content-Type", "application/json")
					w.WriteHeader(http.StatusUnauthorized)
					_, _ = w.Write([]byte(`{"error":"Unauthorized: valid token required","code":401}`))
					return
				}
			}
		}
		next(w, r)
	}
}
