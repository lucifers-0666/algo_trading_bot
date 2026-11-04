"""Indian Equity Transaction Costs & Slippage Engine.
Calculates Brokerage, STT, Exchange transaction charges, SEBI turnover fees,
Stamp Duty, GST, conservative execution slippage, and optional market impact.

Statutory rates strictly follow current SEBI and NSE circulars:
- Securities Transaction Tax (STT): 0.10% on BUY and SELL delivery.
- Exchange Transaction Charges: NSE Cash 0.00297% (NSE Circular Oct 2024).
- SEBI Turnover Fee: ₹10 per crore (0.0001%).
- Stamp Duty (Indian Stamp Act): 0.0015% on BUY delivery only.
- GST: 18% on (Brokerage + Exchange Txn + SEBI Turnover).
"""

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from trader.domain.models import OrderSide


class BrokerageModel(str, Enum):
    """Supported brokerage models for Indian equity trading."""
    DISCOUNT_FLAT = "discount_flat"       # Flat ₹20 or 0.05% (whichever lower)
    ZERO_DELIVERY = "zero_delivery"       # ₹0 brokerage on equity delivery (e.g. Zerodha)
    PERCENTAGE = "percentage"             # Fixed percentage (e.g. 0.10% or 0.25%)


# Official statutory rates
DEFAULT_STT_RATE = 0.001               # 0.10% delivery buy & sell
DEFAULT_NSE_TXN_RATE = 0.0000297       # 0.00297% NSE cash delivery (effective Oct 1, 2024)
DEFAULT_SEBI_RATE = 0.000001          # ₹10 / crore = 0.0001%
DEFAULT_STAMP_DUTY_RATE = 0.00015      # 0.0015% buy delivery only
DEFAULT_GST_RATE = 0.18               # 18% on fees


class TradeCostBreakdown(BaseModel):
    """Detailed ledger of all costs and statutory taxes for an equity delivery trade."""
    side: OrderSide
    gross_price: float
    effective_price: float
    quantity: int
    gross_trade_value: float
    slippage_inr: float
    market_impact_inr: float = 0.0
    brokerage_inr: float
    stt_inr: float                         # Securities Transaction Tax
    exchange_charges_inr: float            # NSE Txn charge
    sebi_charges_inr: float                # SEBI turnover fee
    stamp_duty_inr: float                  # Stamp duty (BUY only)
    gst_inr: float                         # 18% on (Brokerage + Exchange Txn + SEBI)
    statutory_charges_inr: float           # Sum of all regulatory taxes
    total_statutory_taxes: float           # Backwards compatibility alias
    broker_charges_inr: float              # Pure broker commission
    total_costs_inr: float                 # broker_charges + statutory_charges
    net_trade_amount: float                # Outflow for BUY (Gross + Costs), Inflow for SELL (Gross - Costs)


def calculate_trade_costs(
    side: OrderSide,
    price: float,
    quantity: int,
    brokerage_flat: float = 20.0,
    brokerage_model: BrokerageModel = BrokerageModel.DISCOUNT_FLAT,
    brokerage_pct: float = 0.0005,         # 0.05% for percentage / discount cap
    slippage_bps: float = 10.0,            # 10 bps = 0.10%
    market_impact_bps: float = 0.0,        # Additional basis points for illiquid/large fills
    stt_rate: float = DEFAULT_STT_RATE,
    exchange_txn_rate: float = DEFAULT_NSE_TXN_RATE,
    sebi_rate: float = DEFAULT_SEBI_RATE,
    stamp_duty_rate: float = DEFAULT_STAMP_DUTY_RATE,
    gst_rate: float = DEFAULT_GST_RATE,
) -> TradeCostBreakdown:
    """Calculates all brokerage, statutory taxes, and slippage for an NSE cash delivery trade.

    Strictly separates broker commissions from sovereign statutory taxes and prevents
    double-counting of slippage against effective execution prices.
    """
    total_slippage_bps = slippage_bps + market_impact_bps
    slippage_factor = total_slippage_bps / 10000.0

    if side == OrderSide.BUY:
        effective_price = round(price * (1.0 + slippage_factor), 2)
    else:
        effective_price = round(price * (1.0 - slippage_factor), 2)

    gross_value = round(effective_price * quantity, 2)
    slippage_inr = round(abs(effective_price - price) * quantity, 2)
    market_impact_inr = round(gross_value * (market_impact_bps / 10000.0), 2) if market_impact_bps > 0 else 0.0

    # 1. Brokerage Model
    if brokerage_model == BrokerageModel.ZERO_DELIVERY:
        brokerage = 0.0
    elif brokerage_model == BrokerageModel.PERCENTAGE:
        brokerage = round(gross_value * brokerage_pct, 2)
    else:  # DISCOUNT_FLAT
        # Lower of flat fee or small % of trade value
        percent_fee = round(gross_value * brokerage_pct, 2)
        brokerage = min(brokerage_flat, percent_fee) if gross_value < 40000 else brokerage_flat

    # 2. STT (0.1% on equity delivery both buy & sell)
    stt = round(gross_value * stt_rate, 2)

    # 3. Exchange transaction charges (NSE)
    exchange_charges = round(gross_value * exchange_txn_rate, 2)

    # 4. SEBI turnover fee
    sebi_charges = round(gross_value * sebi_rate, 2)

    # 5. Stamp duty (applicable only on BUY side in Indian delivery)
    stamp_duty = round(gross_value * stamp_duty_rate, 2) if side == OrderSide.BUY else 0.0

    # 6. GST (18% on Brokerage + Exchange charges + SEBI charges)
    taxable_services = round(brokerage + exchange_charges + sebi_charges, 2)
    gst = round(taxable_services * gst_rate, 2)

    statutory_taxes = round(stt + exchange_charges + sebi_charges + stamp_duty + gst, 2)
    total_costs = round(brokerage + statutory_taxes, 2)

    if side == OrderSide.BUY:
        net_amount = round(gross_value + total_costs, 2)
    else:
        net_amount = round(gross_value - total_costs, 2)

    return TradeCostBreakdown(
        side=side,
        gross_price=price,
        effective_price=effective_price,
        quantity=quantity,
        gross_trade_value=gross_value,
        slippage_inr=slippage_inr,
        market_impact_inr=market_impact_inr,
        brokerage_inr=brokerage,
        stt_inr=stt,
        exchange_charges_inr=exchange_charges,
        sebi_charges_inr=sebi_charges,
        stamp_duty_inr=stamp_duty,
        gst_inr=gst,
        statutory_charges_inr=statutory_taxes,
        total_statutory_taxes=statutory_taxes,
        broker_charges_inr=brokerage,
        total_costs_inr=total_costs,
        net_trade_amount=net_amount,
    )
