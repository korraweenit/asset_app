import pandas as pd
import numpy as np

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
