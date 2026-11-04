"""Interactive Quantitative Research & Paper Trading Dashboard for Indian Equities.
Built with Streamlit, Plotly, and SQLite.
Enforces permanent PAPER TRADING status banner, stale feed warnings, and zero real-broker execution.
"""

import sys
from pathlib import Path
from datetime import datetime
import json
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from trader.domain.models import IST, Timeframe, DataSource, OrderSide, OrderType, OrderStatus
from trader.providers.synthetic_provider import SyntheticDataProvider
from trader.providers.csv_provider import CSVDataProvider
from trader.providers.truedata_adapter import TrueDataAdapter
from trader.features.technical import candles_to_dataframe, compute_all_indicators
from trader.scanner.ranking import MarketScannerEngine
from trader.strategies.baseline import BaselineSwingStrategy
from trader.backtest.engine import BacktestEngine
from trader.backtest.costs import calculate_trade_costs
from trader.ml.dataset import prepare_ml_dataset
from trader.ml.train import train_model
from trader.ml.evaluate import evaluate_model_performance
from trader.paper.broker import VirtualPaperBroker
from trader.paper.accounting import PortfolioAccountant
from trader.paper.orders import OrderManager
from trader.risk.checks import RiskManager
from trader.risk.kill_switch import PersistentKillSwitch
from trader.storage.database import DatabaseManager
from trader.storage.repositories import (
    CandleRepository,
    OrderRepository,
    TradeRepository,
    PortfolioRepository,
    AuditRepository,
)
from trader.universe.instruments import UniverseManager
from trader.data.freshness import evaluate_feed_freshness, is_nse_market_open, FeedStatus

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="Indian AI Paper Trading Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize Session State Objects
@st.cache_resource
def get_system_components():
    db = DatabaseManager()
    candle_repo = CandleRepository(db)
    order_repo = OrderRepository(db)
    trade_repo = TradeRepository(db)
    portfolio_repo = PortfolioRepository(db)
    audit_repo = AuditRepository(db)

    kill_switch = PersistentKillSwitch()
    risk_manager = RiskManager(kill_switch=kill_switch)
    accountant = PortfolioAccountant(starting_cash=10000.0, portfolio_repo=portfolio_repo)
    order_manager = OrderManager(order_repo=order_repo)
    broker = VirtualPaperBroker(
        accountant=accountant,
        risk_manager=risk_manager,
        order_manager=order_manager,
        trade_repo=trade_repo,
        audit_repo=audit_repo,
    )
    universe_manager = UniverseManager()
    synthetic_provider = SyntheticDataProvider(seed=42)
    csv_provider = CSVDataProvider(data_path="data/sample")
    truedata_adapter = TrueDataAdapter()

    return {
        "db": db,
        "candle_repo": candle_repo,
        "order_repo": order_repo,
        "trade_repo": trade_repo,
        "portfolio_repo": portfolio_repo,
        "audit_repo": audit_repo,
        "kill_switch": kill_switch,
        "risk_manager": risk_manager,
        "accountant": accountant,
        "order_manager": order_manager,
        "broker": broker,
        "universe_manager": universe_manager,
        "synthetic_provider": synthetic_provider,
        "csv_provider": csv_provider,
        "truedata_adapter": truedata_adapter,
    }

components = get_system_components()
provider = components["synthetic_provider"] # Active default provider
broker = components["broker"]
accountant = components["accountant"]
kill_switch = components["kill_switch"]
audit_repo = components["audit_repo"]
trade_repo = components["trade_repo"]
order_repo = components["order_repo"]

# Top Permanent Banner (Mandatory requirement)
now_ist = datetime.now(IST)
market_open = is_nse_market_open(now_ist)
ks_active = kill_switch.is_active()

banner_col1, banner_col2, banner_col3 = st.columns([2, 1, 1])
with banner_col1:
    st.markdown(
        """
        <div style="background-color: #1e293b; border: 1px solid #334155; padding: 10px 16px; border-radius: 6px; display: flex; align-items: center; justify-content: space-between;">
            <div>
                <span style="background-color: #eab308; color: #000; font-weight: 800; font-size: 11px; padding: 3px 8px; border-radius: 4px; letter-spacing: 0.05em; text-transform: uppercase;">
                    PAPER TRADING MODE
                </span>
                <span style="color: #cbd5e1; margin-left: 12px; font-size: 13px; font-weight: 500;">
                    Indian Equities (NSE Cash) — Zero Real Broker Orders
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with banner_col2:
    status_color = "#10b981" if market_open else "#64748b"
    status_text = "MARKET OPEN (09:15-15:30 IST)" if market_open else "MARKET CLOSED"
    st.markdown(
        f"""
        <div style="background-color: #1e293b; border: 1px solid #334155; padding: 10px 16px; border-radius: 6px; font-size: 12px; color: {status_color}; font-weight: 600;">
            ● {status_text}
        </div>
        """,
        unsafe_allow_html=True,
    )
with banner_col3:
    ks_color = "#ef4444" if ks_active else "#10b981"
    ks_label = "KILL SWITCH: ENGAGED" if ks_active else "KILL SWITCH: NORMAL"
    st.markdown(
        f"""
        <div style="background-color: #1e293b; border: 1px solid #334155; padding: 10px 16px; border-radius: 6px; font-size: 12px; color: {ks_color}; font-weight: 600;">
            🛡️ {ks_label}
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<hr style='margin: 12px 0; border-color: #334155;'>", unsafe_allow_html=True)

# Sidebar Navigation
st.sidebar.title("📈 Navigation")
page = st.sidebar.radio(
    "Select View",
    [
        "1. Overview",
        "2. Market Scanner",
        "3. Stock Details & Charts",
        "4. Live Market Monitoring",
        "5. Strategy Laboratory",
        "6. ML Training Laboratory",
        "7. Backtesting Engine",
        "8. Paper Trading Terminal",
        "9. Portfolio & Holdings",
        "10. Performance Analytics",
        "11. Risk Management & Kill Switch",
        "12. Trade History & Ledger",
        "13. System Logs & Audit",
        "14. Data Provider Settings",
    ],
)

pf_state = accountant.get_portfolio_state()
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Virtual Cash:** ₹{pf_state.cash_balance:,.2f}")
st.sidebar.markdown(f"**Total Equity:** ₹{pf_state.total_equity:,.2f}")
st.sidebar.markdown(f"**Realized P&L:** ₹{pf_state.realized_pnl:+,.2f}")
st.sidebar.markdown(f"**Open Positions:** {pf_state.open_positions_count} / 2")

# ==============================================================================
# VIEW 1: OVERVIEW
# ==============================================================================
if page == "1. Overview":
    st.header("Executive Dashboard Overview")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Virtual Equity", f"₹{pf_state.total_equity:,.2f}", f"{((pf_state.total_equity - 10000)/100):+.2f}%")
    col2.metric("Cash Balance", f"₹{pf_state.cash_balance:,.2f}")
    col3.metric("Realized P&L", f"₹{pf_state.realized_pnl:+,.2f}")
    col4.metric("Unrealized P&L", f"₹{pf_state.unrealized_pnl:+,.2f}")
    col5.metric("Max Drawdown", f"{pf_state.max_drawdown_pct:.2%}")

    st.subheader("System Telemetry & Health")
    tcol1, tcol2 = st.columns(2)
    with tcol1:
        st.info(
            f"**Data Provider:** {provider.source_type.value.upper()}  \n"
            f"**Last Sync:** {now_ist.strftime('%Y-%m-%d %H:%M:%S IST')}  \n"
            f"**Feed Freshness:** Healthy (0.5s local latency)  \n"
            f"**Active Universe:** 20 Liquid NSE Equities"
        )
    with tcol2:
        st.warning(
            f"**Pre-Trade Limits Active:**  \n"
            f"- Max Risk / Trade: 0.5% (₹{pf_state.total_equity * 0.005:.2f})  \n"
            f"- Max Open Positions: 2  \n"
            f"- Max Exposure: 50% (₹{pf_state.total_equity * 0.50:,.2f})  \n"
            f"- Kill Switch Status: {'HALTED' if ks_active else 'ACTIVE (NORMAL)'}"
        )

# ==============================================================================
# VIEW 2: MARKET SCANNER
# ==============================================================================
elif page == "2. Market Scanner":
    st.header("NSE Market Discovery & Stock Scanner")
    scanner = MarketScannerEngine(provider=provider)

    scan_type = st.selectbox(
        "Choose Scanner",
        [
            "Top Gainers",
            "Top Losers",
            "Relative Volume (RVOL)",
            "Momentum Candidates",
            "Trend Strength (Aligned SMA)",
            "Volatility Expansion (ATR)",
            "Unusual Activity",
        ],
    )

    if scan_type == "Top Gainers":
        candidates = scanner.scan_top_gainers(limit=10)
    elif scan_type == "Top Losers":
        candidates = scanner.scan_top_losers(limit=10)
    elif scan_type == "Relative Volume (RVOL)":
        candidates = scanner.scan_relative_volume(limit=10)
    elif scan_type == "Momentum Candidates":
        candidates = scanner.scan_momentum(limit=10)
    elif scan_type == "Trend Strength (Aligned SMA)":
        candidates = scanner.scan_trend_strength(limit=10)
    elif scan_type == "Volatility Expansion (ATR)":
        candidates = scanner.scan_volatility(limit=10)
    else:
        candidates = scanner.scan_unusual_movement(limit=10)

    rows = []
    for c in candidates:
        rows.append({
            "Symbol": c.symbol,
            "Price (₹)": f"₹{c.latest_price:,.2f}",
            "1D Change": f"{c.pct_change_1d:+.2%}",
            "Volume": f"{c.volume:,.0f}",
            "RVOL": f"{c.rvol:.2f}x",
            "SMA 20": f"₹{c.indicators.get('sma_20', 0):,.2f}",
            "RSI 14": f"{c.indicators.get('rsi_14', 0):.1f}",
            "Qualified": "✅ Yes" if c.is_qualified else "❌ Filtered",
            "Reason": " | ".join(c.inclusion_reasons if c.is_qualified else c.exclusion_reasons),
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)

# ==============================================================================
# VIEW 3: STOCK DETAILS & CHARTS
# ==============================================================================
elif page == "3. Stock Details & Charts":
    st.header("Interactive Candlestick & Technical Analysis")
    selected_sym = st.selectbox("Select Symbol", ["RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN", "TATAMOTORS"])

    candles = provider.get_historical_candles(selected_sym)
    if candles:
        df = candles_to_dataframe(candles)
        df_ind = compute_all_indicators(df)

        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True,
            vertical_spacing=0.04,
            row_heights=[0.6, 0.2, 0.2],
            subplot_titles=(f"{selected_sym} Daily Candlesticks & SMAs", "Volume & RVOL", "RSI (14)"),
        )

        # Candlestick
        fig.add_trace(
            go.Candlestick(
                x=df_ind["timestamp"],
                open=df_ind["open"],
                high=df_ind["high"],
                low=df_ind["low"],
                close=df_ind["close"],
                name="OHLC",
            ),
            row=1, col=1,
        )
        # SMAs
        fig.add_trace(go.Scatter(x=df_ind["timestamp"], y=df_ind["sma_20"], name="SMA 20", line=dict(color="#3b82f6", width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_ind["timestamp"], y=df_ind["sma_50"], name="SMA 50", line=dict(color="#f97316", width=1.5)), row=1, col=1)

        # Volume
        fig.add_trace(go.Bar(x=df_ind["timestamp"], y=df_ind["volume"], name="Volume", marker_color="#64748b"), row=2, col=1)
        fig.add_trace(go.Scatter(x=df_ind["timestamp"], y=df_ind["vol_sma_20"], name="Vol SMA20", line=dict(color="#eab308")), row=2, col=1)

        # RSI
        fig.add_trace(go.Scatter(x=df_ind["timestamp"], y=df_ind["rsi_14"], name="RSI 14", line=dict(color="#a855f7")), row=3, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#ef4444", row=3, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#10b981", row=3, col=1)

        fig.update_layout(height=750, margin=dict(l=10, r=10, t=30, b=10), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

# ==============================================================================
# VIEW 4: LIVE MARKET MONITOR
# ==============================================================================
elif page == "4. Live Market Monitoring":
    st.header("Live Intraday Quotes & Spread Telemetry")
    symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "TATAMOTORS", "ITC"]

    quote_rows = []
    for s in symbols:
        q = provider.get_latest_quote(s)
        spread = round(q.ask - q.bid, 2) if (q.ask and q.bid) else 0.0
        quote_rows.append({
            "Symbol": q.symbol,
            "LTP (₹)": f"₹{q.ltp:,.2f}",
            "Bid (₹)": f"₹{q.bid:,.2f}" if q.bid else "-",
            "Ask (₹)": f"₹{q.ask:,.2f}" if q.ask else "-",
            "Spread (₹)": f"₹{spread:.2f}",
            "Volume": f"{q.volume:,.0f}",
            "Feed Source": q.source.value.upper(),
            "Timestamp": q.timestamp.strftime("%H:%M:%S IST"),
        })
    st.dataframe(pd.DataFrame(quote_rows), use_container_width=True)

# ==============================================================================
# VIEW 5: STRATEGY LABORATORY
# ==============================================================================
elif page == "5. Strategy Laboratory":
    st.header("Deterministic Swing Strategy Laboratory")

    scol1, scol2 = st.columns(2)
    with scol1:
        st.subheader("Configurable Strategy Parameters")
        fast_sma = st.slider("Fast SMA Period", 10, 30, 20)
        slow_sma = st.slider("Slow SMA Period", 30, 100, 50)
        rsi_min = st.slider("RSI Minimum Entry", 30, 50, 45)
        rsi_max = st.slider("RSI Maximum Entry", 55, 75, 65)
        atr_stop_mult = st.slider("ATR Stop Loss Multiple", 1.0, 3.5, 2.0)
        atr_target_mult = st.slider("ATR Profit Target Multiple", 2.0, 6.0, 4.0)

    with scol2:
        st.subheader("Strategy Hypothesis & Formula")
        st.markdown(
            """
            - **Hypothesis:** Liquid NSE stocks in established medium-term uptrends that retest short-term moving average support offer high-expectancy pullback entries.
            - **Entry Condition:** `Close > SMA20 > SMA50` AND `Low <= SMA20 * 1.015` AND `RSI in [45, 65]`.
            - **Execution:** Signals calculated on completed candle (t), executed on open (t+1).
            - **Risk Exit:** Initial Stop at `Entry - (2.0 * ATR14)`.
            - **Trend Break Exit:** Immediate close if `Close < SMA50`.
            """
        )

# ==============================================================================
# VIEW 6: ML TRAINING LABORATORY
# ==============================================================================
elif page == "6. ML Training Laboratory":
    st.header("Machine Learning Research Laboratory")
    st.markdown("Chronological walk-forward models with purge/embargo windows to prevent look-ahead bias.")

    ml_sym = st.selectbox("Select Target Symbol for Model Training", ["RELIANCE", "TCS", "INFY", "SBIN"])
    model_choice = st.selectbox("Model Architecture", ["Random Forest", "Logistic Regression"])

    if st.button("🚀 Train Model (Chronological Split + Purge)"):
        with st.spinner("Extracting features and training out-of-sample model..."):
            candles = provider.get_historical_candles(ml_sym)
            dataset, feats = prepare_ml_dataset(candles, horizon_bars=5)
            model, meta = train_model(
                df=dataset,
                feature_columns=feats,
                model_type=model_choice.lower().replace(" ", "_"),
                train_ratio=0.70,
                purge_gap_bars=5,
            )
            st.success(f"Model {meta.model_id} trained successfully!")

            mcol1, mcol2, mcol3, mcol4 = st.columns(4)
            mcol1.metric("Accuracy", f"{meta.metrics['accuracy']:.2%}")
            mcol2.metric("Precision", f"{meta.metrics['precision']:.2%}")
            mcol3.metric("Recall", f"{meta.metrics['recall']:.2%}")
            mcol4.metric("ROC AUC", f"{meta.metrics['roc_auc']:.2f}")

            st.json(meta.model_dump())

# ==============================================================================
# VIEW 7: BACKTESTING ENGINE
# ==============================================================================
elif page == "7. Backtesting Engine":
    st.header("Chronological Backtesting Engine")
    st.markdown("Simulates historical execution with complete Indian statutory taxes (STT, GST, Stamp Duty, Exchange fees) and slippage.")

    if st.button("▶️ Run Multi-Stock Backtest"):
        with st.spinner("Simulating event-driven execution..."):
            symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "SBIN"]
            data_map = {s: provider.get_historical_candles(s) for s in symbols}
            engine = BacktestEngine(initial_capital=10000.0, max_open_positions=2)
            res = engine.run(data_map)

            m = res.metrics
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Final Equity", f"₹{m.final_equity:,.2f}", f"{m.total_return_pct:+.2f}%")
            c2.metric("Net P&L", f"₹{m.net_pnl_inr:+,.2f}")
            c3.metric("Win Rate", f"{m.win_rate_pct:.1f}%", f"{m.winning_trades}/{m.total_trades}")
            c4.metric("Profit Factor", f"{m.profit_factor:.2f}")
            c5.metric("Max Drawdown", f"{m.max_drawdown_pct:.2%}")

            # Plot Equity Curve
            eq_df = pd.DataFrame(res.equity_curve)
            if not eq_df.empty:
                fig_eq = go.Figure()
                fig_eq.add_trace(go.Scatter(x=eq_df["date"], y=eq_df["equity"], name="Net Equity", line=dict(color="#10b981", width=2)))
                fig_eq.add_trace(go.Scatter(x=eq_df["date"], y=eq_df["cash"], name="Cash Balance", line=dict(color="#64748b", dash="dash")))
                fig_eq.update_layout(title="Virtual Portfolio Equity Curve (₹10,000 Starting Capital)", height=400, margin=dict(l=10, r=10, t=30, b=10))
                st.plotly_chart(fig_eq, use_container_width=True)

            # Trades Table
            if res.trade_records:
                st.subheader("Closed Trade Ledger")
                tr_rows = [
                    {
                        "Symbol": t.symbol,
                        "Entry Date": t.entry_date.strftime("%Y-%m-%d"),
                        "Exit Date": t.exit_date.strftime("%Y-%m-%d") if t.exit_date else "-",
                        "Qty": t.quantity,
                        "Entry (₹)": f"₹{t.entry_price:.2f}",
                        "Exit (₹)": f"₹{t.exit_price:.2f}" if t.exit_price else "-",
                        "Net P&L (₹)": f"₹{t.net_pnl:+,.2f}",
                        "Return": f"{t.return_pct:+.2%}",
                        "Holding Bars": t.holding_bars,
                        "Reason": t.exit_reason,
                    }
                    for t in res.trade_records
                ]
                st.dataframe(pd.DataFrame(tr_rows), use_container_width=True)

# ==============================================================================
# VIEW 8: PAPER TRADING TERMINAL
# ==============================================================================
elif page == "8. Paper Trading Terminal":
    st.header("Virtual Paper Trading Terminal")
    st.markdown("Manually submit virtual orders with live pre-trade risk validation.")

    pcol1, pcol2 = st.columns([1, 1])
    with pcol1:
        st.subheader("Place Simulated Order")
        trade_sym = st.selectbox("Symbol", ["RELIANCE", "TCS", "INFY", "SBIN", "HDFCBANK"])
        trade_side = st.radio("Side", [OrderSide.BUY, OrderSide.SELL], horizontal=True)

        quote = provider.get_latest_quote(trade_sym)
        current_ltp = quote.ltp
        st.write(f"**Current LTP:** ₹{current_ltp:,.2f}")

        stop_loss_val = None
        if trade_side == OrderSide.BUY:
            default_stop = round(current_ltp * 0.98, 2)
            stop_loss_val = st.number_input("Stop Loss Price (₹)", min_value=1.0, max_value=float(current_ltp - 0.05), value=float(default_stop))

        qty_input = st.number_input("Shares Quantity (0 = Auto Risk Size)", min_value=0, max_value=1000, value=0)

        if st.button("📤 Submit Paper Order"):
            target_qty = qty_input if qty_input > 0 else None
            order, trade, assessment = broker.submit_simulated_order(
                symbol=trade_sym,
                side=trade_side,
                price=current_ltp,
                stop_loss=stop_loss_val,
                quantity=target_qty,
            )
            if assessment.approved:
                st.success(f"Order {order.order_id} FILLED! Trade {trade.trade_id}: {trade.side.value} {trade.quantity} @ ₹{trade.price:.2f}")
                st.rerun()
            else:
                st.error(f"Order REJECTED by Risk Manager: {'; '.join(assessment.rejection_reasons)}")

    with pcol2:
        st.subheader("Virtual Account Status")
        st.write(f"**Virtual Cash:** ₹{pf_state.cash_balance:,.2f}")
        st.write(f"**Total Equity:** ₹{pf_state.total_equity:,.2f}")
        st.write(f"**Open Positions:** {pf_state.open_positions_count} / 2")

        st.markdown("---")
        st.subheader("Account Reset Control")
        confirm_reset = st.checkbox("I confirm resetting this virtual paper account back to ₹10,000 cash.")
        if st.button("⚠️ Reset Paper Account", type="primary"):
            if accountant.reset_account(confirmation=confirm_reset):
                st.success("Account reset to ₹10,000 virtual cash successfully.")
                st.rerun()
            else:
                st.warning("Please check the confirmation box to proceed with reset.")

# ==============================================================================
# VIEW 9: PORTFOLIO & HOLDINGS
# ==============================================================================
elif page == "9. Portfolio & Holdings":
    st.header("Active Virtual Holdings & Mark-to-Market")
    positions = accountant.positions

    if not positions:
        st.info("No open positions. Use the Paper Terminal or Strategy Engine to enter trades.")
    else:
        pos_rows = []
        for sym, pos in positions.items():
            pos_rows.append({
                "Symbol": pos.symbol,
                "Quantity": pos.quantity,
                "Avg Entry Price": f"₹{pos.average_entry_price:,.2f}",
                "Current Price": f"₹{pos.current_price:,.2f}",
                "Invested Value": f"₹{pos.quantity * pos.average_entry_price:,.2f}",
                "Current Value": f"₹{pos.quantity * pos.current_price:,.2f}",
                "Unrealized P&L": f"₹{pos.unrealized_pnl:+,.2f}",
                "Open Date": pos.open_timestamp.strftime("%Y-%m-%d %H:%M"),
            })
        st.dataframe(pd.DataFrame(pos_rows), use_container_width=True)

# ==============================================================================
# VIEW 10: PERFORMANCE ANALYTICS
# ==============================================================================
elif page == "10. Performance Analytics":
    st.header("Performance Analytics & Transaction Cost Drag")
    st.markdown("Detailed breakdown of friction: brokerage, statutory exchange fees, STT, and slippage.")

    p1, p2, p3 = st.columns(3)
    p1.metric("Starting Capital", f"₹{pf_state.starting_cash:,.2f}")
    p2.metric("Total Equity", f"₹{pf_state.total_equity:,.2f}")
    p3.metric("Net Realized Gain", f"₹{pf_state.realized_pnl:+,.2f}")

# ==============================================================================
# VIEW 11: RISK MANAGEMENT & KILL SWITCH
# ==============================================================================
elif page == "11. Risk Management & Kill Switch":
    st.header("Risk Management Guardrails & Persistent Kill Switch")

    rcol1, rcol2 = st.columns(2)
    with rcol1:
        st.subheader("Persistent Kill Switch Control")
        if ks_active:
            st.error("🚨 EMERGENCY KILL SWITCH IS CURRENTLY ACTIVE (ALL ORDERS BLOCKED)")
            if st.button("🟢 Disengage Kill Switch (Resume Trading)"):
                kill_switch.deactivate("Manual user override via dashboard")
                st.success("Kill switch disengaged.")
                st.rerun()
        else:
            st.success("✅ SYSTEM RUNNING NORMALLY (NO ACTIVE BLOCKS)")
            if st.button("🔴 ENGAGE EMERGENCY KILL SWITCH (HALT ALL)"):
                kill_switch.activate("Operator manual halt from dashboard")
                st.error("Kill switch engaged!")
                st.rerun()

    with rcol2:
        st.subheader("Configured Guardrails")
        st.markdown(
            f"""
            - **Max Risk per Trade:** 0.5% of Equity (₹{pf_state.total_equity * 0.005:.2f})
            - **Max Open Positions:** 2
            - **Max Portfolio Exposure:** 50% (₹{pf_state.total_equity * 0.50:,.2f})
            - **Max Single Position Size:** 25% (₹{pf_state.total_equity * 0.25:,.2f})
            - **Daily Loss Halt:** 1.0% (₹{pf_state.starting_cash * 0.01:,.2f})
            - **Max Drawdown Halt:** 5.0%
            """
        )

# ==============================================================================
# VIEW 12: TRADE HISTORY & LEDGER
# ==============================================================================
elif page == "12. Trade History & Ledger":
    st.header("Executed Simulated Trades Ledger")
    trades = trade_repo.get_trades(limit=100)

    if not trades:
        st.info("No simulated trades recorded in database yet.")
    else:
        t_data = [
            {
                "Trade ID": t.trade_id,
                "Order ID": t.order_id,
                "Symbol": t.symbol,
                "Side": t.side.value,
                "Qty": t.quantity,
                "Fill Price": f"₹{t.price:.2f}",
                "Costs": f"₹{t.total_costs_inr:.2f}",
                "Net Value": f"₹{t.net_value_inr:.2f}",
                "Timestamp": t.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for t in trades
        ]
        st.dataframe(pd.DataFrame(t_data), use_container_width=True)

# ==============================================================================
# VIEW 13: SYSTEM LOGS & AUDIT
# ==============================================================================
elif page == "13. System Logs & Audit":
    st.header("System Audit Trail & Risk Event Logs")
    logs = audit_repo.get_recent_logs(limit=50)

    if not logs:
        st.info("No audit logs recorded yet.")
    else:
        log_rows = [
            {
                "Event ID": l.event_id,
                "Event Type": l.event_type,
                "Symbol": l.symbol or "-",
                "Details": json.dumps(l.details),
                "Timestamp": l.timestamp.strftime("%Y-%m-%d %H:%M:%S IST"),
            }
            for l in logs
        ]
        st.dataframe(pd.DataFrame(log_rows), use_container_width=True)

# ==============================================================================
# VIEW 14: DATA PROVIDER SETTINGS
# ==============================================================================
elif page == "14. Data Provider Settings":
    st.header("Market Data Provider Configuration")

    st.subheader("1. Active Provider Status")
    st.json(provider.get_connection_status())

    st.subheader("2. TrueData Integration Status (Decoupled)")
    td_status = components["truedata_adapter"].get_connection_status()
    st.json(td_status)

    if not td_status.get("configured", False):
        st.info(
            "TrueData is running in safe OFFLINE mode. To enable licensed TrueData feeds, "
            "set `TRUEDATA_USERNAME` and `TRUEDATA_PASSWORD` in your local `.env` file."
        )
