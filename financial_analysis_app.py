import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm
from arch import arch_model

# Streamlit app title
st.title("Financial Data Analysis and Trading Strategies")
st.write("Upload a CSV file with financial data (e.g., FTSE 100) to analyze and generate trading strategies.")

# File upload
uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

if uploaded_file is not None:
    # Load the data
    data = pd.read_csv(uploaded_file)
    st.write("### Data Preview")
    st.write(data.head())

    # Clean price data (remove commas and convert to float)
    if 'Price' in data.columns:
        data['Price'] = data['Price'].str.replace(',', '').astype(float)

        # 1. Standard Deviation
        mean_price = data['Price'].mean()
        std_dev = data['Price'].std()
        st.write("### Statistical Analysis")
        st.write(f"Mean Price: {mean_price:.2f}")
        st.write(f"Standard Deviation: {std_dev:.2f}")

        # 2. Price Clusters (Distribution Densities)
        st.write("### Price Distribution (Clusters)")
        fig, ax = plt.subplots()
        ax.hist(data['Price'], bins=10, edgecolor='black')
        ax.axvline(mean_price, color='red', linestyle='dashed', linewidth=1, label=f'Mean Price: {mean_price:.2f}')
        ax.set_title("Price Distribution")
        ax.set_xlabel("Price")
        ax.set_ylabel("Frequency")
        ax.legend()
        st.pyplot(fig)

        # 3. Mean Reversion Rate
        mean_reversion_rate = (abs(data['Price'] - mean_price) / mean_price).mean()
        st.write(f"Mean Reversion Rate: {mean_reversion_rate:.4f} (or {mean_reversion_rate * 100:.2f}%)")

        # 4. Geometric Brownian Motion (GBM)
        def gbm_simulation(S0, mu, sigma, days, n_simulations):
            dt = 1 / days
            price_paths = np.zeros((days, n_simulations))
            price_paths[0] = S0
            for t in range(1, days):
                rand = np.random.normal(0, 1, n_simulations)
                price_paths[t] = price_paths[t - 1] * np.exp((mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * rand)
            return price_paths

        st.write("### Geometric Brownian Motion (GBM) Simulations")
        S0 = data['Price'].iloc[-1]  # Latest price
        mu = data['Price'].pct_change().mean() * 252  # Annualized drift
        sigma = std_dev / mean_price * np.sqrt(252)  # Annualized volatility
        days = 7  # Next 7 days
        n_simulations = 1000  # Number of simulations

        gbm_paths = gbm_simulation(S0, mu, sigma, days, n_simulations)

        fig, ax = plt.subplots()
        ax.plot(gbm_paths)
        ax.set_title("GBM Simulations")
        ax.set_xlabel("Days")
        ax.set_ylabel("Price")
        st.pyplot(fig)

        # 5. Jump Diffusion Model
        def jump_diffusion_simulation(S0, mu, sigma, lambda_jump, mu_jump, sigma_jump, days, n_simulations):
            dt = 1 / days
            price_paths = np.zeros((days, n_simulations))
            price_paths[0] = S0
            for t in range(1, days):
                rand = np.random.normal(0, 1, n_simulations)
                jump = np.random.poisson(lambda_jump * dt, n_simulations) * np.random.normal(mu_jump, sigma_jump, n_simulations)
                price_paths[t] = price_paths[t - 1] * np.exp((mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * rand + jump)
            return price_paths

        st.write("### Jump Diffusion Simulations")
        lambda_jump = 0.05  # Jump frequency
        mu_jump = 0.01  # Mean jump size
        sigma_jump = 0.02  # Jump volatility

        jump_paths = jump_diffusion_simulation(S0, mu, sigma, lambda_jump, mu_jump, sigma_jump, days, n_simulations)

        fig, ax = plt.subplots()
        ax.plot(jump_paths)
        ax.set_title("Jump Diffusion Simulations")
        ax.set_xlabel("Days")
        ax.set_ylabel("Price")
        st.pyplot(fig)

        # 6. GARCH Model
        st.write("### GARCH Model (Volatility Forecasting)")
        returns = data['Price'].pct_change().dropna()
        garch_model = arch_model(returns, vol='Garch', p=1, q=1)
        garch_fit = garch_model.fit()
        st.write(garch_fit.summary())

        # Forecast volatility
        forecast = garch_fit.forecast(horizon=days)
        forecast_volatility = np.sqrt(forecast.variance.iloc[-1])
        st.write("Forecasted Volatility (Next 7 Days):")
        st.write(forecast_volatility)

        # 7. Monte Carlo Simulation
        st.write("### Monte Carlo Simulations")
        monte_carlo_paths = gbm_simulation(S0, mu, sigma, days, n_simulations)
        monte_carlo_final_prices = monte_carlo_paths[-1]
        confidence_interval = np.percentile(monte_carlo_final_prices, [2.5, 97.5])
        st.write(f"95% Confidence Interval for Final Price: {confidence_interval}")

        fig, ax = plt.subplots()
        ax.plot(monte_carlo_paths)
        ax.set_title("Monte Carlo Simulations")
        ax.set_xlabel("Days")
        ax.set_ylabel("Price")
        st.pyplot(fig)

        # 8. Day-Trading Strategies
        st.write("### Day-Trading Strategies")
        latest_price = data['Price'].iloc[-1]
        support = st.number_input("Enter Support Level", value=8100.0)
        resistance = st.number_input("Enter Resistance Level", value=8500.0)

        # Mean Reversion Strategy
        def mean_reversion_strategy(price, mean_price, threshold=0.01):
            if price < mean_price * (1 - threshold):
                return "Buy"
            elif price > mean_price * (1 + threshold):
                return "Sell"
            else:
                return "Hold"

        # Breakout Strategy
        def breakout_strategy(price, support, resistance):
            if price > resistance:
                return "Buy (Breakout)"
            elif price < support:
                return "Sell (Breakdown)"
            else:
                return "Hold"

        st.write(f"Mean Reversion Strategy: {mean_reversion_strategy(latest_price, mean_price)}")
        st.write(f"Breakout Strategy: {breakout_strategy(latest_price, support, resistance)}")

    else:
        st.error("The uploaded file must contain a 'Price' column.")
else:
    st.write("Please upload a CSV file to get started.")