import streamlit as st
#import plotly.graph_objects as go
import pandas as pd
from dataclasses import dataclass


MONTHS_PER_YEAR = 12

@dataclass
class LoanStatus:
    balance: float
    interest: float
    principal: float

def calculate_mortgage_per_year(
        loan_amount_usd: float,
        interest_rate_percentage: float,
        mortgage_years: float,
):
    numerator = (1 + interest_rate_percentage) ** mortgage_years
    denomenator = numerator - 1
    result = loan_amount_usd
    result *= interest_rate_percentage
    result *= numerator
    result /= denomenator
    return result


def calculate_monthly_interest(
        balance_usd: float,
        interest_rate_percentage: float
):
    return (balance_usd * interest_rate_percentage) / 12


def calculate_monthly_principal(
        mortgage_per_month_usd: float,
        interest_usd: float,
        balance_usd: float
):
    return (mortgage_per_month_usd - interest_usd) * (balance_usd > 0)


def calculate_next_loan_status(
        loan_status: LoanStatus
) -> LoanStatus:
    next_months_balance = max(loan_status.balance - loan_status.principal, 0)
    next_months_interest = calculate_monthly_interest(
        balance_usd=next_months_balance,
        interest_rate_percentage=interest_rate_percentage
    )
    next_months_principal = calculate_monthly_principal(
        mortgage_per_month_usd=mortgage_per_month_usd,
        interest_usd=next_months_interest,
        balance_usd=next_months_balance
    )
    next_loan_status = LoanStatus(
        balance=next_months_balance,
        interest=next_months_interest,
        principal=next_months_principal
    )
    return next_loan_status



if __name__ == '__main__':
    st.markdown("This tool helps determine the actual cost of a home purchase in California, USA,"
                "given my understanding of tax and property laws currently standing. This is by no means"
                "a guarantee of what you will end up paying for a home purchase, though please feel"
                "free to email me at frankaeder@gmail.com with any corrections.")

    purchase_price = st.number_input(
        label='Purchase Price',
        value=1_000_000,
    )


    PERCENT_MAX = 100
    down_payment_percentage = st.number_input(
        label='% Down',
        min_value=0.0,
        max_value=100.0,
        value=20.0,
        step=1.0
    )
    down_payment_percentage /= PERCENT_MAX

    interest_rate_percentage = st.number_input(
        label='% Interest',
        min_value=0.0,
        max_value=100.0,
        value=7.0,
        step=1.0
    )
    interest_rate_percentage /= PERCENT_MAX

    property_tax_percentage = st.number_input(
        label='% Property Taxes',
        min_value=0.0,
        max_value=100.0,
        value=1.25,
        step=1.0
    )
    property_tax_percentage /= PERCENT_MAX

    mortgage_years = st.number_input(
        label='Purchase Price',
        value=30,
    )

    loan_amount_usd = purchase_price * (1 - down_payment_percentage)
    st.markdown(f"Loan Amount: {loan_amount_usd}")

    mortgage_per_year_usd = calculate_mortgage_per_year(
        loan_amount_usd=loan_amount_usd,
        interest_rate_percentage=interest_rate_percentage,
        mortgage_years=mortgage_years,
    )
    mortgage_per_month_usd = mortgage_per_year_usd / MONTHS_PER_YEAR

    st.write(mortgage_per_year_usd)
    first_months_interest = calculate_monthly_interest(
        balance_usd=loan_amount_usd,
        interest_rate_percentage=interest_rate_percentage
    )
    first_months_principal = calculate_monthly_principal(
        mortgage_per_month_usd=mortgage_per_month_usd,
        interest_usd=first_months_interest,
        balance_usd=loan_amount_usd
    )

    loan_statuses = [
        LoanStatus(
            balance=loan_amount_usd,
            interest=first_months_interest,
            principal=first_months_principal,
        )
    ]

    while loan_statuses[-1].balance > 0:
        loan_statuses.append(calculate_next_loan_status(loan_statuses[-1]))

    loan_statuses = pd.DataFrame(loan_statuses)

    st.write(loan_statuses)
