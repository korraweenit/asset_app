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

# ==========================================
# 🔄 SESSION STATE MANAGEMENT
# ==========================================
if 'strategy_a' not in st.session_state:
    st.session_state.strategy_a = [{'ticker': 'VOO', 'weight': 80}, {'ticker': 'GLD', 'weight': 20}]
if 'strategy_b' not in st.session_state:
    st.session_state.strategy_b = [{'ticker': 'VOO', 'weight': 100}]

def add_asset(strategy_key):
    st.session_state[strategy_key].append({'ticker': '', 'weight': 0})

def remove_asset(strategy_key, index):
    if len(st.session_state[strategy_key]) > 1:
        st.session_state[strategy_key].pop(index)

# ==========================================
# 📊 LOGIC FUNCTIONS
# ==========================================
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

def calculate_metrics(portfolio_series, total_invested, periodic_returns):
    """คำนวณสถิติสำคัญสำหรับพอร์ต DCA"""
    if portfolio_series.empty: return None
    
    final_value = portfolio_series.iloc[-1]
    total_return = (final_value - total_invested) / total_invested if total_invested > 0 else 0
    
    days = (portfolio_series.index[-1] - portfolio_series.index[0]).days
    actual_years = days / 365.25 if days > 0 else 1.0
    
    # CAGR safety check
    if actual_years > 0 and total_invested > 0 and final_value > 0:
        cagr = ((final_value / total_invested) ** (1/actual_years)) - 1
    else:
        cagr = 0
    
    # Volatility on organic returns (excluding DCA impact)
    # Use np.sqrt(12) for monthly data
    volatility = periodic_returns.fillna(0).std() * np.sqrt(12)
    
    # Max Drawdown
    rolling_max = portfolio_series.cummax()
    drawdown = (portfolio_series / rolling_max) - 1
    max_drawdown = drawdown.min()
    
    return {
        "final_value": final_value,
        "total_invested": total_invested,
        "total_return": total_return,
        "cagr": cagr,
        "volatility": volatility,
        "max_drawdown": max_drawdown,
        "years": actual_years
    }

def calculate_portfolio_dca(data, assets, initial_capital, monthly_dca):
    """คำนวณมูลค่าพอร์ตแบบ DCA + Semi-Annual Rebalance (ME resampled)"""
    # Resample to Month End
    monthly_prices = data.resample('ME').last()
    tickers = [a['ticker'].upper() for a in assets if a['ticker']]
    weights = np.array([a['weight'] / 100 for a in assets if a['ticker']])
    
    if not tickers or monthly_prices.empty:
        return pd.Series(), 0, pd.Series()

    prices = monthly_prices[tickers]
    dates = prices.index
    
    # Initial Setup
    units = np.zeros(len(tickers))
    portfolio_values = []
    periodic_returns = []
    total_invested = 0
    
    # Month 0 (Initial Investment)
    if initial_capital > 0:
        first_prices = prices.iloc[0].values
        units = (initial_capital * weights) / first_prices
        total_invested += initial_capital
    
    portfolio_values.append(np.sum(units * prices.iloc[0].values))
    periodic_returns.append(0)
    
    # Subsequent Months
    for i in range(1, len(dates)):
        prev_value = portfolio_values[-1]
        current_prices = prices.iloc[i].values
        
        # 1. Organic Growth (Update value with current prices)
        value_before_dca = np.sum(units * current_prices)
        
        # Calculate organic return: (ValueBeforeDCA - PrevValue) / PrevValue
        if prev_value > 0:
            ret = (value_before_dca - prev_value) / prev_value
        else:
            ret = 0
        periodic_returns.append(ret)
        
        # 2. Add Monthly DCA
        current_portfolio_value = value_before_dca + monthly_dca
        total_invested += monthly_dca
        
        # 3. Handle Rebalancing (June and December) or just distribute DCA
        if current_date := dates[i]:
            if current_date.month in [6, 12]:
                # Full Rebalance to target weights
                units = (current_portfolio_value * weights) / current_prices
            else:
                # Distribute DCA only (Simplified monthly behavior)
                units += (monthly_dca * weights) / current_prices
            
        portfolio_values.append(np.sum(units * current_prices))
        
    return pd.Series(portfolio_values, index=dates), total_invested, pd.Series(periodic_returns, index=dates)

# ==========================================
# 🎨 FRONTEND UI (Sidebar)
# ==========================================
st.title("⚖️ Portfolio DCA Backtest")

with st.sidebar:
    st.header("💰 Investment Settings")
    initial_cap = st.number_input("เงินลงทุนเริ่มต้น (Initial Capital)", min_value=0, value=0, step=1000)
    monthly_dca = st.number_input("เงิน DCA ทุกเดือน (Monthly DCA)", min_value=0, value=10000, step=500)
    
    st.divider()
    st.header("📅 ช่วงเวลา (Time Period)")
    period_choice = st.selectbox("เลือกช่วงเวลาย้อนหลัง", ["1Y", "5Y", "10Y", "20Y", "YTD"], index=1)

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

    def render_strategy_input(label, strategy_key):
        st.divider()
        st.header(label)
        
        current_weights = 0
        for i, asset in enumerate(st.session_state[strategy_key]):
            col1, col2, col3 = st.columns([3, 4, 1])
            with col1:
                asset['ticker'] = st.text_input(f"Ticker", asset['ticker'], key=f"{strategy_key}_t_{i}").upper()
            with col2:
                asset['weight'] = st.slider(f"Weight (%)", 0, 100, asset['weight'], key=f"{strategy_key}_w_{i}")
                current_weights += asset['weight']
            with col3:
                st.write("") # Spacer
                st.write("") # Spacer
                if st.button("🗑️", key=f"{strategy_key}_rm_{i}"):
                    remove_asset(strategy_key, i)
                    st.rerun()
        
        col_btn, col_info = st.columns([1, 1])
        with col_btn:
            if st.button(f"➕ Add Asset", key=f"{strategy_key}_add"):
                add_asset(strategy_key)
                st.rerun()
        
        with col_info:
            if current_weights == 100:
                st.success(f"Total: {current_weights}%")
            else:
                st.error(f"Total: {current_weights}%")
        
        return current_weights

    total_w_a = render_strategy_input("🛡️ Strategy A", "strategy_a")
    total_w_b = render_strategy_input("🎯 Strategy B", "strategy_b")

    st.divider()
    can_run = (total_w_a == 100) and (total_w_b == 100)
    
    if not can_run:
        st.warning("⚠️ ผลรวม Weight ต้องเท่ากับ 100% ทั้งสองพอร์ตก่อนเริ่ม Backtest")
    
    run_btn = st.button("🚀 Run Comparison", use_container_width=True, disabled=not can_run)

# ==========================================
# 🛡️ EXECUTION
# ==========================================
if run_btn:
    with st.spinner('กำลังประมวลผลข้อมูล...'):
        all_tickers = list(set(
            [a['ticker'] for a in st.session_state.strategy_a if a['ticker']] + 
            [b['ticker'] for b in st.session_state.strategy_b if b['ticker']]
        ))
        
        if not all_tickers:
            st.error("กรุณาระบุ Ticker อย่างน้อยหนึ่งตัว")
        else:
            data = fetch_data(all_tickers, start_date)
            
            if not data.empty:
                # Calculate Portfolio A
                val_a, invest_a, ret_a = calculate_portfolio_dca(data, st.session_state.strategy_a, initial_cap, monthly_dca)
                met_a = calculate_metrics(val_a, invest_a, ret_a)
                
                # Calculate Portfolio B
                val_b, invest_b, ret_b = calculate_portfolio_dca(data, st.session_state.strategy_b, initial_cap, monthly_dca)
                met_b = calculate_metrics(val_b, invest_b, ret_b)
                
                # --- 1. Dashboard Metrics ---
                st.subheader(f"📊 Performance Overview ({met_a['years']:.1f} Years) (Rebalance every 6m)")
                
                col_a, col_b = st.columns(2)
                
                def display_strategy_metrics(label, met, assets):
                    with st.container(border=True):
                        asset_desc = " + ".join([f"{a['ticker']}({a['weight']}%)" for a in assets if a['ticker']])
                        st.markdown(f"#### {label}")
                        st.caption(asset_desc)
                        
                        m1, m2 = st.columns(2)
                        m1.metric("Final Value", f"{met['final_value']:,.0f}")
                        m2.metric("Total Invested", f"{met['total_invested']:,.0f}")
                        
                        m3, m4 = st.columns(2)
                        m3.metric("Total Return", f"{met['total_return']*100:.2f}%")
                        m4.metric("CAGR (%)", f"{met['cagr']*100:.2f}%")
                        
                        m5, m6 = st.columns(2)
                        m5.metric("Volatility", f"{met['volatility']*100:.2f}%")
                        m6.metric("Max Drawdown", f"{met['max_drawdown']*100:.2f}%")

                if met_a:
                    with col_a:
                        display_strategy_metrics("🛡️ Strategy A", met_a, st.session_state.strategy_a)

                if met_b:
                    with col_b:
                        display_strategy_metrics("🎯 Strategy B", met_b, st.session_state.strategy_b)
                
                st.markdown("<br>", unsafe_allow_html=True)

                # --- 2. Chart Display ---
                df_plot = pd.DataFrame({
                    'Strategy A': val_a,
                    'Strategy B': val_b
                })
                fig = px.line(df_plot, title=f"Total Wealth Growth Comparison ({period_choice})")
                fig.update_layout(
                    hovermode="x unified", 
                    yaxis_title="Portfolio Value",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # --- 3. Expander (Bottom) ---
                with st.expander("📂 View Raw Data & Details"):
                    st.dataframe(df_plot.style.format("{:,.2f}"), use_container_width=True)
                    st.info(f"Analysis start from {val_a.index[0].date()} to {val_a.index[-1].date()}")
            else:
                st.error("ไม่พบข้อมูลสำหรับ Tickers หรือช่วงเวลาที่ระบุ")
else:
    if can_run:
        st.info("👈 กด 'Run Comparison' ใน Sidebar เพื่อเริ่มวิเคราะห์")

