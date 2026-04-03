import yfinance as yf
import pandas as pd
import datetime
import streamlit as st

@st.cache_data(ttl=86400) 
def fetch_data(tickers, start_date):
    """ฟังก์ชันดึงข้อมูลราคาปิดย้อนหลัง"""
    end = datetime.date.today()
    try:
        if not tickers: return pd.DataFrame()
        df = yf.download(tickers, start=start_date, end=end)
        if df.empty: return pd.DataFrame()
        
        if len(tickers) == 1:
            data = df[['Adj Close']] if 'Adj Close' in df.columns else df[['Close']]
            data.columns = tickers
        else:
            if 'Adj Close' in df.columns.levels[0]:
                data = df['Adj Close']
            else:
                data = df['Close']
            
        return data.ffill().dropna()
    except Exception as e:
        st.error(f"⚠️ ดึงข้อมูลล้มเหลว: {e}")
        return pd.DataFrame()
