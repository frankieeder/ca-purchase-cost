import streamlit as st
import pandas as pd
from dataclasses import dataclass
import datetime
from dateutil.relativedelta import relativedelta
# import plotly.graph_objects as go


@dataclass
class LoanStatus:
    date: datetime.date
    balance: float
    interest: float
    principal: float


@dataclass
class PropertyLoan:
    MONTHS_PER_YEAR = 12

    loan_amount_usd: float
    interest_rate_percentage: float
    mortgage_years: float
    payment_interval: relativedelta = relativedelta(months=1)

    @property
    def mortgage_per_year_usd(self) -> float:
        numerator = (1 + self.interest_rate_percentage) ** self.mortgage_years
        denomenator = numerator - 1
        result = self.loan_amount_usd
        result *= self.interest_rate_percentage
        result *= numerator
        result /= denomenator
        return result

    @property
    def mortgage_per_month_usd(self) -> float:
        return self.mortgage_per_year_usd / self.MONTHS_PER_YEAR

    def calculate_monthly_interest(
            self,
            balance_usd: float,
    ) -> float:
        return (balance_usd * self.interest_rate_percentage) / 12

    def calculate_monthly_principal(
            self,
            interest_usd: float,
            balance_usd: float
    ) -> float:
        return (self.mortgage_per_month_usd - interest_usd) * (balance_usd > 0)

    def calculate_next_loan_status(
            self,
            loan_status: LoanStatus
    ) -> LoanStatus:
        next_months_balance = max(loan_status.balance - loan_status.principal, 0)
        next_months_interest = self.calculate_monthly_interest(
            balance_usd=next_months_balance
        )
        next_months_principal = self.calculate_monthly_principal(
            interest_usd=next_months_interest,
            balance_usd=next_months_balance
        )
        next_loan_status = LoanStatus(
            date=loan_status.date + self.payment_interval,
            balance=next_months_balance,
            interest=next_months_interest,
            principal=next_months_principal
        )
        return next_loan_status

    @property
    def initial_loan_status(self) -> LoanStatus:
        first_months_interest = self.calculate_monthly_interest(
            balance_usd=self.loan_amount_usd,
        )
        first_months_principal = self.calculate_monthly_principal(
            interest_usd=first_months_interest,
            balance_usd=self.loan_amount_usd
        )
        initial_loan_status = LoanStatus(
            date=datetime.date.today(),
            balance=self.loan_amount_usd,
            interest=first_months_interest,
            principal=first_months_principal,
        )
        return initial_loan_status

    def __iter__(self) -> iter[LoanStatus]:
        loan_status = self.initial_loan_status
        yield loan_status
        while loan_status.balance > 0:
            loan_status = self.calculate_next_loan_status(loan_status)
            yield loan_status

    def as_dataframe(self) -> pd.DataFrame:
        df = pd.DataFrame(iter(self))
        df['date'] = pd.to_datetime(df['date'])
        return df

    def yearly_dataframe(self) -> pd.DataFrame:
        df = self.as_dataframe()
        df_by_year = (
            df
            .groupby(df['date'].dt.year)
            .agg(dict(
                balance='max',
                interest='sum',
                principal='sum'
            ))
        )
        return df_by_year


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

    property_loan = PropertyLoan(
        loan_amount_usd=loan_amount_usd,
        interest_rate_percentage=interest_rate_percentage,
        mortgage_years=mortgage_years,
    )
    st.markdown(f"Loan Amount: {property_loan.loan_amount_usd}")

    loan_statuses = property_loan.as_dataframe()

    st.write(loan_statuses)
    st.write(property_loan.yearly_dataframe())
