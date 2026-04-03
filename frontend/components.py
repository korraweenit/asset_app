import streamlit as st

def add_asset(strategy_key):
    st.session_state[strategy_key].append({'ticker': '', 'weight': 0})

def remove_asset(strategy_key, index):
    if len(st.session_state[strategy_key]) > 1:
        st.session_state[strategy_key].pop(index)

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
