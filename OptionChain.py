import pandas as pd
from td.client import TDClient  # https://github.com/areed1192/td-ameritrade-python-api
import csv
from datetime import datetime, time, timedelta
import os

#Extra packages to check out for other functionality with TD API:
    # https://tda-api.readthedocs.io/en/stable/example.html
    # https://tdameritrade.readthedocs.io/en/latest/ / https://github.com/timkpaine/tdameritrade/blob/master/tdameritrade/client.py
    # https://github.com/jeog/TDAmeritradeAPI,

def main():

    # if we are past market close, then let's change time to 1pm since data is last updated at 1pm
    if datetime.today().weekday() > 4:
        # if day is saturday/sunday (int 5/6), our option chain is as recent as 1pm Friday (mkt close)
        # get the last friday and put the date into string date with time 1pm
        days_past_friday = datetime.today().weekday() - 4
        timestamp = (datetime.today() - timedelta(days=days_past_friday)).strftime("%Y-%m-%d 13.00.00")
    else:
        if datetime.today().time() > time(13, 0):
            timestamp = datetime.today().strftime("%Y-%m-%d 13.00.00")
        else:
            timestamp = datetime.today().strftime("%Y-%m-%d %H.%M.%S")

    ###PARAMETERS###
    client = os.environ["TD_CLIENT_ID"]
    uri = os.environ["TD_REDIRECT_URL"]
    creds = os.environ["TD_CREDENTIALS_PATH"]
    begin_date = "2021-02-06"
    end_date = "2021-02-13"
    tickers = []
    min_mid_price = .13
    max_loss = -1
    min_movement_to_itm = 1.9
    call_output = r"C:/your/output/location"
    put_output = r"C:/your/output/location"
    ###END PARAMETERS###

    # Create a new session. This uses my stored environment variables for logging on.
    TDSession = TDClient(
        client_id=client,
        redirect_uri=uri,
        credentials_path=creds
    )

    # Login to the session
    TDSession.login()

    CALLSdf, PUTSdf = get_chain(tickers,TDSession,begin_date,end_date)

    headers = ["Ticker","Expiration Date","Spread Bid","Spread Ask","Mid",
               "Strike Sold","Strike Bought","Strike Spread","Max Loss","Spot Price",
               "Pct mvmt to short ATM"]

    call_opportunities, put_opportunities = [headers], [headers]

    for ticker in tickers:

        #we can't compare options across tickers, so we need to filter to a df per ticker
        CALLSdf_ticker_filtered = CALLSdf.loc[(CALLSdf["underlyingTicker"] == ticker)]
        PUTSdf_ticker_filtered = PUTSdf.loc[(PUTSdf["underlyingTicker"] == ticker)]

        #unique list of expiry dates per ticker
        call_expiry_dates = [x for x in CALLSdf["expirationDate"].drop_duplicates()]
        put_expiry_dates = [x for x in PUTSdf["expirationDate"].drop_duplicates()]

        for call_expiration_date in call_expiry_dates:
            # Calls first
            CALLSdf_date_filtered = CALLSdf_ticker_filtered.loc[(CALLSdf["expirationDate"] == call_expiration_date)]

            for row in CALLSdf_date_filtered.itertuples(index=True,name=None):
                #begin call spread with short first
                #we sell @ bid, buy @ ask
                bid_short = row[5]
                ask_short = row[6]
                bid_strike = row[33]
                underlying_price = row[48]
                pct_to_short_ITM_call = ((bid_strike - underlying_price)/underlying_price) * 100
                for row2 in CALLSdf_date_filtered.itertuples(index=True, name=None):
                    bid_long = row2[5]
                    ask_long = row2[6]
                    spread_bid = ask_long - bid_short
                    spread_ask = bid_long - ask_short
                    # if the mid is > 0, then we would be opening a spread with a net debit
                    if spread_ask + spread_bid < 0:
                        # absolute value in order to properly display premium and calculate PnLs
                        spread_mid = abs((spread_ask + spread_bid) / 2)
                    else:
                        # don't want this spread if it is not a net credit, so skip the row
                        continue

                    ask_strike = row2[33]
                    strike_spread = ask_strike - bid_strike

                    # strike spread needs at be at least 1 because TDA doesn't allow vertical spreads where strike spread < 1
                    # net_premium > .013 because it costs 67 cents per contract and we're trading 2 (so commissions are $1.34)
                    if spread_mid - strike_spread > max_loss and strike_spread >= 1 \
                        and spread_mid > min_mid_price and pct_to_short_ITM_call > min_movement_to_itm:

                        call_opportunities.append([ticker,call_expiration_date,abs(spread_bid),
                                                   abs(spread_ask),spread_mid,
                                                   bid_strike,ask_strike,strike_spread,
                                                   (spread_mid-strike_spread),
                                                   underlying_price, pct_to_short_ITM_call])

        for put_expiration_date in put_expiry_dates:
            PUTSdf_date_filtered = PUTSdf_ticker_filtered.loc[(PUTSdf["expirationDate"] == put_expiration_date)]
            for row in PUTSdf_date_filtered.itertuples(index=True,name=None):
                #sell at bid, buy at ask
                bid_short = row[5]
                ask_short = row[6]
                bid_strike = row[33]
                underlying_price = row[48]
                pct_to_short_ITM_put = ((bid_strike - underlying_price) / underlying_price) * 100
                for row2 in PUTSdf_date_filtered.itertuples(index=True,name=None):
                    bid_long = row2[5]
                    ask_long = row2[6]
                    spread_bid = ask_long - bid_short
                    spread_ask = bid_long - ask_short
                    ask_strike = row2[33]
                    # if the mid is > 0, then we would be opening a spread with a net debit
                    if spread_ask + spread_bid < 0:
                        # absolute value in order to properly display premium and calculate PnLs
                        spread_mid = abs((spread_ask + spread_bid) / 2)
                    else:
                        # don't want this spread if it is not a net credit, so skip the row
                        continue

                    strike_spread = bid_strike - ask_strike

                    if spread_mid - strike_spread > max_loss and strike_spread >= 1\
                    and spread_mid > min_mid_price and pct_to_short_ITM_put < -min_movement_to_itm:
                        # strike spread needs at be at least 1 because TDA doesn't allow vertical spreads where strike spread < 1
                        # net_premium > .013 because it costs 67 cents per contract and we're trading 2 (so commissions are $1.34)
                        put_opportunities.append([ticker,put_expiration_date,abs(spread_bid),
                                                  abs(spread_ask),spread_mid,
                                                  bid_strike,ask_strike,strike_spread,
                                                  (spread_mid-strike_spread),
                                                  underlying_price, pct_to_short_ITM_put])

    with open(call_output,"w",newline="") as oppfile:
        writer = csv.writer(oppfile)
        writer.writerows(call_opportunities)

    with open(put_output,"w",newline="") as oppfile2:
        writer = csv.writer(oppfile2)
        writer.writerows(put_opportunities)

def get_chain(tickers,TDSession,begin_date,end_date):

    PUTquotes = []
    CALLquotes = []
    underlyingPrices = []

    for ticker in tickers:

        chain = TDSession.get_options_chain(option_chain={"symbol": ticker})
        price = chain["underlyingPrice"]

        if [ticker, price] not in underlyingPrices:
            underlyingPrices.append([ticker, price])

        for date in chain['callExpDateMap']:
            for strike in chain['callExpDateMap'][date]:
                CALLquotes.extend(chain['callExpDateMap'][date][strike])

        for date in chain['putExpDateMap']:
            for strike in chain['putExpDateMap'][date]:
                PUTquotes.extend(chain['putExpDateMap'][date][strike])

    mastercallsdf = pd.DataFrame(CALLquotes)
    masterputsdf = pd.DataFrame(PUTquotes)
    prices = pd.DataFrame(underlyingPrices, columns = ["underlyingTicker","price"])

    #remove any non-standard options
    mastercallsdf = mastercallsdf.loc[(mastercallsdf["nonStandard"] == False)]
    masterputsdf = masterputsdf.loc[(masterputsdf["nonStandard"] == False)]

    #drop all rows where bid and/or ask is 0. We only want to consider options with liquidity
    mastercallsdf = mastercallsdf.loc[(mastercallsdf["bid"] != 0) & (mastercallsdf["ask"] != 0)]
    masterputsdf = masterputsdf.loc[(masterputsdf["bid"] != 0) & (masterputsdf["ask"] != 0)]

    #filter out in-the-money options
    mastercallsdf = mastercallsdf.loc[(mastercallsdf["inTheMoney"] == False)]
    masterputsdf = masterputsdf.loc[(masterputsdf["inTheMoney"] == False)]

    #format dates
    for col in ["tradeTimeInLong", "quoteTimeInLong",
                "expirationDate", "lastTradingDay"]:
        masterputsdf[col] = pd.to_datetime(masterputsdf[col], unit='ms')
        mastercallsdf[col] = pd.to_datetime(mastercallsdf[col], unit='ms')
        # returns it in UTC (7 hours ahead of Seattle/PST)
        # to_datetime is deprecated, need to switch to to_pydatetime at some point

    # filter out options based expiration date preferences.
    mastercallsdf = mastercallsdf.loc[(mastercallsdf["expirationDate"] >= begin_date) & (mastercallsdf["expirationDate"] <= end_date)]
    masterputsdf = masterputsdf.loc[(masterputsdf["expirationDate"] >= begin_date) & (masterputsdf["expirationDate"] <= end_date)]

    # add ticker column
    mastercallsdf["underlyingTicker"] = mastercallsdf["symbol"].str.split("_").str[0]
    masterputsdf["underlyingTicker"] = masterputsdf["symbol"].str.split("_").str[0]

    # set underlyingTicker as index, join the price column from the prices df to the main dfs
    mastercallsdf = mastercallsdf.set_index("underlyingTicker").join(prices.set_index("underlyingTicker"))
    masterputsdf = masterputsdf.set_index("underlyingTicker").join(prices.set_index("underlyingTicker"))

    #now we have dupe values (tickers) in the index column. Move underlyingTicker back to its own column, and reindex
    mastercallsdf["underlyingTicker"] = mastercallsdf.index
    masterputsdf["underlyingTicker"] = masterputsdf.index

    mastercallsdf.reset_index(inplace=True,drop=True)
    masterputsdf.reset_index(inplace=True, drop=True)

    return mastercallsdf, masterputsdf

main()