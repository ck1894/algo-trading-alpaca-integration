# Returns historical data for a list of tickers
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
        df_data[ticker] = df_data[ticker].between_time("09:31", "16:00")    
    return df_data

# Calculates Stochastic Oscillator (lookback = lookback period, k and d = moving average window)
def stochastic(df_dict, lookback=14, k=3, d=3):
    for df in df_dict:
        df_dict[df]["HH"] = df_dict[df]["high"].rolling(lookback).max()
        df_dict[df]["LL"] = df_dict[df]["low"].rolling(lookback).min()
        df_dict[df]["%K"] = (100 * (df_dict[df]["close"] - df_dict[df]["LL"]) / (df_dict[df]["HH"] - df_dict[df]["LL"])).rolling(k).mean()
        df_dict[df]["%D"] = df_dict[df]["%K"].rolling(d).mean()
        df_dict[df].drop(["HH", "LL"], axis=1, inplace=True)

# Calculates MACD (a = fast moving average, b = slow moving average, c = signal line ma window)
def MACD(df_dict, a=12, b=26, c=9):    
    for df in df_dict:
        df_dict[df]["ma_fast"] = df_dict[df]["close"].ewm(span=a, min_periods=a).mean()
        df_dict[df]["ma_slow"] = df_dict[df]["close"].ewm(span=b, min_periods=b).mean()
        df_dict[df]["macd"] = df_dict[df]["ma_fast"] - df_dict[df]["ma_slow"]
        df_dict[df]["signal"] = df_dict[df]["macd"].ewm(span=c, min_periods=c).mean()
        df_dict[df].drop(["ma_fast", "ma_slow"], axis=1, inplace=True)

# Calculates intraday KPIs
def winRate(DF):
    df = DF["return"]
    pos = df[df > 1]
    neg = df[df < 1]
    return (len(pos) / len(pos + neg)) * 100

def meanretpertrade(DF):
    df = DF["return"]
    df_temp = (df - 1).dropna()
    return df_temp[df_temp != 0].mean()

def meanretwintrade(DF):
    df = DF["return"]
    df_temp = (df - 1).dropna()
    return df_temp[df_temp > 0].mean()

def meanretlostrade(DF):
    df = DF["return"]
    df_temp = (df - 1).dropna()
    return df_temp[df_temp < 0].mean()

def maxconsectvloss(DF):
    df = DF["return"]
    df_temp = df.dropna(axis = 0)
    df_temp2 = np.where(df_temp < 1, 1, 0)
    count_consecutive = []
    seek = 0
    for i in range(len(df_temp2)):
        if df_temp2[i] == 0:
            if seek > 0:
                count_consecutive.append(seek)
            seek = 0
        else:
            seek += 1
    if len(count_consecutive) > 0:
        return max(count_consecutive)
    else:
        return 0
