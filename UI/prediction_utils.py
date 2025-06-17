import pandas as pd
from firebase_admin import db
from datetime import datetime
from prophet import Prophet
from statsmodels.tsa.arima.model import ARIMA
import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error

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

def _fill_missing_periods(df, date_col, value_col, freq='W'):
    df = df.copy()
    df = df.set_index(date_col).sort_index()
    df = df.resample(freq).sum().asfreq(freq, fill_value=0)
    df = df.reset_index()
    return df

def _print_backtest_metrics(y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    print(f"[DEBUG] Backtest MAE: {mae:.2f}, RMSE: {rmse:.2f}")
    return mae, rmse

def prophet_forecast(df, periods=1, freq='W'):
    """
    Run Prophet ML forecast on filtered order data.
    Returns None if not enough valid data or on error.
    """
    if df is None or df.empty or len(df) < 2:
        print("[DEBUG] Not enough data for Prophet forecast.")
        return None
    df = df.copy()
    df = df.dropna(subset=['date', 'amount'])
    df = df[df['amount'] >= 0]  # allow zero, remove negative
    df = _fill_missing_periods(df, 'date', 'amount', freq)
    prophet_df = df.rename(columns={'date': 'ds', 'amount': 'y'})
    prophet_df = prophet_df[['ds', 'y']]
    if len(prophet_df) < 2:
        print("[DEBUG] Not enough data after filling for Prophet forecast.")
        return None
    try:
        m = Prophet()
        m.fit(prophet_df)
        # Backtest: predict last 2 points and compare
        if len(prophet_df) > 4:
            hist = prophet_df[:-2]
            m_hist = Prophet()
            m_hist.fit(hist)
            future_hist = m_hist.make_future_dataframe(periods=2, freq=freq)
            forecast_hist = m_hist.predict(future_hist)
            y_true = prophet_df['y'].iloc[-2:]
            y_pred = forecast_hist['yhat'].iloc[-2:]
            _print_backtest_metrics(y_true, y_pred)
        future = m.make_future_dataframe(periods=periods, freq=freq)
        forecast = m.predict(future)
        print(f"[DEBUG] Prophet forecast output: {forecast[['ds','yhat','yhat_lower','yhat_upper']].tail(periods)}")
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)
    except Exception as e:
        print(f"Prophet error: {e}")
        return None

def prophet_revenue_forecast(df, periods=1, freq='W'):
    if df is None or df.empty or len(df) < 2:
        print("[DEBUG] Not enough data for Prophet revenue forecast.")
        return None
    df = df.copy()
    df = df.dropna(subset=['date', 'amount'])
    df = df[df['amount'] >= 0]
    df = _fill_missing_periods(df, 'date', 'amount', freq)
    prophet_df = df.rename(columns={'date': 'ds', 'amount': 'y'})
    prophet_df = prophet_df[['ds', 'y']]
    if len(prophet_df) < 2:
        print("[DEBUG] Not enough data after filling for Prophet revenue forecast.")
        return None
    try:
        m = Prophet()
        m.fit(prophet_df)
        future = m.make_future_dataframe(periods=periods, freq=freq)
        forecast = m.predict(future)
        print(f"[DEBUG] Prophet revenue forecast output: {forecast[['ds','yhat','yhat_lower','yhat_upper']].tail(periods)}")
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)
    except Exception as e:
        print(f"Prophet revenue error: {e}")
        return None

def prophet_profit_forecast(df, periods=1, freq='W'):
    if df is None or df.empty or len(df) < 2 or 'profit' not in df.columns:
        print("[DEBUG] Not enough data for Prophet profit forecast.")
        return None
    df = df.copy()
    df = df.dropna(subset=['date', 'profit'])
    df = df[df['profit'] >= 0]
    df = _fill_missing_periods(df, 'date', 'profit', freq)
    prophet_df = df.rename(columns={'date': 'ds', 'profit': 'y'})
    prophet_df = prophet_df[['ds', 'y']]
    if len(prophet_df) < 2:
        print("[DEBUG] Not enough data after filling for Prophet profit forecast.")
        return None
    try:
        m = Prophet()
        m.fit(prophet_df)
        future = m.make_future_dataframe(periods=periods, freq=freq)
        forecast = m.predict(future)
        print(f"[DEBUG] Prophet profit forecast output: {forecast[['ds','yhat','yhat_lower','yhat_upper']].tail(periods)}")
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)
    except Exception as e:
        print(f"Prophet profit error: {e}")
        return None

def prophet_returning_customers_forecast(df, periods=1, freq='W'):
    if df is None or df.empty or len(df) < 2 or 'customer_id' not in df.columns:
        print("[DEBUG] Not enough data for Prophet returning customers forecast.")
        return None
    df = df.copy()
    df = df.dropna(subset=['date', 'customer_id'])
    df['week'] = df['date'].dt.to_period('W').apply(lambda r: r.start_time)
    weekly = df.groupby('week')['customer_id'].apply(lambda x: x.duplicated().sum()).reset_index()
    weekly = weekly.rename(columns={'week': 'ds', 'customer_id': 'y'})
    weekly = _fill_missing_periods(weekly, 'ds', 'y', freq)
    if weekly.empty or len(weekly) < 2:
        print("[DEBUG] Not enough data after filling for Prophet returning customers forecast.")
        return None
    try:
        m = Prophet()
        m.fit(weekly)
        future = m.make_future_dataframe(periods=periods, freq=freq)
        forecast = m.predict(future)
        print(f"[DEBUG] Prophet returning customers forecast output: {forecast[['ds','yhat','yhat_lower','yhat_upper']].tail(periods)}")
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(periods)
    except Exception as e:
        print(f"Prophet returning customers error: {e}")
        return None

def prophet_product_forecast(df, product_id, periods=1, freq='W'):
    if df is None or df.empty or len(df) < 2 or 'product_id' not in df.columns:
        print("[DEBUG] Not enough data for Prophet product forecast.")
        return None
    df = df[df['product_id'] == product_id]
    df = df.dropna(subset=['date', 'amount'])
    df = df[df['amount'] >= 0]
    df = _fill_missing_periods(df, 'date', 'amount', freq)
    prophet_df = df.rename(columns={'date': 'ds', 'amount': 'y'})
    prophet_df = prophet_df[['ds', 'y']]
    if len(prophet_df) < 2:
        print("[DEBUG] Not enough data after filling for Prophet product forecast.")
        return None
    try:
        m = Prophet()
        m.fit(prophet_df)
        future = m.make_future_dataframe(periods=periods, freq=freq)
        forecast = m.predict(future)
        print(f"[DEBUG] Prophet product forecast output: {forecast[['ds','yhat','yhat_lower','yhat_upper']].tail(periods)}")
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