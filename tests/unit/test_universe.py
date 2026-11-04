"""Unit tests for Universe Manager."""

from trader.universe.instruments import UniverseManager


def test_universe_manager_curated_stocks():
    um = UniverseManager()
    symbols = um.get_all_symbols()
    assert len(symbols) >= 20
    assert "RELIANCE" in symbols
    assert "TCS" in symbols

    inst = um.get_instrument("RELIANCE")
    assert inst is not None
    assert inst.name == "Reliance Industries Ltd."
    assert inst.series == "EQ"
    assert inst.tick_size == 0.05

    it_stocks = um.get_symbols_by_industry("IT")
    assert "TCS" in it_stocks
    assert "INFY" in it_stocks

