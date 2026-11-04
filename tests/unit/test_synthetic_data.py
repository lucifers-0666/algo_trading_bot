"""Unit tests for Synthetic Market Data Generator."""

from trader.data.synthetic import generate_synthetic_candles, generate_universe_dataset
from trader.data.validation import validate_candle_sequence


def test_generate_synthetic_candles_validity():
    candles = generate_synthetic_candles("RELIANCE", num_days=50, seed=42)
    assert len(candles) == 50
    assert all(c.symbol == "RELIANCE" for c in candles)

    # Validate that entire sequence is clean and monotonic
    valid, res = validate_candle_sequence(candles)
    assert len(valid) == 50
    assert res.is_valid is True


def test_generate_synthetic_candles_reproducibility():
    run1 = generate_synthetic_candles("TCS", num_days=30, seed=123)
    run2 = generate_synthetic_candles("TCS", num_days=30, seed=123)
    for c1, c2 in zip(run1, run2):
        assert c1.timestamp == c2.timestamp
        assert c1.open == c2.open
        assert c1.close == c2.close
        assert c1.volume == c2.volume


def test_generate_universe_dataset():
    symbols = ["RELIANCE", "TCS", "INFY"]
    dataset = generate_universe_dataset(symbols=symbols, num_days=20, base_seed=10)
    assert set(dataset.keys()) == set(symbols)
    for sym, candles in dataset.items():
        assert len(candles) == 20

