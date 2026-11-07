# Point-in-time NIFTY 500 universe input

The EOD job expects a locally maintained CSV at `data/universe/nifty500.csv` with one required column:

    symbol
    RELIANCE
    TCS
    INFY

Maintain this file from an exchange/provider source whose use and storage rights have been verified. Record the effective date and source in the Task Scheduler UniverseVersion parameter or in a companion change log. Do not silently overwrite historical constituent membership: retain each session's snapshot so backtests do not use today's constituents for past dates.

The PowerShell runner rejects fewer than 450 or more than 500 unique valid symbols. This is a sanity check, not proof that the file is the official NIFTY 500. Validate membership against the current official constituent file before scheduling.

No constituent file is committed because it is time-varying market data and its redistribution rights have not been established.
