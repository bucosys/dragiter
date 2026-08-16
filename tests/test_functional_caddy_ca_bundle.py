"""
Functional test: TLS with custom CA bundle via local Caddy reverse proxy.
"""

import socket
import ssl
from pathlib import Path

import pytest

from tests.e2e.test_e2e_infrastructure import _run_dragiter


def caddy_tls_is_available(host: str = "localhost", port: int = 8443) -> bool:
    """Return True if something accepts TLS connections on host:port."""
    try:
        context = ssl.create_default_context()
        # We only care that the port is open and speaks TLS.
        # Certificate verification is intentionally disabled for the probe.
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with socket.create_connection((host, port), timeout=2) as sock:
            with context.wrap_socket(sock, server_hostname=host):
                return True
    except Exception:
        return False


@pytest.mark.skipif(
    not caddy_tls_is_available(),
    reason="Caddy TLS proxy not available on localhost:8443",
)
def test_functional_caddy_ca_bundle(tiny_example_dir):
    """
    Run a tiny workflow against Ollama behind Caddy using a custom CA bundle.
    Requires:
      - Caddy running on https://localhost:8443
      - CA cert at ~/mtls-test/ca.crt (or adjust path below)
      - Ollama reachable behind the proxy
    """
    tests_dir = Path(__file__).parent.resolve()
    ca_bundle = Path.home() / "ca-bundle-test" / "ca.crt"

    if not ca_bundle.is_file():
        pytest.skip(f"CA bundle not found: {ca_bundle}")

    temp_output_dir = tiny_example_dir / "outputs" / "tiny_caddy_ca"
    temp_output_dir.mkdir(parents=True, exist_ok=True)

    # Minimal config: base_url + ca_bundle via CLI, rest from a small toml if needed
    flags = [
        "-v",
        "--base-url", "https://localhost:8443/v1",
        "--api-key", "ollama",
        "--model-name", "qwen3:8b",
        "--ca-bundle-file", str(ca_bundle),
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

    print(f"✅ Caddy CA-bundle workflow passed. Results in: {temp_output_dir}")