import os
import json
from alpaca_trade_api.rest import REST, TimeFrame, TimeFrameUnit
import alpaca_trade_api as tradeapi 
import time 

# Connect to Alpaca
os.chdir("/Users/chan/Documents")
endpoint = "https://data.alpaca.markets/v2"
headers = json.loads(open("keys.txt", 'r').read())
api = tradeapi.REST(headers["APCA-API-KEY-ID"], headers["APCA-API-SECRET-KEY"], base_url='https://paper-api.alpaca.markets')  


# Assign tickers to trade and cap position 
tickers = ['AMZN','INTC','MSFT','AAPL','GOOG']
max_pos = 1000


# Create dictionary to store Stochastic Oscillator signal
stoch_signal = {}
for ticker in tickers:
    stoch_signal[ticker] = ""


# Define trading strategy
def main():
    global stoch_signal
    historical_data = hist_data(tickers, start_date=time.strftime("%Y-%m-%d"), timeframe="Minute") 
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
                        print("bought {} shares of {}".format(max(1, int(max_pos/historical_data[ticker]["close"].iloc[-1])), ticker))
                        try:
                            filled_qty = api.get_position(ticker).qty
                            time.sleep(1)
                            api.submit_order(ticker, int(filled_qty), "sell", "trailing_stop", "day", trail_percent="1.5")
                        except Exception as e: 
                            print(ticker, e)


# Run testing strategy (tweak time variables accordingly to match candle interval)
starttime = time.time()
timeout = starttime + 60 * 60 * 1
while time.time() <= timeout:
    print("starting iteration at {}".format(time.strftime("%Y-%m-%d %H:%M:%S")))
    main()
    time.sleep(60 - ((time.time() - starttime) % 60))
    

# Close out all positions after timeout
api.close_all_positions()
time.sleep(10)
api.cancel_all_orders()
time.sleep(10)
 
