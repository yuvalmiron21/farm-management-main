import pandas as pd
from firebase_admin import db
from datetime import datetime
from prophet import Prophet
from statsmodels.tsa.arima.model import ARIMA
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import ParameterGrid
from prophet.diagnostics import cross_validation, performance_metrics
import logging

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] - %(message)s')

def get_order_history():
    """
    Fetches and merges order and order detail data from Firebase.
    This version uses a LEFT merge to be more robust, ensuring all orders are kept
    even if they lack detail entries.
    """
    # 1. Fetch Orders
    order_ref = db.reference('Order')
    orders = order_ref.get() or {}
    order_list = []
    for order_id, order_data in orders.items():
        order_list.append({
            'OrderID': order_id,
            'date': order_data.get('OrderDate'),
            'customer_id': order_data.get('CustomerID'),
            'status': order_data.get('Status'),
            'amount': float(order_data.get('TotalAmount', 0)) # Use TotalAmount as default
        })
    if not order_list:
        return pd.DataFrame()
    df_orders = pd.DataFrame(order_list)
    df_orders['date'] = pd.to_datetime(df_orders['date'], errors='coerce')

    # 2. Fetch OrderDetails
    detail_ref = db.reference('OrderDetail')
    details = detail_ref.get() or {}
    detail_list = []
    if details: # Only process if details exist
        for detail_id, detail_data in details.items():
            detail_list.append({
                'OrderID': detail_data.get('OrderID'),
                'product_id': detail_data.get('ProductID'),
                'quantity': float(detail_data.get('Quantity', 0)),
                # Calculate detail amount, will be used to create a more accurate total amount
                'detail_amount': float(detail_data.get('Quantity', 0)) * float(detail_data.get('UnitPrice', 0))
            })
    
    if not detail_list:
        # If no details, return the orders DataFrame as is.
        return df_orders.dropna(subset=['date'])

    df_details = pd.DataFrame(detail_list)
    
    # Sum details per order to get a new total amount based on details
    df_details_sum = df_details.groupby('OrderID').agg(
        product_id_list=('product_id', lambda x: list(x)),
        total_detail_amount=('detail_amount', 'sum')
    ).reset_index()

    # 3. Merge orders with details using a LEFT join
    df_merged = pd.merge(df_orders, df_details_sum, on='OrderID', how='left')

    # If detail amount is available and greater than 0, use it. Otherwise, keep original order amount.
    df_merged['amount'] = df_merged['total_detail_amount'].where(df_merged['total_detail_amount'] > 0, df_merged['amount'])
    
    # Explode the DataFrame to have one row per product for orders with multiple products
    # First, handle cases where product_id_list might be NaN (for orders without details)
    df_merged['product_id_list'] = df_merged['product_id_list'].apply(lambda d: d if isinstance(d, list) else [])
    # For product-specific forecasts, we need a row per product.
    # We will create a new df for that, but for general forecasts, we use the aggregated one.
    # The current implementation of product forecast expects a single product_id column.
    # This requires a more significant change. For now, let's make a simple explode.
    df_final = df_merged.explode('product_id_list').rename(columns={'product_id_list': 'product_id'})

    # Clean up and return
    df_final = df_final.drop(columns=['total_detail_amount'])
    return df_final.dropna(subset=['date'])

def get_unique_customers_and_statuses():
    df = get_order_history()
    customers = sorted(df['customer_id'].dropna().unique())
    statuses = sorted(df['status'].dropna().unique())
    return customers, statuses

def filter_orders(df, customer_id=None, status=None, start_date=None, end_date=None):
    if customer_id and customer_id != 'All':
        df = df[df['customer_id'] == customer_id]
    if status and status != 'All':
        df = df[df['status'] == status]
    if start_date:
        df = df[df['date'] >= pd.to_datetime(start_date)]
    if end_date:
        df = df[df['date'] <= pd.to_datetime(end_date)]
    return df

def predict_orders(df, period_weeks=4):
    if df.empty:
        return 0
    df = df.set_index('date').resample('W').sum()
    return df['amount'].tail(period_weeks).mean()

def get_weekly_production(df):
    if df.empty:
        return pd.DataFrame()
    df = df.set_index('date').resample('W').sum()
    return df

def _fill_missing_periods(df, date_col, value_col, freq='W'):
    df = df.copy()
    df = df.set_index(date_col).sort_index()
    df = df.resample(freq).sum().asfreq(freq, fill_value=0)
    df = df.reset_index()
    return df

def _run_prophet_forecast(model, prophet_df, periods, freq):
    """Helper to run model and return forecast."""
    model.fit(prophet_df)
    future = model.make_future_dataframe(periods=periods, freq=freq)
    forecast = model.predict(future)
    return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)

def generate_forecast(df, date_col, value_col, periods=1, freq='W'):
    """
    Generates an advanced forecast using Prophet, including hyperparameter tuning and cross-validation.
    """
    if df is None or df.empty or len(df) < 10:  # Increased minimum data size for robust CV
        logging.warning(f"Not enough data for forecast on value '{value_col}'. Need at least 10 data points, have {len(df)}.")
        return None

    df = df.copy()
    df = df.dropna(subset=[date_col, value_col])
    if value_col in ['amount', 'profit']:
        df = df[df[value_col] >= 0]
    
    df = _fill_missing_periods(df, date_col, value_col, freq)
    prophet_df = df.rename(columns={date_col: 'ds', value_col: 'y'})
    prophet_df = prophet_df[['ds', 'y']]

    if len(prophet_df) < 10:
        logging.warning(f"Not enough data after processing for forecast on value '{value_col}'. Need at least 10 data points, have {len(prophet_df)}.")
        return None

    # --- Smart Forecasting Strategy ---
    if len(prophet_df) > 26:
        logging.info(f"Large dataset ({len(prophet_df)} points) for '{value_col}'. Skipping CV for performance.")
        try:
            model = Prophet(yearly_seasonality=True)
            return _run_prophet_forecast(model, prophet_df, periods, freq)
        except Exception as e:
            logging.error(f"Forecast failed for large dataset on value '{value_col}': {e}")
            return None

    # For smaller datasets, proceed with hyperparameter tuning.
    logging.info(f"Smaller dataset ({len(prophet_df)} points) for '{value_col}'. Starting hyperparameter tuning.")
    param_grid = {
        'changepoint_prior_scale': [0.01, 0.1, 0.5],
        'seasonality_prior_scale': [0.1, 1.0, 10.0],
        'seasonality_mode': ['additive', 'multiplicative'],
    }
    grid = ParameterGrid(param_grid)
    best_params = {}
    best_mae = float('inf')

    initial_period = f'{max(90, len(prophet_df) - 10 * 7)} days'
    period = '30 days'
    horizon = f'{periods * 7} days'

    for params in grid:
        try:
            m = Prophet(**params)
            m.fit(prophet_df)
            df_cv = cross_validation(m, initial=initial_period, period=period, horizon=horizon, parallel=None)
            df_p = performance_metrics(df_cv, rolling_window=1)
            mae = df_p['mae'].values[0]
            if mae < best_mae:
                best_mae = mae
                best_params = params
        except Exception as e:
            logging.warning(f"CV failed for params {params} on value '{value_col}': {e}")
            continue

    if not best_params:
        logging.error(f"Hyperparameter tuning failed for '{value_col}'. Using default.")
        best_params = {'changepoint_prior_scale': 0.1, 'seasonality_prior_scale': 1.0, 'seasonality_mode': 'additive'}

    logging.info(f"Best params for '{value_col}': {best_params} (MAE: {best_mae:.2f})")

    try:
        final_model = Prophet(**best_params)
        return _run_prophet_forecast(final_model, prophet_df, periods, freq)
    except Exception as e:
        logging.error(f"Final forecast failed for value '{value_col}': {e}")
        return None

def prophet_forecast(df, periods=1, freq='W'):
    """
    Run Prophet ML forecast on filtered order data.
    Now uses the advanced generate_forecast function.
    """
    return generate_forecast(df, date_col='date', value_col='amount', periods=periods, freq=freq)

def prophet_revenue_forecast(df, periods=1, freq='W'):
    """
    Run Prophet ML forecast on revenue data.
    Now uses the advanced generate_forecast function.
    """
    return generate_forecast(df, date_col='date', value_col='amount', periods=periods, freq=freq)

def prophet_profit_forecast(df, periods=1, freq='W'):
    """
    Run Prophet ML forecast on profit data.
    Now uses the advanced generate_forecast function.
    """
    return generate_forecast(df, date_col='date', value_col='profit', periods=periods, freq=freq)

def prophet_returning_customers_forecast(df, periods=1, freq='W'):
    if df is None or df.empty or len(df) < 2 or 'customer_id' not in df.columns:
        logging.warning("Not enough data for returning customers forecast.")
        return None
    
    df = df.copy()
    df = df.dropna(subset=['date', 'customer_id'])
    
    df['week_start'] = df['date'].dt.to_period('W').apply(lambda p: p.start_time)
    
    # Get unique customers per week
    weekly_customers = df.groupby('week_start')['customer_id'].unique().apply(set).reset_index()
    weekly_customers = weekly_customers.sort_values('week_start').reset_index(drop=True)

    returning_counts = []
    seen_customers = set()

    for index, row in weekly_customers.iterrows():
        current_week_customers = row['customer_id']
        
        # Customers returning this week are those seen in previous weeks
        returning_this_week = seen_customers.intersection(current_week_customers)
        
        returning_counts.append({
            'date': row['week_start'],
            'returning_customers': len(returning_this_week)
        })
        
        # Add current week's customers to the set of seen customers for next iterations
        seen_customers.update(current_week_customers)
        
    if not returning_counts:
        logging.warning("No returning customer data to generate forecast.")
        return None
        
    weekly_returning_df = pd.DataFrame(returning_counts)

    return generate_forecast(weekly_returning_df, date_col='date', value_col='returning_customers', periods=periods, freq=freq)

def prophet_product_forecast(df, product_id, periods=1, freq='W'):
    if df is None or df.empty or 'product_id' not in df.columns:
        logging.warning(f"Not enough data for product forecast for product_id: {product_id}.")
        return None
        
    df_product = df[df['product_id'] == product_id].copy()
    if df_product.empty:
        logging.warning(f"No data for product_id: {product_id}.")
        return None

    return generate_forecast(df_product, date_col='date', value_col='amount', periods=periods, freq=freq)

def get_product_list():
    df = get_order_history()
    if 'product_id' in df.columns:
        return sorted(df['product_id'].dropna().unique())
    return []

def arima_forecast(df, periods=1):
    if df is None or df.empty or len(df) < 6:
        print("[DEBUG] Not enough data for ARIMA forecast.")
        return None
    df = df.copy()
    df = df.dropna(subset=['date', 'amount'])
    df = df.set_index('date').resample('W').sum().asfreq('W', fill_value=0)
    try:
        model = ARIMA(df['amount'], order=(1,1,1))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=periods)
        print(f"[DEBUG] ARIMA forecast output: {forecast}")
        return forecast
    except Exception as e:
        print(f'ARIMA error: {e}')
        return None 