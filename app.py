import streamlit as st
import pandas as pd
import plotly.express as px
import datetime

# Import backend functions
from backend.data import fetch_data
from backend.calc import calculate_metrics, calculate_portfolio_dca

# Import frontend components
from frontend.components import render_strategy_input, display_strategy_metrics

# ==========================================
# ⚙️ CONFIG & STYLE
# ==========================================
st.set_page_config(page_title="Portfolio Backtest Comparison", layout="wide")

# Load Custom CSS
with open("frontend/style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ==========================================
# 🔄 SESSION STATE MANAGEMENT
# ==========================================
if 'strategy_a' not in st.session_state:
    st.session_state.strategy_a = [{'ticker': 'VOO', 'weight': 80}, {'ticker': 'GLD', 'weight': 20}]
if 'strategy_b' not in st.session_state:
    st.session_state.strategy_b = [{'ticker': 'VOO', 'weight': 100}]

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
