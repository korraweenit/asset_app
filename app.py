import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import datetime
import numpy as np

# ==========================================
# ⚙️ CONFIG & STYLE
# ==========================================
st.set_page_config(page_title="Portfolio Backtest Comparison", layout="wide")

# Custom CSS for better looking metrics
st.markdown("""
    <style>
    [data-testid="stMetricValue"] {
        font-size: 28px;
        color: #1E88E5;
    }
    [data-testid="stMetricLabel"] {
        font-weight: bold;
        text-transform: uppercase;
        font-size: 14px;
    }
    .stMetric {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_data(ttl=86400) 
def fetch_data(tickers, start_date):
    """ฟังก์ชันดึงข้อมูลราคาปิดย้อนหลัง"""
    end = datetime.date.today()
    try:
        df = yf.download(tickers, start=start_date, end=end)
        if df.empty: return pd.DataFrame()
        
        if isinstance(df.columns, pd.MultiIndex):
            if 'Adj Close' in df.columns.levels[0]:
                data = df['Adj Close']
            else:
                data = df['Close']
        else:
            data = df[['Adj Close']] if 'Adj Close' in df.columns else df[['Close']]
            
        return data.ffill().dropna()
    except Exception as e:
        st.error(f"⚠️ ดึงข้อมูลล้มเหลว: {e}")
        return pd.DataFrame()

def calculate_metrics(cum_return, daily_returns):
    """คำนวณสถิติสำคัญ: Total Return, CAGR, Volatility, Max Drawdown"""
    days = (cum_return.index[-1] - cum_return.index[0]).days
    actual_years = days / 365.25 if days > 0 else 1.0
    
    total_return = (cum_return.iloc[-1] - 1)
    cagr = (cum_return.iloc[-1] ** (1/actual_years)) - 1 if actual_years > 0 else total_return
    
    # Volatility (Annualized Standard Deviation)
    volatility = daily_returns.std() * np.sqrt(252)
    
    # Max Drawdown
    rolling_max = cum_return.cummax()
    drawdown = (cum_return / rolling_max) - 1
    max_drawdown = drawdown.min()
    
    return {
        "total_return": total_return,
        "cagr": cagr,
        "volatility": volatility,
        "max_drawdown": max_drawdown,
        "years": actual_years
    }

# ==========================================
# 🎨 FRONTEND UI (Sidebar)
# ==========================================
st.title("⚖️ Strategy Comparison: A vs B")

with st.sidebar:
    st.header("📅 ช่วงเวลา (Time Period)")
    period_choice = st.selectbox("เลือกช่วงเวลาย้อนหลัง", ["1Y", "5Y", "10Y", "20Y", "YTD"], index=2)

    today = datetime.date.today()
    if period_choice == "1Y":
        start_date = today - datetime.timedelta(days=365)
    elif period_choice == "5Y":
        start_date = today - datetime.timedelta(days=5*365)
    elif period_choice == "10Y":
        start_date = today - datetime.timedelta(days=10*365)
    elif period_choice == "20Y":
        start_date = today - datetime.timedelta(days=20*365)
    else: # YTD
        start_date = datetime.date(today.year, 1, 1)

    st.divider()
    
    st.header("🛡️ Strategy A")
    a_t1 = st.text_input("Asset 1 (A)", "VOO", key="at1").upper()
    a_w1 = st.slider(f"Weight {a_t1} (%)", 0, 100, 80, key="aw1")
    a_t2 = st.text_input("Asset 2 (A)", "GLD", key="at2").upper()
    a_w2 = 100 - a_w1
    st.info(f"💡 {a_t2} = {a_w2}%")

    st.divider()
    
    st.header("🎯 Strategy B")
    b_t1 = st.text_input("Asset 1 (B)", "VOO", key="bt1").upper()
    b_w1 = st.slider(f"Weight {b_t1} (%)", 0, 100, 100, key="bw1")
    b_t2 = st.text_input("Asset 2 (B)", "GLD", key="bt2").upper()
    b_w2 = 100 - b_w1
    st.info(f"💡 {b_t2} = {b_w2}%")

# ==========================================
# 🛡️ EXECUTION
# ==========================================
if st.sidebar.button("🚀 Run Comparison", use_container_width=True):
    with st.spinner('กำลังประมวลผลข้อมูล...'):
        all_tickers = list(set([a_t1, a_t2, b_t1, b_t2]))
        data = fetch_data(all_tickers, start_date)
        
        if not data.empty:
            returns = data.pct_change().dropna()
            
            # คำนวณรายวัน
            port_a_ret = (returns[a_t1] * (a_w1/100)) + (returns[a_t2] * (a_w2/100))
            cum_a = (1 + port_a_ret).cumprod()
            
            port_b_ret = (returns[b_t1] * (b_w1/100)) + (returns[b_t2] * (b_w2/100))
            cum_b = (1 + port_b_ret).cumprod()
            
            # Metrics Calculation
            met_a = calculate_metrics(cum_a, port_a_ret)
            met_b = calculate_metrics(cum_b, port_b_ret)
            
            # --- 1. Dashboard Metrics (Scorecards) ---
            st.subheader(f"📊 Performance Overview ({met_a['years']:.1f} Years)")
            
            col_a, col_b = st.columns(2)
            
            with col_a:
                with st.container(border=True):
                    st.markdown(f"#### 🛡️ Strategy A: {a_t1}({a_w1}%) + {a_t2}({a_w2}%)")
                    m1, m2 = st.columns(2)
                    m1.metric("Total Return", f"{met_a['total_return']*100:.2f}%")
                    m2.metric("CAGR (%)", f"{met_a['cagr']*100:.2f}%")
                    
                    m3, m4 = st.columns(2)
                    m3.metric("Volatility (SD)", f"{met_a['volatility']*100:.2f}%")
                    m4.metric("Max Drawdown", f"{met_a['max_drawdown']*100:.2f}%")

            with col_b:
                with st.container(border=True):
                    st.markdown(f"#### 🎯 Strategy B: {b_t1}({b_w1}%) + {b_t2}({b_w2}%)")
                    m1, m2 = st.columns(2)
                    m1.metric("Total Return", f"{met_b['total_return']*100:.2f}%")
                    m2.metric("CAGR (%)", f"{met_b['cagr']*100:.2f}%")
                    
                    m3, m4 = st.columns(2)
                    m3.metric("Volatility (SD)", f"{met_b['volatility']*100:.2f}%")
                    m4.metric("Max Drawdown", f"{met_b['max_drawdown']*100:.2f}%")
            
            st.markdown("<br>", unsafe_allow_html=True)

            # --- 2. Chart Display ---
            df_plot = pd.DataFrame({
                'Strategy A': cum_a,
                'Strategy B': cum_b
            })
            fig = px.line(df_plot, title=f"Portfolio Growth Comparison ({period_choice})")
            fig.update_layout(
                hovermode="x unified", 
                yaxis_title="Portfolio Value ($1 Base)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # --- 3. Expander (Bottom) ---
            with st.expander("📂 View Raw Data & Details"):
                st.dataframe(df_plot.style.format("{:.4f}"), use_container_width=True)
                st.info(f"Analysis start from {cum_a.index[0].date()} to {cum_a.index[-1].date()}")
        else:
            st.error("ไม่พบข้อมูลสำหรับ Tickers หรือช่วงเวลาที่ระบุ")
else:
    st.info("👈 ปรับแต่งพอร์ตโฟลิโอใน Sidebar แล้วกด 'Run Comparison' เพื่อเริ่มวิเคราะห์")
