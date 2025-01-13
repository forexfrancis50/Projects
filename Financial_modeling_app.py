import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.express as px
import plotly.graph_objects as go
from scipy.stats import norm  # For Monte Carlo Simulation
from io import BytesIO  # For Excel export

# Function to calculate financial projections
def calculate_projections(data, revenue_growth, cogs_percent, op_exp_growth, tax_rate, capex_percent, discount_rate, terminal_growth):
    projections = []
    for year in range(1, 6):
        if year == 1:
            revenue = data['Revenue'] * (1 + revenue_growth)
            cogs = revenue * cogs_percent
            op_exp = data['Operating Expenses'] * (1 + op_exp_growth)
        else:
            revenue = projections[-1]['Revenue'] * (1 + revenue_growth)
            cogs = revenue * cogs_percent
            op_exp = projections[-1]['Operating Expenses'] * (1 + op_exp_growth)
        
        gross_profit = revenue - cogs
        operating_income = gross_profit - op_exp
        net_income = operating_income * (1 - tax_rate)
        capex = revenue * capex_percent
        free_cash_flow = net_income + op_exp - capex  # Simplified FCF calculation
        
        projections.append({
            'Year': year,
            'Revenue': revenue,
            'COGS': cogs,
            'Gross Profit': gross_profit,
            'Operating Expenses': op_exp,
            'Operating Income': operating_income,
            'Net Income': net_income,
            'CapEx': capex,
            'Free Cash Flow': free_cash_flow
        })
    
    return pd.DataFrame(projections)

# Function to calculate DCF, NPV, and IRR
def calculate_valuation(projections, discount_rate, terminal_growth):
    free_cash_flows = projections['Free Cash Flow'].values
    terminal_value = free_cash_flows[-1] * (1 + terminal_growth) / (discount_rate - terminal_growth)
    
    # Discounted Cash Flows
    discounted_cash_flows = []
    for i, fcf in enumerate(free_cash_flows):
        discounted_cash_flows.append(fcf / (1 + discount_rate) ** (i + 1))
    
    # Terminal Value Discounted
    discounted_terminal_value = terminal_value / (1 + discount_rate) ** len(free_cash_flows)
    
    # Total Enterprise Value
    enterprise_value = sum(discounted_cash_flows) + discounted_terminal_value
    
    # NPV (assuming no initial investment)
    npv = enterprise_value
    
    # IRR
    irr = npf.irr(free_cash_flows)
    
    return enterprise_value, npv, irr, discounted_cash_flows, discounted_terminal_value

# Function to create DCF table
def create_dcf_table(projections, discounted_cash_flows, discounted_terminal_value):
    dcf_table = projections[['Year', 'Free Cash Flow']].copy()
    dcf_table['Discounted Cash Flow'] = discounted_cash_flows
    dcf_table.loc[len(dcf_table)] = ['Terminal Value', None, discounted_terminal_value]
    dcf_table.loc[len(dcf_table)] = ['Enterprise Value', None, dcf_table['Discounted Cash Flow'].sum()]
    return dcf_table

# Function to calculate WACC
def calculate_wacc(cost_of_equity, cost_of_debt, tax_rate, equity, debt):
    wacc = (equity / (equity + debt)) * cost_of_equity + (debt / (equity + debt)) * cost_of_debt * (1 - tax_rate)
    return wacc

# Function to calculate payback period
def calculate_payback_period(free_cash_flows, initial_investment):
    cumulative_cash_flow = 0
    for i, fcf in enumerate(free_cash_flows):
        cumulative_cash_flow += fcf
        if cumulative_cash_flow >= initial_investment:
            return i + 1  # Payback period in years
    return None  # If payback period exceeds projection years

# Function to calculate valuation multiples
def calculate_valuation_multiples(enterprise_value, ebitda, net_income):
    ev_ebitda = enterprise_value / ebitda if ebitda != 0 else None
    pe_ratio = enterprise_value / net_income if net_income != 0 else None
    return ev_ebitda, pe_ratio

# Function to perform sensitivity analysis
def sensitivity_analysis(projections, discount_rate, terminal_growth, revenue_growth_range, cogs_percent_range):
    results = []
    for rev_growth in revenue_growth_range:
        for cogs_percent in cogs_percent_range:
            projections_temp = calculate_projections(projections.iloc[0].to_dict(), rev_growth, cogs_percent, 0.03, 0.25, 0.05, discount_rate, terminal_growth)
            enterprise_value, _, _, _, _ = calculate_valuation(projections_temp, discount_rate, terminal_growth)
            results.append({
                'Revenue Growth': rev_growth,
                'COGS %': cogs_percent,
                'Enterprise Value': enterprise_value
            })
    return pd.DataFrame(results)

# Function to perform Monte Carlo Simulation
def monte_carlo_simulation(projections, discount_rate, terminal_growth, iterations=1000):
    enterprise_values = []
    for _ in range(iterations):
        rev_growth = np.random.normal(0.05, 0.02)  # Random revenue growth
        cogs_percent = np.random.normal(0.60, 0.05)  # Random COGS %
        projections_temp = calculate_projections(projections.iloc[0].to_dict(), rev_growth, cogs_percent, 0.03, 0.25, 0.05, discount_rate, terminal_growth)
        enterprise_value, _, _, _, _ = calculate_valuation(projections_temp, discount_rate, terminal_growth)
        enterprise_values.append(enterprise_value)
    return enterprise_values

# Function to calculate financial ratios
def calculate_financial_ratios(data):
    ratios = {}
    if 'Revenue' in data and 'Cost of Goods Sold' in data:
        ratios['Gross Margin'] = (data['Revenue'] - data['Cost of Goods Sold']) / data['Revenue']
    if 'Revenue' in data and 'Operating Expenses' in data:
        ratios['Operating Margin'] = (data['Revenue'] - data['Cost of Goods Sold'] - data['Operating Expenses']) / data['Revenue']
    if 'Net Income' in data and 'Revenue' in data:
        ratios['Net Profit Margin'] = data['Net Income'] / data['Revenue']
    if 'Current Assets' in data and 'Current Liabilities' in data:
        ratios['Current Ratio'] = data['Current Assets'] / data['Current Liabilities']
    if 'Liabilities' in data and 'Shareholders\' Equity' in data:
        ratios['Debt-to-Equity Ratio'] = data['Liabilities'] / data['Shareholders\' Equity']
    return ratios

# Function to export results to Excel
def export_to_excel(projections, dcf_table, enterprise_value, npv, irr, ratios):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        projections.to_excel(writer, sheet_name='Projections', index=False)
        dcf_table.to_excel(writer, sheet_name='DCF Table', index=False)
        pd.DataFrame({
            'Metric': ['Enterprise Value', 'NPV', 'IRR'],
            'Value': [enterprise_value, npv, irr]
        }).to_excel(writer, sheet_name='Valuation Results', index=False)
        pd.Series(ratios).to_excel(writer, sheet_name='Financial Ratios')
    output.seek(0)
    return output

# Streamlit App
st.title("Financial modeling assistant")
st.write("Upload your financial statements (Excel file) and provide assumptions for projections.")

# File upload
uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])
if uploaded_file is not None:
    try:
        # Read Excel file
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = xls.sheet_names
        
        # Select sheet
        sheet_name = st.selectbox("Select Sheet", sheet_names)
        df = pd.read_excel(uploaded_file, sheet_name=sheet_name)
        
        # Display uploaded data
        st.write("Uploaded Data:")
        st.dataframe(df)
        
        # Extract relevant columns (flexible to column names)
        data = {}
        try:
            if df.iloc[:, 0].str.contains('Revenue', case=False, na=False).any():
                data['Revenue'] = df.loc[df.iloc[:, 0].str.contains('Revenue', case=False, na=False), df.columns[1]].values[0]
            if df.iloc[:, 0].str.contains('Cost of Goods Sold', case=False, na=False).any():
                data['Cost of Goods Sold'] = df.loc[df.iloc[:, 0].str.contains('Cost of Goods Sold', case=False, na=False), df.columns[1]].values[0]
            if df.iloc[:, 0].str.contains('Operating Expenses', case=False, na=False).any():
                data['Operating Expenses'] = df.loc[df.iloc[:, 0].str.contains('Operating Expenses', case=False, na=False), df.columns[1]].values[0]
            if df.iloc[:, 0].str.contains('Current Assets', case=False, na=False).any():
                data['Current Assets'] = df.loc[df.iloc[:, 0].str.contains('Current Assets', case=False, na=False), df.columns[1]].values[0]
            if df.iloc[:, 0].str.contains('Current Liabilities', case=False, na=False).any():
                data['Current Liabilities'] = df.loc[df.iloc[:, 0].str.contains('Current Liabilities', case=False, na=False), df.columns[1]].values[0]
            if df.iloc[:, 0].str.contains('Liabilities', case=False, na=False).any():
                data['Liabilities'] = df.loc[df.iloc[:, 0].str.contains('Liabilities', case=False, na=False), df.columns[1]].values[0]
            if df.iloc[:, 0].str.contains('Shareholders\' Equity', case=False, na=False).any():
                data['Shareholders\' Equity'] = df.loc[df.iloc[:, 0].str.contains('Shareholders\' Equity', case=False, na=False), df.columns[1]].values[0]
        except Exception as e:
            st.error("Error: Unable to extract required data. Please ensure the sheet contains the necessary fields.")
            st.stop()
        
        # User inputs for assumptions
        st.sidebar.header("Assumptions")
        revenue_growth = st.sidebar.number_input("Revenue Growth Rate (%)", value=5.0) / 100
        cogs_percent = st.sidebar.number_input("COGS as % of Revenue", value=60.0) / 100
        op_exp_growth = st.sidebar.number_input("Operating Expenses Growth Rate (%)", value=3.0) / 100
        tax_rate = st.sidebar.number_input("Tax Rate (%)", value=25.0) / 100
        capex_percent = st.sidebar.number_input("CapEx as % of Revenue", value=5.0) / 100
        discount_rate = st.sidebar.number_input("Discount Rate (%)", value=10.0) / 100
        terminal_growth = st.sidebar.number_input("Terminal Growth Rate (%)", value=3.0) / 100
        
        # Calculate projections
        if 'Revenue' in data and 'Cost of Goods Sold' in data and 'Operating Expenses' in data:
            projections = calculate_projections(data, revenue_growth, cogs_percent, op_exp_growth, tax_rate, capex_percent, discount_rate, terminal_growth)
            st.write("Financial Projections:")
            st.dataframe(projections)
            
            # Calculate valuation
            enterprise_value, npv, irr, discounted_cash_flows, discounted_terminal_value = calculate_valuation(projections, discount_rate, terminal_growth)
            st.write("Valuation Results:")
            st.write(f"Enterprise Value (DCF): ${enterprise_value:,.2f}")
            st.write(f"NPV: ${npv:,.2f}")
            st.write(f"IRR: {irr * 100:.2f}%")
            
            # DCF Table
            dcf_table = create_dcf_table(projections, discounted_cash_flows, discounted_terminal_value)
            st.write("DCF Table:")
            st.dataframe(dcf_table)
            
            # Plot DCF Table
            st.write("DCF Table Visualization:")
            fig = go.Figure(data=[go.Table(
                header=dict(values=list(dcf_table.columns),
                            fill_color='paleturquoise',
                            align='left'),
                cells=dict(values=[dcf_table[col] for col in dcf_table.columns],
                           fill_color='lavender',
                           align='left'))
            ])
            st.plotly_chart(fig)
        else:
            st.warning("Insufficient data to calculate financial projections and valuation.")
        
        # WACC Calculation
        st.sidebar.header("WACC Inputs")
        cost_of_equity = st.sidebar.number_input("Cost of Equity (%)", value=12.0) / 100
        cost_of_debt = st.sidebar.number_input("Cost of Debt (%)", value=6.0) / 100
        equity = st.sidebar.number_input("Equity ($)", value=4000000)
        debt = st.sidebar.number_input("Debt ($)", value=2000000)
        wacc = calculate_wacc(cost_of_equity, cost_of_debt, tax_rate, equity, debt)
        st.write(f"Weighted Average Cost of Capital (WACC): {wacc * 100:.2f}%")
        
        # Payback Period
        initial_investment = st.sidebar.number_input("Initial Investment ($)", value=5000000)
        if 'Free Cash Flow' in projections:
            payback_period = calculate_payback_period(projections['Free Cash Flow'].values, initial_investment)
            st.write(f"Payback Period: {payback_period} years")
        else:
            st.warning("Insufficient data to calculate payback period.")
        
        # Valuation Multiples
        if 'Operating Income' in projections and 'Net Income' in projections:
            ebitda = projections['Operating Income'].sum()  # Simplified EBITDA calculation
            net_income = projections['Net Income'].sum()
            ev_ebitda, pe_ratio = calculate_valuation_multiples(enterprise_value, ebitda, net_income)
            st.write(f"EV/EBITDA: {ev_ebitda:.2f}")
            st.write(f"P/E Ratio: {pe_ratio:.2f}")
        else:
            st.warning("Insufficient data to calculate valuation multiples.")
        
        # Sensitivity Analysis
        if 'Revenue' in data and 'Cost of Goods Sold' in data:
            st.write("Sensitivity Analysis:")
            revenue_growth_range = np.linspace(0.03, 0.07, 5)  # 3% to 7%
            cogs_percent_range = np.linspace(0.55, 0.65, 5)  # 55% to 65%
            sensitivity_results = sensitivity_analysis(projections, discount_rate, terminal_growth, revenue_growth_range, cogs_percent_range)
            st.dataframe(sensitivity_results.pivot(index='Revenue Growth', columns='COGS %', values='Enterprise Value'))
        else:
            st.warning("Insufficient data to perform sensitivity analysis.")
        
        # Monte Carlo Simulation
        if 'Revenue' in data and 'Cost of Goods Sold' in data:
            st.write("Monte Carlo Simulation:")
            enterprise_values = monte_carlo_simulation(projections, discount_rate, terminal_growth)
            fig = go.Figure(data=[go.Histogram(x=enterprise_values, nbinsx=50)])
            fig.update_layout(title="Distribution of Enterprise Value", xaxis_title="Enterprise Value", yaxis_title="Frequency")
            st.plotly_chart(fig)
        else:
            st.warning("Insufficient data to perform Monte Carlo simulation.")
        
        # Financial Ratios
        ratios = calculate_financial_ratios(data)
        if ratios:
            st.write("Financial Ratios:")
            st.write(pd.Series(ratios))
        else:
            st.warning("Insufficient data to calculate financial ratios.")
        
        # Export Results
        if 'projections' in locals() and 'dcf_table' in locals() and 'enterprise_value' in locals() and 'ratios' in locals():
            st.write("Export Results:")
            output = export_to_excel(projections, dcf_table, enterprise_value, npv, irr, ratios)
            st.download_button(
                label="Download Results as Excel",
                data=output,
                file_name="financial_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    
    except Exception as e:
        st.error(f"An error occurred: {e}. Please check the file format and data.")
