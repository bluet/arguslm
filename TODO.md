# TODO

## Pre-Deployment Security (Required before non-localhost deployment)

- [ ] **API Authentication**: Add auth middleware (JWT/OAuth2 or API key) to all endpoints
- [ ] **Inbound Rate Limiting**: Add `slowapi` or equivalent on `/trigger`, benchmark, and WebSocket endpoints to prevent credit exhaustion
- [ ] **CORS Tightening**: Restrict `allow_methods` and `allow_headers` to explicit lists instead of `["*"]`
- [ ] **Security Headers**: Add `X-Frame-Options`, `X-Content-Type-Options`, `Content-Security-Policy`, `Strict-Transport-Security` in nginx.conf
- [ ] **TLS/HTTPS**: Configure TLS termination (nginx or reverse proxy)
- [ ] **Snyk CI Policy**: Add `.snyk` ignore rules for false positives (CWE-547 on api_key variables)
