import random

# Keep quantify_timeline and quantify_location as they are used by the new logic
def quantify_timeline(timeline):
    """Converts a timeline string into a numerical value in months."""
    timeline_map = {
        "1-3months": 2,
        "3-6months": 4.5,
        "6-12months": 9,
        "1-2years": 18,
        "2+years": 30,
    }
    return timeline_map.get(timeline, 8) # Default to 8 months if not found

def quantify_location(location):
    """Converts a location scope string into a numerical score."""
    location_map = {
        "local": 1,
        "country": 2,
        "global": 3,
    }
    return location_map.get(location, 2) # Default to 2 (country) if not found

def calculate_better_risk_assessment(data):
    """
    A more accurate risk calculation that combines rules and scoring logic.
    """
    budget = data.get("budget", 0)
    timeline_months = quantify_timeline(data.get("timeline", ""))
    location_score = quantify_location(data.get("location", ""))
    cofounders = data.get("number_of_cofounders", 0)
    complexity = data.get("technical_complexity", 5)
    revenue = data.get("total_revenue", 0)
    expense = data.get("total_expense", 0)

    # 🚨 Step 1: Hard Rules (critical risk triggers)
    if revenue == 0 and expense > budget * 0.8:
        return _result("High", 95, "No revenue but expenses exceed 80% of budget. Critical financial risk.")
    if revenue > 0 and expense > 3 * revenue:
        return _result("High", 90, "Expenses are more than triple the revenue, indicating severe financial strain.")
    if cofounders == 1 and complexity >= 8:
        return _result("High", 85, "Single founder with very high technical complexity poses significant execution risk.")
    if budget < expense * 0.5:
        return _result("High", 80, "Budget is less than half of expected expenses. Insufficient funding risk.")

    # ✅ Step 2: Scoring System
    risk_score = 0

    # Financial risk (improved calculation)
    if revenue > 0:
        profit_margin = (revenue - expense) / revenue
        if profit_margin < -0.5:  # More than 50% loss
            risk_score += 30
        elif profit_margin < 0:  # Negative but less than 50% loss
            risk_score += 20
        elif profit_margin < 0.1:  # Less than 10% profit
            risk_score += 10
        elif profit_margin < 0.2:  # Less than 20% profit
            risk_score += 5
    else:
        # No revenue case
        if expense > 0:
            risk_score += 25
        if expense > budget * 0.6:
            risk_score += 15

    # Budget adequacy (NEW)
    if budget > 0:
        budget_coverage = budget / (expense + 1)  # +1 to avoid division by zero
        if budget_coverage < 0.5:
            risk_score += 20
        elif budget_coverage < 0.8:
            risk_score += 10
        elif budget_coverage < 1.0:
            risk_score += 5

    # Timeline risk (improved logic)
    if timeline_months > 24:
        risk_score += 8  # Very long timelines can be risky
    elif timeline_months > 18:
        risk_score += 5
    elif timeline_months > 12:
        risk_score += 3
    elif timeline_months < 3:
        risk_score += 5  # Very short timelines can also be risky

    # Location scope (adjusted weights)
    if location_score == 3:  # Global
        risk_score += 4  # Reduced from 6
    elif location_score == 2:  # Country
        risk_score += 3
    else:  # Local
        risk_score += 2

    # Founder team strength (improved)
    if cofounders == 1:
        risk_score += 8  # Reduced from 10
    elif cofounders == 2:
        risk_score += 3  # Reduced from 5
    elif cofounders >= 4:
        risk_score += 2  # Too many cofounders can also be risky

    # Technical complexity (adjusted weights)
    if complexity >= 8:
        risk_score += 15
    elif complexity >= 6:
        risk_score += 10
    elif complexity >= 4:
        risk_score += 6
    elif complexity <= 2:
        risk_score += 3  # Very low complexity might indicate lack of innovation

    # Final classification (adjusted thresholds)
    if risk_score >= 75:
        return _result("High", risk_score, "High overall risk due to a combination of financial, scope, and execution challenges.")
    elif risk_score >= 45:
        return _result("Medium", risk_score, "Moderate risk, with some areas requiring attention in funding or project execution.")
    else:
        return _result("Low", risk_score, "Overall low risk, indicating a well-planned project with manageable challenges.")

def _result(level, score, reason):
    return {
        "risk_level": level,
        "risk_score": min(100, score), # Cap score at 100
        "explanation": reason
    }

# Removed old Z-score related functions and benchmarks
# ZSCORE_BENCHMARKS = {...}
# def calculate_z_score(...)
# def calculate_risk_assessment(...)
# def get_mock_z_score_analysis(...)
