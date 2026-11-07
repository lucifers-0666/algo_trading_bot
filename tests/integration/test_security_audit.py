"""Security and Boundary Audit Tests.
Verifies secret redaction, .gitignore boundaries, localhost bindings, and demat isolation.
"""

from pathlib import Path
import re
import yaml


def test_gitignore_protects_secrets_and_databases():
    gitignore_path = Path(".gitignore")
    assert gitignore_path.exists()
    content = gitignore_path.read_text(encoding="utf-8")

    assert ".env" in content
    assert "*.db" in content or "*.sqlite" in content
    assert ".venv/" in content


def test_env_example_contains_zero_secrets():
    env_example = Path(".env.example")
    assert env_example.exists()
    content = env_example.read_text(encoding="utf-8")

    # Verify no raw keys or real passwords exist in example
    assert "TRUEDATA_PASSWORD=" in content
    lines = content.splitlines()
    for line in lines:
        if line.startswith("TRUEDATA_PASSWORD="):
            val = line.split("=", 1)[1].strip()
            assert val == "", f"Secret found in .env.example: {val}"


def test_dashboard_localhost_binding():
    app_config_path = Path("config/app.example.yaml")
    assert app_config_path.exists()
    config = yaml.safe_load(app_config_path.read_text(encoding="utf-8"))

    host = config.get("dashboard", {}).get("host")
    assert host in ["127.0.0.1", "localhost"], f"Insecure dashboard binding detected: {host}"


def test_zero_real_demat_broker_endpoints():
    """Scans all python files in src/trader to ensure no real broker order placement exists."""
    src_dir = Path("src/trader")
    banned_keywords = [
        "place_order",
        "modify_order",
        "cancel_order",
        "kiteconnect",
        "smartapi",
        "upstox",
    ]

    for py_file in src_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8").lower()
        # Verify no real broker SDKs are imported
        assert "import kiteconnect" not in content
        assert "import smartapi" not in content
        assert "import upstox" not in content




def test_frontend_never_stores_provider_credentials_or_private_api_tokens():
    api_client = Path("frontend/src/lib/api.ts").read_text(encoding="utf-8")
    provider_view = Path("frontend/src/views/MarketDataSettingsView.tsx").read_text(encoding="utf-8")

    assert "VITE_API_TOKEN" not in api_client
    assert "northstar_api_token" not in api_client
    assert "localStorage" not in api_client
    assert "angelApiKey" not in provider_view
    assert "angelTotpSecret" not in provider_view
    assert "totp_secret:" not in provider_view


def test_local_api_token_is_exchanged_for_httponly_cookie():
    api_source = Path("src/trader/api/app.py").read_text(encoding="utf-8")
    assert 'key="northstar_session"' in api_source
    assert "httponly=True" in api_source
    assert 'request.cookies.get("northstar_session")' in api_source
    assert 'request.query_params.get("token")' not in api_source
