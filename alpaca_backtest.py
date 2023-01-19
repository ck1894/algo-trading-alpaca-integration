import os
import json
from alpaca_trade_api.rest import REST, TimeFrame, TimeFrameUnit
from copy import deepcopy 
import numpy as np
import pandas as pd


# Connect to Alpaca
os.chdir("/Users/chan/Documents")
endpoint = "https://data.alpaca.markets/v2"
headers = json.loads(open("keys.txt",'r').read())


# Load historical data for backtesting
tickers = ['AMZN','INTC','MSFT','AAPL','GOOG']
historical_data = hist_data(tickers, start_date="2022-10-01", timeframe="Hour") 
ohlc_dict = deepcopy(historical_data)


# Calculate MACD and Stochastic Oscillator for historical data
MACD(ohlc_dict)
stochastic(ohlc_dict)


# Create dictionaries to store signals and trade data
stoch_signal = {}
tickers_signal = {}
tickers_return = {}
trade_count = {}
trade_data = {}
hwm = {}

for ticker in tickers: 
    ohlc_dict[ticker].dropna(inplace=True)
    stoch_signal[ticker] = "" 
    tickers_signal[ticker] = ""
    trade_count[ticker] = 0
    hwm[ticker] = 0
    tickers_return[ticker] = [0]
    trade_data[ticker] = {}


# Define backtesting logic  
def main():
    for ticker in tickers: 
        print("looping through {}".format(ticker))
        for i in range(1, len(ohlc_dict[ticker])-1):
            if ohlc_dict[ticker]["%K"][i] < 20:
                stoch_signal[ticker] = "oversold"
            elif ohlc_dict[ticker]["%K"][i] > 80:
                stoch_signal[ticker] = "overbought"
    
            if tickers_signal[ticker] == "":
                tickers_return[ticker].append(0)
                if ohlc_dict[ticker]["macd"][i] > ohlc_dict[ticker]["signal"][i] and \
                   ohlc_dict[ticker]["macd"][i-1] < ohlc_dict[ticker]["signal"][i-1] and \
                   stoch_signal[ticker] == "oversold":
                       tickers_signal[ticker] = "Buy"
                       trade_count[ticker] += 1
                       trade_data[ticker][trade_count[ticker]] = [ohlc_dict[ticker]["open"][i+1]]
                       hwm[ticker] = ohlc_dict[ticker]["open"][i+1]
            
            elif tickers_signal[ticker] == "Buy":
                if ohlc_dict[ticker]["low"][i] < 0.985 * hwm[ticker]:
                    tickers_signal[ticker] = ""
                    trade_data[ticker][trade_count[ticker]].append(0.985 * hwm[ticker])
                    trade_count[ticker] += 1
                    tickers_return[ticker].append(0.985 * hwm[ticker] / ohlc_dict[ticker]["close"][i-1] -1)
                else:
                    hwm[ticker] = max(hwm[ticker], ohlc_dict[ticker]["high"][i])
                    tickers_return[ticker].append(ohlc_dict[ticker]["close"][i] / ohlc_dict[ticker]["close"][i] -1)
        
        if trade_count[ticker] % 2 != 0: 
            trade_data[ticker][trade_count[ticker]].append(ohlc_dict[ticker]["close"][i+1])
            
        tickers_return[ticker].append(0)
        ohlc_dict[ticker]["ret"] = np.array(tickers_return[ticker]) 


# Run backtesting 
main()


# Evaluate result using intraday KPIs
trade_df = {}
overall_return = 0

for ticker in tickers: 
    trade_df[ticker] = pd.DataFrame(trade_data[ticker]).T
    trade_df[ticker].columns = ["entry_pr", "exit_pr"]
    trade_df[ticker]["return"] = trade_df[ticker]["exit_pr"] / trade_df[ticker]["entry_pr"]
    print("return for {} = {}".format(ticker, trade_df[ticker]["return"].cumprod().iloc[-1] -1))
    overall_return += (1 / len(tickers)) * (trade_df[ticker]["return"].cumprod().iloc[-1] -1)

print("overall return of strategy = {}".format(overall_return))
    
win_rate = {}
mean_ret_pt = {}
mean_ret_pwt = {}
mean_ret_plt = {}
max_cons_loss = {}

for ticker in tickers:
    print("calculating intraday KPIs for ",ticker)
    win_rate[ticker] =  winRate(trade_df[ticker])      
    mean_ret_pt[ticker] =  meanretpertrade(trade_df[ticker])
    mean_ret_pwt[ticker] =  meanretwintrade(trade_df[ticker])
    mean_ret_plt[ticker] =  meanretlostrade(trade_df[ticker])
    max_cons_loss[ticker] =  maxconsectvloss(trade_df[ticker])

KPI_df = pd.DataFrame([win_rate,mean_ret_pt,mean_ret_pwt,mean_ret_plt,max_cons_loss],
                      index=["Win Rate","Mean Return Per Trade","MR Per WR", "MR Per LR", "Max Cons Loss"])      
KPI_df = KPI_df.T
    
