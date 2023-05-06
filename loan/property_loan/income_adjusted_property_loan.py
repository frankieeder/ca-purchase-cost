import pandas as pd
from dataclasses import dataclass
import plotly.graph_objects as go

from .property_loan import PropertyLoan


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
