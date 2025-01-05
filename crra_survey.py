import json

def calculate_crra_from_responses(responses):
    """Calculate CRRA based on weighted responses."""
    weights = {
        'loss_aversion': 0.3,
        'wealth_gamble': 0.3,
        'portfolio_choice': 0.2,
        'income_risk': 0.2
    }
    
    crra_indicators = {
        'loss_aversion': responses['loss_threshold'] / 25,  # Scale 0-100% to 0-4
        'wealth_gamble': (100 - responses['risk_percentage']) / 25,  # Inverse scale
        'portfolio_choice': (100 - responses['stock_allocation']) / 20,  # Convert to 1-5 scale
        'income_risk': responses['safe_choice'] / 20  # Scale 0-100 to 0-5
    }
    
    weighted_crra = sum(crra * weights[k] for k, crra in crra_indicators.items())
    
    # Ensure CRRA is between 1 and 10
    return max(1, min(10, weighted_crra))

def ask_questions():
    """Interactive questionnaire to determine CRRA."""
    print("\nCRRA (Coefficient of Relative Risk Aversion) Estimation Questionnaire")
    print("=" * 70)
    print("\nPlease answer the following questions to help determine your risk tolerance.")
    
    responses = {}
    
    # Question 1: Loss Aversion
    print("\nQuestion 1: Loss Threshold")
    print("Imagine you have €100,000 in savings. What is the maximum percentage loss")
    print("you could tolerate in one year before switching to a more conservative investment?")
    while True:
        try:
            loss = float(input("Enter percentage (0-100): "))
            if 0 <= loss <= 100:
                responses['loss_threshold'] = loss
                break
            else:
                print("Please enter a number between 0 and 100")
        except ValueError:
            print("Please enter a valid number")
    
    # Question 2: Wealth Gamble
    print("\nQuestion 2: Risk Assessment")
    print("You are offered a one-time investment opportunity:")
    print("- 50% chance to increase your current wealth by 50%")
    print("- 50% chance to decrease your current wealth by X%")
    print("What is the maximum loss percentage (X) you would accept?")
    while True:
        try:
            risk = float(input("Enter maximum loss percentage (0-100): "))
            if 0 <= risk <= 100:
                responses['risk_percentage'] = risk
                break
            else:
                print("Please enter a number between 0 and 100")
        except ValueError:
            print("Please enter a valid number")
    
    # Question 3: Portfolio Choice
    print("\nQuestion 3: Portfolio Allocation")
    print("In a long-term investment portfolio, what percentage would you ideally")
    print("allocate to risky assets (stocks, commodities) vs safe assets (bonds, cash)?")
    while True:
        try:
            stocks = float(input("Enter percentage for risky assets (0-100): "))
            if 0 <= stocks <= 100:
                responses['stock_allocation'] = stocks
                break
            else:
                print("Please enter a number between 0 and 100")
        except ValueError:
            print("Please enter a valid number")
    
    # Question 4: Income Risk
    print("\nQuestion 4: Income Security")
    print("If offered two job opportunities:")
    print("A) Fixed salary at your current income level")
    print("B) Variable salary averaging 30% higher but with significant variations")
    print("What probability of keeping your job in option B would you require to choose it?")
    while True:
        try:
            safety = float(input("Enter required probability (0-100): "))
            if 0 <= safety <= 100:
                responses['safe_choice'] = safety
                break
            else:
                print("Please enter a number between 0 and 100")
        except ValueError:
            print("Please enter a valid number")
    
    return responses

def interpret_crra(crra):
    """Provide interpretation of CRRA value and comparison with typical values."""
    if crra < 2:
        profile = {
            "risk_profile": "Very Aggressive",
            "description": "You're comfortable with significant risk for higher returns",
            "typical_allocation": "80-100% risky assets",
            "investor_type": "Growth/Aggressive Growth investor",
            "percentile": "Top 10% most aggressive investors"
        }
    elif crra < 3:
        profile = {
            "risk_profile": "Aggressive",
            "description": "You're willing to accept substantial risk for better returns",
            "typical_allocation": "70-80% risky assets",
            "investor_type": "Growth investor",
            "percentile": "Top 25% of aggressive investors"
        }
    elif crra < 4:
        profile = {
            "risk_profile": "Moderate",
            "description": "You seek balance between risk and security",
            "typical_allocation": "50-70% risky assets",
            "investor_type": "Balanced investor",
            "percentile": "Middle 30% of investors (average risk tolerance)"
        }
    elif crra < 6:
        profile = {
            "risk_profile": "Conservative",
            "description": "You prioritize security over high returns",
            "typical_allocation": "30-50% risky assets",
            "investor_type": "Income with Growth investor",
            "percentile": "Bottom 25% more conservative investors"
        }
    else:
        profile = {
            "risk_profile": "Very Conservative",
            "description": "You strongly prefer security and stability",
            "typical_allocation": "10-30% risky assets",
            "investor_type": "Income/Preservation investor",
            "percentile": "Bottom 10% most conservative investors"
        }
    return profile

def print_crra_scale(user_crra):
    """Print a text-based scale showing where the user's CRRA falls."""
    print("\nCRRA Scale (How you compare to typical investors):")
    print("=" * 70)
    print("CRRA Range  Risk Profile       Typical Investor Type")
    print("-" * 70)
    ranges = [
        (1, 2, "Very Aggressive  Professional investors, high-growth seekers"),
        (2, 3, "Aggressive       Growth investors, long investment horizon"),
        (3, 4, "Moderate        Balanced investors, middle-aged professionals"),
        (4, 6, "Conservative    Pre-retirees, income-focused investors"),
        (6, 10, "Very Conservative  Retirees, capital preservation focused")
    ]
    
    for start, end, desc in ranges:
        marker = "→" if start <= user_crra < end else " "
        print(f"{marker} {start:3.1f}-{end:<4.1f}  {desc}")

def main():
    try:
        # Get responses from questionnaire
        responses = ask_questions()
        
        # Calculate CRRA
        crra = calculate_crra_from_responses(responses)
        
        # Get interpretation
        interpretation = interpret_crra(crra)
        
        # Print results with enhanced context
        print("\nResults:")
        print("=" * 70)
        print(f"\nYour estimated CRRA value is: {crra:.2f}")
        print(f"Risk Profile: {interpretation['risk_profile']}")
        print(f"Description: {interpretation['description']}")
        print(f"Typical Asset Allocation: {interpretation['typical_allocation']}")
        print(f"Investor Type: {interpretation['investor_type']}")
        print(f"Market Context: {interpretation['percentile']}")
        
        # Print CRRA scale
        print_crra_scale(crra)
        
        print("\nTypical CRRA Values by Investor Type:")
        print("-" * 70)
        print("• 1.0-2.0: Professional traders, very aggressive investors")
        print("• 2.0-3.0: Young investors with stable income, growth-focused")
        print("• 3.0-4.0: Average retail investors, balanced approach")
        print("• 4.0-6.0: Conservative investors, pre-retirees")
        print("• 6.0+   : Very conservative investors, retirees")
        
        # Save results
        results = {
            "crra": crra,
            "responses": responses,
            "interpretation": interpretation
        }
        
        with open("crra_results.json", "w") as f:
            json.dump(results, f, indent=2)
        print("\nResults have been saved to 'crra_results.json'")
        
        print("\nRecommendation for Portfolio Optimizer:")
        print("-" * 70)
        print(f"Use CRRA = {round(crra, 1)} in your portfolio optimization calculations")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()