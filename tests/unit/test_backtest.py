"""Unit tests for Indian Equity Backtesting Engine and Transaction Costs."""

from trader.domain.models import OrderSide
from trader.backtest.costs import calculate_trade_costs
from trader.backtest.metrics import compute_performance_metrics
from trader.backtest.engine import BacktestEngine
from trader.data.synthetic import generate_synthetic_candles


def test_transaction_costs_indian_equities():
    # Buy ₹10,000 worth of shares (10 shares @ ₹1,000, 0 slippage for exact math)
    costs_buy = calculate_trade_costs(
        side=OrderSide.BUY,
        price=1000.0,
        quantity=10,
        brokerage_flat=20.0,
        slippage_bps=0.0,
    )
    assert costs_buy.gross_trade_value == 10000.0
    assert costs_buy.stt_inr == 10.0 # 0.1%
    assert costs_buy.stamp_duty_inr == 1.50 # 0.0015%
    assert costs_buy.exchange_charges_inr == 0.30  # 0.00297% (NSE Oct 2024 circular)
    assert costs_buy.brokerage_inr == 5.0 # Min of flat 20 or 0.05% of 10k = 5
    assert costs_buy.gst_inr > 0.0
    assert costs_buy.net_trade_amount > costs_buy.gross_trade_value

    # Sell ₹10,000 worth of shares: Stamp duty must be 0 in India
    costs_sell = calculate_trade_costs(
        side=OrderSide.SELL,
        price=1000.0,
        quantity=10,
        brokerage_flat=20.0,
        slippage_bps=0.0,
    )
    assert costs_sell.stamp_duty_inr == 0.0
    assert costs_sell.stt_inr == 10.0
    assert costs_sell.net_trade_amount < costs_sell.gross_trade_value


def test_performance_metrics_calculation():
    initial = 10000.0
    equity_series = [
        {"equity": 10000.0},
        {"equity": 10200.0},
        {"equity": 10100.0},
        {"equity": 10400.0},
    ]
    trade_logs = [
        {"is_closed": True, "net_pnl": 200.0, "gross_pnl": 250.0, "costs_inr": 50.0},
        {"is_closed": True, "net_pnl": -100.0, "gross_pnl": -60.0, "costs_inr": 40.0},
        {"is_closed": True, "net_pnl": 300.0, "gross_pnl": 340.0, "costs_inr": 40.0},
    ]
    metrics = compute_performance_metrics(initial, equity_series, trade_logs)

    assert metrics.final_equity == 10400.0
    assert metrics.net_pnl_inr == 400.0
    assert metrics.total_trades == 3
    assert metrics.winning_trades == 2
    assert metrics.losing_trades == 1
    assert metrics.win_rate_pct == round((2.0 / 3.0) * 100, 2)
    assert metrics.profit_factor == 5.0 # 500 / 100
    assert metrics.total_costs_paid_inr == 130.0
    assert metrics.max_drawdown_inr == 100.0


def test_backtest_engine_run_synthetic():
    c_rel = generate_synthetic_candles("RELIANCE", num_days=120, seed=10)
    c_tcs = generate_synthetic_candles("TCS", num_days=120, seed=20)

    engine = BacktestEngine(initial_capital=10000.0, max_open_positions=2)
    res = engine.run({"RELIANCE": c_rel, "TCS": c_tcs})

    assert len(res.equity_curve) > 50
    # At every single bar: open_positions <= 2
    for pt in res.equity_curve:
        assert pt["open_positions"] <= 2
        assert pt["cash"] >= 0.0
        assert round(pt["cash"] + pt["exposure"], 2) == pt["equity"]

    # Verify gross P&L is strictly greater than or equal to net P&L
    assert res.metrics.gross_pnl_inr >= res.metrics.net_pnl_inr
