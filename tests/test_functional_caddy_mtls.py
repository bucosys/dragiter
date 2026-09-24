"""
Functional test: mutual TLS (mTLS) via local Caddy reverse proxy.
"""

from pathlib import Path
import socket
import ssl

import pytest
from tests.e2e.test_e2e_infrastructure import _run_dragiter


def caddy_tls_is_available(host: str = "localhost", port: int = 8444) -> bool:
    """Return True if something accepts TLS connections on host:port."""
    try:
        context = ssl.create_default_context()
        # Probe only: do not verify server cert here.
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with socket.create_connection((host, port), timeout=2) as sock:
            with context.wrap_socket(sock, server_hostname=host):
                return True
    except Exception:
        return False


@pytest.mark.skipif(
    not caddy_tls_is_available(),
    reason="Caddy TLS proxy not available on localhost:8444",
)
def test_functional_caddy_mtls(tiny_example_dir):
    """
    Run a tiny workflow against Ollama behind Caddy using full mTLS.

    Requires:
      - Caddy on https://localhost:8444 with client_auth enabled
      - ~/mtls-test/ca.crt
      - ~/mtls-test/client.crt
      - ~/mtls-test/client.key
      - Ollama reachable behind the proxy

    Covers EXEC-17.
    """
    mtls_dir = Path.home() / "mtls-test"
    ca_bundle = mtls_dir / "ca.crt"
    client_cert = mtls_dir / "client.crt"
    client_key = mtls_dir / "client.key"

    for path in (ca_bundle, client_cert, client_key):
        if not path.is_file():
            pytest.skip(f"mTLS file not found: {path}")

    temp_output_dir = tiny_example_dir / "outputs" / "tiny_caddy_mtls"
    temp_output_dir.mkdir(parents=True, exist_ok=True)

    flags = [
        "-v",
        "--base-url", "https://localhost:8444/v1",
        "--api-key", "ollama",
        "--model-name", "qwen3:8b",
        "--ca-bundle-file", str(ca_bundle),
        "--client-cert-file", str(client_cert),
        "--client-key-file", str(client_key),
        "-p", str(tiny_example_dir / "01_tiny_prompt.toml"),
        "-r", str(tiny_example_dir / "01_tiny_resource.toml"),
        "-l", str(tiny_example_dir / "01_tiny_loop.txt"),
        "-O", str(temp_output_dir),
        "-m", "w",
    ]

    result = _run_dragiter(flags, timeout=360)

    assert result.returncode == 0, f"Test failed:\n{result.stderr}"

    created_files = list(temp_output_dir.glob("**/*"))
    assert len(created_files) > 0, "No output files were created"

    print(f"✅ Caddy mTLS workflow passed. Results in: {temp_output_dir}")
