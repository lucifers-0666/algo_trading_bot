"""Indian Equity Transaction Costs & Slippage Engine.
Calculates Brokerage, STT, Exchange transaction charges, SEBI turnover fees,
Stamp Duty, GST, and conservative execution slippage.
"""

from typing import Dict, Any
from pydantic import BaseModel
from trader.domain.models import OrderSide


class TradeCostBreakdown(BaseModel):
    """Detailed ledger of all costs and statutory taxes for an equity delivery trade."""
    side: OrderSide
    gross_price: float
    effective_price: float
    quantity: int
    gross_trade_value: float
    slippage_inr: float
    brokerage_inr: float
    stt_inr: float # Securities Transaction Tax (0.1% on delivery)
    exchange_charges_inr: float # NSE Txn charge 0.00325%
    sebi_charges_inr: float # ₹10 per crore (0.0001%)
    stamp_duty_inr: float # 0.0015% on buy delivery
    gst_inr: float # 18% on (Brokerage + Exchange Txn + SEBI)
    total_statutory_taxes: float
    total_costs_inr: float
    net_trade_amount: float # Outflow for BUY (Gross + Costs), Inflow for SELL (Gross - Costs)


def calculate_trade_costs(
    side: OrderSide,
    price: float,
    quantity: int,
    brokerage_flat: float = 20.0,
    slippage_bps: float = 10.0, # 10 bps = 0.10%
    stt_rate: float = 0.001, # 0.1% delivery
    exchange_txn_rate: float = 0.0000325, # 0.00325%
    sebi_rate: float = 0.000001, # 0.0001%
    stamp_duty_rate: float = 0.00015, # 0.0015% buy only
    gst_rate: float = 0.18, # 18%
) -> TradeCostBreakdown:
    """Calculates all brokerage, taxes, and slippage for an NSE cash delivery trade."""
    slippage_factor = slippage_bps / 10000.0

    if side == OrderSide.BUY:
        effective_price = round(price * (1.0 + slippage_factor), 2)
    else:
        effective_price = round(price * (1.0 - slippage_factor), 2)

    gross_value = round(effective_price * quantity, 2)
    slippage_inr = round(abs(effective_price - price) * quantity, 2)

    # 1. Brokerage (capped at flat fee or small % for discount broker)
    brokerage = min(brokerage_flat, round(gross_value * 0.0005, 2)) if gross_value < 40000 else brokerage_flat

    # 2. STT (0.1% on equity delivery both buy & sell)
    stt = round(gross_value * stt_rate, 2)

    # 3. Exchange transaction charges
    exchange_charges = round(gross_value * exchange_txn_rate, 2)

    # 4. SEBI turnover fee
    sebi_charges = round(gross_value * sebi_rate, 2)

    # 5. Stamp duty (applicable only on BUY side in Indian markets)
    stamp_duty = round(gross_value * stamp_duty_rate, 2) if side == OrderSide.BUY else 0.0

    # 6. GST (18% on Brokerage + Exchange charges + SEBI charges)
    taxable_services = brokerage + exchange_charges + sebi_charges
    gst = round(taxable_services * gst_rate, 2)

    total_taxes = round(stt + exchange_charges + sebi_charges + stamp_duty + gst, 2)
    total_costs = round(brokerage + total_taxes, 2)

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
        brokerage_inr=brokerage,
        stt_inr=stt,
        exchange_charges_inr=exchange_charges,
        sebi_charges_inr=sebi_charges,
        stamp_duty_inr=stamp_duty,
        gst_inr=gst,
        total_statutory_taxes=total_taxes,
        total_costs_inr=total_costs,
        net_trade_amount=net_amount,
    )
