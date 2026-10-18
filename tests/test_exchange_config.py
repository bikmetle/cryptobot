import os
import subprocess
import sys

import pytest


def run_config(**values):
    env = {k: v for k, v in os.environ.items() if k not in {
        "EXCHANGE", "API_KEY", "SECRET_KEY", "PASSPHRASE",
        "BITGET_API_KEY", "BITGET_SECRET_KEY", "BITGET_PASSPHRASE",
    }}
    env.update(PYTHON_DOTENV_DISABLED="1", **values)
    return subprocess.run(
        [sys.executable, "-c", "import trading; from consts import EXCHANGE; print(EXCHANGE, trading.buy_btc.__module__)"],
        env=env, capture_output=True, text=True,
    )


@pytest.mark.parametrize("exchange,expected", [("bitget", "bitget"), ("BINANCE", "binance")])
def test_production_uses_selected_exchange(exchange, expected):
    result = run_config(ENV="PROD", EXCHANGE=exchange)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"{expected} {expected}"


def test_defaults_to_bitget():
    result = run_config(ENV="PROD")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "bitget bitget"


@pytest.mark.parametrize("environment", ["DEV", "TEST"])
def test_simulation_remains_enabled_for_both_exchanges(environment):
    result = run_config(ENV=environment, EXCHANGE="binance")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "binance bitget_mock"


def test_unknown_exchange_fails_instead_of_trading_elsewhere():
    result = run_config(ENV="PROD", EXCHANGE="typo")
    assert result.returncode != 0
    assert "ValueError" in result.stderr


@pytest.mark.parametrize("prefixed", [False, True])
def test_bitget_credentials_keep_legacy_compatibility(prefixed):
    env = dict(os.environ, PYTHON_DOTENV_DISABLED="1", API_KEY="legacy-key",
               SECRET_KEY="legacy-secret", PASSPHRASE="legacy-pass")
    for name in ("API_KEY", "SECRET_KEY", "PASSPHRASE"):
        env.pop(f"BITGET_{name}", None)
        if prefixed:
            env[f"BITGET_{name}"] = "prefixed"
    result = subprocess.run(
        [sys.executable, "-c", "from consts import API_KEY, SECRET_KEY, PASSPHRASE; print(API_KEY, SECRET_KEY, PASSPHRASE)"],
        env=env, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == ("prefixed prefixed prefixed" if prefixed else "legacy-key legacy-secret legacy-pass")
