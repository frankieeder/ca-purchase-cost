import streamlit as st

from streamlit_utils import percentage_input
from loan import IncomeAdjustedPropertyLoan


def populate_mortgage_container(container):
    with container:
        purchase_price = st.number_input(
            label='Purchase Price',
            value=1_000_000,
        )

        down_payment_percentage = percentage_input(
            label='% Down',
            value=20.0,
        )

        interest_rate_percentage = percentage_input(
            label='% Interest',
            value=7.0,
        )

        property_tax_percentage = percentage_input(
            label='% Property Taxes',
            value=1.25,
        )

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
        home_appreciation_percentage = percentage_input(
            label='% Home Value Appreciation per Year',
            value=7.0,
        )
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
