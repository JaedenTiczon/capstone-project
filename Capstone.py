import streamlit as st
import uuid
import datetime
import os
import pandas as pd
import plotly.graph_objects as go
import requests
from supabase import create_client
from risk_logic import TradeInput, RiskAssessor, AssessmentResult

# --- OPTION B: Supabase Cloud Database (Permanent Storage) ---
@st.cache_resource
def init_supabase():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_supabase()

# --- Live Market Data (Cached for 60 seconds to avoid API spam) ---
@st.cache_data(ttl=60)
def fetch_live_prices():
    """Fetch live prices from CoinGecko (crypto) and ExchangeRate API (forex)."""
    prices = {}
    
    # Crypto: BTC & ETH from CoinGecko (free, no API key)
    try:
        crypto_url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd&include_24hr_change=true"
        r = requests.get(crypto_url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            prices["BTC"] = {"price": data["bitcoin"]["usd"], "change": data["bitcoin"].get("usd_24h_change", 0)}
            prices["ETH"] = {"price": data["ethereum"]["usd"], "change": data["ethereum"].get("usd_24h_change", 0)}
    except:
        pass
    
    # Forex: EUR/USD from ExchangeRate API (free, no API key)
    try:
        forex_url = "https://open.er-api.com/v6/latest/EUR"
        r = requests.get(forex_url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            prices["EUR/USD"] = {"price": data["rates"].get("USD", 0), "change": None}
    except:
        pass
    
    return prices

# ==========================================
# PART 3: The User Interface (The "Face")
# ==========================================

# 1. Page Configuration (Title, Icon)
st.set_page_config(
    page_title="Greedy Algo Risk Assessor",
    page_icon="🛡️",
    layout="centered"
)

# 2. Main Title & Description
st.title("🛡️ Trading Risk Evaluator")
st.markdown("""
**CS Project: Greedy Algorithm Implementation**
This tool uses a deterministic **Greedy Algorithm** to assess trade risk in real-time.
It evaluates critical rules first (Risk %, Drawdown) and rejects unsafe trades immediately.
""")

# --- Sidebar ---
with st.sidebar:
    st.header("Account Settings")
    capital = st.number_input("Account Capital ($)", min_value=100.0, value=10000.0, step=100.0)
    leverage = st.slider("Leverage (x)", min_value=1.0, max_value=50.0, value=1.0, step=0.1)
    
    # --- Risk Rules Explained ---
    st.divider()
    st.header("📋 Risk Rules")
    st.markdown("""
    The Greedy Algorithm checks **3 rules in order**.  
    If any rule fails, the trade is **immediately rejected**.
    
    **Rule 1: Position Exposure**  
    ❌ Rejected if `(Position × Leverage) / Capital ≥ 1.0`  
    *Your effective position must be less than your account.*
    
    **Rule 2: Leverage Cap**  
    ❌ Rejected if `Leverage > 20x`  
    *Excessive leverage amplifies losses beyond recovery.*
    
    **Rule 3: Risk/Reward Ratio**  
    ❌ Rejected if `R:R < 1.5`  
    *You must earn at least $1.50 for every $1 risked.*
    """)
    
    # --- Quick Links ---
    st.divider()
    st.header("🔗 Trader Tools")
    st.markdown("""
    - [📊 TradingView](https://www.tradingview.com)
    - [⚡ Velo.xyz](https://velo.xyz)
    - [📅 Forex Factory](https://www.forexfactory.com)
    - [📰 CoinDesk News](https://www.coindesk.com)
    - [🏦 Investing.com Calendar](https://www.investing.com/economic-calendar/)
    - [📈 CoinGecko](https://www.coingecko.com)
    """)

# Tabs
tab_eval, tab_history, tab_market = st.tabs(["Trade Evaluation", "Session History", "Market Data"])

with tab_eval:
    # --- Main Input Form ---
    st.subheader("Proposed Trade Details")
    
    col1, col2 = st.columns(2)
    with col1:
        entry_price = st.number_input("Entry Price", min_value=0.01, value=100.0)
        stop_loss = st.number_input("Stop Loss Price", min_value=0.01, value=98.0)
    
    with col2:
        take_profit = st.number_input("Take Profit Price", min_value=0.01, value=105.0)
        position_size = st.number_input("Position Size ($)", min_value=0.01, value=100.0, step=10.0)
    
    # --- Dynamic Pre-calculations ---
    st.markdown("---")
    st.subheader("Live Trade Setup")
    
    is_long = take_profit > entry_price
    if is_long:
        risk_per_unit = entry_price - stop_loss
        reward_per_unit = take_profit - entry_price
    else:
        risk_per_unit = stop_loss - entry_price
        reward_per_unit = entry_price - take_profit
    
    # Effective Exposure = (Position Size * Leverage) / Capital
    effective_exposure = (position_size * leverage) / capital if capital > 0 else 0
    rr_ratio = reward_per_unit / risk_per_unit if risk_per_unit > 0 else 0
    
    metric_col1, metric_col2 = st.columns(2)
    with metric_col1:
        exposure_label = f"{effective_exposure:.2f}x"
        st.metric("Exposure Ratio", exposure_label, delta="Safe" if effective_exposure < 1.0 else "⚠️ Over 1:1!", delta_color="normal" if effective_exposure < 1.0 else "inverse")
    with metric_col2:
        st.metric("Risk:Reward Ratio", f"1 : {rr_ratio:.2f}")

    # --- Privacy Logic: Anonymous Session ID ---
    if 'session_id' not in st.session_state:
        st.session_state['session_id'] = str(uuid.uuid4())
    
    st.divider()
    
    # ==========================================
    # PART 4: The Interaction Loop
    # ==========================================
    
    if st.button("Assess Risk (Greedy Check)", type="primary", use_container_width=True):
        
        # A. Instantiate the Logic
        assessor = RiskAssessor()
        
        # B. Package the Inputs
        trade_input = TradeInput(
            capital=capital,
            position_size=position_size,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            leverage=leverage
        )
        
        # C. Run the Algorithm
        result = assessor.evaluate_trade(trade_input)
        
        # D. Display Result (Visual Feedback)
        if result.is_safe:
            st.success(f"### ✅ Trade Accepted (Safe)")
            st.write(f"**Reason:** {result.message}")
            st.metric("Risk Level", "Low", delta="Approved")
            
            # Show all rules passed
            st.info("**All 3 rules passed:**\n"
                     "1. ✅ Position Exposure < 1:1\n"
                     "2. ✅ Leverage ≤ 20x\n"
                     "3. ✅ Risk/Reward ≥ 1.5")
        else:
            st.error(f"### ❌ Trade Rejected (High Risk)")
            st.write(f"**Reason:** {result.message}")
            st.metric("Risk Level", result.risk_level, delta="-Rejected", delta_color="inverse")
            
            # Show exactly which rule was triggered with a detailed breakdown
            if result.failed_rule:
                st.warning(f"⚠️ **Greedy Algorithm stopped at:** `{result.failed_rule}`")
                
                # Detailed rule-by-rule breakdown
                rules_status = []
                if "Exposure" in result.failed_rule:
                    rules_status.append(f"1. ❌ **Position Exposure** → {effective_exposure:.2f}x (must be < 1.0x)")
                    rules_status.append("2. ⏭️ Leverage — *skipped (Rule 1 already failed)*")
                    rules_status.append("3. ⏭️ Risk/Reward — *skipped (Rule 1 already failed)*")
                elif "Leverage" in result.failed_rule:
                    rules_status.append("1. ✅ Position Exposure — passed")
                    rules_status.append(f"2. ❌ **Leverage** → {leverage}x (must be ≤ 20x)")
                    rules_status.append("3. ⏭️ Risk/Reward — *skipped (Rule 2 already failed)*")
                elif "Risk/Reward" in result.failed_rule:
                    rules_status.append("1. ✅ Position Exposure — passed")
                    rules_status.append("2. ✅ Leverage — passed")
                    rules_status.append(f"3. ❌ **Risk/Reward** → 1:{rr_ratio:.2f} (must be ≥ 1:1.5)")
                
                st.markdown("**Rule-by-Rule Breakdown (Greedy Order):**")
                for line in rules_status:
                    st.markdown(line)

        # Visual Analytics (Plotly)
        if risk_per_unit > 0:
            fig = go.Figure()
            
            fig.add_shape(type="rect", x0=0, x1=1,
                y0=entry_price, y1=take_profit,
                fillcolor="rgba(39, 174, 96, 0.3)", line_width=0, layer="below")
            
            fig.add_shape(type="rect", x0=0, x1=1,
                y0=stop_loss, y1=entry_price,
                fillcolor="rgba(231, 76, 60, 0.3)", line_width=0, layer="below")
            
            fig.add_trace(go.Scatter(x=[0, 1], y=[entry_price, entry_price],
                mode="lines", name="Entry", line=dict(color="#2c3e50", width=3, dash="dash")))
            fig.add_trace(go.Scatter(x=[0, 1], y=[stop_loss, stop_loss],
                mode="lines", name="Stop Loss", line=dict(color="#c0392b", width=3)))
            fig.add_trace(go.Scatter(x=[0, 1], y=[take_profit, take_profit],
                mode="lines", name="Take Profit", line=dict(color="#27ae60", width=3)))
            
            fig.update_layout(
                title=dict(text="Trade Setup Visualization", x=0.5),
                xaxis=dict(visible=False, showticklabels=False),
                yaxis_title="Price Area", showlegend=False,
                margin=dict(l=20, r=20, t=40, b=20), height=300
            )
            st.plotly_chart(fig, use_container_width=True)

        # E. Privacy-Preserving Logging
        try:
            supabase.table("session_logs").insert({
                "session_id": st.session_state['session_id'][:8] + "-****-****",
                "risk_level": result.risk_level,
                "decision": 'Accepted' if result.is_safe else 'Rejected'
            }).execute()
            st.caption(f"🔒 Analysis logged permanently (Session: {st.session_state['session_id'][:8]}...)")
        except Exception as e:
            st.caption(f"⚠️ Log failed to save: {e}")

with tab_history:
    st.subheader("📚 Permanent Session History")
    st.markdown("100% anonymized logs stored permanently in a cloud database. Data persists across server restarts.")
    
    try:
        response = supabase.table("session_logs").select("created_at, session_id, risk_level, decision").order("created_at", desc=True).limit(100).execute()
        
        if response.data and len(response.data) > 0:
            df = pd.DataFrame(response.data)
            
            if 'created_at' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
                df = df.rename(columns={'created_at': 'Timestamp', 'session_id': 'Session_ID', 'risk_level': 'Risk_Level', 'decision': 'Decision'})
            
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            st.markdown("### 📊 Global Analytics")
            stat_col1, stat_col2 = st.columns(2)
            with stat_col1:
                st.metric("Total Evaluations", len(df))
            with stat_col2:
                accepted_count = len(df[df['Decision'] == 'Accepted'])
                accepted_rate = (accepted_count / len(df)) * 100 if len(df) > 0 else 0
                st.metric("Acceptance Rate", f"{accepted_rate:.1f}%")
        else:
            st.info("No session logs recorded yet. Run a check to start logging!")
    except Exception as e:
        st.error(f"Could not load session history: {e}")

with tab_market:
    st.subheader("📡 Live Market Data")
    st.caption("Prices refresh every 60 seconds. Data from CoinGecko & Open ExchangeRate.")
    
    prices = fetch_live_prices()
    
    if prices:
        p_col1, p_col2, p_col3 = st.columns(3)
        
        if "BTC" in prices:
            with p_col1:
                btc = prices["BTC"]
                change_str = f"{btc['change']:.2f}%" if btc['change'] else "N/A"
                st.metric("₿ BTC/USD", f"${btc['price']:,.2f}", delta=change_str)
        
        if "ETH" in prices:
            with p_col2:
                eth = prices["ETH"]
                change_str = f"{eth['change']:.2f}%" if eth['change'] else "N/A"
                st.metric("Ξ ETH/USD", f"${eth['price']:,.2f}", delta=change_str)
        
        if "EUR/USD" in prices:
            with p_col3:
                eur = prices["EUR/USD"]
                st.metric("💱 EUR/USD", f"{eur['price']:.4f}", delta="Live Rate")
    else:
        st.warning("Could not fetch live prices. API may be rate-limited. Try again in a minute.")
    
    # --- Economic Calendar / News Alerts ---
    st.markdown("---")
    st.subheader("📅 Economic Calendar & News")
    st.markdown("""
    **Major events that move markets:**  
    Stay updated on FOMC, CPI, NFP, and other high-impact events.  
    Click below to view live economic calendars:
    """)
    
    news_col1, news_col2 = st.columns(2)
    with news_col1:
        st.link_button("📅 Forex Factory Calendar", "https://www.forexfactory.com/calendar", use_container_width=True)
        st.link_button("📰 CoinDesk Crypto News", "https://www.coindesk.com", use_container_width=True)
    with news_col2:
        st.link_button("🏦 Investing.com Calendar", "https://www.investing.com/economic-calendar/", use_container_width=True)
        st.link_button("⚡ Velo.xyz Live Alerts", "https://velo.xyz", use_container_width=True)
    
    st.markdown("---")
    st.markdown("""
    > **💡 Tip:** Always check the economic calendar before placing trades.  
    > Events like **FOMC**, **CPI**, and **NFP** can cause extreme volatility.  
    > If a red-flag event is within 30 minutes, consider waiting before entering.
    """)

# --- Educational Footer ---
st.markdown("---")
with st.expander("🎓 How does the Greedy Algorithm work here?"):
    st.markdown("""
    1.  **Priority Queue:** Rules are sorted by importance.
        *   Priority 1: Don't blow up the account (Position Exposure).
        *   Priority 2: Don't use insane leverage (Max 20x).
        *   Priority 3: Is it profitable? (R:R Ratio ≥ 1.5).
    2.  **No Backtracking:** If Rule 1 fails, the algorithm **stops**. It doesn't care if the trade has a 1000% potential profit.
    3.  **Local Optimality:** At each step, it makes the safest choice immediately. This guarantees a "safe" set of trades without needing complex simulations.
    """)
