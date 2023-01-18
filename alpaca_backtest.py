import os
import json
from alpaca_trade_api.rest import REST, TimeFrame, TimeFrameUnit
from copy import deepcopy 
import numpy as np
import pandas as pd

os.chdir("/Users/chan/Documents")
endpoint = "https://data.alpaca.markets/v2"
headers = json.loads(open("keys.txt",'r').read())

tickers = ['AMZN','INTC','MSFT','AAPL','GOOG']

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
        df_data[ticker] = df_data[ticker].between_time("09:31","16:00")    
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

def winRate(DF):
    df = DF["return"]
    pos = df[df>1]
    neg = df[df<1]
    return (len(pos)/len(pos+neg))*100

def meanretpertrade(DF):
    df = DF["return"]
    df_temp = (df-1).dropna()
    return df_temp[df_temp!=0].mean()

def meanretwintrade(DF):
    df = DF["return"]
    df_temp = (df-1).dropna()
    return df_temp[df_temp>0].mean()

def meanretlostrade(DF):
    df = DF["return"]
    df_temp = (df-1).dropna()
    return df_temp[df_temp<0].mean()

def maxconsectvloss(DF):
    df = DF["return"]
    df_temp = df.dropna(axis=0)
    df_temp2 = np.where(df_temp<1,1,0)
    count_consecutive = []
    seek = 0
    for i in range(len(df_temp2)):
        if df_temp2[i] == 0:
            if seek > 0:
                count_consecutive.append(seek)
            seek = 0
        else:
            seek+=1
    if len(count_consecutive) > 0:
        return max(count_consecutive)
    else:
        return 0

historical_data = hist_data(tickers, start_date = "2022-10-01", timeframe = "Hour") 

ohlc_dict = deepcopy(historical_data)

stoch_signal = {}
tickers_signal = {}
tickers_return = {}
trade_count = {}
trade_data = {}
hwm = {}

MACD(ohlc_dict)
stochastic(ohlc_dict)

for ticker in tickers: 
    ohlc_dict[ticker].dropna(inplace=True)
    stoch_signal[ticker] = "" 
    tickers_signal[ticker] = ""
    trade_count[ticker] = 0
    hwm[ticker] = 0
    tickers_return[ticker] = [0]
    trade_data[ticker] = {}


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
    
trade_df = {}
overall_return = 0
for ticker in tickers: 
    trade_df[ticker] = pd.DataFrame(trade_data[ticker]).T
    trade_df[ticker].columns = ["entry_pr", "exit_pr"]
    trade_df[ticker]["return"] = trade_df[ticker]["exit_pr"] / trade_df[ticker]["entry_pr"]
    print("return for {} = {}".format(ticker, trade_df[ticker]["return"].cumprod().iloc[-1] -1))
    overall_return += (1/len(tickers)) * (trade_df[ticker]["return"].cumprod().iloc[-1] -1)

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
KPI_df.T
    
