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
    position_size: float    # Dollar amount invested (e.g., $100 USD)
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
    - If a critical rule fails, we IMMEDIATELY reject the trade.
    - We do NOT "backtrack" or check if the trade is otherwise amazing.
    - A single fatal flaw makes the entire trade invalid.
    
    This is O(1) complexity because we have a fixed number of rules.
    It is extremely efficient compared to "scoring" every possible factor.
    """
    
    # --- Configuration Constants (The Rules) ---
    MAX_EXPOSURE = 1.0           # Rule 1: Effective exposure must be < 1:1 with capital
    MAX_LEVERAGE = 20.0          # Rule 2: Max 20x leverage
    MIN_RISK_REWARD = 1.5        # Rule 3: Must earn at least $1.50 for every $1 risked

    def evaluate_trade(self, trade: TradeInput) -> AssessmentResult:
        """
        The main Greedy Function.
        
        It behaves like a rigid gatekeeper. It checks gates one by one.
        If any gate is closed, it turns you away instantly.
        """
        
        # 1. Preliminary Calculations (The Math)
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

        # Effective Exposure = (Position Size * Leverage) / Capital
        # This shows how much of your account is at risk after leverage amplification.
        # Example: $100 position * 10x leverage = $1000 effective exposure on a $500 account = 2.0x (DANGEROUS)
        effective_exposure = (trade.position_size * trade.leverage) / trade.capital

        # Risk : Reward Ratio (based on price levels, independent of position size)
        rr_ratio = reward_per_unit / risk_per_unit if risk_per_unit > 0 else 0

        # =========================================================
        # THE GREEDY EVALUATION LOOP
        # Priority Order: Safety (Survival) > Profitability (Growth)
        # =========================================================

        # --- Rule 1: Position Exposure (Most Critical) ---
        # "Is the effective position (after leverage) >= your entire account?"
        # Higher leverage = higher exposure = more danger.
        if effective_exposure >= self.MAX_EXPOSURE:
            return AssessmentResult(
                is_safe=False,
                risk_level="High",
                message=f"Rule 1 Failed: Effective exposure {effective_exposure:.2f}x is at or above 1:1 with capital.",
                failed_rule="Position Exposure (1:1 Rule)"
            )

        # --- Rule 2: Leverage Constraints ---
        # "Is the leverage incredibly dangerous?"
        if trade.leverage > self.MAX_LEVERAGE:
            return AssessmentResult(
                is_safe=False,
                risk_level="High",
                message=f"Rule 2 Failed: Leverage {trade.leverage}x exceeds max {self.MAX_LEVERAGE}x.",
                failed_rule="Maximum Leverage"
            )

        # --- Rule 3: Risk/Reward Efficiency ---
        # "Is this trade worth the trouble?"
        if rr_ratio < self.MIN_RISK_REWARD:
            return AssessmentResult(
                is_safe=False,
                risk_level="Medium",
                message=f"Rule 3 Failed: R:R {rr_ratio:.2f} is below min {self.MIN_RISK_REWARD}.",
                failed_rule="Risk/Reward Ratio"
            )

        # If we survived all the "Rejection Gates", the trade is Accepted.
        return AssessmentResult(
            is_safe=True,
            risk_level="Low",
            message=f"APPROVED: Exposure {effective_exposure:.2f}x | R:R {rr_ratio:.2f}",
            failed_rule=None
        )

# ==========================================
# Self-Test Section
# ==========================================
if __name__ == "__main__":
    print("Running Self-Test on risk_logic.py...")
    
    assessor = RiskAssessor()
    
    # Test Case 1: Safe Trade ($100 on $10,000 account, 1x leverage)
    safe_input = TradeInput(
        capital=10000, 
        position_size=100,     # $100 USD position
        entry_price=100, 
        stop_loss=98,
        take_profit=105,
        leverage=1
    )
    result = assessor.evaluate_trade(safe_input)
    print(f"Test 1 (Safe):          {result.message} -> Passed? {result.is_safe}")

    # Test Case 2: Dangerous Trade ($500 on $500 account = 1:1 ratio)
    danger_input = TradeInput(
        capital=500,
        position_size=500,     # $500 USD = entire account
        entry_price=71711.20, 
        stop_loss=72866.10,
        take_profit=67503.00,
        leverage=1
    )
    result2 = assessor.evaluate_trade(danger_input)
    print(f"Test 2 (1:1 Exposure):  {result2.message} -> Passed? {result2.is_safe}")

    # Test Case 3: Leverage makes it dangerous ($100 on $500 with 10x leverage = 2.0x exposure)
    leveraged_input = TradeInput(
        capital=500,
        position_size=100,     # Only $100, but...
        entry_price=71711.20,
        stop_loss=72866.10,
        take_profit=67503.00,
        leverage=10             # 10x makes it $1000 effective = 2.0x exposure!
    )
    result3 = assessor.evaluate_trade(leveraged_input)
    print(f"Test 3 (Leverage Risk): {result3.message} -> Passed? {result3.is_safe}")

    # Test Case 4: Leverage keeps it safe ($100 on $500 with 2x leverage = 0.4x exposure)
    safe_lev_input = TradeInput(
        capital=500,
        position_size=100,     # $100 with 2x = $200 effective
        entry_price=71711.20,
        stop_loss=72866.10,
        take_profit=67503.00,
        leverage=2
    )
    result4 = assessor.evaluate_trade(safe_lev_input)
    print(f"Test 4 (Lev Safe):      {result4.message} -> Passed? {result4.is_safe}")
