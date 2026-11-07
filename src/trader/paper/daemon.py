"""Autonomous Paper Trading Daemon.
Monitors Indian market hours, scans for quantitative alpha setups, evaluates
risk guardrails and protections, and automatically executes simulated paper trades.
STRICTLY SIMULATED PAPER TRADING ONLY. NO REAL ORDER ROUTING.
"""

import asyncio
import logging
from collections import deque
from datetime import datetime
from typing import Dict, Any, List, Optional
import threading
import time

from trader.domain.models import IST, OrderSide, OrderType, DataSource
from trader.data.calendar import default_nse_calendar
from trader.data.freshness import evaluate_feed_freshness, FreshnessReport, FeedStatus
from trader.paper.broker import VirtualPaperBroker
from trader.decision.decision_engine import DecisionEngine
from trader.scanner.ranking import MarketScannerEngine
from trader.risk.checks import RiskManager
from trader.strategies.protections import RiskProtectionManager

logger = logging.getLogger(__name__)


class AutonomousPaperTradingDaemon:
    """Background execution runner for automated paper trading in Indian equities."""

    def __init__(
        self,
        broker: VirtualPaperBroker,
        decision_engine: DecisionEngine,
        scanner_engine: MarketScannerEngine,
        risk_manager: RiskManager,
        protection_manager: RiskProtectionManager,
        scan_interval_seconds: int = 30,
        max_log_entries: int = 100,
    ):
        self.broker = broker
        self.decision_engine = decision_engine
        self.scanner_engine = scanner_engine
        self.risk_manager = risk_manager
        self.protection_manager = protection_manager
        self.scan_interval_seconds = scan_interval_seconds

        self._is_running = False
        self._force_market_open = False  # Defaults to False: explicit opt-in only for testing
        self.trailing_stop_enabled = True
        self.trailing_stop_atr_mult = 2.0
        self.max_holding_bars: Optional[int] = 30
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._last_scan_time: Optional[datetime] = None
        self._total_auto_trades = 0
        self._logs: deque[Dict[str, Any]] = deque(maxlen=max_log_entries)

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def force_market_open(self) -> bool:
        return self._force_market_open

    @force_market_open.setter
    def force_market_open(self, val: bool) -> None:
        self._force_market_open = bool(val)

    def _log_event(self, event_type: str, symbol: Optional[str], message: str, details: Optional[Dict[str, Any]] = None) -> None:
        entry = {
            "timestamp": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST"),
            "event_type": event_type,
            "symbol": symbol or "MARKET",
            "message": message,
            "details": details or {},
        }
        self._logs.appendleft(entry)
        logger.info(f"[AUTOBOT {event_type}] {symbol or 'GLOBAL'}: {message}")

    def get_status(self) -> Dict[str, Any]:
        now_ist = datetime.now(IST)
        market_open = default_nse_calendar.is_market_open(now_ist)
        open_positions = list(self.broker.accountant.positions.values())

        return {
            "is_running": self._is_running,
            "force_market_open": self._force_market_open,
            "scan_interval_seconds": self.scan_interval_seconds,
            "is_market_hours": market_open,
            "effective_market_active": market_open or self._force_market_open,
            "last_scan_time": self._last_scan_time.strftime("%Y-%m-%d %H:%M:%S IST") if self._last_scan_time else None,
            "open_positions_count": len(open_positions),
            "cash_balance": round(self.broker.accountant.cash_balance, 2),
            "total_equity": round(self.broker.accountant.get_portfolio_state().total_equity, 2),
            "total_auto_trades": self._total_auto_trades,
            "recent_logs": list(self._logs)[:25],
        }

    def start(self) -> None:
        if self._is_running:
            return
        self._stop_event.clear()
        self._is_running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="AutoPaperTraderDaemon")
        self._thread.start()
        self._log_event("SYSTEM", None, "Autonomous paper trading daemon started.")

    def stop(self) -> None:
        if not self._is_running:
            return
        self._stop_event.set()
        self._is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._log_event("SYSTEM", None, "Autonomous paper trading daemon stopped.")

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.run_iteration()
            except Exception as e:
                logger.error(f"Error in auto paper trading cycle: {e}", exc_info=True)
                self._log_event("ERROR", None, f"Execution cycle error: {str(e)}")

            # Sleep in small increments for responsive stop
            for _ in range(self.scan_interval_seconds * 2):
                if self._stop_event.is_set():
                    break
                time.sleep(0.5)

    def run_iteration(self) -> Dict[str, Any]:
        """Runs a complete evaluation and paper execution cycle."""
        now_ist = datetime.now(IST)
        self._last_scan_time = now_ist
        is_mkt_open = default_nse_calendar.is_market_open(now_ist)

        if not is_mkt_open and not self._force_market_open:
            self._log_event("STANDBY", None, "NSE market is currently closed. Auto-trading in standby.")
            return {"status": "market_closed"}

        # Check Kill Switch
        if self.risk_manager.kill_switch.is_active():
            reason = self.risk_manager.kill_switch.get_reason() or "Emergency kill switch active"
            self._log_event("HALT", None, f"Kill switch active: {reason}. Skipping buy proposals.")
            # Still monitor open positions for emergency stops
            self._evaluate_open_positions()
            return {"status": "kill_switch_active", "reason": reason}

        # Step 1: Manage open positions (Check stop loss, profit targets)
        closed_positions = self._evaluate_open_positions()

        # Step 2: Check risk constraints for new entries
        positions = list(self.broker.accountant.positions.values())
        if len(positions) >= self.risk_manager.max_open_positions:
            self._log_event("RISK_LIMIT", None, f"Maximum positions limit reached ({len(positions)}/{self.risk_manager.max_open_positions}). No new entries.")
            return {"status": "max_positions_reached", "closed": closed_positions}

        if self.broker.accountant.cash_balance < 500.0:
            self._log_event("RISK_LIMIT", None, f"Insufficient cash (₹{self.broker.accountant.cash_balance:.2f}) for new paper positions.")
            return {"status": "insufficient_cash", "closed": closed_positions}

        # Step 3: Scan candidate equities
        provider = self.scanner_engine.provider
        self.scanner_engine.refresh_snapshot()
        candidates = self.scanner_engine.scan_top_gainers() + self.scanner_engine.scan_momentum()
        
        # Deduplicate candidate symbols
        seen_syms = set(p.symbol for p in positions)
        unique_candidates = []
        for c in candidates:
            sym = c.symbol.upper()
            if sym not in seen_syms:
                seen_syms.add(sym)
                unique_candidates.append(c)

        if not unique_candidates:
            self._log_event("SCAN", None, "Scan cycle complete: No eligible candidates outside current holdings.")
            return {"status": "no_candidates", "closed": closed_positions}

        # Step 4: Evaluate candidates through Decision Support Engine
        executed_orders = []
        for cand in unique_candidates[:4]:  # Evaluate top 4 candidates
            sym = cand.symbol.upper()

            # Check symbol cooldown protection
            if self.protection_manager.is_symbol_in_cooldown(sym):
                self._log_event("PROTECTION", sym, f"Symbol {sym} is in cooldown after stop-loss exit. Skipping.")
                continue

            # Run decision engine on bar close (t)
            try:
                dossier = self.decision_engine.evaluate(
                    symbol=sym,
                    strategy_name="baseline",
                    provider=provider,
                    portfolio=self.broker.accountant.get_portfolio_state(),
                    open_positions=list(self.broker.accountant.positions.values()),
                )
            except Exception as e:
                logger.warning(f"Failed to evaluate decision for {sym}: {e}")
                continue

            # High conviction threshold: >= 60 and APPROVE
            if dossier.action in ("APPROVE", "APPROVE_PAPER_BUY") and dossier.conviction_score >= 60.0:
                # Real Feed Freshness Verification on latest quote (t+1 entry fill)
                try:
                    quote = provider.get_latest_quote(sym)
                    source_label = quote.source.value if hasattr(quote, "source") else "UNKNOWN"
                    freshness = evaluate_feed_freshness(
                        last_update=quote.timestamp,
                        source_type=source_label,
                        is_configured=getattr(provider, "is_configured", True),
                        is_connected=getattr(provider, "_is_connected", True),
                        force_market_open=self._force_market_open,
                    )
                except Exception as e:
                    self._log_event(
                        "DATA_ERROR_GUARD",
                        sym,
                        f"Live quote retrieval failed for {sym}: {e}. Halting auto-buy entry.",
                    )
                    continue

                if not freshness.is_actionable:
                    self._log_event(
                        "STALE_FEED_GUARD",
                        sym,
                        f"Skipping auto-buy for {sym}: Data feed {freshness.status.value} is not actionable ({freshness.message}). Forbidding entry on stale data.",
                    )
                    continue

                current_price = quote.ltp
                stop_loss = dossier.stop_loss or round(current_price * 0.97, 2)
                target = dossier.target or round(current_price * 1.06, 2)

                try:
                    order, trade, assessment = self.broker.submit_simulated_order(
                        symbol=sym,
                        side=OrderSide.BUY,
                        price=current_price,
                        stop_loss=stop_loss,
                        target=target,
                        trailing_stop_atr_mult=self.trailing_stop_atr_mult if self.trailing_stop_enabled else None,
                        feed_freshness=freshness,
                    )

                    if assessment.approved and trade:
                        self._total_auto_trades += 1
                        self.protection_manager.record_trade(trade)
                        forced_tag = " [FORCED_MARKET_OPEN]" if self._force_market_open else ""
                        executed_orders.append({
                            "symbol": sym,
                            "quantity": trade.quantity,
                            "price": trade.price,
                            "conviction": dossier.conviction_score,
                            "forced_market_open": self._force_market_open,
                        })
                        self._log_event(
                            "AUTO_BUY",
                            sym,
                            f"Auto paper BUY executed{forced_tag}: {trade.quantity} shares of {sym} at ₹{trade.price:.2f} (Conviction: {dossier.conviction_score}/100, Stop: ₹{stop_loss:.2f})",
                            {
                                "order_id": order.order_id,
                                "quantity": trade.quantity,
                                "price": trade.price,
                                "conviction": dossier.conviction_score,
                                "forced_market_open": self._force_market_open,
                            },
                        )
                        # Avoid opening too many positions in a single cycle
                        if len(self.broker.accountant.positions) >= self.risk_manager.max_open_positions:
                            break
                    else:
                        reasons = ", ".join(assessment.rejection_reasons)
                        self._log_event("RISK_REJECT", sym, f"Risk rejected buy for {sym}: {reasons}")
                except Exception as ex:
                    logger.error(f"Error submitting auto paper order for {sym}: {ex}")
            else:
                self._log_event("DECISION_SKIP", sym, f"Candidate {sym} conviction {dossier.conviction_score}/100 ({dossier.action}) below auto-buy threshold.")

        return {
            "status": "success",
            "executed": executed_orders,
            "closed": closed_positions,
        }

    def _evaluate_open_positions(self) -> List[Dict[str, Any]]:
        """Evaluates active holdings and automatically closes positions hitting stop-loss or profit targets.
        Strictly requires fresh actionable quotes during active market hours; refuses to trigger stop losses
        on unverified historical candle closes.
        """
        closed = []
        positions = list(self.broker.accountant.positions.values())
        provider = self.scanner_engine.provider

        for pos in positions:
            sym = pos.symbol.upper()
            try:
                quote = provider.get_latest_quote(sym)
                source_label = quote.source.value if hasattr(quote, "source") else "UNKNOWN"
                freshness = evaluate_feed_freshness(
                    last_update=quote.timestamp,
                    source_type=source_label,
                    is_configured=getattr(provider, "is_configured", True),
                    is_connected=getattr(provider, "_is_connected", True),
                    force_market_open=self._force_market_open,
                )
                if not freshness.is_actionable:
                    self._log_event(
                        "STALE_FEED_GUARD",
                        sym,
                        f"Skipping stop-loss evaluation for {sym}: Data feed {freshness.status.value} is not actionable ({freshness.message}). Forbidding exit on stale data.",
                    )
                    continue
                current_price = quote.ltp
            except Exception as e:
                self._log_event(
                    "DATA_ERROR_GUARD",
                    sym,
                    f"Live quote retrieval failed for {sym}: {e}. Halting position evaluation; refusing to execute stop-loss on historical fallback.",
                )
                continue

            # Update position mark-to-market and holding count
            pos.holding_bars += 1
            pos.update_market_price(current_price)
            self.broker.accountant.update_unrealized_pnl(sym, current_price)

            # ATR trailing stop ratcheting (monotonically non-decreasing)
            if self.trailing_stop_enabled:
                atr = None
                mult = pos.trailing_stop_atr_mult or self.trailing_stop_atr_mult or 2.0
                if hasattr(provider, "get_historical_candles"):
                    try:
                        candles = provider.get_historical_candles(sym)
                        if candles and len(candles) >= 14:
                            from trader.indicators.technical import TechnicalIndicatorEngine
                            df = TechnicalIndicatorEngine.candles_to_dataframe(candles)
                            df = TechnicalIndicatorEngine.add_atr(df, period=14)
                            last_atr = float(df["atr_14"].iloc[-1])
                            if last_atr > 0:
                                atr = last_atr
                    except Exception:
                        pass

                if atr is not None and atr > 0:
                    candidate_stop = round(pos.highest_price - (atr * mult), 2)
                else:
                    candidate_stop = round(pos.highest_price * 0.97, 2)

                if pos.stop_loss is None or candidate_stop > pos.stop_loss:
                    old_stop = pos.stop_loss
                    pos.stop_loss = candidate_stop
                    if self.broker.accountant.position_repo:
                        self.broker.accountant.position_repo.save_position(pos)
                    if old_stop is not None and candidate_stop > old_stop:
                        self._log_event(
                            "TRAILING_STOP_UPDATE",
                            sym,
                            f"Trailing stop ratcheted up for {sym}: ₹{old_stop:.2f} -> ₹{candidate_stop:.2f} (High: ₹{pos.highest_price:.2f})",
                            {"highest_price": pos.highest_price, "new_stop": candidate_stop},
                        )

            # Check exit conditions
            exit_triggered = False
            exit_reason = ""
            event_type = ""
            exit_msg = ""

            # 1. Stop-Loss / Trailing Stop
            if pos.stop_loss is not None and current_price <= pos.stop_loss:
                exit_triggered = True
                is_trailing = pos.stop_loss > pos.average_entry_price
                exit_reason = "TRAILING_STOP" if is_trailing else "STOP_LOSS"
                event_type = "AUTO_SELL_TRAILING_STOP" if is_trailing else "AUTO_SELL_STOP"
                exit_msg = (
                    f"Trailing-stop hit for {sym} at ₹{current_price:.2f} (Stop was ₹{pos.stop_loss:.2f}). Closed {pos.quantity} shares."
                    if is_trailing
                    else f"Stop-loss hit for {sym} at ₹{current_price:.2f} (Stop was ₹{pos.stop_loss:.2f}). Closed {pos.quantity} shares."
                )

            # 2. Profit target
            elif pos.target is not None and current_price >= pos.target:
                exit_triggered = True
                exit_reason = "PROFIT_TARGET"
                event_type = "AUTO_SELL_TARGET"
                exit_msg = f"Profit target reached for {sym} at ₹{current_price:.2f} (Target was ₹{pos.target:.2f}). Closed {pos.quantity} shares."

            # 3. Time stop
            elif self.max_holding_bars is not None and pos.holding_bars >= self.max_holding_bars:
                exit_triggered = True
                exit_reason = "TIME_STOP"
                event_type = "AUTO_SELL_TIME_STOP"
                exit_msg = f"Time-stop reached for {sym} after {pos.holding_bars} evaluation cycles. Closed {pos.quantity} shares at ₹{current_price:.2f}."

            if exit_triggered:
                try:
                    order, trade, _ = self.broker.submit_simulated_order(
                        symbol=sym,
                        side=OrderSide.SELL,
                        price=current_price,
                        quantity=pos.quantity,
                    )
                    if trade:
                        self._total_auto_trades += 1
                        self.protection_manager.record_trade(trade)
                        forced_tag = " [FORCED_MARKET_OPEN]" if self._force_market_open else ""
                        closed.append({
                            "symbol": sym,
                            "reason": exit_reason,
                            "price": current_price,
                            "forced_market_open": self._force_market_open,
                        })
                        self._log_event(
                            event_type,
                            sym,
                            f"{exit_msg}{forced_tag}",
                            {
                                "realized_pnl": trade.realized_pnl,
                                "reason": exit_reason,
                                "forced_market_open": self._force_market_open,
                            },
                        )
                except Exception as e:
                    logger.error(f"Failed to execute {exit_reason} sell for {sym}: {e}")

        return closed

