import math
from typing import Dict, Any

def calculate_property_metrics(price: float, 
                               rent: float, 
                               down_payment_percent: float, 
                               interest_rate: float, 
                               loan_term_years: int, 
                               monthly_expenses: float) -> Dict[str, float]:
    """
    Calculates key financial metrics for a rental property.
    
    Args:
        price: The purchase price of the property.
        rent: The monthly rental income.
        down_payment_percent: The down payment percentage (e.g., 20 for 20%).
        interest_rate: The annual interest rate (e.g., 7 for 7%).
        loan_term_years: The loan term in years.
        monthly_expenses: Monthly expenses (taxes, insurance, maintenance, etc.)
        
    Returns:
        A dictionary containing calculated metrics.
    """
    # Calculate down payment and loan amount
    down_payment = price * (down_payment_percent / 100)
    loan_amount = price - down_payment
    
    # Calculate monthly mortgage payment
    # Formula: M = P [ r(1+r)^n ] / [ (1+r)^n - 1 ]
    monthly_interest_rate = (interest_rate / 100) / 12
    n_payments = loan_term_years * 12
    
    if monthly_interest_rate == 0:
        # Handle edge case of 0% interest
        mortgage_payment = loan_amount / n_payments
    else:
        mortgage_payment = loan_amount * (
            (monthly_interest_rate * math.pow(1 + monthly_interest_rate, n_payments)) / 
            (math.pow(1 + monthly_interest_rate, n_payments) - 1)
        )
    
    # Calculate cash flow
    cash_flow = rent - mortgage_payment - monthly_expenses
    
    # Calculate annual cash flow
    annual_cash_flow = cash_flow * 12
    
    # Calculate cash-on-cash return
    cash_on_cash_return = (annual_cash_flow / down_payment) * 100
    
    return {
        "down_payment": down_payment,
        "loan_amount": loan_amount,
        "mortgage_payment": mortgage_payment,
        "cash_flow": cash_flow,
        "annual_cash_flow": annual_cash_flow,
        "cash_on_cash_return": cash_on_cash_return
    }
