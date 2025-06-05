import pandas as pd
from firebase_admin import db
from datetime import datetime
from prophet import Prophet
from statsmodels.tsa.arima.model import ARIMA

def get_order_history():
    ref = db.reference('Order')
    orders = ref.get() or {}
    data = []
    for order in orders.values():
        data.append({
            'date': order.get('OrderDate'),
            'amount': float(order.get('TotalAmount', 0)),
            'customer_id': order.get('CustomerID', None),
            'status': order.get('Status', None)
        })
    df = pd.DataFrame(data)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    return df

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

def prophet_forecast(df, periods=1, freq='W'):
    """
    Run Prophet ML forecast on filtered order data.
    Returns None if not enough valid data or on error.
    """
    # Check for valid DataFrame and enough data
    if df is None or df.empty or len(df) < 3:
        return None
    df = df.copy()
    # Drop rows with missing or invalid values
    df = df.dropna(subset=['date', 'amount'])
    # Remove non-positive values (if not logical for your case)
    df = df[df['amount'] > 0]
    if df.empty or len(df) < 3:
        return None
    # Prophet expects columns: ds (date), y (value)
    prophet_df = df.rename(columns={'date': 'ds', 'amount': 'y'})
    prophet_df = prophet_df[['ds', 'y']]
    # Final check for NaN or inf
    if prophet_df['y'].isnull().any() or prophet_df['ds'].isnull().any() or not prophet_df['y'].apply(lambda x: isinstance(x, (int, float))).all():
        return None
    try:
        m = Prophet()
        m.fit(prophet_df)
        future = m.make_future_dataframe(periods=periods, freq=freq)
        forecast = m.predict(future)
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)
    except Exception as e:
        print(f"Prophet error: {e}")
        return None

def prophet_revenue_forecast(df, periods=1, freq='W'):
    """Forecast total revenue for the next period using Prophet."""
    if df is None or df.empty or len(df) < 3:
        return None
    df = df.copy()
    df = df.dropna(subset=['date', 'amount'])
    df = df[df['amount'] > 0]
    if df.empty or len(df) < 3:
        return None
    prophet_df = df.rename(columns={'date': 'ds', 'amount': 'y'})
    prophet_df = prophet_df[['ds', 'y']]
    try:
        m = Prophet()
        m.fit(prophet_df)
        future = m.make_future_dataframe(periods=periods, freq=freq)
        forecast = m.predict(future)
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)
    except Exception as e:
        print(f"Prophet revenue error: {e}")
        return None

def prophet_profit_forecast(df, periods=1, freq='W'):
    """Forecast profit for the next period using Prophet."""
    if df is None or df.empty or len(df) < 3 or 'profit' not in df.columns:
        return None
    df = df.copy()
    df = df.dropna(subset=['date', 'profit'])
    df = df[df['profit'] > 0]
    if df.empty or len(df) < 3:
        return None
    prophet_df = df.rename(columns={'date': 'ds', 'profit': 'y'})
    prophet_df = prophet_df[['ds', 'y']]
    try:
        m = Prophet()
        m.fit(prophet_df)
        future = m.make_future_dataframe(periods=periods, freq=freq)
        forecast = m.predict(future)
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)
    except Exception as e:
        print(f"Prophet profit error: {e}")
        return None

def prophet_returning_customers_forecast(df, periods=1, freq='W'):
    """Forecast number of returning customers for the next period using Prophet."""
    if df is None or df.empty or len(df) < 3 or 'customer_id' not in df.columns:
        return None
    df = df.copy()
    df = df.dropna(subset=['date', 'customer_id'])
    # Count returning customers per week
    df['week'] = df['date'].dt.to_period('W').apply(lambda r: r.start_time)
    weekly = df.groupby('week')['customer_id'].apply(lambda x: x.duplicated().sum()).reset_index()
    weekly = weekly.rename(columns={'week': 'ds', 'customer_id': 'y'})
    if weekly.empty or len(weekly) < 3:
        return None
    try:
        m = Prophet()
        m.fit(weekly)
        future = m.make_future_dataframe(periods=periods, freq=freq)
        forecast = m.predict(future)
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)
    except Exception as e:
        print(f"Prophet returning customers error: {e}")
        return None

def prophet_product_forecast(df, product_id, periods=1, freq='W'):
    """Forecast order amount for a specific product for the next period using Prophet."""
    if df is None or df.empty or len(df) < 3 or 'product_id' not in df.columns:
        return None
    df = df[df['product_id'] == product_id]
    df = df.dropna(subset=['date', 'amount'])
    df = df[df['amount'] > 0]
    if df.empty or len(df) < 3:
        return None
    prophet_df = df.rename(columns={'date': 'ds', 'amount': 'y'})
    prophet_df = prophet_df[['ds', 'y']]
    try:
        m = Prophet()
        m.fit(prophet_df)
        future = m.make_future_dataframe(periods=periods, freq=freq)
        forecast = m.predict(future)
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)
    except Exception as e:
        print(f"Prophet product error: {e}")
        return None

def get_product_list():
    df = get_order_history()
    if 'product_id' in df.columns:
        return sorted(df['product_id'].dropna().unique())
    return []

def arima_forecast(df, periods=1):
    """
    Forecast order amount for the next period using ARIMA.
    Returns a pandas Series with the forecast.
    """
    if df is None or df.empty or len(df) < 10:
        return None
    df = df.copy()
    df = df.dropna(subset=['date', 'amount'])
    df = df.set_index('date').resample('W').sum()
    try:
        model = ARIMA(df['amount'], order=(1,1,1))
        model_fit = model.fit()
        forecast = model_fit.forecast(steps=periods)
        return forecast
    except Exception as e:
        print(f'ARIMA error: {e}')
        return None 