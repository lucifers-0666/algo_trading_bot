"""Chronological Event-Driven Backtesting Engine for Indian Equities.
Simulates realistic order execution at next-bar open (t+1) from signals evaluated on bar close (t).
Incorporates complete Indian statutory transaction costs, slippage, and portfolio risk sizing.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import pandas as pd

from trader.domain.models import Candle, OrderSide, IST
from trader.features.technical import candles_to_dataframe, compute_all_indicators
from trader.strategies.baseline import BaselineSwingStrategy, StrategySignal, SignalType
from trader.backtest.costs import calculate_trade_costs, TradeCostBreakdown
from trader.backtest.metrics import PerformanceMetrics, compute_performance_metrics
from trader.risk.sizing import calculate_position_size


class BacktestTradeRecord(BaseModel):
    symbol: str
    entry_date: datetime
    exit_date: Optional[datetime] = None
    entry_price: float
    exit_price: Optional[float] = None
    quantity: int
    entry_costs: float
    exit_costs: float = 0.0
    entry_slippage: float = 0.0
    exit_slippage: float = 0.0
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    return_pct: float = 0.0
    holding_bars: int = 0
    exit_reason: str = ""
    is_closed: bool = False


class BacktestResult(BaseModel):
    metrics: PerformanceMetrics
    equity_curve: List[Dict[str, Any]]
    trade_records: List[BacktestTradeRecord]


class BacktestEngine:
    """Event-driven chronological backtest simulator."""

    def __init__(
        self,
        strategy: Optional[BaselineSwingStrategy] = None,
        initial_capital: float = 10000.0,
        max_open_positions: int = 2,
        max_risk_pct: float = 0.005,
        max_position_size_pct: float = 0.25,
        max_portfolio_exposure_pct: float = 0.50,
        slippage_bps: float = 10.0,
        brokerage_flat: float = 20.0,
        trailing_stop_enabled: bool = False,
        trailing_stop_atr_mult: float = 2.0,
        max_holding_bars: Optional[int] = None,
    ):
        self.strategy = strategy or BaselineSwingStrategy()
        self.initial_capital = initial_capital
        self.max_open_positions = max_open_positions
        self.max_risk_pct = max_risk_pct
        self.max_position_size_pct = max_position_size_pct
        self.max_portfolio_exposure_pct = max_portfolio_exposure_pct
        self.slippage_bps = slippage_bps
        self.brokerage_flat = brokerage_flat
        self.trailing_stop_enabled = trailing_stop_enabled or getattr(self.strategy, "trailing_stop_enabled", False)
        self.trailing_stop_atr_mult = trailing_stop_atr_mult
        self.max_holding_bars = max_holding_bars or getattr(self.strategy, "max_holding_candles", None)

    def run(self, symbol_candles_map: Dict[str, List[Candle]]) -> BacktestResult:
        """Executes chronological multi-symbol simulation across all candle dates."""
        # 1. Prepare indicator dataframes for all symbols
        symbol_dfs: Dict[str, pd.DataFrame] = {}
        all_dates = set()

        for sym, candles in symbol_candles_map.items():
            if len(candles) >= 55:
                df = candles_to_dataframe(candles)
                df_ind = compute_all_indicators(df)
                symbol_dfs[sym] = df_ind
                all_dates.update(df_ind["timestamp"].tolist())

        sorted_dates = sorted(list(all_dates))
        if not sorted_dates:
            metrics = compute_performance_metrics(self.initial_capital, [], [])
            return BacktestResult(metrics=metrics, equity_curve=[], trade_records=[])

        # State tracking
        cash = self.initial_capital
        open_trades: Dict[str, Dict[str, Any]] = {} # symbol -> trade dict
        closed_trades: List[BacktestTradeRecord] = []
        equity_curve: List[Dict[str, Any]] = []
        pending_orders: List[Dict[str, Any]] = [] # Signals from t to execute on t+1 open

        for current_idx, current_date in enumerate(sorted_dates):
            # -------------------------------------------------------------
            # STEP A: Execute pending entry orders generated on previous bar (t-1)
            # -------------------------------------------------------------
            for ord_req in pending_orders:
                sym = ord_req["symbol"]
                if sym in open_trades:
                    continue # Already open

                if len(open_trades) >= self.max_open_positions:
                    continue # Positions full

                df_sym = symbol_dfs.get(sym)
                if df_sym is None:
                    continue

                bar_row = df_sym[df_sym["timestamp"] == current_date]
                if bar_row.empty:
                    continue

                open_price = float(bar_row.iloc[0]["open"])
                high_price = float(bar_row.iloc[0]["high"])
                low_price = float(bar_row.iloc[0]["low"])
                close_price = float(bar_row.iloc[0]["close"])
                bar_vol = float(bar_row.iloc[0].get("volume", 1.0))

                # Circuit limit check on entry: cannot enter if circuit-locked or zero volume
                if (high_price == low_price and open_price == close_price) or bar_vol <= 0:
                    continue

                stop_loss = ord_req["stop_loss"]

                # Recompute sizing at actual execution open price
                curr_exposure = sum(t["quantity"] * t["current_price"] for t in open_trades.values())
                curr_equity = cash + curr_exposure
                sizing = calculate_position_size(
                    entry_price=open_price,
                    stop_loss=stop_loss,
                    total_equity=curr_equity,
                    cash_balance=cash,
                    max_risk_pct=self.max_risk_pct,
                    max_position_size_pct=self.max_position_size_pct,
                    max_portfolio_exposure_pct=self.max_portfolio_exposure_pct,
                    current_invested_capital=curr_exposure,
                )

                if sizing.approved and sizing.quantity > 0:
                    cost_breakdown = calculate_trade_costs(
                        side=OrderSide.BUY,
                        price=open_price,
                        quantity=sizing.quantity,
                        brokerage_flat=self.brokerage_flat,
                        slippage_bps=self.slippage_bps,
                    )
                    if cash >= cost_breakdown.net_trade_amount:
                        cash -= cost_breakdown.net_trade_amount
                        open_trades[sym] = {
                            "symbol": sym,
                            "entry_date": current_date,
                            "entry_price": cost_breakdown.effective_price,
                            "quantity": sizing.quantity,
                            "stop_loss": stop_loss,
                            "target": ord_req.get("target"),
                            "highest_price": open_price,
                            "entry_costs": cost_breakdown.total_costs_inr,
                            "entry_slippage": cost_breakdown.slippage_inr,
                            "holding_bars": 0,
                            "current_price": open_price,
                        }

            pending_orders.clear()

            # -------------------------------------------------------------
            # STEP B: Manage active positions (Exits & Mark-to-Market)
            # -------------------------------------------------------------
            symbols_to_close = []
            for sym, t_data in open_trades.items():
                df_sym = symbol_dfs.get(sym)
                bar_row = df_sym[df_sym["timestamp"] == current_date]
                if bar_row.empty:
                    continue

                bar = bar_row.iloc[0]
                bar_open = float(bar["open"])
                bar_high = float(bar["high"])
                bar_low = float(bar["low"])
                bar_close = float(bar["close"])
                bar_vol = float(bar.get("volume", 1.0))

                t_data["current_price"] = bar_close
                t_data["holding_bars"] += 1

                # Circuit limit check: if stock is locked or no volume, cannot execute exit today
                if (bar_high == bar_low and bar_open == bar_close) or bar_vol <= 0:
                    continue

                # Active stop-loss and profit target coming into this bar (no look-ahead)
                stop_loss = t_data.get("stop_loss")
                target = t_data.get("target")

                exit_triggered = False
                nominal_exit = bar_close
                exit_reason = ""

                # 1. Intrabar Stop-Loss & Target Check
                stop_hit = stop_loss is not None and bar_low <= stop_loss
                target_hit = target is not None and bar_high >= target

                if stop_hit and target_hit:
                    exit_triggered = True
                    exit_reason = "Stop-loss hit (Intrabar collision, conservative assumption)"
                    nominal_exit = bar_open if bar_open <= stop_loss else stop_loss
                elif stop_hit:
                    exit_triggered = True
                    is_trailing = stop_loss > t_data["entry_price"]
                    exit_reason = "Trailing-stop triggered" if is_trailing else "Stop-loss triggered"
                    nominal_exit = bar_open if bar_open <= stop_loss else stop_loss
                elif target_hit:
                    exit_triggered = True
                    exit_reason = "Target reached"
                    nominal_exit = bar_open if bar_open >= target else target
                elif self.max_holding_bars is not None and t_data["holding_bars"] >= self.max_holding_bars:
                    exit_triggered = True
                    exit_reason = f"Time-stop reached ({t_data['holding_bars']} bars)"
                    nominal_exit = bar_open
                else:
                    # 2. Slice historical slice up to current bar to evaluate strategy technical exit on close
                    slice_df = df_sym[df_sym["timestamp"] <= current_date]
                    exit_sig = self.strategy.evaluate_exit(
                        df_ind=slice_df,
                        entry_price=t_data["entry_price"],
                        stop_loss=t_data["stop_loss"],
                        target=t_data.get("target"),
                        holding_candles=t_data["holding_bars"],
                    )
                    if exit_sig is not None and exit_sig.signal_type == SignalType.SELL:
                        exit_triggered = True
                        nominal_exit = exit_sig.metrics.get("exit_price", bar_close)
                        exit_reason = exit_sig.reason

                # Ratchet trailing stop on bar close ONLY if position survived this bar
                if not exit_triggered:
                    if bar_high > t_data.get("highest_price", 0.0):
                        t_data["highest_price"] = bar_high
                    if self.trailing_stop_enabled:
                        atr = float(bar.get("atr_14", 0.0))
                        if atr > 0:
                            candidate_stop = round(t_data["highest_price"] - (atr * self.trailing_stop_atr_mult), 2)
                        else:
                            candidate_stop = round(t_data["highest_price"] * 0.97, 2)
                        if t_data.get("stop_loss") is None or candidate_stop > t_data["stop_loss"]:
                            t_data["stop_loss"] = candidate_stop

                if exit_triggered:
                    cost_breakdown = calculate_trade_costs(
                        side=OrderSide.SELL,
                        price=nominal_exit,
                        quantity=t_data["quantity"],
                        brokerage_flat=self.brokerage_flat,
                        slippage_bps=self.slippage_bps,
                    )
                    cash += cost_breakdown.net_trade_amount

                    gross_pnl = round((cost_breakdown.effective_price - t_data["entry_price"]) * t_data["quantity"], 2)
                    total_trade_costs = round(t_data["entry_costs"] + cost_breakdown.total_costs_inr, 2)
                    net_pnl = round(gross_pnl - total_trade_costs, 2)
                    ret_pct = round((net_pnl / (t_data["entry_price"] * t_data["quantity"])) * 100.0, 2)

                    closed_rec = BacktestTradeRecord(
                        symbol=sym,
                        entry_date=t_data["entry_date"],
                        exit_date=current_date,
                        entry_price=t_data["entry_price"],
                        exit_price=cost_breakdown.effective_price,
                        quantity=t_data["quantity"],
                        entry_costs=t_data["entry_costs"],
                        exit_costs=cost_breakdown.total_costs_inr,
                        entry_slippage=t_data.get("entry_slippage", 0.0),
                        exit_slippage=cost_breakdown.slippage_inr,
                        gross_pnl=gross_pnl,
                        net_pnl=net_pnl,
                        return_pct=ret_pct,
                        holding_bars=t_data["holding_bars"],
                        exit_reason=exit_reason,
                        is_closed=True,
                    )
                    closed_trades.append(closed_rec)
                    symbols_to_close.append(sym)

            for sym in symbols_to_close:
                del open_trades[sym]

            # -------------------------------------------------------------
            # STEP C: Evaluate new entries on completed bar close (t)
            # -------------------------------------------------------------
            if len(open_trades) < self.max_open_positions:
                for sym, df_sym in symbol_dfs.items():
                    if sym in open_trades:
                        continue

                    slice_df = df_sym[df_sym["timestamp"] <= current_date]
                    if len(slice_df) < 55:
                        continue

                    sig = self.strategy.evaluate_entry(slice_df)
                    if sig is not None and sig.signal_type == SignalType.BUY:
                        pending_orders.append({
                            "symbol": sym,
                            "stop_loss": sig.suggested_stop_loss,
                            "target": sig.suggested_target,
                            "signal_date": current_date,
                        })

            # Record portfolio mark-to-market equity
            market_exposure = sum(t["quantity"] * t["current_price"] for t in open_trades.values())
            total_equity = round(cash + market_exposure, 2)
            equity_curve.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "timestamp": current_date.isoformat(),
                "cash": round(cash, 2),
                "exposure": round(market_exposure, 2),
                "equity": total_equity,
                "open_positions": len(open_trades),
            })

        # Explicit end-of-test mark-to-market valuation for remaining open positions
        if sorted_dates:
            last_dt = sorted_dates[-1]
            for sym, t_data in open_trades.items():
                # Keep an open position marked to the final close. Do not book a
                # hypothetical exit fee/slippage as a paid cost or fabricate an exit fill.
                gross_pnl = round(
                    (t_data["current_price"] - t_data["entry_price"]) * t_data["quantity"], 2
                )
                net_pnl = round(gross_pnl - t_data["entry_costs"], 2)
                ret_pct = round(
                    (net_pnl / (t_data["entry_price"] * t_data["quantity"])) * 100.0, 2
                )

                open_rec = BacktestTradeRecord(
                    symbol=sym,
                    entry_date=t_data["entry_date"],
                    exit_date=None,
                    entry_price=t_data["entry_price"],
                    exit_price=None,
                    quantity=t_data["quantity"],
                    entry_costs=t_data["entry_costs"],
                    exit_costs=0.0,
                    entry_slippage=t_data.get("entry_slippage", 0.0),
                    exit_slippage=0.0,
                    gross_pnl=gross_pnl,
                    net_pnl=net_pnl,
                    return_pct=ret_pct,
                    holding_bars=t_data["holding_bars"],
                    exit_reason="END_OF_TEST_OPEN_MTM",
                    is_closed=False,
                )
                closed_trades.append(open_rec)

        # Calculate institutional metrics
        trade_logs_for_metrics = [
            {
                "is_closed": r.is_closed,
                "net_pnl": r.net_pnl,
                "gross_pnl": r.gross_pnl,
                "costs_inr": r.entry_costs + r.exit_costs,
                "slippage_inr": r.entry_slippage + r.exit_slippage,
            }
            for r in closed_trades
        ]
        metrics = compute_performance_metrics(self.initial_capital, equity_curve, trade_logs_for_metrics)

        return BacktestResult(
            metrics=metrics,
            equity_curve=equity_curve,
            trade_records=closed_trades,
        )

