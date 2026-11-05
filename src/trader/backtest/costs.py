"""Indian Equity Transaction Costs & Multi-Broker Engine.
Calculates Brokerage, STT, Exchange transaction charges, SEBI turnover fees,
Stamp Duty, GST, Depository Participant (DP) charges, and execution slippage.

Supports distinct broker fee schedules:
- Angel One (SmartAPI / iTrade Prime)
- Zerodha (Kite)
- Dhan
- Fyers
- Flat Zero (pure statutory baseline)

Supports both DELIVERY (CNC) and INTRADAY (MIS) trade types with statutory differentiation:
- STT: Delivery is 0.10% on BUY and SELL. Intraday is 0.025% on SELL only.
- Stamp Duty: Delivery is 0.0015% on BUY. Intraday is 0.003% on BUY.
- DP Charges: Applicable only on equity SELL delivery (per scrip per day).
- Exchange Txn: NSE Cash 0.00297% (NSE circular Oct 2024).
- SEBI Turnover: ₹10/crore (0.0001%).
- GST: 18% on (Brokerage + Exchange Txn + SEBI Fees).
"""

from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from trader.domain.models import OrderSide


class BrokerProfile(str, Enum):
    """Supported Indian broker profiles with verified pricing structures."""
    ANGEL_ONE = "ANGEL_ONE"
    ZERODHA = "ZERODHA"
    DHAN = "DHAN"
    FYERS = "FYERS"
    FLAT_ZERO = "FLAT_ZERO"


class TradeType(str, Enum):
    """Execution classification for equity trading."""
    DELIVERY = "DELIVERY"  # CNC: Cash and Carry (Holding in Demat)
    INTRADAY = "INTRADAY"  # MIS: Margin Intraday Square-off


class BrokerageModel(str, Enum):
    """Supported brokerage models for Indian equity trading."""
    DISCOUNT_FLAT = "discount_flat"       # Flat ₹20 or 0.05% (whichever lower)
    ZERO_DELIVERY = "zero_delivery"       # ₹0 brokerage on equity delivery (e.g. Zerodha)
    PERCENTAGE = "percentage"             # Fixed percentage (e.g. 0.10% or 0.25%)


# Statutory tax rates (Official NSE / SEBI circulars)
STT_DELIVERY_RATE = 0.0010              # 0.10% buy & sell
STT_INTRADAY_SELL_RATE = 0.00025        # 0.025% sell only
NSE_TXN_RATE = 0.0000297                # 0.00297% NSE cash delivery & intraday
SEBI_TURNOVER_RATE = 0.000001          # ₹10 per crore = 0.0001%
STAMP_DUTY_DELIVERY_RATE = 0.00015      # 0.0015% buy only
STAMP_DUTY_INTRADAY_RATE = 0.00003      # 0.003% buy only
GST_RATE = 0.18                         # 18% GST on services

# Backward-compatibility aliases
DEFAULT_STT_RATE = STT_DELIVERY_RATE
DEFAULT_NSE_TXN_RATE = NSE_TXN_RATE
DEFAULT_SEBI_RATE = SEBI_TURNOVER_RATE
DEFAULT_STAMP_DUTY_RATE = STAMP_DUTY_DELIVERY_RATE
DEFAULT_GST_RATE = GST_RATE

# Depository Participant (DP) Charges per company sell debit (base fee before GST)
# DP charges are levied by Depositories (CDSL/NSDL) and the Depository Participant
DP_CHARGES_BASE: Dict[BrokerProfile, float] = {
    BrokerProfile.ANGEL_ONE: 20.0,       # ₹20 + GST = ₹23.60
    BrokerProfile.ZERODHA: 13.50,        # ₹13.50 + GST = ₹15.93
    BrokerProfile.DHAN: 12.50,           # ₹12.50 + GST = ₹14.75
    BrokerProfile.FYERS: 12.50,          # ₹12.50 + GST = ₹14.75
    BrokerProfile.FLAT_ZERO: 0.0,
}


class TradeCostBreakdown(BaseModel):
    """Detailed ledger of all costs, broker commissions, and statutory taxes."""
    broker: BrokerProfile = BrokerProfile.ANGEL_ONE
    trade_type: TradeType = TradeType.DELIVERY
    side: OrderSide
    gross_price: float
    effective_price: float
    quantity: int
    gross_trade_value: float
    slippage_inr: float
    market_impact_inr: float = 0.0
    brokerage_inr: float
    stt_inr: float
    exchange_charges_inr: float
    sebi_charges_inr: float
    stamp_duty_inr: float
    gst_inr: float
    dp_charges_inr: float = 0.0
    statutory_charges_inr: float
    total_statutory_taxes: float
    broker_charges_inr: float
    total_costs_inr: float
    net_trade_amount: float


class RoundtripSimulation(BaseModel):
    """Simulated buy-and-sell roundtrip with complete tax, brokerage, and DP charge ledger."""
    symbol: str
    broker: BrokerProfile
    trade_type: TradeType
    quantity: int
    buy_price: float
    sell_price: float
    gross_pnl: float
    gross_pnl_pct: float
    total_brokerage: float
    total_stt: float
    total_exchange_txn: float
    total_sebi: float
    total_stamp_duty: float
    total_gst: float
    total_dp_charges: float
    total_statutory_taxes: float
    total_costs: float
    net_pnl: float
    net_pnl_pct: float
    breakeven_sell_price: float
    buy_costs: TradeCostBreakdown
    sell_costs: TradeCostBreakdown


def calculate_trade_costs(
    side: OrderSide,
    price: float,
    quantity: int,
    brokerage_flat: float = 20.0,
    brokerage_model: Optional[BrokerageModel] = None,
    brokerage_pct: float = 0.0005,         # 0.05% for percentage / discount cap
    slippage_bps: float = 5.0,             # 5 bps conservative default
    market_impact_bps: float = 0.0,
    stt_rate: Optional[float] = None,
    exchange_txn_rate: float = DEFAULT_NSE_TXN_RATE,
    sebi_rate: float = DEFAULT_SEBI_RATE,
    stamp_duty_rate: Optional[float] = None,
    gst_rate: float = DEFAULT_GST_RATE,
    broker: Optional[BrokerProfile] = None,
    trade_type: TradeType = TradeType.DELIVERY,
    include_dp_charges: Optional[bool] = None,
) -> TradeCostBreakdown:
    """Calculates all brokerage, statutory taxes, DP charges, and slippage for an Indian equity trade."""
    total_slippage_bps = slippage_bps + market_impact_bps
    slippage_factor = total_slippage_bps / 10000.0

    if side == OrderSide.BUY:
        effective_price = round(price * (1.0 + slippage_factor), 2)
    else:
        effective_price = round(price * (1.0 - slippage_factor), 2)

    gross_value = round(effective_price * quantity, 2)
    slippage_inr = round(abs(effective_price - price) * quantity, 2)
    market_impact_inr = round(gross_value * (market_impact_bps / 10000.0), 2) if market_impact_bps > 0 else 0.0

    selected_broker = broker or (BrokerProfile.FLAT_ZERO if brokerage_model == BrokerageModel.ZERO_DELIVERY else BrokerProfile.ANGEL_ONE)

    # 1. Brokerage calculation
    if brokerage_model is not None:
        if brokerage_model == BrokerageModel.ZERO_DELIVERY:
            brokerage = 0.0
        elif brokerage_model == BrokerageModel.PERCENTAGE:
            brokerage = round(gross_value * brokerage_pct, 2)
        else:  # DISCOUNT_FLAT
            percent_fee = round(gross_value * brokerage_pct, 2)
            brokerage = min(brokerage_flat, percent_fee) if gross_value < 40000 else brokerage_flat
    elif broker is not None:
        if broker == BrokerProfile.FLAT_ZERO:
            brokerage = 0.0
        elif broker in [BrokerProfile.ZERODHA, BrokerProfile.DHAN, BrokerProfile.FYERS]:
            if trade_type == TradeType.DELIVERY:
                brokerage = 0.0
            else:
                brokerage = min(20.0, round(gross_value * 0.0003, 2))
        elif broker == BrokerProfile.ANGEL_ONE:
            if trade_type == TradeType.DELIVERY:
                brokerage = 0.0
            else:
                brokerage = min(20.0, round(gross_value * 0.0025, 2))
        else:
            percent_fee = round(gross_value * brokerage_pct, 2)
            brokerage = min(brokerage_flat, percent_fee) if gross_value < 40000 else brokerage_flat
    else:
        # Default fallback
        percent_fee = round(gross_value * brokerage_pct, 2)
        brokerage = min(brokerage_flat, percent_fee) if gross_value < 40000 else brokerage_flat

    # 2. Securities Transaction Tax (STT)
    if stt_rate is not None:
        stt = round(gross_value * stt_rate, 2)
    elif trade_type == TradeType.DELIVERY:
        stt = round(gross_value * STT_DELIVERY_RATE, 2)
    else:
        stt = round(gross_value * STT_INTRADAY_SELL_RATE, 2) if side == OrderSide.SELL else 0.0

    # 3. Exchange transaction charges (NSE Cash: 0.00297%)
    exchange_charges = round(gross_value * exchange_txn_rate, 2)

    # 4. SEBI turnover fee (₹10 / crore = 0.0001%)
    sebi_charges = round(gross_value * sebi_rate, 2)

    # 5. Stamp duty (applicable ONLY on BUY side)
    if side == OrderSide.BUY:
        actual_stamp_rate = (
            stamp_duty_rate
            if stamp_duty_rate is not None
            else (STAMP_DUTY_DELIVERY_RATE if trade_type == TradeType.DELIVERY else STAMP_DUTY_INTRADAY_RATE)
        )
        stamp_duty = round(gross_value * actual_stamp_rate, 2)
    else:
        stamp_duty = 0.0

    # 6. DP (Depository Participant) Charges: Levied ONLY on SELL delivery
    # Enabled when broker profile is explicitly passed or include_dp_charges=True
    should_include_dp = include_dp_charges if include_dp_charges is not None else (broker is not None and brokerage_model is None)
    dp_charges = 0.0
    if should_include_dp and side == OrderSide.SELL and trade_type == TradeType.DELIVERY:
        base_dp = DP_CHARGES_BASE.get(selected_broker, 0.0)
        dp_charges = round(base_dp * (1.0 + gst_rate), 2)

    # 7. GST: 18% on (Brokerage + Exchange charges + SEBI charges)
    taxable_services = round(brokerage + exchange_charges + sebi_charges, 2)
    gst = round(taxable_services * gst_rate, 2)

    # Sums
    statutory_taxes = round(stt + exchange_charges + sebi_charges + stamp_duty + gst + dp_charges, 2)
    total_costs = round(brokerage + statutory_taxes, 2)

    if side == OrderSide.BUY:
        net_amount = round(gross_value + total_costs, 2)
    else:
        net_amount = round(gross_value - total_costs, 2)

    return TradeCostBreakdown(
        broker=selected_broker,
        trade_type=trade_type,
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
        dp_charges_inr=dp_charges,
        statutory_charges_inr=statutory_taxes,
        total_statutory_taxes=statutory_taxes,
        broker_charges_inr=brokerage,
        total_costs_inr=total_costs,
        net_trade_amount=net_amount,
    )


def simulate_roundtrip_trade(
    symbol: str,
    buy_price: float,
    sell_price: float,
    quantity: int,
    broker: BrokerProfile = BrokerProfile.ANGEL_ONE,
    trade_type: TradeType = TradeType.DELIVERY,
    slippage_bps: float = 5.0,
) -> RoundtripSimulation:
    """Calculates full buy-and-sell roundtrip costs, net PnL, and breakeven exit price."""
    buy_costs = calculate_trade_costs(
        side=OrderSide.BUY,
        price=buy_price,
        quantity=quantity,
        broker=broker,
        trade_type=trade_type,
        slippage_bps=slippage_bps,
    )

    sell_costs = calculate_trade_costs(
        side=OrderSide.SELL,
        price=sell_price,
        quantity=quantity,
        broker=broker,
        trade_type=trade_type,
        slippage_bps=slippage_bps,
    )

    gross_pnl = round((sell_price - buy_price) * quantity, 2)
    gross_pnl_pct = round((gross_pnl / (buy_price * quantity)) * 100.0, 2) if (buy_price * quantity) > 0 else 0.0

    total_brokerage = round(buy_costs.brokerage_inr + sell_costs.brokerage_inr, 2)
    total_stt = round(buy_costs.stt_inr + sell_costs.stt_inr, 2)
    total_exchange_txn = round(buy_costs.exchange_charges_inr + sell_costs.exchange_charges_inr, 2)
    total_sebi = round(buy_costs.sebi_charges_inr + sell_costs.sebi_charges_inr, 2)
    total_stamp = round(buy_costs.stamp_duty_inr + sell_costs.stamp_duty_inr, 2)
    total_gst = round(buy_costs.gst_inr + sell_costs.gst_inr, 2)
    total_dp = round(sell_costs.dp_charges_inr, 2)
    total_statutory = round(total_stt + total_exchange_txn + total_sebi + total_stamp + total_gst + total_dp, 2)
    total_costs = round(total_brokerage + total_statutory, 2)

    net_pnl = round(gross_pnl - total_costs, 2)
    net_pnl_pct = round((net_pnl / (buy_price * quantity)) * 100.0, 2) if (buy_price * quantity) > 0 else 0.0

    # Calculate breakeven exit price:
    # Breakeven Sell Price * Qty - Sell Costs = Buy Gross + Buy Costs
    # Approximation accounting for proportional sell fees + fixed DP charges
    variable_sell_tax_rate = (
        (STT_DELIVERY_RATE if trade_type == TradeType.DELIVERY else STT_INTRADAY_SELL_RATE)
        + NSE_TXN_RATE
        + SEBI_TURNOVER_RATE
        + (NSE_TXN_RATE + SEBI_TURNOVER_RATE) * GST_RATE
    )
    fixed_sell_costs = total_dp + sell_costs.brokerage_inr
    breakeven_sell = round(
        (buy_costs.net_trade_amount + fixed_sell_costs) / (quantity * (1.0 - variable_sell_tax_rate)),
        2
    )

    return RoundtripSimulation(
        symbol=symbol.strip().upper(),
        broker=broker,
        trade_type=trade_type,
        quantity=quantity,
        buy_price=buy_price,
        sell_price=sell_price,
        gross_pnl=gross_pnl,
        gross_pnl_pct=gross_pnl_pct,
        total_brokerage=total_brokerage,
        total_stt=total_stt,
        total_exchange_txn=total_exchange_txn,
        total_sebi=total_sebi,
        total_stamp_duty=total_stamp,
        total_gst=total_gst,
        total_dp_charges=total_dp,
        total_statutory_taxes=total_statutory,
        total_costs=total_costs,
        net_pnl=net_pnl,
        net_pnl_pct=net_pnl_pct,
        breakeven_sell_price=breakeven_sell,
        buy_costs=buy_costs,
        sell_costs=sell_costs,
    )
