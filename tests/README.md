# Tests for dragiter

This directory contains unit, security, functional and end-to-end tests for the
dragiter CLI tool.

The tests are **not** included in the installed wheel. They ship only with the
source distribution (sdist) and the Git repository.

## Prerequisites

- Python ≥ 3.11
- pytest (`pip install pytest` or install the project with the `dev` extra)

```bash
pip install -e ".[dev]"
```

## How to run the tests

### From a cloned repository or unpacked source tree

```bash
pytest -q
# or
python -m pytest
```

### From a published source distribution

```bash
pip download dragiter --no-binary=:all: -d .
tar xf dragiter-*.tar.gz
cd dragiter-*/
pip install -e ".[dev]"
pytest -q
```

Most tests run without any network access or API keys.  
Optional integration tests are skipped automatically when the required service
or environment variable is missing.

---

## Live cloud E2E tests (Grok, Gemini, Claude)

These tests make real API calls and are therefore skipped unless the
corresponding environment variable is set.

| Provider | Required environment variable | Notes |
|----------|-------------------------------|-------|
| xAI Grok | `GROK_API_KEY`                | Uses the official OpenAI-compatible endpoint |
| Google Gemini | `GEMINI_API_KEY`          | Uses Google’s OpenAI-compatible endpoint |
| Anthropic Claude | `CLAUDE_API_KEY`        | Requires an **OpenAI-compatible proxy** (LiteLLM, OpenRouter, custom gateway, …). Anthropic’s native `/v1/messages` API is **not** supported. |

**Example (Linux / macOS):**

```bash
export GROK_API_KEY="xai-…"
export GEMINI_API_KEY="AIza…"
export CLAUDE_API_KEY="sk-ant-…"

# optional – only needed for the Claude test
export DRAGITER_BASE_URL="http://localhost:4000/v1"   # your OpenAI-compatible proxy
export DRAGITER_MODEL_NAME="claude-sonnet-4"

pytest tests/e2e/test_grok_e2e_minimal.py \
       tests/e2e/test_gemini_e2e_minimal.py \
       tests/e2e/test_claude_e2e_minimal.py -v
```

Never commit real API keys. Prefer the patterns described in the user manual
(“How to supply API keys securely”).

---

## Local Ollama functional test

Requires a running Ollama instance with at least one model.

```bash
ollama serve          # if not already running
ollama pull qwen3:8b  # or any other model you prefer
pytest tests/test_functional_ollama.py -v
```

---

## TLS / mTLS tests with Caddy

Two functional tests verify the TLS-related CLI flags:

| Test | Port | Required files under `~/mtls-test/` | CLI flags exercised |
|------|------|-------------------------------------|---------------------|
| CA-bundle only | 8443 | `ca.crt` | `--ca-bundle-file` |
| Full mTLS | 8444 | `ca.crt`, `client.crt`, `client.key` | `--ca-bundle-file`, `--client-cert-file`, `--client-key-file` |

Both tests expect Ollama to be reachable behind the Caddy reverse proxy.

### 1. Prepare the working directory

```bash
mkdir -p ~/mtls-test && cd ~/mtls-test
```

### 2. CA-bundle only (port 8443)

```bash
# CA
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 \
  -out ca.crt \
  -subj "/CN=Local-Test-CA" \
  -addext "basicConstraints=critical,CA:TRUE" \
  -addext "keyUsage=critical,keyCertSign,cRLSign" \
  -addext "subjectKeyIdentifier=hash"

# Server certificate
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -subj "/CN=localhost"

cat > server_ext.cnf << 'EOF'
basicConstraints=CA:FALSE
keyUsage=digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=DNS:localhost,IP:127.0.0.1
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid,issuer
EOF

openssl x509 -req -in server.csr \
  -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out server.crt -days 825 -sha256 \
  -extfile server_ext.cnf

# Verify
openssl verify -CAfile ca.crt server.crt

# Caddyfile
cat > Caddyfile << 'EOF'
localhost:8443 {
    tls ./server.crt ./server.key
    reverse_proxy localhost:11434
}
EOF

caddy run --config Caddyfile
```

In another terminal:

```bash
pytest tests/test_functional_caddy_ca_bundle.py -v
```

### 3. Full mTLS (port 8444)

Reuse the same CA or create a fresh set:

```bash
# Client certificate (shown by dragiter)
openssl genrsa -out client.key 2048
openssl req -new -key client.key -out client.csr -subj "/CN=dragiter-client"
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out client.crt -days 825 -sha256

# Caddyfile with client authentication
cat > Caddyfile_mtls << 'EOF'
localhost:8444 {
    tls ./server.crt ./server.key {
        client_auth {
            mode require_and_verify
            trusted_ca_cert_file ./ca.crt
        }
    }
    reverse_proxy localhost:11434
}
EOF

caddy run --config Caddyfile_mtls
```

Then:

```bash
pytest tests/test_functional_caddy_mtls.py -v
```

### Manual verification (outside pytest)

```bash
# CA-bundle only
dragiter \
  --base-url "https://localhost:8443/v1" \
  --api-key "ollama" \
  --model-name "qwen3:8b" \
  --ca-bundle-file ~/mtls-test/ca.crt \
  -p … -r … -l …

# Full mTLS
dragiter \
  --base-url "https://localhost:8444/v1" \
  --api-key "ollama" \
  --model-name "qwen3:8b" \
  --ca-bundle-file ~/mtls-test/ca.crt \
  --client-cert-file ~/mtls-test/client.crt \
  --client-key-file  ~/mtls-test/client.key \
  -p … -r … -l …
```

---

## Notes

- New tests should follow the naming convention `test_*.py`.
- Security and circuit-breaker tests live directly under `tests/` and need no
  external services.
- The tiny self-contained fixtures used by many functional tests are located
  in `tests/fixtures/01_tiny_functional_test/`.
