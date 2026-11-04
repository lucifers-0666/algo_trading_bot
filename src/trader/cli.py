"""Command Line Interface for Indian Equity AI Paper Trading Platform.
Provides terminal commands for validation, screening, backtesting, ML training,
and kill switch control with rich terminal formatting.
"""

import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import argparse
from pathlib import Path
from datetime import datetime
import json
from rich.console import Console
from rich.table import Table

from trader.domain.models import IST, OrderSide, Timeframe
from trader.data.normalizer import normalize_row_to_candle
from trader.data.validation import validate_candle_sequence
from trader.providers.synthetic_provider import SyntheticDataProvider
from trader.providers.csv_provider import CSVDataProvider
from trader.scanner.ranking import MarketScannerEngine
from trader.strategies.baseline import BaselineSwingStrategy
from trader.backtest.engine import BacktestEngine
from trader.ml.dataset import prepare_ml_dataset
from trader.ml.train import train_model
from trader.paper.broker import VirtualPaperBroker
from trader.risk.kill_switch import PersistentKillSwitch
from trader.storage.database import DatabaseManager
from trader.storage.repositories import PortfolioRepository

console = Console(force_terminal=True, legacy_windows=False)


def cmd_validate_data(args):
    """Validates an OHLCV CSV file against structural rules."""
    p = Path(args.file)
    if not p.exists():
        console.print(f"[bold red]File not found:[/bold red] {p}")
        sys.exit(1)

    provider = CSVDataProvider()
    count = provider.load_file(p)
    console.print(f"[bold green]Validation Succeeded![/bold green] Ingested and validated {count} candles from {p.name}")


def cmd_scan(args):
    """Runs market scanners and displays candidates."""
    provider = SyntheticDataProvider(seed=42)
    scanner = MarketScannerEngine(provider=provider)

    table = Table(title=f"NSE Market Scanner — Top Gainers & Momentum")
    table.add_column("Symbol", style="cyan", no_wrap=True)
    table.add_column("Price (₹)", justify="right")
    table.add_column("1D Return", justify="right")
    table.add_column("RVOL", justify="right")
    table.add_column("RSI 14", justify="right")
    table.add_column("Status", style="bold")
    table.add_column("Reason")

    gainers = scanner.scan_top_gainers(limit=args.limit)
    for c in gainers:
        ret_style = "green" if c.pct_change_1d > 0 else "red"
        table.add_row(
            c.symbol,
            f"₹{c.latest_price:,.2f}",
            f"[{ret_style}]{c.pct_change_1d:+.2%}[/{ret_style}]",
            f"{c.rvol:.2f}x",
            f"{c.indicators.get('rsi_14', 50):.1f}",
            "QUALIFIED" if c.is_qualified else "FILTERED",
            c.inclusion_reasons[0] if c.inclusion_reasons else c.exclusion_reasons[0],
        )
    console.print(table)


def cmd_backtest(args):
    """Executes chronological event-driven backtesting."""
    console.print("[cyan]Initializing historical backtest engine with Indian transaction costs...[/cyan]")
    provider = SyntheticDataProvider(seed=42)
    symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN"]
    candles_map = {s: provider.get_historical_candles(s) for s in symbols}

    engine = BacktestEngine(initial_capital=args.capital)
    result = engine.run(candles_map)
    m = result.metrics

    table = Table(title="Backtest Performance Summary")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Initial Capital", f"₹{m.initial_capital:,.2f}")
    table.add_row("Final Equity", f"₹{m.final_equity:,.2f}")
    table.add_row("Net P&L", f"₹{m.net_pnl_inr:+,.2f}")
    table.add_row("Total Return", f"{m.total_return_pct:+.2f}%")
    table.add_row("Win Rate", f"{m.win_rate_pct:.1f}% ({m.winning_trades}/{m.total_trades})")
    table.add_row("Profit Factor", f"{m.profit_factor:.2f}")
    table.add_row("Total Costs Paid", f"₹{m.total_costs_paid_inr:,.2f}")
    table.add_row("Max Drawdown", f"{m.max_drawdown_pct:.2%} (₹{m.max_drawdown_inr:,.2f})")
    table.add_row("Sharpe Ratio", f"{m.sharpe_ratio:.2f}")

    console.print(table)


def cmd_train(args):
    """Trains a walk-forward model."""
    console.print(f"[cyan]Generating features and training {args.model}...[/cyan]")
    provider = SyntheticDataProvider(seed=42)
    candles = provider.get_historical_candles(args.symbol)
    dataset, feats = prepare_ml_dataset(candles, horizon_bars=5)

    model, meta = train_model(
        df=dataset,
        feature_columns=feats,
        model_type=args.model,
        train_ratio=0.70,
        purge_gap_bars=5,
    )
    console.print(f"[bold green]Model trained successfully![/bold green] Model ID: [yellow]{meta.model_id}[/yellow]")
    console.print(f"Accuracy: {meta.metrics['accuracy']:.2%} | ROC AUC: {meta.metrics['roc_auc']:.2f}")


def cmd_status(args):
    """Outputs current portfolio and safety status."""
    db = DatabaseManager()
    pf_repo = PortfolioRepository(db)
    ks = PersistentKillSwitch()

    snapshot = pf_repo.get_latest_snapshot()
    cash = snapshot.cash_balance if snapshot else 10000.0
    equity = snapshot.total_equity if snapshot else 10000.0
    pnl = snapshot.realized_pnl if snapshot else 0.0

    table = Table(title="Indian Equity Paper Trading Platform — System Status")
    table.add_column("Component", style="bold")
    table.add_column("Status / Value")

    table.add_row("Execution Mode", "[yellow]PAPER TRADING ONLY (Simulation)[/yellow]")
    table.add_row("Kill Switch", "[red]HALTED (ENGAGED)[/red]" if ks.is_active() else "[green]NORMAL (ACTIVE)[/green]")
    table.add_row("Virtual Equity", f"₹{equity:,.2f}")
    table.add_row("Cash Balance", f"₹{cash:,.2f}")
    table.add_row("Realized P&L", f"₹{pnl:+,.2f}")

    console.print(table)


def cmd_kill_switch(args):
    """Engages or disengages the persistent emergency kill switch."""
    ks = PersistentKillSwitch()
    action = args.action.lower()
    if action == "on":
        ks.activate("CLI command invocation")
        console.print("[bold red]🚨 KILL SWITCH ENGAGED! All new trading entries are now strictly blocked.[/bold red]")
    elif action == "off":
        ks.deactivate("CLI command invocation")
        console.print("[bold green]✅ KILL SWITCH DISENGAGED! Normal paper trading resumed.[/bold green]")
    else:
        status_str = "ACTIVE (HALTED)" if ks.is_active() else "NORMAL (DISENGAGED)"
        console.print(f"Current Kill Switch State: {status_str}")


def app():
    parser = argparse.ArgumentParser(description="Indian AI Paper Trading CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available sub-commands")

    # validate-data
    p_val = subparsers.add_parser("validate-data", help="Validate an OHLCV CSV file")
    p_val.add_argument("--file", required=True, help="Path to CSV file")

    # scan
    p_scan = subparsers.add_parser("scan", help="Run market screener across universe")
    p_scan.add_argument("--limit", type=int, default=10, help="Number of results to display")

    # backtest
    p_bt = subparsers.add_parser("backtest", help="Execute historical strategy simulation")
    p_bt.add_argument("--capital", type=float, default=10000.0, help="Starting capital in INR")
    p_bt.add_argument("--days", type=int, default=150, help="Lookback days")

    # train
    p_tr = subparsers.add_parser("train", help="Train a leak-free ML model")
    p_tr.add_argument("--symbol", default="RELIANCE", help="Symbol to train on")
    p_tr.add_argument("--model", default="random_forest", choices=["random_forest", "logistic_regression"])
    p_tr.add_argument("--days", type=int, default=150, help="Historical candle days")

    # status
    subparsers.add_parser("status", help="Display portfolio and safety telemetry")

    # kill-switch
    p_ks = subparsers.add_parser("kill-switch", help="Control emergency kill switch")
    p_ks.add_argument("action", choices=["on", "off", "status"], default="status", nargs="?")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "validate-data":
        cmd_validate_data(args)
    elif args.command == "scan":
        cmd_scan(args)
    elif args.command == "backtest":
        cmd_backtest(args)
    elif args.command == "train":
        cmd_train(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "kill-switch":
        cmd_kill_switch(args)


if __name__ == "__main__":
    app()
