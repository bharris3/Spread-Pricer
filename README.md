# TDA-Spread-Pricer
 
This script will pull the option chains for a list of tickers provided, and output the bid/ask for spreads that follow the parameters inputted.

You'll need to set a few variables / params:

client_id (You can either set this as environment var or direct string) <br>
redirect_uri (You can either set this as environment var or direct string) </br>
credentials_path (You can either set this as environment var or direct string) </br>
tickers -> list of strings <br>
min_mid_price -> float <br>
max_loss -> float <br>
min_movement_to_itm -> float

Example Output for a put:

Ticker | Expiration Date | Spread Bid | Spread Ask | Mid | Strike Sold | Strike Bought | Strike Spread | Max Loss | Spot Price | Pct mvmt to short ATM
--- | --- | --- | --- |--- |--- |--- |--- |--- |--- |---
DUST | 2/12/2021 | 0.08 | 0.24 | 0.16 | 19.5 | 18.5 | 1 | -0.92 | 20.46 | -4.692082111