import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import io
import base64
from typing import List, Dict, Tuple, Optional
import seaborn as sns
from models.Log import Batch, Log
import logging
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.inspection import permutation_importance
import re
from io import BytesIO
import json

class InsightsEngine:
    """
    Analyzes farm data to generate actionable insights using ML techniques.
    """
    def __init__(self, batches, logs):
        """Initialize the insights engine with batch and log data"""
        self.batches = batches
        self.logs = logs
        self.insights = []
        self.models = {}
        self.feature_importance = {}
        self.optimal_conditions = {}
        self.ready = False
        
        # Check if we have valid data
        if not self.batches or not self.logs:
            print("InsightsEngine initialized with empty data")
            self.has_yield_data = False
            return
            
        # Try to convert a sample log to see if it has harvest data
        if isinstance(self.logs, list) and len(self.logs) > 0:
            sample_log = self.logs[0]
            if hasattr(sample_log, 'harvest') and sample_log.harvest is not None:
                self.has_yield_data = True
            else:
                self.has_yield_data = False
        else:
            self.has_yield_data = False
            
        print(f"InsightsEngine initialized with {len(self.batches)} batches and {len(self.logs)} logs")
        
    def generate_insights(self):
        """Generate insights from the data"""
        try:
            # Clear previous insights
            self.insights = []
            
            # Prepare the data
            df = self.prepare_data_for_analysis()
            
            if df.empty:
                self.insights.append({
                    'type': 'warning',
                    'title': 'Insufficient Data',
                    'description': 'Not enough data available for analysis. Please log more batches and harvests.'
                })
                self.ready = True
                return False
            
            # Run analysis methods
            self.analyze_yield_factors()
            self.find_optimal_conditions()
            self.analyze_growth_timeline()
            self.analyze_seasonal_patterns()
            self.analyze_bagging_impact()
            
            # If we have no insights, add a default message
            if not self.insights:
                self.insights.append({
                    'type': 'warning',
                    'title': 'Analysis In Progress',
                    'description': 'Continue adding more batch data for meaningful insights.'
                })
            
            self.ready = True
            return True
        except Exception as e:
            print(f"Error generating insights: {str(e)}")
            self.insights.append({
                'type': 'warning',
                'title': 'Analysis Error',
                'description': f'An error occurred during analysis. Please try again later.'
            })
            self.ready = True
            return False
        
    def analyze_yield_factors(self):
        """Analyze factors that influence yield"""
        try:
            # Prepare data for analysis
            df = self.prepare_data_for_analysis()
            
            if df.empty or len(df) < 5:
                self.insights.append({
                    'type': 'warning',
                    'title': 'Insufficient Data for Analysis',
                    'description': 'Not enough batch data is available for meaningful analysis. Please add more data.'
                })
                return
                
            # Calculate total harvest per batch (convert to kg for display)
            batch_yield = df.groupby('batch_id')['weight'].sum().reset_index()
            batch_yield.rename(columns={'weight': 'total_yield'}, inplace=True)
            
            # Get available columns
            available_columns = ['batch_id', 'mushroom_type']
            for col in ['temperature', 'humidity', 'light']:
                if col in df.columns:
                    available_columns.append(col)
            
            # Merge with original data to get batch properties
            yield_data = pd.merge(batch_yield, df[available_columns].drop_duplicates(), on='batch_id')
            
            # If we have fewer than 5 complete batches, don't do the analysis
            if yield_data['batch_id'].nunique() < 5:
                self.insights.append({
                    'type': 'warning',
                    'title': 'Insufficient Batch Data',
                    'description': 'At least 5 completed batches are needed for reliable yield analysis. Currently analyzing based on limited data.'
                })
            
            # Analyze environmental factors
            for factor in ['temperature', 'humidity', 'co2']:
                if factor in yield_data.columns and not yield_data[factor].isna().all():
                    # Only proceed if we have meaningful data
                    if yield_data[factor].nunique() > 1:
                        # Simple correlation
                        corr = yield_data[['total_yield', factor]].corr().iloc[0, 1]
                        
                        if abs(corr) > 0.3:
                            direction = "positively" if corr > 0 else "negatively"
                            strength = "strongly" if abs(corr) > 0.7 else "moderately"
                            self.insights.append({
                                'type': 'yield_factor',
                                'title': f'{factor.title()} Impact on Yield',
                                'description': f'{factor.title()} is {strength} {direction} correlated with yield (correlation: {corr:.2f})'
                            })
            
            # Analyze mushroom type differences in yield
            if 'mushroom_type' in yield_data.columns and yield_data['mushroom_type'].nunique() > 1:
                type_yield = yield_data.groupby('mushroom_type', observed=True)['total_yield'].mean().sort_values(ascending=False)
                
                if not type_yield.empty:
                    best_type = type_yield.index[0]
                    self.insights.append({
                        'type': 'yield_factor',
                        'title': 'Highest Yielding Mushroom Type',
                        'description': f'{best_type} has the highest average yield at {type_yield.iloc[0]/1000:.2f}kg per batch.'
                    })
        except Exception as e:
            print(f"Error in analyze_yield_factors: {str(e)}")
            self.insights.append({
                'type': 'warning',
                'title': 'Analysis Error',
                'description': f'An error occurred during yield factor analysis: {str(e)}'
            })
    
    def find_optimal_conditions(self):
        """Find optimal environmental conditions for mushroom growth"""
        try:
            # Prepare data for analysis
            df = self.prepare_data_for_analysis()
            
            if df.empty or len(df) < 5:
                return
                
            # Calculate total harvest per batch
            batch_yield = df.groupby('batch_id')['weight'].sum().reset_index()
            batch_yield.rename(columns={'weight': 'total_yield'}, inplace=True)
            
            # Map our environmental variable names to data columns
            env_factors = {
                'temperature': 'air_temp',  # Use air_temp as temperature
                'humidity': 'humidity',
                'light': None  # We don't have light data
            }
            
            # Find optimal temperature
            if 'air_temp' in df.columns and not df['air_temp'].isna().all():
                # Group by batch and get average temperature
                temp_by_batch = df.groupby('batch_id')['air_temp'].mean().reset_index()
                temp_by_batch.rename(columns={'air_temp': 'temperature'}, inplace=True)
                
                # Merge with yield data
                temp_data = pd.merge(batch_yield, temp_by_batch, on='batch_id')
                
                if len(temp_data) >= 3:
                    # Group by temperature ranges
                    temp_data['temp_range'] = pd.cut(temp_data['temperature'], bins=5)
                    temp_yield = temp_data.groupby('temp_range', observed=True)['total_yield'].mean().reset_index()
                    
                    if not temp_yield.empty:
                        best_temp_range = temp_yield.loc[temp_yield['total_yield'].idxmax()]['temp_range']
                        
                        # Extract midpoint of the range
                        mid_temp = (best_temp_range.left + best_temp_range.right) / 2
                        
                        self.insights.append({
                            'type': 'optimal_condition',
                            'title': 'Optimal Temperature',
                            'description': f'Maintain temperature around {mid_temp:.1f}°C for best yields.'
                        })
            
            # Find optimal humidity
            if 'humidity' in df.columns and not df['humidity'].isna().all():
                # Group by batch and get average humidity
                humidity_by_batch = df.groupby('batch_id')['humidity'].mean().reset_index()
                
                # Merge with yield data
                humidity_data = pd.merge(batch_yield, humidity_by_batch, on='batch_id')
                
                if len(humidity_data) >= 3:
                    # Group by humidity ranges
                    humidity_data['humidity_range'] = pd.cut(humidity_data['humidity'], bins=5)
                    humidity_yield = humidity_data.groupby('humidity_range', observed=True)['total_yield'].mean().reset_index()
                    
                    if not humidity_yield.empty:
                        best_humidity_range = humidity_yield.loc[humidity_yield['total_yield'].idxmax()]['humidity_range']
                        
                        # Extract midpoint of the range
                        mid_humidity = (best_humidity_range.left + best_humidity_range.right) / 2
                        
                        self.insights.append({
                            'type': 'optimal_condition',
                            'title': 'Optimal Humidity',
                            'description': f'Maintain humidity around {mid_humidity:.1f}% for best results.'
                        })
            
            # Find optimal CO2 conditions
            if 'co2' in df.columns and not df['co2'].isna().all():
                # Group by batch and get average CO2
                co2_by_batch = df.groupby('batch_id')['co2'].mean().reset_index()
                
                # Normalize CO2 values if they're unusually high or low
                co2_mean = co2_by_batch['co2'].mean()
                if co2_mean < 10:  # too low, might be in thousands of ppm
                    co2_by_batch['co2'] = co2_by_batch['co2'] * 1000
                elif co2_mean > 10000:  # too high, might be in raw values
                    co2_by_batch['co2'] = co2_by_batch['co2'] / 1000
                
                # Merge with yield data
                co2_data = pd.merge(batch_yield, co2_by_batch, on='batch_id')
                
                if len(co2_data) >= 3:
                    # Group by CO2 ranges
                    co2_data['co2_range'] = pd.cut(co2_data['co2'], bins=5)
                    co2_yield = co2_data.groupby('co2_range', observed=True)['total_yield'].mean().reset_index()
                    
                    if not co2_yield.empty:
                        best_co2_range = co2_yield.loc[co2_yield['total_yield'].idxmax()]['co2_range']
                        
                        # Extract midpoint of the range
                        mid_co2 = (best_co2_range.left + best_co2_range.right) / 2
                        
                        self.insights.append({
                            'type': 'optimal_condition',
                            'title': 'Optimal CO2 Levels',
                            'description': f'Maintain CO2 levels around {mid_co2:.0f} ppm for optimal growth.'
                        })
        except Exception as e:
            print(f"Error finding optimal conditions: {str(e)}")
            
    def analyze_growth_timeline(self):
        """Analyze the growth timeline and harvest patterns"""
        try:
            # Prepare data for analysis
            df = self.prepare_data_for_analysis()
            
            if df.empty or len(df) < 5:
                return
                
            # If we have timestamps, analyze time to harvest
            if 'created_at' in df.columns and 'timestamp' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
                df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
                
                # Filter to only include harvests with valid weights
                harvest_df = df[df['weight'] > 0].copy()
                
                if harvest_df.empty:
                    return
                
                # Calculate days from batch creation to harvest, with sanity checks
                harvest_df['days_to_harvest'] = (harvest_df['timestamp'] - harvest_df['created_at']).dt.days
                
                # Filter out unrealistic values (more than 100 days or negative)
                harvest_df = harvest_df[(harvest_df['days_to_harvest'] > 0) & 
                                        (harvest_df['days_to_harvest'] < 100)]
                
                if harvest_df.empty:
                    return
                
                # Group by batch and find first harvest
                batch_first_harvest = harvest_df.groupby('batch_id')['days_to_harvest'].min().reset_index()
                
                if len(batch_first_harvest) >= 3:
                    avg_days = batch_first_harvest['days_to_harvest'].mean()
                    
                    self.insights.append({
                        'type': 'harvesting',
                        'title': 'Time to First Harvest',
                        'description': f'On average, first harvests occur {avg_days:.1f} days after batch creation.'
                    })
        except Exception as e:
            print(f"Error analyzing growth timeline: {str(e)}")
            
    def analyze_seasonal_patterns(self):
        """Analyze seasonal patterns in yield"""
        try:
            # Prepare data for analysis
            df = self.prepare_data_for_analysis()
            
            if df.empty or len(df) < 10:  # Need more data for seasonal analysis
                return
                
            # If we have timestamps, analyze seasonal patterns
            if 'created_at' in df.columns:
                df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
                
                # Extract month from timestamp
                df['month'] = df['created_at'].dt.month
                
                # Calculate total harvest per batch
                batch_yield = df.groupby(['batch_id', 'month'])['weight'].sum().reset_index()
                
                # Group by month and calculate average yield
                monthly_yield = batch_yield.groupby('month')['weight'].mean().reset_index()
                
                if len(monthly_yield) >= 3:
                    # Find best month
                    best_month_idx = monthly_yield['weight'].idxmax()
                    best_month = monthly_yield.loc[best_month_idx]['month']
                    best_yield = monthly_yield.loc[best_month_idx]['weight']
                    
                    # Convert month number to name
                    month_names = {
                        1: 'January', 2: 'February', 3: 'March', 4: 'April',
                        5: 'May', 6: 'June', 7: 'July', 8: 'August',
                        9: 'September', 10: 'October', 11: 'November', 12: 'December'
                    }
                    
                    month_name = month_names.get(best_month, f"Month {best_month}")
                    
                    self.insights.append({
                        'type': 'seasonal',
                        'title': 'Seasonal Yield Patterns',
                        'description': f'Batches started in {month_name} show the highest average yields ({best_yield/1000:.2f}kg).'
                    })
        except Exception as e:
            print(f"Error analyzing seasonal patterns: {str(e)}")
            
    def analyze_bagging_impact(self):
        """Analyze impact of bagging on mushroom growth"""
        try:
            # This is a placeholder for future implementation
            # When bagging data becomes available, implement analysis here
            pass
        except Exception as e:
            print(f"Error analyzing bagging impact: {str(e)}")

    def get_insights(self, top_n=None, insight_type=None):
        """Get insights, optionally filtered by type and limited to top_n"""
        try:
            if not self.ready:
                self.generate_insights()
                
            # Filter by type if specified
            if insight_type:
                filtered_insights = [i for i in self.insights if i['type'] == insight_type]
            else:
                filtered_insights = self.insights
                
            # Limit to top_n if specified
            if top_n and isinstance(top_n, int) and top_n > 0:
                return filtered_insights[:top_n]
            else:
                return filtered_insights
        except Exception as e:
            print(f"Error getting insights: {str(e)}")
            return []
        
    def get_summary_text(self):
        """Get a summary of all insights"""
        try:
            if not self.insights:
                return "Not enough data available for meaningful insights. Continue adding batch data to receive operational recommendations."
            
            yield_insights = [i for i in self.insights if i['type'] == 'yield_factor']
            optimal_insights = [i for i in self.insights if i['type'] == 'optimal_condition']
            warning_insights = [i for i in self.insights if i['type'] == 'warning']
            
            summary = "Farm Performance Insights Summary:\n\n"
            
            # Add warning if present
            if warning_insights:
                summary += f"⚠️ {warning_insights[0]['description']}\n\n"
            
            # Add yield factors
            if yield_insights:
                top_yield_factor = yield_insights[0]
                summary += f"🔍 {top_yield_factor['title']}: {top_yield_factor['description']}\n\n"
            
            # Add optimal conditions if available
            optimal_temp = optimal_humidity = optimal_co2 = None
            
            for insight in optimal_insights:
                desc = insight['description'].lower()
                
                try:
                    if 'temperature' in desc or 'temp' in desc:
                        match = re.search(r'(\d+\.?\d*)', desc)
                        if match:
                            optimal_temp = match.group(1)
                    elif 'humidity' in desc:
                        match = re.search(r'(\d+\.?\d*)', desc)
                        if match:
                            optimal_humidity = match.group(1)
                    elif 'co2' in desc:
                        match = re.search(r'(\d+\.?\d*)', desc)
                        if match:
                            optimal_co2 = match.group(1)
                except Exception as e:
                    print(f"Error extracting condition from insight: {str(e)}")
            
            if any([optimal_temp, optimal_humidity, optimal_co2]):
                summary += "🌱 Optimal growing conditions: "
                conditions = []
                
                if optimal_temp:
                    conditions.append(f"Temperature: {optimal_temp}°C")
                if optimal_humidity:
                    conditions.append(f"Humidity: {optimal_humidity}%")
                if optimal_co2:
                    conditions.append(f"CO2: {optimal_co2} ppm")
                
                summary += ", ".join(conditions) + "\n\n"
            
            # Add guidance
            guidance_insights = [i for i in self.insights if i['type'] == 'guidance']
            if guidance_insights:
                summary += f"💡 Key recommendation: {guidance_insights[0]['description']}\n\n"
            
            harvest_insights = [i for i in self.insights if i['type'] == 'harvesting']
            if harvest_insights:
                summary += f"🍄 {harvest_insights[0]['title']}: {harvest_insights[0]['description']}\n\n"
                
            summary += "Explore the tabs below for detailed insights and recommendations."
            return summary
        except Exception as e:
            print(f"Error generating summary text: {str(e)}")
            return "Analysis complete. Explore the tabs below for insights."

    def get_features_plot(self):
        """Generate a feature importance plot"""
        try:
            # Prepare data for analysis
            df = self.prepare_data_for_analysis()
            
            if df.empty or len(df) < 5 or df['batch_id'].nunique() < 3:
                return None
                
            # Calculate total harvest per batch
            batch_yield = df.groupby('batch_id')['weight'].sum().reset_index()
            batch_yield.rename(columns={'weight': 'total_yield'}, inplace=True)
            
            # Prepare feature data by aggregating by batch
            feature_columns = {
                'air_temp': 'Temperature',
                'substrate_temp': 'Substrate Temp',
                'humidity': 'Humidity',
                'co2': 'CO2'
            }
            
            feature_data = []
            for batch_id in df['batch_id'].unique():
                batch_df = df[df['batch_id'] == batch_id]
                
                batch_features = {'batch_id': batch_id}
                
                # Add mushroom type if available
                if 'mushroom_type' in batch_df.columns:
                    mtype = batch_df['mushroom_type'].iloc[0] if not batch_df['mushroom_type'].isna().all() else None
                    batch_features['mushroom_type'] = mtype
                
                # Calculate mean for each numerical feature
                for col, display_name in feature_columns.items():
                    if col in batch_df.columns and not batch_df[col].isna().all():
                        batch_features[col] = batch_df[col].mean()
                
                feature_data.append(batch_features)
            
            # Convert to DataFrame
            features_df = pd.DataFrame(feature_data)
            
            # Merge with yield data
            yield_data = pd.merge(batch_yield, features_df, on='batch_id')
            
            if len(yield_data) < 5:
                return None
                
            # One-hot encode categorical variables
            if 'mushroom_type' in yield_data.columns and yield_data['mushroom_type'].nunique() > 1:
                yield_data = pd.get_dummies(yield_data, columns=['mushroom_type'], drop_first=True)
            
            # Select features
            feature_cols = [col for col in yield_data.columns 
                           if col not in ['batch_id', 'total_yield', 'created_at'] 
                           and not yield_data[col].isna().all()]
            
            if not feature_cols:
                return None
                
            X = yield_data[feature_cols]
            y = yield_data['total_yield']
            
            # Fill NaN values with mean
            X = X.fillna(X.mean())
            
            # Fit a random forest regressor
            model = RandomForestRegressor(n_estimators=50, random_state=42)
            try:
                model.fit(X, y)
            except Exception as e:
                print(f"Error fitting model: {str(e)}")
                return None
            
            # Get feature importances
            importances = model.feature_importances_
            indices = np.argsort(importances)[::-1]
            
            # Plot feature importances
            plt.figure(figsize=(10, 6))
            plt.title('Feature Importances for Yield')
            plt.bar(range(X.shape[1]), importances[indices], align='center')
            plt.xticks(range(X.shape[1]), [X.columns[i] for i in indices], rotation=45)
            plt.tight_layout()
            
            # Convert plot to base64 string
            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            image_png = buffer.getvalue()
            buffer.close()
            
            plt.close()
            
            return base64.b64encode(image_png).decode('utf-8')
        except Exception as e:
            print(f"Error generating features plot: {str(e)}")
            return None

    def get_seasonal_plot(self):
        """Generate a seasonal yield plot as a base64 string"""
        try:
            # Prepare data for analysis
            df = self.prepare_data_for_analysis()
            
            if df.empty or len(df) < 10:  # Need sufficient data for seasonal analysis
                return None
                
            # Check if we have timestamp data
            if 'created_at' not in df.columns:
                return None
                
            # Convert timestamp to datetime if needed
            df['created_at'] = pd.to_datetime(df['created_at'], errors='coerce')
            
            # Extract month from timestamp
            df['month'] = df['created_at'].dt.month
            
            # Group by month and calculate average yield
            batch_yield = df.groupby(['batch_id', 'month'])['weight'].sum().reset_index()
            monthly_yield = batch_yield.groupby('month')['weight'].mean().reset_index()
            
            if len(monthly_yield) < 3:  # Need at least 3 months of data
                return None
                
            # Create plot
            plt.figure(figsize=(10, 6))
            
            # Create month names for x-axis
            month_names = {
                1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
                7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
            }
            
            monthly_yield['month_name'] = monthly_yield['month'].map(month_names)
            monthly_yield = monthly_yield.sort_values('month')
            
            # Create bar plot
            ax = sns.barplot(x='month_name', y='weight', data=monthly_yield)
            plt.title('Seasonal Yield Patterns', fontsize=14)
            plt.xlabel('Month', fontsize=12)
            plt.ylabel('Average Yield (g)', fontsize=12)
            
            # Add data labels
            for p in ax.patches:
                ax.annotate(f'{p.get_height():.1f}g', 
                           (p.get_x() + p.get_width() / 2., p.get_height()),
                           ha = 'center', va = 'bottom',
                           xytext = (0, 5), textcoords = 'offset points')
            
            plt.tight_layout()
            
            # Convert to base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close()
            
            return image_base64
            
        except Exception as e:
            print(f"Error generating seasonal plot: {str(e)}")
            return None
            
    def get_harvest_timeline_plot(self):
        """Generate a harvest timeline plot as a base64 string"""
        try:
            # Prepare data for analysis
            df = self.prepare_data_for_analysis()
            
            if df.empty or len(df) < 10:  # Need sufficient data points
                return None
                
            # Check if we have days_after_plant data
            if 'days_after_plant' not in df.columns or 'weight' not in df.columns:
                return None
                
            # Only use logs where weight/harvest is recorded
            harvest_logs = df[df['weight'].notna() & (df['weight'] > 0)]
            
            if harvest_logs.empty or len(harvest_logs) < 10:
                return None
                
            # Group by days after planting
            harvest_by_day = harvest_logs.groupby('days_after_plant')['weight'].mean().reset_index()
            
            if len(harvest_by_day) < 5:
                return None
                
            # Create plot
            plt.figure(figsize=(10, 6))
            
            # Create line plot
            sns.lineplot(x='days_after_plant', y='weight', data=harvest_by_day, marker='o')
            plt.title('Harvest Timeline After Planting', fontsize=14)
            plt.xlabel('Days After Planting', fontsize=12)
            plt.ylabel('Average Harvest (g)', fontsize=12)
            
            # Find and mark peak day
            peak_day = harvest_by_day.loc[harvest_by_day['weight'].idxmax()]
            plt.axvline(x=peak_day['days_after_plant'], color='r', linestyle='--', alpha=0.7)
            plt.text(peak_day['days_after_plant'] + 1, peak_day['weight'] * 0.9, 
                   f'Peak Harvest\nDay {int(peak_day["days_after_plant"])}', color='r')
            
            plt.tight_layout()
            
            # Convert to base64
            buffer = BytesIO()
            plt.savefig(buffer, format='png')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
            plt.close()
            
            return image_base64
            
        except Exception as e:
            print(f"Error generating harvest timeline plot: {str(e)}")
            return None

    def prepare_data_for_analysis(self):
        """Prepare data for analysis by merging logs and batches"""
        try:
            if not self.logs or not self.batches:
                return pd.DataFrame()
                
            # Convert logs to DataFrame if necessary - handle Log objects appropriately
            if isinstance(self.logs, list) and all(hasattr(item, '__dict__') for item in self.logs):
                # Convert Log objects to dictionaries
                logs_data = [{
                    'batch_id': log.batch_id,
                    'weight': log.harvest if hasattr(log, 'harvest') else None,  # Use harvest as weight
                    'timestamp': log.date if hasattr(log, 'date') else None,
                    'air_temp': log.air_temp if hasattr(log, 'air_temp') else None,
                    'substrate_temp': log.substrate_temp if hasattr(log, 'substrate_temp') else None,
                    'humidity': log.rh_humidity if hasattr(log, 'rh_humidity') else None,
                    'co2': log.co2 if hasattr(log, 'co2') else None,
                    'if_bagged': log.if_bagged if hasattr(log, 'if_bagged') else None,
                    'days_after_plant': log.days_after_plant if hasattr(log, 'days_after_plant') else None
                } for log in self.logs if hasattr(log, 'batch_id') and log.batch_id is not None]
                logs_df = pd.DataFrame(logs_data)
            else:
                logs_df = pd.DataFrame(self.logs) if isinstance(self.logs, list) else self.logs
            
            # Convert batches to DataFrame if necessary - handle Batch objects appropriately
            if isinstance(self.batches, list) and all(hasattr(item, '__dict__') for item in self.batches):
                # Convert Batch objects to dictionaries
                batches_data = [{
                    'id': batch.batch_id if hasattr(batch, 'batch_id') else None,
                    'mushroom_type': batch.mushroom_type if hasattr(batch, 'mushroom_type') else None,
                    'created_at': batch.start_date if hasattr(batch, 'start_date') else None,
                    'substrate': batch.substrate if hasattr(batch, 'substrate') else None,
                    'room_number': batch.room_number if hasattr(batch, 'room_number') else None
                } for batch in self.batches if hasattr(batch, 'batch_id')]
                batches_df = pd.DataFrame(batches_data)
            else:
                batches_df = pd.DataFrame(self.batches) if isinstance(self.batches, list) else self.batches
            
            if logs_df.empty or batches_df.empty:
                print("Empty logs or batches DataFrame")
                return pd.DataFrame()
                
            # Print column info for debugging
            print(f"Log columns: {logs_df.columns.tolist()}")
            print(f"Batch columns: {batches_df.columns.tolist()}")
            
            # Ensure required columns exist
            required_columns = ['batch_id', 'weight']
            missing_columns = [col for col in required_columns if col not in logs_df.columns]
            if missing_columns:
                print(f"Missing required columns in logs: {missing_columns}")
                return pd.DataFrame()
            
            # Extract environmental conditions from batches
            batch_conditions = batches_df[['id', 'mushroom_type', 'created_at']].copy()
            batch_conditions.rename(columns={'id': 'batch_id'}, inplace=True)
            
            # Extract temperature, humidity, light if available
            for factor in ['temperature', 'humidity', 'light']:
                if factor in batches_df.columns:
                    batch_conditions[factor] = batches_df[factor]
            
            # Add environmental data from logs if not in batches
            if 'temperature' not in batch_conditions.columns and 'air_temp' in logs_df.columns:
                # Aggregate temperature by batch
                temp_by_batch = logs_df.groupby('batch_id')['air_temp'].mean().reset_index()
                temp_by_batch.rename(columns={'air_temp': 'temperature'}, inplace=True)
                batch_conditions = pd.merge(batch_conditions, temp_by_batch, on='batch_id', how='left')
                
            if 'humidity' not in batch_conditions.columns and 'humidity' in logs_df.columns:
                # Aggregate humidity by batch
                humidity_by_batch = logs_df.groupby('batch_id')['humidity'].mean().reset_index()
                batch_conditions = pd.merge(batch_conditions, humidity_by_batch, on='batch_id', how='left')
                
            # Convert created_at to datetime if it's a string
            if 'created_at' in batch_conditions and batch_conditions['created_at'].dtype == 'object':
                batch_conditions['created_at'] = pd.to_datetime(batch_conditions['created_at'], errors='coerce')
            
            # Merge logs with batch conditions
            merged_data = pd.merge(logs_df, batch_conditions, on='batch_id', how='left')
            return merged_data
        except Exception as e:
            print(f"Error preparing data for analysis: {str(e)}")
            return pd.DataFrame()

    def generate_decision_tree_plot(self):
        """Generate a decision tree visualization for yield prediction"""
        try:
            # Prepare data for analysis
            df = self.prepare_data_for_analysis()
            
            if df.empty or len(df) < 10:
                return {"explanation": "Not enough data for decision tree analysis. Need at least 10 data points."}
            
            print(f"Total records: {len(df)}")
            print(f"Unique batch IDs: {df['batch_id'].nunique()}")
            
            # Calculate total harvest per batch
            batch_yield = df.groupby('batch_id')['weight'].sum().reset_index()
            batch_yield.rename(columns={'weight': 'total_yield'}, inplace=True)
            
            # Get days to first harvest for each batch
            harvest_days = {}
            for batch_id in df['batch_id'].unique():
                batch_data = df[df['batch_id'] == batch_id]
                # Find records with harvest weight > 0
                harvest_records = batch_data[batch_data['weight'] > 0]
                if not harvest_records.empty:
                    # Get minimum days_after_plant for harvests
                    if 'days_after_plant' in harvest_records.columns:
                        min_days = harvest_records['days_after_plant'].min()
                        if pd.notna(min_days) and min_days > 0 and min_days < 100:  # Sanity check
                            harvest_days[batch_id] = min_days
            
            print(f"Batches with valid first harvest day: {len(harvest_days)}")
            if harvest_days:
                print(f"Average days to first harvest: {sum(harvest_days.values())/len(harvest_days):.1f}")
            
            # Prepare feature data by batch - focusing on practical features only
            feature_data = []
            for batch_id in df['batch_id'].unique():
                batch_df = df[df['batch_id'] == batch_id]
                
                # Skip if no meaningful data
                if len(batch_df) < 3:
                    continue
                    
                batch_features = {'batch_id': batch_id}
                
                # Add key environmental factors
                env_factors = ['air_temp', 'co2', 'humidity', 'substrate_temp']
                for factor in env_factors:
                    if factor in batch_df.columns and not batch_df[factor].isna().all():
                        # Get average during growing period
                        valid_values = batch_df[factor].dropna()
                        if len(valid_values) > 0:
                            # Normalize CO2 readings if they're very high
                            if factor == 'co2' and valid_values.mean() > 5000:
                                batch_features[factor] = valid_values.mean() / 1000  # Convert to thousands
                            else:
                                batch_features[factor] = valid_values.mean()
                
                # Add days to first harvest if available
                if batch_id in harvest_days:
                    batch_features['days_to_harvest'] = harvest_days[batch_id]
                
                # Add mushroom type
                if 'mushroom_type' in batch_df.columns:
                    mtype = batch_df['mushroom_type'].iloc[0] if not batch_df['mushroom_type'].isna().all() else None
                    if mtype is not None:
                        batch_features['mushroom_type'] = mtype
                
                # Only add if we have useful data
                if len(batch_features) > 2:  # batch_id + at least 1 feature
                    feature_data.append(batch_features)
            
            # Convert to DataFrame
            features_df = pd.DataFrame(feature_data)
            
            if features_df.empty or len(features_df) < 5:
                return {"explanation": "Not enough batches with complete data for analysis. Need at least 5."}
                
            print(f"Feature DataFrame shape: {features_df.shape}")
            print(f"Feature columns: {features_df.columns.tolist()}")
            
            # Merge with yield data
            yield_data = pd.merge(batch_yield, features_df, on='batch_id', how='inner')
            print(f"After merge: {len(yield_data)} batches with complete data")
            
            if len(yield_data) < 5:
                return {"explanation": "Not enough batches with yield data. Need at least 5 for reliable analysis."}
            
            # Create a meaningful target variable: high vs. low yield
            median_yield = yield_data['total_yield'].median()
            yield_data['high_yield'] = (yield_data['total_yield'] > median_yield).astype(int)
            
            # Only include mushroom types with enough samples
            if 'mushroom_type' in yield_data.columns:
                type_counts = yield_data['mushroom_type'].value_counts()
                valid_types = type_counts[type_counts >= 3].index.tolist()
                if valid_types:
                    yield_data = yield_data[yield_data['mushroom_type'].isin(valid_types)]
                    print(f"Valid mushroom types with ≥3 samples: {valid_types}")
            
            # Separate analysis by mushroom type for better results
            result_by_type = {}
            mushroom_types = []
            
            # If we have mushroom type and enough data, do separate analysis
            if 'mushroom_type' in yield_data.columns and yield_data['mushroom_type'].nunique() > 1:
                mushroom_types = yield_data['mushroom_type'].unique()
                
                # For each mushroom type with enough data
                for mtype in mushroom_types:
                    type_data = yield_data[yield_data['mushroom_type'] == mtype].copy()
                    if len(type_data) >= 3:
                        type_result = self._analyze_decision_factors(type_data, mtype)
                        if type_result:
                            result_by_type[mtype] = type_result
            
            # Also do overall analysis
            overall_result = self._analyze_decision_factors(yield_data, "All Types")
            
            # Compile final results
            final_results = {
                "overall": overall_result,
                "by_type": result_by_type,
                "mushroom_types": mushroom_types.tolist() if isinstance(mushroom_types, np.ndarray) else list(mushroom_types)
            }
            
            # Generate comprehensive explanation
            explanation = self._generate_decision_tree_explanation(final_results)
            
            # Return interactive HTML content
            html_content = self._generate_decision_tree_html(final_results)
            
            return {
                "explanation": explanation,
                "html_content": html_content,
                "results": final_results
            }
            
        except Exception as e:
            print(f"Error generating decision tree plot: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"explanation": f"Error generating decision tree: {str(e)}"}
    
    def _analyze_decision_factors(self, data, label):
        """Analyze decision factors for a subset of data"""
        try:
            # Select only numeric columns and non-zero variance features
            X_cols = [col for col in data.columns if col not in ['batch_id', 'total_yield', 'high_yield', 'mushroom_type']]
            X = data[X_cols]
            
            # Remove columns with all NaN or zero variance
            X = X.loc[:, ~X.isna().all()]
            X = X.loc[:, X.var() > 0]
            
            # Fix CO2 values if needed
            if 'co2' in X.columns:
                co2_mean = X['co2'].mean()
                if co2_mean < 10:  # too low, might be in thousands of ppm
                    X['co2'] = X['co2'] * 1000
                    print(f"Adjusted CO2 values (multiplied by 1000): new mean = {X['co2'].mean():.2f}")
                elif co2_mean > 10000:  # too high, might be in raw values
                    X['co2'] = X['co2'] / 1000
                    print(f"Adjusted CO2 values (divided by 1000): new mean = {X['co2'].mean():.2f}")
            
            # If we don't have enough features, return None
            if X.shape[1] < 1:
                return None
                
            # Fill NaN values with mean
            X = X.fillna(X.mean())
            y = data['high_yield']
            
            # Train Random Forest for feature importance
            from sklearn.ensemble import RandomForestClassifier
            rf = RandomForestClassifier(n_estimators=50, max_depth=3, random_state=42)
            rf.fit(X, y)
            
            # Get feature importance, keep only important features (>0.01)
            importances = rf.feature_importances_
            feature_importance = pd.DataFrame({
                'feature': X.columns,
                'importance': importances
            }).sort_values('importance', ascending=False)
            
            # Filter out zero/near-zero importance features
            feature_importance = feature_importance[feature_importance['importance'] > 0.01]
            
            if feature_importance.empty:
                return None
                
            # Retrain with important features only
            important_features = feature_importance['feature'].tolist()
            X_important = X[important_features]
            
            # Train Decision Tree with important features
            from sklearn.tree import DecisionTreeClassifier, export_text
            dt = DecisionTreeClassifier(max_depth=3, min_samples_leaf=2, random_state=42)
            dt.fit(X_important, y)
            
            # Get decision rules as text
            tree_text = export_text(dt, feature_names=list(important_features))
            
            # Extract key thresholds from the decision tree
            thresholds = {}
            for feature in important_features:
                # Find all thresholds for this feature in the tree text
                feature_thresholds = []
                for line in tree_text.split('\n'):
                    if f"{feature} <=" in line or f"{feature} >" in line:
                        try:
                            threshold = float(line.split(feature)[1].replace("<=", "").replace(">", "").strip())
                            feature_thresholds.append(threshold)
                        except:
                            pass
                
                if feature_thresholds:
                    thresholds[feature] = sorted(feature_thresholds)
            
            # Calculate optimal conditions based on high-yield instances
            high_yield_data = data[data['high_yield'] == 1]
            optimal_conditions = {}
            for feature in important_features:
                if feature in high_yield_data.columns:
                    values = high_yield_data[feature].dropna()
                    if not values.empty:
                        optimal_conditions[feature] = {
                            'mean': float(values.mean()),
                            'median': float(values.median()),
                            'min': float(values.min()),
                            'max': float(values.max())
                        }
            
            return {
                'feature_importance': feature_importance.to_dict('records'),
                'tree_text': tree_text,
                'thresholds': thresholds,
                'optimal_conditions': optimal_conditions
            }
        except Exception as e:
            print(f"Error in _analyze_decision_factors for {label}: {str(e)}")
            return None
    
    def _generate_decision_tree_explanation(self, results):
        """Generate a human-readable explanation of decision tree results"""
        overall = results.get('overall', {})
        by_type = results.get('by_type', {})
        
        explanation = "Decision tree analysis shows "
        
        # If we have overall results
        if overall and 'feature_importance' in overall and overall['feature_importance']:
            top_feature = overall['feature_importance'][0]
            explanation += f"that {top_feature['feature']} is the most important factor "
            
            # Add threshold if available
            if top_feature['feature'] in overall.get('thresholds', {}):
                thresholds = overall['thresholds'][top_feature['feature']]
                if thresholds:
                    explanation += f"with optimal values around {thresholds[0]:.1f} "
            
            explanation += "for determining yield outcomes"
            
            # Add second most important factor if available
            if len(overall['feature_importance']) > 1:
                second_feature = overall['feature_importance'][1]
                explanation += f", followed by {second_feature['feature']} "
                if second_feature['importance'] > 0.2:
                    explanation += f"(importance: {second_feature['importance']:.0%}) "
        
        # Add type-specific insights if available
        if by_type:
            explanation += ". When analyzing by mushroom type: "
            type_insights = []
            
            for mtype, type_result in by_type.items():
                if type_result and 'feature_importance' in type_result and type_result['feature_importance']:
                    top_type_feature = type_result['feature_importance'][0]
                    type_insight = f"for {mtype}, {top_type_feature['feature']} is key"
                    
                    # Add optimal value if available
                    if top_type_feature['feature'] in type_result.get('optimal_conditions', {}):
                        opt = type_result['optimal_conditions'][top_type_feature['feature']]
                        type_insight += f" (optimal: {opt['mean']:.1f})"
                        
                    type_insights.append(type_insight)
            
            if type_insights:
                explanation += "; ".join(type_insights)
        
        explanation += ". View the detailed results for practical growing recommendations."
        return explanation
    
    def _generate_decision_tree_html(self, results):
        """Generate interactive HTML for decision tree visualization"""
        overall = results.get('overall', {})
        by_type = results.get('by_type', {})
        mushroom_types = results.get('mushroom_types', [])
        
        html = """
        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 5px; font-family: Arial, sans-serif;">
            <h2 style="color: #333;">Yield Decision Factors Analysis</h2>
            <p style="color: #555; margin-bottom: 20px;">This analysis shows what factors influence your mushroom yields and the optimal conditions for high yield.</p>
        """
        
        # First add a clear explanation of what the classes mean
        html += """
        <div style="background-color: #e8f4fc; padding: 10px; border-radius: 5px; margin-bottom: 20px;">
            <h3 style="color: #2980b9; margin-top: 0;">Understanding the Analysis</h3>
            <p><strong>Low Yield (Class 0):</strong> Yields below the median value for your batches</p>
            <p><strong>High Yield (Class 1):</strong> Yields above the median value for your batches</p>
            <p>The decision tree shows the environmental factors that best predict whether a batch will have high or low yield.</p>
        </div>
        """
        
        # Add interactive prediction simulator
        html += """
        <div style="background-color: #f0f9e8; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
            <h3 style="color: #27ae60; margin-top: 0;">Yield Predictor</h3>
            <p>Adjust the values below to see how they would affect your predicted yield:</p>
            <div id="simulator" style="margin-top: 15px;">
                <div id="simulator-inputs">
                    <!-- Inputs will be added dynamically based on important features -->
                </div>
                <div style="margin-top: 15px;">
                    <button onclick="predictYield()" style="background-color: #27ae60; color: white; border: none; padding: 8px 15px; border-radius: 4px; cursor: pointer;">Predict Yield</button>
                </div>
                <div id="prediction-result" style="margin-top: 15px; padding: 10px; background-color: white; border-radius: 4px; display: none;">
                    <p id="prediction-text"></p>
                </div>
            </div>
        </div>
        """
        
        # Create tabs for overall and type-specific analysis
        html += """
        <div class="tabs" style="margin-top: 20px;">
            <div class="tab-buttons" style="display: flex; margin-bottom: 10px; border-bottom: 1px solid #ccc; padding-bottom: 10px;">
                <button class="tab-button active" data-tab="overall" style="padding: 8px 16px; margin-right: 5px; border: none; background-color: #3498db; color: white; border-radius: 4px; cursor: pointer;">All Types</button>
        """
        
        # Add button for each mushroom type
        for mtype in mushroom_types:
            if mtype in by_type:
                html += f"""
                <button class="tab-button" data-tab="{mtype}" style="padding: 8px 16px; margin-right: 5px; border: none; background-color: #2c3e50; color: white; border-radius: 4px; cursor: pointer;">{mtype}</button>
                """
        
        html += """
            </div>
            <div class="tab-content">
        """
        
        # Overall tab content
        html += """
                <div class="tab-pane active" id="overall">
                    <h3>Overall Yield Factors</h3>
        """
        
        if overall and 'feature_importance' in overall and overall['feature_importance']:
            # Feature importance bar chart
            html += """
                    <div style="margin-top: 20px;">
                        <h4>Feature Importance</h4>
                        <div style="width: 100%; overflow-x: auto;">
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Feature</th>
                                    <th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Importance</th>
                                    <th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Visualization</th>
                                </tr>
            """
            
            for feature in overall['feature_importance']:
                # Only include features with non-zero importance
                if feature['importance'] > 0.01:
                    bar_width = int(feature['importance'] * 100) * 3  # Scale for visualization
                    feature_id = feature['feature'].replace(' ', '_')
                    
                    html += f"""
                                <tr>
                                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{feature['feature']}</td>
                                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{feature['importance']:.2f}</td>
                                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">
                                        <div class="viz-bar" 
                                             id="bar_{feature_id}" 
                                             style="background-color: #3498db; height: 20px; width: {bar_width}px; cursor: pointer;"
                                             onclick="showFeatureDetails('{feature['feature']}', {feature['importance']})">
                                        </div>
                                    </td>
                                </tr>
                    """
            
            html += """
                            </table>
                        </div>
                    </div>
            """
            
            # Optimal conditions
            if 'optimal_conditions' in overall and overall['optimal_conditions']:
                html += """
                    <div style="margin-top: 20px;">
                        <h4>Optimal Conditions for High Yield</h4>
                        <div style="width: 100%; overflow-x: auto;">
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Factor</th>
                                    <th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Optimal Value</th>
                                    <th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Range</th>
                                </tr>
                """
                
                for feature, values in overall['optimal_conditions'].items():
                    html += f"""
                                <tr>
                                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{feature}</td>
                                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{values['mean']:.2f}</td>
                                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{values['min']:.2f} - {values['max']:.2f}</td>
                                </tr>
                    """
                
                html += """
                            </table>
                        </div>
                    </div>
                """
            
            # Decision tree text - with better formatting
            if 'tree_text' in overall:
                html += """
                    <div style="margin-top: 20px;">
                        <h4>Decision Rules</h4>
                        <div style="background-color: white; padding: 10px; border-radius: 3px; overflow-x: auto; font-family: monospace;">
                """
                
                tree_lines = overall['tree_text'].split('\n')
                for line in tree_lines:
                    if "class: 0" in line:
                        # Low yield node - format in red
                        formatted_line = line.replace("class: 0", "<span style='color: #e74c3c; font-weight: bold;'>Low Yield</span>")
                        html += f"<div>{formatted_line}</div>"
                    elif "class: 1" in line:
                        # High yield node - format in green
                        formatted_line = line.replace("class: 1", "<span style='color: #2ecc71; font-weight: bold;'>High Yield</span>")
                        html += f"<div>{formatted_line}</div>"
                    else:
                        html += f"<div>{line}</div>"
                
                html += """
                        </div>
                    </div>
                """
        
        html += """
                </div>
        """
        
        # Tab content for each mushroom type - similar structure as overall
        for mtype in mushroom_types:
            if mtype in by_type and by_type[mtype]:
                type_result = by_type[mtype]
                
                html += f"""
                <div class="tab-pane" id="{mtype}">
                    <h3>Yield Factors for {mtype}</h3>
                """
                
                if 'feature_importance' in type_result and type_result['feature_importance']:
                    # Feature importance bar chart
                    html += """
                    <div style="margin-top: 20px;">
                        <h4>Feature Importance</h4>
                        <div style="width: 100%; overflow-x: auto;">
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Feature</th>
                                    <th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Importance</th>
                                    <th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Visualization</th>
                                </tr>
                    """
                    
                    for feature in type_result['feature_importance']:
                        # Only include features with non-zero importance
                        if feature['importance'] > 0.01:
                            bar_width = int(feature['importance'] * 100) * 3  # Scale for visualization
                            feature_id = f"{mtype}_{feature['feature']}".replace(' ', '_')
                            
                            html += f"""
                                <tr>
                                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{feature['feature']}</td>
                                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">{feature['importance']:.2f}</td>
                                    <td style="padding: 8px; border-bottom: 1px solid #ddd;">
                                        <div class="viz-bar" 
                                             id="bar_{feature_id}" 
                                             style="background-color: #3498db; height: 20px; width: {bar_width}px; cursor: pointer;"
                                             onclick="showFeatureDetails('{feature['feature']}', {feature['importance']}, '{mtype}')">
                                        </div>
                                    </td>
                                </tr>
                            """
                    
                    html += """
                            </table>
                        </div>
                    </div>
                    """
                    
                    # Optimal conditions
                    if 'optimal_conditions' in type_result and type_result['optimal_conditions']:
                        html += """
                        <div style="margin-top: 20px;">
                            <h4>Optimal Conditions for High Yield</h4>
                            <div style="width: 100%; overflow-x: auto;">
                                <table style="width: 100%; border-collapse: collapse;">
                                    <tr>
                                        <th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Factor</th>
                                        <th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Optimal Value</th>
                                        <th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Range</th>
                                    </tr>
                        """
                        
                        for feature, values in type_result['optimal_conditions'].items():
                            html += f"""
                                    <tr>
                                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{feature}</td>
                                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{values['mean']:.2f}</td>
                                        <td style="padding: 8px; border-bottom: 1px solid #ddd;">{values['min']:.2f} - {values['max']:.2f}</td>
                                    </tr>
                            """
                        
                        html += """
                                </table>
                            </div>
                        </div>
                        """
                    
                    # Decision tree text with better formatting
                    if 'tree_text' in type_result:
                        html += """
                        <div style="margin-top: 20px;">
                            <h4>Decision Rules</h4>
                            <div style="background-color: white; padding: 10px; border-radius: 3px; overflow-x: auto; font-family: monospace;">
                        """
                        
                        tree_lines = type_result['tree_text'].split('\n')
                        for line in tree_lines:
                            if "class: 0" in line:
                                # Low yield node - format in red
                                formatted_line = line.replace("class: 0", "<span style='color: #e74c3c; font-weight: bold;'>Low Yield</span>")
                                html += f"<div>{formatted_line}</div>"
                            elif "class: 1" in line:
                                # High yield node - format in green
                                formatted_line = line.replace("class: 1", "<span style='color: #2ecc71; font-weight: bold;'>High Yield</span>")
                                html += f"<div>{formatted_line}</div>"
                            else:
                                html += f"<div>{line}</div>"
                        
                        html += """
                            </div>
                        </div>
                        """
                
                html += """
                </div>
                """
        
        html += """
            </div>
        </div>
        """
        
        # Feature details modal
        html += """
        <div id="feature-modal" style="display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.7);">
            <div style="margin: 10% auto; padding: 20px; width: 60%; background-color: white; border-radius: 8px;">
                <span onclick="closeModal()" style="float: right; cursor: pointer; font-size: 20px;">&times;</span>
                <h3 id="modal-title">Feature Details</h3>
                <div id="modal-content" style="margin-top: 15px;"></div>
            </div>
        </div>
        """
        
        # Add JavaScript for tab switching and interactivity
        html += """
        <script>
            document.addEventListener('DOMContentLoaded', function() {
                // Get all tab buttons
                var tabButtons = document.querySelectorAll('.tab-button');
                
                // Add click event listener to each button
                tabButtons.forEach(function(button) {
                    button.addEventListener('click', function() {
                        // Remove active class from all buttons and panes
                        document.querySelectorAll('.tab-button').forEach(function(btn) {
                            btn.classList.remove('active');
                            btn.style.backgroundColor = '#2c3e50';
                        });
                        document.querySelectorAll('.tab-pane').forEach(function(pane) {
                            pane.classList.remove('active');
                            pane.style.display = 'none';
                        });
                        
                        // Add active class to clicked button
                        this.classList.add('active');
                        this.style.backgroundColor = '#3498db';
                        
                        // Show corresponding tab pane
                        var tabId = this.getAttribute('data-tab');
                        var tabPane = document.getElementById(tabId);
                        if (tabPane) {
                            tabPane.classList.add('active');
                            tabPane.style.display = 'block';
                        }
                        
                        // Update simulator inputs based on the selected tab
                        updateSimulatorInputs(tabId);
                    });
                });
                
                // Set initial active tab
                document.querySelector('.tab-button.active').click();
                
                // Initialize the simulator
                initializeSimulator();
            });
            
            // Store the decision tree rules for prediction
            var decisionRules = {};
        """
        
        # Add decision tree rules data for each tab
        html += f"""
            // Overall rules
            decisionRules['overall'] = {json.dumps(overall)} || {{}};
            
            // Mushroom type rules
            """
        
        for mtype in mushroom_types:
            if mtype in by_type:
                html += f"decisionRules['{mtype}'] = {json.dumps(by_type[mtype])} || {{}};\n"
        
        # Add simulator functions
        html += """
            function initializeSimulator() {
                updateSimulatorInputs('overall');
            }
            
            function updateSimulatorInputs(tabId) {
                var inputsContainer = document.getElementById('simulator-inputs');
                inputsContainer.innerHTML = '';
                
                var rules = decisionRules[tabId];
                if (!rules || !rules.tree_text) return;
                
                // Create inputs for top features
                var features = rules.tree_text.split('\n').filter(line => line.includes('class:')).slice(0, 4); // Top 4 most important features
                
                features.forEach(function(feature) {
                    var featureName = feature.split('class:')[1].trim();
                    var inputId = 'input_' + featureName.replace(/\\s+/g, '_');
                    
                    var defaultValue = '';
                    var min = '';
                    var max = '';
                    var step = 0.1;
                    
                    // Set sensible defaults based on feature name
                    if (featureName.includes('temp')) {
                        defaultValue = '25';
                        min = '15';
                        max = '35';
                    } else if (featureName.includes('humid')) {
                        defaultValue = '75';
                        min = '50';
                        max = '95';
                    } else if (featureName.includes('co2')) {
                        defaultValue = '1000';
                        min = '500';
                        max = '2000';
                        step = 100;
                    } else if (featureName.includes('days')) {
                        defaultValue = '30';
                        min = '10';
                        max = '60';
                        step = 1;
                    }
                    
                    // Use optimal values if available
                    if (rules.optimal_conditions && rules.optimal_conditions[featureName]) {
                        defaultValue = rules.optimal_conditions[featureName].mean.toFixed(1);
                        min = (rules.optimal_conditions[featureName].min * 0.8).toFixed(1);
                        max = (rules.optimal_conditions[featureName].max * 1.2).toFixed(1);
                    }
                    
                    var inputHTML = `
                        <div style="margin-bottom: 10px;">
                            <label for="${inputId}" style="display: block; margin-bottom: 5px;">${featureName}</label>
                            <input type="range" id="${inputId}" name="${featureName}" 
                                   min="${min}" max="${max}" step="${step}" value="${defaultValue}"
                                   oninput="document.getElementById('${inputId}_value').textContent = this.value"
                                   style="width: 70%;">
                            <span id="${inputId}_value">${defaultValue}</span>
                        </div>
                    `;
                    
                    inputsContainer.innerHTML += inputHTML;
                });
            }
            
            function predictYield() {
                var activeTab = document.querySelector('.tab-button.active').getAttribute('data-tab');
                var rules = decisionRules[activeTab];
                
                if (!rules || !rules.tree_text) {
                    showPrediction("Not enough data for prediction");
                    return;
                }
                
                // Get input values
                var inputValues = {};
                document.querySelectorAll('#simulator-inputs input').forEach(function(input) {
                    inputValues[input.name] = parseFloat(input.value);
                });
                
                // Simple decision tree traversal based on the rules
                var prediction = traverseDecisionTree(rules.tree_text, inputValues);
                
                // Display prediction
                if (prediction === 1) {
                    showPrediction("HIGH YIELD 🎉", true);
                } else {
                    showPrediction("LOW YIELD ⚠️", false);
                }
            }
            
            function traverseDecisionTree(treeText, inputValues) {
                var lines = treeText.split('\\n');
                var prediction = 0; // Default to low yield
                
                // Very simple tree parser - handle only top-level conditions
                for (var i = 0; i < lines.length; i++) {
                    var line = lines[i];
                    
                    // Look for decision nodes
                    for (var feature in inputValues) {
                        if (line.includes(feature)) {
                            var value = inputValues[feature];
                            
                            // Parse condition
                            if (line.includes('<=')) {
                                var threshold = parseFloat(line.split('<=')[1]);
                                if (value <= threshold) {
                                    // Look ahead for class in next line
                                    if (lines[i+1] && lines[i+1].includes('class: 1')) {
                                        prediction = 1;
                                        break;
                                    }
                                }
                            } else if (line.includes('>')) {
                                var threshold = parseFloat(line.split('>')[1]);
                                if (value > threshold) {
                                    // Look ahead for class in next line
                                    if (lines[i+1] && lines[i+1].includes('class: 1')) {
                                        prediction = 1;
                                        break;
                                    }
                                }
                            }
                        }
                    }
                }
                
                return prediction;
            }
            
            function showPrediction(text, isHighYield) {
                var resultDiv = document.getElementById('prediction-result');
                var textDiv = document.getElementById('prediction-text');
                
                resultDiv.style.display = 'block';
                resultDiv.style.backgroundColor = isHighYield ? '#d5f5e3' : '#fadbd8';
                textDiv.textContent = text;
                
                if (isHighYield) {
                    textDiv.innerHTML = `<strong style="color: #27ae60; font-size: 18px;">${text}</strong><p>Based on your inputs, these conditions are favorable for high yields.</p>`;
                } else {
                    textDiv.innerHTML = `<strong style="color: #e74c3c; font-size: 18px;">${text}</strong><p>These conditions may result in lower yields. Try adjusting the values to match the optimal conditions.</p>`;
                }
            }
            
            function showFeatureDetails(feature, importance, mushroomType) {
                var modalTitle = document.getElementById('modal-title');
                var modalContent = document.getElementById('modal-content');
                var modal = document.getElementById('feature-modal');
                
                var typeText = mushroomType ? ' for ' + mushroomType : '';
                modalTitle.textContent = feature + typeText;
                
                var tab = mushroomType || 'overall';
                var rules = decisionRules[tab];
                
                var html = `<p><strong>Importance Score:</strong> ${importance.toFixed(2)}</p>`;
                
                // Add optimal values if available
                if (rules.optimal_conditions && rules.optimal_conditions[feature]) {
                    var values = rules.optimal_conditions[feature];
                    html += `
                        <div style="margin-top: 15px;">
                            <h4>Optimal Values</h4>
                            <ul>
                                <li><strong>Mean:</strong> ${values.mean.toFixed(2)}</li>
                                <li><strong>Median:</strong> ${values.median.toFixed(2)}</li>
                                <li><strong>Range:</strong> ${values.min.toFixed(2)} - ${values.max.toFixed(2)}</li>
                            </ul>
                        </div>
                    `;
                }
                
                // Add thresholds if available
                if (rules.thresholds && rules.thresholds[feature]) {
                    var thresholds = rules.thresholds[feature];
                    html += `
                        <div style="margin-top: 15px;">
                            <h4>Decision Thresholds</h4>
                            <p>The decision tree uses these values to split data:</p>
                            <ul>
                    `;
                    
                    thresholds.forEach(function(threshold) {
                        html += `<li>${threshold.toFixed(2)}</li>`;
                    });
                    
                    html += `
                            </ul>
                        </div>
                    `;
                }
                
                // Add generic advice
                html += `
                    <div style="margin-top: 15px;">
                        <h4>Recommendation</h4>
                        <p>Keep ${feature} within the optimal range for best results.</p>
                    </div>
                `;
                
                modalContent.innerHTML = html;
                modal.style.display = 'block';
            }
            
            function closeModal() {
                document.getElementById('feature-modal').style.display = 'none';
            }
        </script>
        <style>
            .tab-pane { display: none; }
            .tab-pane.active { display: block; }
            .tab-button.active { background-color: #3498db !important; }
            .viz-bar:hover { opacity: 0.8; }
            
            /* Add pulse animation to bars */
            @keyframes pulse {
                0% { opacity: 1; }
                50% { opacity: 0.7; }
                100% { opacity: 1; }
            }
            
            .viz-bar {
                animation: pulse 2s infinite;
                transition: width 0.3s ease;
            }
        </style>
        """
        
        html += """
        </div>
        """
        
        return html

    def get_algorithm_details(self, insight_type=None):
        """Get details about the algorithms and features used for generating insights"""
        algorithm_details = {
            'yield_factor': {
                'name': 'Correlation and Random Forest',
                'features': 'Temperature, humidity, CO2, mushroom type, substrate amount',
                'description': 'We analyze the correlation between environmental factors and yield, then use a Random Forest model to identify the most important features affecting your harvest performance.'
            },
            'optimal_condition': {
                'name': 'Binning and Yield Optimization',
                'features': 'Temperature, humidity, CO2, yield per batch',
                'description': 'We divide environmental measurements into ranges and identify which ranges produce the highest average yields, providing optimal growing condition recommendations.'
            },
            'harvesting': {
                'name': 'Time Series Analysis',
                'features': 'Days after planting, harvest weights, timestamps',
                'description': 'We analyze the timing of harvests across batches to identify optimal harvesting timelines and peak production periods.'
            },
            'seasonal': {
                'name': 'Seasonal Decomposition',
                'features': 'Batch creation date, yield, mushroom type',
                'description': 'We analyze yield patterns across different months to identify seasonal trends in your mushroom production.'
            },
            'decision_tree': {
                'name': 'Decision Tree Classification',
                'features': 'All environmental and batch factors',
                'description': 'We use a decision tree model to classify batches into high-yield and low-yield categories, identifying the most critical decision points for successful cultivation.'
            }
        }
        
        if insight_type and insight_type in algorithm_details:
            return algorithm_details[insight_type]
        
        return algorithm_details 