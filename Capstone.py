import streamlit as st
import uuid
import datetime
import os
import pandas as pd
import plotly.graph_objects as go
from risk_logic import TradeInput, RiskAssessor, AssessmentResult

# --- OPTION A: Global In-Memory Log (Shared across all users) ---
# To switch to Option B, simply delete this function and use a database call instead.
@st.cache_resource
def get_global_logs():
    return []

global_logs = get_global_logs()

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

# --- Sidebar for Account Settings ---
with st.sidebar:
    st.header("Account Settings")
    capital = st.number_input("Account Capital ($)", min_value=100.0, value=10000.0, step=100.0)
    leverage = st.slider("Leverage (x)", min_value=1.0, max_value=50.0, value=1.0, step=0.1)

# Tabs
tab_eval, tab_history = st.tabs(["Trade Evaluation", "Session History"])

with tab_eval:
    # --- Main Input Form ---
    st.subheader("Proposed Trade Details")
    
    col1, col2 = st.columns(2)
    with col1:
        entry_price = st.number_input("Entry Price", min_value=0.01, value=100.0)
        stop_loss = st.number_input("Stop Loss Price", min_value=0.01, value=98.0)
    
    with col2:
        take_profit = st.number_input("Take Profit Price", min_value=0.01, value=105.0)
        position_size = st.number_input("Position Size (Units)", min_value=0.01, value=1.0)
    
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
    
    total_risk = risk_per_unit * position_size
    risk_pct = (total_risk / capital) * 100 if capital > 0 else 0
    rr_ratio = reward_per_unit / risk_per_unit if risk_per_unit > 0 else 0
    
    metric_col1, metric_col2 = st.columns(2)
    with metric_col1:
        st.metric("Live Risk %", f"{risk_pct:.2f}%")
    with metric_col2:
        st.metric("Risk:Reward Ratio", f"1 : {rr_ratio:.2f}")

    # --- Privacy Logic: Anonymous Session ID ---
    if 'session_id' not in st.session_state:
        # Create a unique ID for this user session when they first load the page
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
        else:
            st.error(f"### ❌ Trade Rejected (High Risk)")
            st.write(f"**Reason:** {result.message}")
            st.metric("Risk Level", result.risk_level, delta="-Rejected", delta_color="inverse")
            if result.failed_rule:
                st.warning(f"⚠️ **Greedy Algorithm Filter:** Stopped at '{result.failed_rule}'")

        # Visual Analytics (Plotly)
        if risk_per_unit > 0: # Sanity check for plotting
            fig = go.Figure()
            
            # Profit zone
            fig.add_shape(
                type="rect",
                x0=0, x1=1,
                y0=entry_price, y1=take_profit,
                fillcolor="rgba(39, 174, 96, 0.3)", # Greenish
                line_width=0,
                layer="below"
            )
            
            # Risk zone
            fig.add_shape(
                type="rect",
                x0=0, x1=1,
                y0=stop_loss, y1=entry_price,
                fillcolor="rgba(231, 76, 60, 0.3)", # Reddish
                line_width=0,
                layer="below"
            )
            
            # Entry Line
            fig.add_trace(go.Scatter(
                x=[0, 1], y=[entry_price, entry_price],
                mode="lines", name="Entry",
                line=dict(color="#2c3e50", width=3, dash="dash")
            ))
            
            # Stop Loss Line
            fig.add_trace(go.Scatter(
                x=[0, 1], y=[stop_loss, stop_loss],
                mode="lines", name="Stop Loss",
                line=dict(color="#c0392b", width=3)
            ))
            
            # Take Profit Line
            fig.add_trace(go.Scatter(
                x=[0, 1], y=[take_profit, take_profit],
                mode="lines", name="Take Profit",
                line=dict(color="#27ae60", width=3)
            ))
            
            fig.update_layout(
                title=dict(text="Trade Setup Visualization", x=0.5),
                xaxis=dict(visible=False, showticklabels=False),
                yaxis_title="Price Area",
                showlegend=False,
                margin=dict(l=20, r=20, t=40, b=20),
                height=300
            )
            st.plotly_chart(fig, use_container_width=True)

        # E. Privacy-Preserving Logging
        # --- OPTION A: Appending to Global In-Memory List ---
        # Note: Replace this section with Option B (Database Insert) later
        log_entry = {
            "Timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "Session_ID": st.session_state['session_id'][:8] + "-****-****",
            "Risk_Level": result.risk_level,
            "Decision": 'Accepted' if result.is_safe else 'Rejected'
        }
        
        global_logs.insert(0, log_entry) # Put newest at the top
        # Keep only the last 100 to prevent memory leaks
        if len(global_logs) > 100:
            global_logs.pop()
        # ----------------------------------------------------
            
        st.caption(f"🔒 Analysis queued in live memory (Session: {st.session_state['session_id'][:8]}...)")

with tab_history:
    st.subheader("📚 Live Session History (Orderbook Style)")
    st.markdown("100% anonymized live tape. This data runs in-memory and will clear when the Streamlit server restarts.")
    
    # --- OPTION A: In-Memory Display ---
    # Note: Replace this block with Option B (Database Fetch) later
    if len(global_logs) > 0:
        df = pd.DataFrame(global_logs)
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # System Analytics
        st.markdown("### 📊 Live Analytics")
        stat_col1, stat_col2 = st.columns(2)
        with stat_col1:
            st.metric("Live Evaluations", len(df))
        with stat_col2:
            accepted_count = len(df[df['Decision'] == 'Accepted'])
            accepted_rate = (accepted_count / len(df)) * 100 if len(df) > 0 else 0
            st.metric("Live Acceptance Rate", f"{accepted_rate:.1f}%")
    else:
        st.info("No active sessions in memory right now. Run a check to start the tape!")

# --- Educational Footer ---
st.markdown("---")
with st.expander("🎓 How does the Greedy Algorithm work here?"):
    st.markdown("""
    1.  **Priority Queue:** Rules are sorted by importance.
        *   Priority 1: Don't blow up the account (Max Risk %).
        *   Priority 2: Don't use insane leverage.
        *   Priority 3: Is it profitable? (R:R Ratio).
    2.  **No Backtracking:** If Rule 1 fails, the algorithm **stops**. It doesn't care if the trade has a 1000% potential profit.
    3.  **Local Optimality:** At each step, it makes the safest choice immediately. This guarantees a "safe" set of trades without needing complex simulations.
    """)
