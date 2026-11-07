# Point-in-time NIFTY 500 universe input

The EOD job expects a locally maintained CSV at `data/universe/nifty500.csv` with two required columns:

    symbol,tick_size
    RELIANCE,0.05
    TCS,0.10
    INFY,0.05

Maintain this file from an exchange/provider source whose use and storage rights have been verified. NSE equity tick sizes are price-linked and periodically reviewed; use the current monthly applicable tick size for each security, not a universal hard-coded ₹0.05. Record the effective date and source in the Task Scheduler UniverseVersion parameter or in a companion change log. Do not silently overwrite historical constituent membership: retain each session's snapshot so backtests do not use today's constituents for past dates.

The PowerShell runner requires a positive tick_size for every symbol and rejects fewer than 450 or more than 500 unique valid symbols. This is a sanity check, not proof that the file is the official NIFTY 500. Validate membership against the current official constituent file before scheduling.

No constituent file is committed because it is time-varying market data and its redistribution rights have not been established.
