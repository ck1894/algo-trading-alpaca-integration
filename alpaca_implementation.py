import os
import json
from alpaca_trade_api.rest import REST, TimeFrame, TimeFrameUnit
import alpaca_trade_api as tradeapi 
import time 

os.chdir("/Users/chan/Documents")
endpoint = "https://data.alpaca.markets/v2"
headers = json.loads(open("keys.txt",'r').read())
api = tradeapi.REST(headers["APCA-API-KEY-ID"], headers["APCA-API-SECRET-KEY"],base_url='https://paper-api.alpaca.markets')  

tickers = ['AMZN','INTC','MSFT','AAPL','GOOG']
max_pos = 1000
stoch_signal = {}
for ticker in tickers:
    stoch_signal[ticker] = ""

def hist_data(symbols, start_date, timeframe):
    df_data = {}
    api = REST(headers["APCA-API-KEY-ID"], headers["APCA-API-SECRET-KEY"], base_url=endpoint)
    for ticker in symbols:
        if timeframe == "Minute":
            df_data[ticker] = api.get_bars(ticker, TimeFrame.Minute, start_date, adjustment='all').df
        elif timeframe == "15Minute":
            df_data[ticker] = api.get_bars(ticker, TimeFrame(15, TimeFrameUnit.Minute), start_date, adjustment='all').df
        elif timeframe == "Hour":
            df_data[ticker] = api.get_bars(ticker, TimeFrame.Hour, start_date, adjustment='all').df
        else:
            df_data[ticker] = api.get_bars(ticker, TimeFrame.Day, start_date, adjustment='all').df
        #df_data[ticker] = df_data[ticker].between_time("09:31","16:00")    
    return df_data

def stochastic(df_dict, lookback=14, k=3, d=3):
    for df in df_dict:
        df_dict[df]["HH"] = df_dict[df]["high"].rolling(lookback).max()
        df_dict[df]["LL"] = df_dict[df]["low"].rolling(lookback).min()
        df_dict[df]["%K"] = (100 * (df_dict[df]["close"] - df_dict[df]["LL"])/(df_dict[df]["HH"]-df_dict[df]["LL"])).rolling(k).mean()
        df_dict[df]["%D"] = df_dict[df]["%K"].rolling(d).mean()
        df_dict[df].drop(["HH","LL"], axis=1, inplace=True)

def MACD(df_dict, a=12, b=26, c=9):    
    for df in df_dict:
        df_dict[df]["ma_fast"] = df_dict[df]["close"].ewm(span=a, min_periods=a).mean()
        df_dict[df]["ma_slow"] = df_dict[df]["close"].ewm(span=b, min_periods=b).mean()
        df_dict[df]["macd"] = df_dict[df]["ma_fast"] - df_dict[df]["ma_slow"]
        df_dict[df]["signal"] = df_dict[df]["macd"].ewm(span=c, min_periods=c).mean()
        df_dict[df].drop(["ma_fast","ma_slow"], axis=1, inplace=True)

def main():
    global stoch_signal
    historical_data = hist_data(tickers, start_date =time.strftime("%Y-%m-%d"), timeframe = "Minute") 
    MACD(historical_data)
    stochastic(historical_data)
    positions = api.list_positions()
    
    for ticker in tickers: 
        historical_data[ticker].dropna(inplace=True)
        existing_pos = False
    
        if historical_data[ticker]["%K"].iloc[-1] < 20:
            stoch_signal[ticker] = "oversold"
        elif historical_data[ticker]["%K"].iloc[-1] > 80:
            stoch_signal[ticker] = "overbought"
    
        for position in positions:
            if len(positions) > 0:
                if position.symbol == ticker and position.qty != 0: 
                    print("existing position of {} shares in {}...skip signal".format(position.qty, ticker))
                    existing_pos == True
    
        if historical_data[ticker]["macd"].iloc[-1] > historical_data[ticker]["signal"].iloc[-1] and \
            historical_data[ticker]["macd"].iloc[-2] < historical_data[ticker]["signal"].iloc[-2] and \
                stoch_signal[ticker] == "oversold" and \
                    existing_pos == False:
                        api.submit_order(ticker, max(1,int(max_pos/historical_data[ticker]["close"].iloc[-1])), "buy", "market", "ioc")
                        time.sleep(2)
                        print("bought {} shares of {}".format(max(1,int(max_pos/historical_data[ticker]["close"].iloc[-1])), ticker))
                        try:
                            filled_qty = api.get_position(ticker).qty
                            time.sleep(1)
                            api.submit_order(ticker, int(filled_qty), "sell", "trailing_stop", "day", trail_percent = "1.5")
                        except Exception as e: 
                            print(ticker, e)
    
starttime = time.time()
timeout = starttime + 60 * 60 * 1
while time.time() <= timeout:
    print("starting iteration at {}".format(time.strftime("%Y-%m-%d %H:%M:%S")))
    main()
    time.sleep(60 - ((time.time() - starttime) % 60))
    
    
api.close_all_positions()
time.sleep(10)
api.cancel_all_orders()
time.sleep(10)
    
