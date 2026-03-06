from risk_logic import RiskAssessor, TradeInput

print("--- DEBUG START ---")
assessor = RiskAssessor()
safe_input = TradeInput(
    capital=10000, 
    position_size=1, 
    entry_price=100, 
    stop_loss=98,
    take_profit=105,
    leverage=1
)
result = assessor.evaluate_trade(safe_input)
print(f"Result Safe: {result.is_safe}")
print(f"Result Msg: {result.message}")
print(f"Result Rule: {result.failed_rule}")
print("--- DEBUG END ---")
