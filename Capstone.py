import streamlit as st
import uuid
import datetime
import os
from risk_logic import TradeInput, RiskAssessor, AssessmentResult

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

# --- Main Input Form ---
st.subheader("Proposed Trade Details")

col1, col2 = st.columns(2)
with col1:
    entry_price = st.number_input("Entry Price", min_value=0.01, value=100.0)
    stop_loss = st.number_input("Stop Loss Price", min_value=0.01, value=98.0)

with col2:
    take_profit = st.number_input("Take Profit Price", min_value=0.01, value=105.0)
    position_size = st.number_input("Position Size (Units)", min_value=0.01, value=1.0)

# --- Privacy Logic: Anonymous Session ID ---
if 'session_id' not in st.session_state:
    # Create a unique ID for this user session when they first load the page
    st.session_state['session_id'] = str(uuid.uuid4())

st.divider()

# ==========================================
# PART 4: The Interaction Loop
# ==========================================

if st.button("Assess Risk (Greedy Check)", type="primary"):
    
    # A. Instantiate the Logic
    # We create the "Brain"
    assessor = RiskAssessor()
    
    # B. Package the Inputs
    # We put user data into our DTO (Data Transfer Object)
    trade_input = TradeInput(
        capital=capital,
        position_size=position_size,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        leverage=leverage
    )
    
    # C. Run the Algorithm
    # The "Brain" does the work. result is an AssessmentResult object.
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

    # E. Privacy-Preserving Logging
    # Requirement: Log ONLY Session ID, Time, and Risk Level. NO INPUT DATA.
    log_file = "session_logs.csv"
    timestamp = datetime.datetime.now().isoformat()
    
    log_entry = f"{timestamp},{st.session_state['session_id']},{result.risk_level},{'Accepted' if result.is_safe else 'Rejected'}\n"
    
    # Check if file exists to write header
    file_exists = os.path.isfile(log_file)
    
    with open(log_file, "a") as f:
        if not file_exists:
            f.write("Timestamp,Session_ID,Risk_Level,Decision\n") # Header
        f.write(log_entry)
        
    st.caption(f"🔒 Analysis logged anonymously (Session: {st.session_state['session_id'][:8]}...)")

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
