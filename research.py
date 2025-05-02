#%% Load Data and Libraries for Interactive Session

import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from src.utils import DATA_DIR # Assuming DATA_DIR is correctly defined in utils

logging.info("--- Interactive Session: Loading Data ---")

try:
    # Define paths relative to DATA_DIR
    daily_clean_path = DATA_DIR / "daily_clean.parquet"
    monthly_clean_path = DATA_DIR / "monthly_clean.parquet"

    # Load the processed dataframes
    daily_clean = pd.read_parquet(daily_clean_path)
    monthly_clean = pd.read_parquet(monthly_clean_path)

    logging.info(f"Loaded daily_clean: {daily_clean.shape}")
    logging.info(f"Loaded monthly_clean: {monthly_clean.shape}")
    print("Data loaded successfully into 'daily_clean' and 'monthly_clean' variables.")
    # Display head of monthly data as an example
    print("\nMonthly Clean Head:")
    print(monthly_clean.head())

except FileNotFoundError as e:
    logging.error(f"Error loading data: {e}. Run the full main.py script first to generate processed files.")
    print(f"ERROR: Could not load data files. Please run 'python main.py' first.")
except Exception as e:
    logging.error(f"An unexpected error occurred during data loading: {e}", exc_info=True)
    print(f"ERROR: An unexpected error occurred: {e}")

# Add a blank line after this cell's code
print("\nCell execution finished.")

#%% Plot Monthly Price vs Fair Value (Example)

logging.info("--- Interactive Session: Plotting ---")

# Check if the variables exist in the interactive session's memory
if 'monthly_clean' in locals() and isinstance(monthly_clean, pd.DataFrame):
    # Check if the fair value columns were added (e.g., from a previous OLS run if you adapt this later)
    plot_cols = ['price_usd']
    if 'fair_price_ext' in monthly_clean.columns:
        plot_cols.append('fair_price_ext')
    if 'fair_price_base' in monthly_clean.columns:
        plot_cols.append('fair_price_base')

    if len(plot_cols) > 1:
        logging.info(f"Plotting columns: {plot_cols}")
        try:
            monthly_clean[plot_cols].plot(figsize=(12, 6), logy=True,
                                        title="Monthly ETH Price vs Model Fair Values (Log Scale)")
            plt.ylabel("Price (USD Log Scale)")
            plt.xlabel("Date")
            plt.grid(True, which='both', linestyle='--', linewidth=0.5)
            plt.show() # This command tells matplotlib to display the plot
            print("Plot generated.")
        except Exception as e:
             logging.error(f"Failed to generate plot: {e}", exc_info=True)
             print(f"ERROR: Plotting failed: {e}")
    else:
        logging.warning("Fair value columns not found in monthly_clean DataFrame. Plotting only actual price.")
        try:
            monthly_clean['price_usd'].plot(figsize=(12, 6), logy=True, title="Monthly ETH Price (Log Scale)")
            plt.ylabel("Price (USD Log Scale)")
            plt.xlabel("Date")
            plt.grid(True, which='both', linestyle='--', linewidth=0.5)
            plt.show()
            print("Plot generated (actual price only).")
        except Exception as e:
             logging.error(f"Failed to generate price plot: {e}", exc_info=True)
             print(f"ERROR: Plotting price failed: {e}")

else:
    logging.warning("monthly_clean DataFrame not found in interactive session memory.")
    print("ERROR: 'monthly_clean' not loaded. Run the previous cell first.")

print("\nCell execution finished.") 