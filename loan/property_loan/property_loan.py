import pandas as pd
from typing import Iterable

from dataclasses import dataclass
import datetime
from dateutil.relativedelta import relativedelta
import plotly.graph_objects as go

from ..loan_status import LoanStatus


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