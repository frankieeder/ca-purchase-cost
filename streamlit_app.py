import streamlit as st
import pandas as pd
from dataclasses import dataclass
import datetime
from dateutil.relativedelta import relativedelta
from typing import Iterable
import plotly.graph_objects as go


@dataclass
class LoanStatus:
    date: datetime.date
    balance: float
    interest: float
    principal: float
    taxes: float


@dataclass(kw_only=True)
class PropertyLoan:
    MONTHS_PER_YEAR = 12
    YEARLY_AGGREGATIONS = dict(
        balance='max',
        interest='sum',
        principal='sum',
        taxes='sum',
    )
    PAYMENT_COLUMN_MAPPINGS = dict(
        interest='Interest',
        principal='Principal',
        taxes='Taxes',
    )

    purchase_price: float
    down_payment_percentage: float
    interest_rate_percentage: float
    mortgage_years: float
    property_taxes_yearly_usd: float
    home_appreciation_percentage: float
    include_appreciation_as_reduction: bool = True
    payment_interval: relativedelta = relativedelta(months=1)

    @property
    def loan_amount_usd(self):
        return self.purchase_price * (1 - self.down_payment_percentage)

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
        return (balance_usd * self.interest_rate_percentage) / self.MONTHS_PER_YEAR

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
            principal=next_months_principal,
            taxes=loan_status.taxes,
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
            taxes=self.property_taxes_monthly_usd,
        )
        return initial_loan_status

    def __iter__(self) -> Iterable[LoanStatus]:
        loan_status = self.initial_loan_status
        yield loan_status
        while loan_status.balance > 0:
            loan_status = self.calculate_next_loan_status(loan_status)
            yield loan_status

    @property
    def dataframe(self) -> pd.DataFrame:
        df = pd.DataFrame(iter(self))
        df['date'] = pd.to_datetime(df['date'])
        return df

    @property
    def dataframe_yearly(self) -> pd.DataFrame:
        df = self.dataframe
        df_by_year = (
            df
            .groupby(df['date'].dt.year)
            .agg(self.YEARLY_AGGREGATIONS)
        )
        return df_by_year

    @property
    def total_interest(self):
        return self.dataframe['interest'].sum()

    @classmethod
    def _make_graph_from_df(cls, df) -> go.Figure:
        fig = go.Figure(data=[
            go.Bar(
                name=col_title,
                x=df.index,
                y=df[col]
            )
            for col, col_title
            in cls.PAYMENT_COLUMN_MAPPINGS.items()
            if col in df.columns
        ])
        fig.update_layout(barmode='relative')
        return fig

    def graph_yearly(self) -> go.Figure:
        return self._make_graph_from_df(self.dataframe_yearly)

    def graph_monthly(self) -> go.Figure:
        return self._make_graph_from_df(self.dataframe.set_index('date'))

    @property
    def property_taxes_monthly_usd(self):
        return self.property_taxes_yearly_usd / self.MONTHS_PER_YEAR


@dataclass(kw_only=True)
class IncomeAdjustedPropertyLoan(PropertyLoan):
    STANDARD_DEDUCTION = 13_850.00
    PAYMENT_COLUMN_MAPPINGS = dict(
        interest='Interest',
        principal='Principal',
        taxes='Taxes',
        estimated_tax_savings='Estimated Tax Savings',
        estimated_appreciation_effective_mortgage_decrease='Appreciation Reduction'
    )

    agi_usd: float
    itemized_deductions_usd: float

    @property
    def dataframe_yearly(self) -> pd.DataFrame:
        df = super().dataframe_yearly
        df['agi'] = self.agi_usd
        df['total_itemized_deductions'] = df['interest'] + self.itemized_deductions_usd
        df['standard_deduction'] = self.STANDARD_DEDUCTION
        df['maximum_deduction'] = df[['total_itemized_deductions', 'standard_deduction']].max(axis=1)
        df['agi_reduced'] = df['agi'] - df['maximum_deduction']
        df['estimated_tax_savings'] = -0.4 * df['maximum_deduction']
        if self.include_appreciation_as_reduction:
            df['estimated_appreciation_effective_mortgage_decrease'] = - self.appreciation_effective_mortgage_decrease
        existing_payment_columns = list(self.PAYMENT_COLUMN_MAPPINGS.keys() & set(df.columns))
        df['total'] = df[existing_payment_columns].sum(axis=1)
        return df

    def graph_yearly(self) -> go.Figure:
        fig = super().graph_yearly()
        df = self.dataframe_yearly
        fig.add_trace(go.Line(
            name='Net',
            x=df.index,
            y=df['total'],
        ))
        return fig

    def appreciation_multiplier_at_year(self, year: float):
        return (1 + self.home_appreciation_percentage) ** year

    @property
    def final_value(self):
        multiplier = self.appreciation_multiplier_at_year(self.mortgage_years)
        final_value = multiplier * self.purchase_price
        return final_value

    @property
    def anticipated_profit(self):
        return self.final_value - self.purchase_price

    @property
    def appreciation_effective_mortgage_decrease(self):
        return self.anticipated_profit / (self.mortgage_years * self.MONTHS_PER_YEAR)


PERCENT_MAX = 100


def populate_mortgage_container(container):
    with container:
        purchase_price = st.number_input(
            label='Purchase Price',
            value=1_000_000,
        )

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
            label='Mortgage Duration (years)',
            value=30,
        )
    return (
        purchase_price,
        down_payment_percentage,
        interest_rate_percentage,
        property_tax_percentage,
        mortgage_years,
    )


def populate_simulation_container(container):
    with container:
        home_appreciation_percentage = st.number_input(
            label='% Home Value Appreciation per Year',
            min_value=0.0,
            max_value=100.0,
            value=7.0,
            step=1.0
        )
        home_appreciation_percentage /= PERCENT_MAX
        include_appreciation_as_reduction = st.checkbox("Include appreciation as reduction in monthly payment")
    return (
        home_appreciation_percentage,
        include_appreciation_as_reduction,
    )


def populate_taxes_container(container):
    with container:
        agi_usd = st.number_input(
            label='Adjusted Gross Income',
            help='excluding property related deductions, which we will calculate',
            min_value=0.0,
            value=70_000.0,
        )
        itemized_deductions_usd = st.number_input(
            label='Itemized Deductions',
            help='Used in above calculation',
            min_value=0.0,
            value=0.0,
        )
    return (
        agi_usd,
        itemized_deductions_usd
    )


if __name__ == '__main__':
    st.markdown("This tool helps determine the actual cost of a home purchase in California, USA, "
                "given my understanding of tax and property laws currently standing. This is by no means "
                "a guarantee of what you will end up paying for a home purchase, though please feel "
                "free to email me at frankaeder@gmail.com with any corrections.")

    with st.sidebar:
        mortgage_tab, simulation_tab, taxes_tab = st.tabs([
            'Mortgage',
            'Simulation',
            'Taxes',
        ])

        (
            purchase_price,
            down_payment_percentage,
            interest_rate_percentage,
            property_tax_percentage,
            mortgage_years,
        ) = populate_mortgage_container(mortgage_tab)

        (
            home_appreciation_percentage,
            include_appreciation_as_reduction,
        ) = populate_simulation_container(simulation_tab)

        (
            agi_usd,
            itemized_deductions_usd
        ) = populate_taxes_container(taxes_tab)

    property_loan = IncomeAdjustedPropertyLoan(
        purchase_price=purchase_price,
        down_payment_percentage=down_payment_percentage,
        interest_rate_percentage=interest_rate_percentage,
        mortgage_years=mortgage_years,
        property_taxes_yearly_usd=purchase_price * property_tax_percentage,
        home_appreciation_percentage=home_appreciation_percentage,
        include_appreciation_as_reduction=include_appreciation_as_reduction,

        agi_usd=agi_usd,
        itemized_deductions_usd=itemized_deductions_usd,
    )

    st.markdown("---")

    st.markdown(f"Loan Amount: {property_loan.loan_amount_usd}")
    st.markdown(f"Monthly Payment: {property_loan.mortgage_per_month_usd}")
    st.markdown(f"Total Interest Paid: {property_loan.total_interest}")

    st.markdown("---")

    st.write(property_loan.graph_yearly())
    st.write(property_loan.graph_monthly())
