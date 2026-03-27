import streamlit as st
import uuid
import datetime
import os
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client
from risk_logic import TradeInput, RiskAssessor, AssessmentResult

# --- OPTION B: Supabase Cloud Database (Permanent Storage) ---
@st.cache_resource
def init_supabase():
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = init_supabase()

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
    # Higher leverage = higher exposure = more danger
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
        # --- OPTION B: Supabase Cloud Database Insert ---
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
    
    # --- OPTION B: Supabase Cloud Database Fetch ---
    try:
        response = supabase.table("session_logs").select("created_at, session_id, risk_level, decision").order("created_at", desc=True).limit(100).execute()
        
        if response.data and len(response.data) > 0:
            df = pd.DataFrame(response.data)
            
            # Format timestamp for display
            if 'created_at' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S')
                df = df.rename(columns={'created_at': 'Timestamp', 'session_id': 'Session_ID', 'risk_level': 'Risk_Level', 'decision': 'Decision'})
            
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # System Analytics
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
