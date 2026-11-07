"""Unit tests for NextSessionForecaster.
Verifies feature generation, calibrated probability, volatility ranges,
baseline comparisons, and ledger evaluations.
"""

from datetime import datetime, timedelta
import pytest
from trader.domain.models import Candle, DataSource, IST, Timeframe
from trader.ml.forecaster import NextSessionForecaster, ForecastDirection, PredictionStatus
from tests.fixtures.synthetic_fixture import SyntheticDataProvider


def test_forecaster_feature_computation():
    provider = SyntheticDataProvider()
    candles = provider.get_historical_candles("NIFTY", timeframe=Timeframe.DAILY)
    assert len(candles) >= 50

    forecaster = NextSessionForecaster(ledger_dir="data/test_forecasts")
    df = forecaster.generate_features(candles)

    assert "ret_1d" in df.columns
    assert "rsi_14" in df.columns
    assert "atr_pct" in df.columns
    assert "sma_20" in df.columns
    assert "volatility_20" in df.columns


def test_forecaster_next_session_prediction():
    provider = SyntheticDataProvider()
    candles = provider.get_historical_candles("INFY", timeframe=Timeframe.DAILY)

    forecaster = NextSessionForecaster(ledger_dir="data/test_forecasts")
    forecast = forecaster.forecast_next_session("INFY", candles)

    assert forecast.symbol == "INFY"
    assert forecast.direction in [ForecastDirection.BULLISH, ForecastDirection.BEARISH, ForecastDirection.NEUTRAL]
    assert 0.0 <= forecast.prob_up <= 1.0
    assert 0.0 <= forecast.prob_down <= 1.0
    assert round(forecast.prob_up + forecast.prob_down, 2) == 1.0
    assert forecast.expected_range_low < forecast.current_price < forecast.expected_range_high
    assert len(forecast.primary_technical_drivers) > 0

    # Verify baseline comparisons
    assert forecast.baselines.zero_return_direction == ForecastDirection.NEUTRAL
    assert forecast.baselines.persistence_direction in [ForecastDirection.BULLISH, ForecastDirection.BEARISH, ForecastDirection.NEUTRAL]


def test_forecaster_ledger_and_evaluation():
    forecaster = NextSessionForecaster(ledger_dir="data/test_forecasts")
    provider = SyntheticDataProvider()
    candles = provider.get_historical_candles("RELIANCE", timeframe=Timeframe.DAILY)

    # 1. Generate prediction
    f = forecaster.forecast_next_session("RELIANCE", candles[:-1])
    ledger = forecaster.get_ledger("RELIANCE")
    assert len(ledger) >= 1
    assert ledger[0]["status"] == PredictionStatus.PENDING.value

    # 2. Evaluate with realized candle
    eval_result = forecaster.evaluate_realized_candles({"RELIANCE": candles})
    assert "total_predictions" in eval_result
    assert "accuracy_pct" in eval_result

