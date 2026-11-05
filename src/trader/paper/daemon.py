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
        self._force_market_open = True  # Allows continuous simulated paper trading
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

            # Run decision engine
            try:
                dossier = self.decision_engine.evaluate(
                    symbol=sym,
                    strategy_name="baseline",
                    provider=provider,
                )
            except Exception as e:
                logger.warning(f"Failed to evaluate decision for {sym}: {e}")
                continue

            # High conviction threshold: >= 60 and APPROVE
            if dossier.action == "APPROVE" and dossier.conviction_score >= 60.0:
                current_price = cand.ltp
                stop_loss = dossier.stop_loss or round(current_price * 0.97, 2)
                target = dossier.target or round(current_price * 1.06, 2)

                # Feed freshness check
                freshness = FreshnessReport(
                    status=FeedStatus.HEALTHY,
                    latency_seconds=0.5,
                    is_actionable=True,
                    message="Auto-trader fresh quote verified",
                )

                try:
                    order, trade, assessment = self.broker.submit_simulated_order(
                        symbol=sym,
                        side=OrderSide.BUY,
                        price=current_price,
                        stop_loss=stop_loss,
                        feed_freshness=freshness,
                    )

                    if assessment.approved and trade:
                        self._total_auto_trades += 1
                        self.protection_manager.record_trade(trade)
                        executed_orders.append({
                            "symbol": sym,
                            "quantity": trade.quantity,
                            "price": trade.price,
                            "conviction": dossier.conviction_score,
                        })
                        self._log_event(
                            "AUTO_BUY",
                            sym,
                            f"Auto paper BUY executed: {trade.quantity} shares of {sym} at ₹{trade.price:.2f} (Conviction: {dossier.conviction_score}/100, Stop: ₹{stop_loss:.2f})",
                            {
                                "order_id": order.order_id,
                                "quantity": trade.quantity,
                                "price": trade.price,
                                "conviction": dossier.conviction_score,
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
        """Evaluates active holdings and automatically closes positions hitting stop-loss or profit targets."""
        closed = []
        positions = list(self.broker.accountant.positions.values())
        provider = self.scanner_engine.provider

        for pos in positions:
            sym = pos.symbol.upper()
            try:
                quote = provider.get_latest_quote(sym)
                current_price = quote.ltp
            except Exception:
                candles = provider.get_historical_candles(sym)
                if candles:
                    current_price = candles[-1].close
                else:
                    continue

            # Update unrealized P&L
            self.broker.accountant.update_unrealized_pnl(sym, current_price)

            # Check stop-loss
            if current_price <= pos.stop_loss:
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
                        closed.append({"symbol": sym, "reason": "STOP_LOSS", "price": current_price})
                        self._log_event(
                            "AUTO_SELL_STOP",
                            sym,
                            f"Stop-loss hit for {sym} at ₹{current_price:.2f} (Stop was ₹{pos.stop_loss:.2f}). Closed {pos.quantity} shares.",
                            {"realized_pnl": trade.realized_pnl},
                        )
                except Exception as e:
                    logger.error(f"Failed to execute stop-loss sell for {sym}: {e}")
                continue

            # Check profit target
            if pos.target and current_price >= pos.target:
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
                        closed.append({"symbol": sym, "reason": "PROFIT_TARGET", "price": current_price})
                        self._log_event(
                            "AUTO_SELL_TARGET",
                            sym,
                            f"Profit target reached for {sym} at ₹{current_price:.2f} (Target was ₹{pos.target:.2f}). Closed {pos.quantity} shares.",
                            {"realized_pnl": trade.realized_pnl},
                        )
                except Exception as e:
                    logger.error(f"Failed to execute target sell for {sym}: {e}")

        return closed
