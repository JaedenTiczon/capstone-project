from dataclasses import dataclass
from typing import Optional, List, Tuple
from datetime import datetime

# ==========================================
# PART 1: Data Structures (The "Input")
# ==========================================

@dataclass
class TradeInput:
    """
    A simple container for all the numbers a trader enters.
    
    CS Concept: Data Transfer Object (DTO)
    We use a Class (specifically a dataclass) to group related data together.
    This avoids passing 6 different arguments to every function.
    """
    capital: float          # Total account balance (e.g., $10,000)
    position_size: float    # Number of units/contracts (e.g., 1.5 BTC)
    entry_price: float      # Price we buy/sell at
    stop_loss: float       # Price where we exit if wrong
    take_profit: float     # Price where we exit if right
    leverage: float = 1.0  # Optional leverage (default 1x)

@dataclass
class AssessmentResult:
    """
    The output of our calculation.
    """
    is_safe: bool          # Final decision: Accepted (True) or Rejected (False)
    risk_level: str        # "Low", "Medium", "High"
    message: str           # Explanation for the user (e.g., "Risk is too high!")
    failed_rule: Optional[str] = None # Which rule caused the rejection?

# ==========================================
# PART 2: The Algorithm (The "Brain")
# ==========================================

class RiskAssessor:
    """
    The core decision-making engine.
    
    ALGORITHMIC APPROACH: GREEDY ALGORITHM
    
    Why Greedy?
    A Greedy Algorithm builds a solution piece by piece, always choosing the next piece
    that offers the most immediate benefit (or in our case, immediate safety).
    
    Our "Greedy Choice Property":
    - We evaluate rules in order of CRITICALITY (Priority).
    - If a critical rule fails (e.g., Risk > 2%), we IMMEDIATELY reject the trade.
    - We do NOT "backtrack" or check if the trade is otherwise amazing.
    - A single fatal flaw makes the entire trade invalid.
    
    This is O(1) complexity because we have a fixed number of rules.
    It is extremely efficient compared to "scoring" every possible factor.
    """
    
    # --- Configuration Constants (The Rules) ---
    MAX_RISK_PERCENT = 1.00      # Rule 1: Max 100% risk of total capital (1:1 Ratio)
    MAX_DRAWDOWN_PERCENT = 0.05  # Rule 2: Max 5% drawdown (for this trade's impact)
    MIN_RISK_REWARD = 1.5        # Rule 3: Must earn at least $1.50 for every $1 risked
    MAX_LEVERAGE = 20.0          # Rule 4: Max 20x leverage

    def evaluate_trade(self, trade: TradeInput) -> AssessmentResult:
        """
        The main Greedy Function.
        
        It behaves like a rigid gatekeeper. It checks gates one by one.
        If any gate is closed, it turns you away instantly.
        """
        
        # 1. Preliminary Calculations (The Math)
        # We need to know the basic numbers before we can apply rules.
        is_long = trade.take_profit > trade.entry_price
        
        if is_long:
            risk_per_unit = trade.entry_price - trade.stop_loss
            reward_per_unit = trade.take_profit - trade.entry_price
        else: # Short trade
            risk_per_unit = trade.stop_loss - trade.entry_price
            reward_per_unit = trade.entry_price - trade.take_profit

        # Sanity Check: If inputs makes no sense (e.g. Stop Loss is WRONG side)
        if risk_per_unit <= 0:
            return AssessmentResult(False, "Error", "Invalid Stop Loss: It must be below entry for Longs, above for Shorts.", "Sanity Check")

        # Total money at risk = (Risk per unit * Size)
        # Note: In specialized trading (FX), this formula might be more complex, 
        # but for this CS project, we stick to the standard linear formula.
        total_risk_amount = risk_per_unit * trade.position_size
        
        # Risk as a percentage of account = (Total Risk / Capital)
        risk_percent = total_risk_amount / trade.capital

        # Risk : Reward Ratio
        rr_ratio = reward_per_unit / risk_per_unit if risk_per_unit > 0 else 0

        # Drawdown Impact (Simplified logic for linear assets)
        potential_drawdown = risk_percent  # In this simplified model, risk % IS the potential drawdown impact

        # =========================================================
        # THE GREEDY EVALUATION LOOP
        # Priority Order: Safety (Survival) > Profitability (Growth)
        # =========================================================

        # --- Rule 1: Capital Preservation (Most Critical) ---
        # "Can this trade blow up my account?"
        if risk_percent > self.MAX_RISK_PERCENT:
            # GREEDY ACTION: Reject immediately. Do not pass Go.
            return AssessmentResult(
                is_safe=False,
                risk_level="High",
                message=f"Rule 1 Failed: Risk {risk_percent:.2%} exceeds max {self.MAX_RISK_PERCENT:.2%}.",
                failed_rule="Maximum Risk %"
            )

        # --- Rule 2: Leverage Constraints ---
        # "Is the leverage incredibly dangerous?"
        if trade.leverage > self.MAX_LEVERAGE:
            # GREEDY ACTION: Reject.
            return AssessmentResult(
                is_safe=False,
                risk_level="High",
                message=f"Rule 2 Failed: Leverage {trade.leverage}x exceeds max {self.MAX_LEVERAGE}x.",
                failed_rule="Maximum Leverage"
            )

        # --- Rule 3: Risk/Reward Efficiency ---
        # "Is this trade worth the trouble?"
        if rr_ratio < self.MIN_RISK_REWARD:
            # GREEDY ACTION: Reject. 
            # Note: A trade can be "safe" (low risk) but "bad" (low reward). 
            # Our algorithm rejects it anyway because it's suboptimal.
            return AssessmentResult(
                is_safe=False,
                risk_level="Medium",
                message=f"Rule 3 Failed: R:R {rr_ratio:.2f} is below min {self.MIN_RISK_REWARD}.",
                failed_rule="Risk/Reward Ratio"
            )

        #If we survived all the "Rejection Gates", the trade is Accepted.
        return AssessmentResult(
            is_safe=True,
            risk_level="Low",
            message=f"APPROVED: Risk {risk_percent:.2%} | R:R {rr_ratio:.2f}",
            failed_rule=None
        )

# ==========================================
# Self-Test Section
# ==========================================
if __name__ == "__main__":
    # This block allows us to test the Logic without running the UI.
    # It will run only if we execute "python risk_logic.py" directly.
    
    print("Running Self-Test on risk_logic.py...")
    
    # Test Case 1: Convert a Safe Trade
    assessor = RiskAssessor()
    safe_input = TradeInput(
        capital=10000, 
        position_size=1, 
        entry_price=100, 
        stop_loss=98,   # Risk $2 * 1 = $2 (0.02% risk) -> Very safe
        take_profit=105, # Reward $5 -> R:R 2.5
        leverage=1
    )
    result = assessor.evaluate_trade(safe_input)
    print(f"Test 1 (Safe): {result.message} -> Passed? {result.is_safe}")

    # Test Case 2: Dangerous Trade (Risk > 2%)
    danger_input = TradeInput(
        capital=1000,      # Small account
        position_size=10, 
        entry_price=100, 
        stop_loss=90,      # Risk $10 * 10 = $100 (10% risk!)
        take_profit=200,   # Massive reward, but risk is too high
        leverage=1
    )
    result2 = assessor.evaluate_trade(danger_input)
    print(f"Test 2 (High Risk): {result2.message} -> Passed? {result2.is_safe}")
