"""Institutional Configuration and Settings Provider.
Single source of truth loading configuration from YAML with environment variable overrides.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic import BaseModel, Field


class RiskSettings(BaseModel):
    initial_capital_inr: float = 10000.0
    max_risk_per_trade_pct: float = 0.005  # 0.5% risk per trade
    max_open_positions: int = 2           # Strictly no more than 2 positions
    max_portfolio_exposure_pct: float = 0.50  # 50% max capital exposure
    max_position_size_pct: float = 0.25      # 25% single-stock cap
    daily_loss_limit_pct: float = 0.01        # 1.0% daily equity loss limit
    max_drawdown_pause_pct: float = 0.05      # 5.0% peak equity drawdown halt
    allow_shorting: bool = False
    allow_leverage: bool = False
    allow_pyramiding: bool = False


class TransactionCostSettings(BaseModel):
    brokerage_per_order_inr: float = 20.0
    stt_delivery_pct: float = 0.001
    exchange_txn_charge_pct: float = 0.0000325
    sebi_turnover_charge_pct: float = 0.000001
    stamp_duty_buy_pct: float = 0.00015
    gst_pct: float = 0.18
    default_slippage_bps: float = 10.0  # 10 bps conservative slippage


class GuardSettings(BaseModel):
    stale_data_timeout_seconds: int = 300
    min_stock_price_inr: float = 20.0
    max_stock_price_inr: float = 50000.0
    duplicate_order_window_seconds: int = 60
    kill_switch_file: str = "config/kill_switch.state"


class ExitSettings(BaseModel):
    trailing_stop_enabled: bool = True
    trailing_stop_atr_mult: float = 2.0
    trailing_stop_pct: Optional[float] = None
    max_holding_bars: Optional[int] = 30
    time_stop_minutes: Optional[int] = None


class ServerSecuritySettings(BaseModel):
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_token: Optional[str] = None
    localhost_only: bool = True


class Settings(BaseModel):
    app_env: str = "development"
    app_mode: str = "paper"
    database_url: str = "sqlite:///data/storage/paper_trader.db"
    risk: RiskSettings = Field(default_factory=RiskSettings)
    costs: TransactionCostSettings = Field(default_factory=TransactionCostSettings)
    guards: GuardSettings = Field(default_factory=GuardSettings)
    exits: ExitSettings = Field(default_factory=ExitSettings)
    security: ServerSecuritySettings = Field(default_factory=ServerSecuritySettings)


_cached_settings: Optional[Settings] = None


def load_settings(config_dir: Optional[Path] = None) -> Settings:
    """Loads settings from YAML configuration files and environment overrides."""
    global _cached_settings

    if config_dir is None:
        # Default to repo root config/ directory
        base_dir = Path(__file__).resolve().parent.parent.parent.parent
        config_dir = base_dir / "config"

    risk_dict: Dict[str, Any] = {}
    costs_dict: Dict[str, Any] = {}
    guards_dict: Dict[str, Any] = {}

    risk_file = config_dir / "risk.yaml"
    if not risk_file.exists():
        risk_file = config_dir / "risk.example.yaml"

    if risk_file.exists():
        try:
            with open(risk_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                risk_dict = data.get("risk", {})
                costs_dict = data.get("transaction_costs", {})
                guards_dict = data.get("guards", {})
        except Exception:
            pass

    # Environment overrides
    api_token = os.getenv("NORTHSTAR_API_TOKEN") or None
    app_env = os.getenv("APP_ENV", "development")
    app_mode = os.getenv("APP_MODE", "paper")
    db_url = os.getenv("DATABASE_URL", "sqlite:///data/storage/paper_trader.db")

    settings = Settings(
        app_env=app_env,
        app_mode=app_mode,
        database_url=db_url,
        risk=RiskSettings(**risk_dict),
        costs=TransactionCostSettings(**costs_dict),
        guards=GuardSettings(**guards_dict),
        exits=ExitSettings(),
        security=ServerSecuritySettings(
            api_host=os.getenv("API_HOST", "127.0.0.1"),
            api_port=int(os.getenv("API_PORT", "8000")),
            api_token=api_token,
            localhost_only=True,
        ),
    )
    _cached_settings = settings
    return settings


def get_settings() -> Settings:
    """Singleton getter for application settings."""
    global _cached_settings
    if _cached_settings is None:
        _cached_settings = load_settings()
    return _cached_settings
