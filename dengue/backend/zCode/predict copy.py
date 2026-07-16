from datetime import datetime, timedelta
from django.db import models
from backend.models import Barangay, DengueCase, DailyForecast, PredictionResult, WeeklyAverage, ModelVersion
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_absolute_error, mean_squared_error
import numpy as np
import pandas as pd
import joblib
import os
from django.conf import settings
import warnings
warnings.filterwarnings('ignore')

# Global model directory
MODEL_DIR = os.path.join(settings.BASE_DIR, 'ml_models')
os.makedirs(MODEL_DIR, exist_ok=True)

def get_historical_weather_fallback(year, week):
    """Get weather data from WeeklyAverage with fallback"""
    try:
        # Try to get from WeeklyAverage first (this is your main source)
        weekly_avg = WeeklyAverage.objects.filter(year=year, week=week).first()
        
        if weekly_avg:
            return {
                'rainfall': float(weekly_avg.avg_rainfall_chance) if weekly_avg.avg_rainfall_chance else 35.0,
                'temp_max': float(weekly_avg.avg_temperature) if weekly_avg.avg_temperature else 30.0,
                'temp_min': float(weekly_avg.min_temperature) if weekly_avg.min_temperature else 25.0,
                'wind_speed': float(weekly_avg.avg_wind_speed) if weekly_avg.avg_wind_speed else 12.0,
                'humidity': float(weekly_avg.avg_humidity) if weekly_avg.avg_humidity else 70.0
            }
        
        # Fallback to seasonal averages if no WeeklyAverage data
        if 1 <= week <= 12 or 48 <= week <= 52:  # Dry season (Jan-Mar, Dec)
            return {'rainfall': 15.0, 'temp_max': 32.0, 'temp_min': 24.0, 'wind_speed': 12.0, 'humidity': 65.0}
        elif 22 <= week <= 40:  # Wet season (Jun-Oct)
            return {'rainfall': 65.0, 'temp_max': 30.0, 'temp_min': 25.0, 'wind_speed': 15.0, 'humidity': 80.0}
        else:  # Transition months
            return {'rainfall': 40.0, 'temp_max': 31.0, 'temp_min': 25.0, 'wind_speed': 13.0, 'humidity': 75.0}
        
    except Exception as e:
        print(f"⚠️ Weather fallback error for {year}-W{week}: {str(e)}")
        # Return reasonable defaults
        return {'rainfall': 35.0, 'temp_max': 30.0, 'temp_min': 25.0, 'wind_speed': 12.0, 'humidity': 70.0}

def should_retrain_model(barangay):
    """Determine if model needs retraining based on new data"""
    latest_version = ModelVersion.objects.filter(
        barangay=barangay
    ).order_by('-version').first()
    
    if not latest_version:
        return True  # No existing model
    
    # Check if significant new data arrived since last training
    new_data_count = DengueCase.objects.filter(
        barangay=barangay,
        year_reported__gte=latest_version.training_data_up_to.year
    ).count()
    
    # Retrain if we have more than 2 new weeks of data
    return new_data_count >= 2

def train_new_model(barangay, X, y):
    """Train a new model with GridSearchCV"""
    try:
        if len(X) < 5:
            print(f"⚠️ Not enough data for {barangay.name}, using simple model")
            model = RandomForestRegressor(n_estimators=50, random_state=42)
            model.fit(X, y)
            return model
        
        # Use GridSearchCV for better models with sufficient data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        model = GridSearchCV(
            RandomForestRegressor(random_state=42),
            param_grid={
                'n_estimators': [50, 100],
                'max_depth': [5, 10, None],
                'min_samples_split': [2, 5]
            },
            cv=min(3, len(X_train) - 1),  # Adjust CV based on data size
            scoring='neg_mean_absolute_error'
        )
        model.fit(X_train, y_train)
        
        # Calculate accuracy
        y_pred = model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        print(f"✅ Model trained for {barangay.name} - MAE: {mae:.2f}")
        
        return model.best_estimator_
        
    except Exception as e:
        print(f"❌ Error training model for {barangay.name}: {str(e)}")
        # Fallback to simple model
        model = RandomForestRegressor(n_estimators=50, random_state=42)
        model.fit(X, y)
        return model

def incremental_training(barangay, existing_model, X, y):
    """Update existing model with new data"""
    try:
        # For Random Forest, we can use warm_start to add more trees
        if hasattr(existing_model, 'warm_start'):
            existing_model.n_estimators += 20
            existing_model.fit(X, y)
        else:
            # Retrain completely if warm_start not available
            existing_model = train_new_model(barangay, X, y)
        
        print(f"🔄 Incrementally updated model for {barangay.name}")
        return existing_model
        
    except Exception as e:
        print(f"❌ Error in incremental training for {barangay.name}: {str(e)}")
        return train_new_model(barangay, X, y)

def prepare_training_data(barangay):
    """Prepare features and targets for training using WeeklyAverage data"""
    # ✅ USE ALL DATA - no year exclusion!
    historical_cases = DengueCase.objects.filter(
        barangay=barangay
    ).order_by('year_reported', 'week_reported')

    if not historical_cases.exists():
        return None, None

    df_cases = pd.DataFrame(list(historical_cases.values(
        'year_reported', 'week_reported', 'num_cases'
    )))

    weather_data = []
    
    for _, row in df_cases.iterrows():
        year = row['year_reported']
        week = row['week_reported']
        
        # Get ALL weather data from WeeklyAverage with fallback
        weather = get_historical_weather_fallback(year, week)
        
        weather_data.append({
            'year_reported': year,
            'week_reported': week,
            'rainfall': weather['rainfall'],
            'temp_max': weather['temp_max'],
            'temp_min': weather['temp_min'],
            'wind_speed': weather['wind_speed'],
            'humidity': weather['humidity']
        })

    df_weather = pd.DataFrame(weather_data)
    
    # Merge cases with weather
    merged = pd.merge(df_cases, df_weather, on=['year_reported', 'week_reported'])
    
    if merged.empty:
        return None, None

    # Create lag features
    try:
        merged['lag1_cases'] = merged['num_cases'].shift(1)
        merged['lag1_rainfall'] = merged['rainfall'].shift(1)
        merged['lag2_rainfall'] = merged['rainfall'].shift(2)
        merged['lag1_temp_max'] = merged['temp_max'].shift(1)
        merged['lag1_humidity'] = merged['humidity'].shift(1)
        merged = merged.dropna()
    except Exception as e:
        print(f"Error creating lag features for {barangay.name}: {str(e)}")
        return None, None

    if merged.empty:
        return None, None

    # Prepare features and target
    feature_columns = ['lag1_cases', 'lag1_rainfall', 'lag2_rainfall', 
                      'temp_max', 'temp_min', 'wind_speed', 'lag1_humidity']
    
    # Only use columns that exist
    available_columns = [col for col in feature_columns if col in merged.columns]
    
    if not available_columns:
        print(f"❌ No features available for {barangay.name}")
        return None, None

    X = merged[available_columns]
    y = merged['num_cases']
    
    print(f"📊 Training data for {barangay.name}: {len(X)} samples, {len(available_columns)} features")
    
    return X, y

def create_default_prediction(barangay, target_year, target_week):
    """Create a default prediction for barangays with insufficient data"""
    try:
        # Use average of similar barangays or conservative estimate
        avg_cases = DengueCase.objects.filter(
            barangay__name__icontains=barangay.name.split()[0]  # Similar area
        ).aggregate(avg=models.Avg('num_cases'))['avg'] or 2.0
        
        predicted_cases = max(1, avg_cases * 0.7)  # Conservative estimate
        
        PredictionResult.objects.update_or_create(
            barangay=barangay,
            year_prediction=target_year,
            week_prediction=target_week,
            defaults={
                'numerical_risk_level': predicted_cases,
                'confidence_score': 0.3,  # Low confidence for default predictions
                'risk_level': "Low" if predicted_cases < 3 else "Moderate",
                'trend': 'neutral'
            }
        )
        print(f"📝 Created default prediction for {barangay.name}")
        
    except Exception as e:
        print(f"❌ Error creating default prediction: {str(e)}")

def predict_dengue_risk():
    """Main prediction function with cascading weekly forecasting and improved confidence"""
    barangays = Barangay.objects.all()
    today = datetime.now().date()
    current_year = today.year
    current_week = today.isocalendar()[1]

    predictions = []
    successful_predictions = 0
    failed_predictions = 0

    print(f"🚀 Starting dengue prediction for {len(barangays)} barangays...")

    for barangay in barangays:
        try:
            model_path = os.path.join(MODEL_DIR, f"model_{barangay.barangay_id}.pkl")

            # Prepare training data
            X, y = prepare_training_data(barangay)
            if X is None or len(X) < 3:
                print(f"⚠️ Insufficient data for {barangay.name}, creating default prediction")
                for week_offset in range(0, 3):
                    target_week = (current_week + week_offset - 1) % 52 + 1
                    target_year = current_year + ((current_week + week_offset - 1) // 52)
                    create_default_prediction(barangay, target_year, target_week)
                failed_predictions += 1
                continue

            # Load or train model
            needs_retraining = should_retrain_model(barangay)
            if os.path.exists(model_path) and not needs_retraining:
                model = joblib.load(model_path)
                print(f"📁 Using existing model for {barangay.name}")
            else:
                if os.path.exists(model_path) and needs_retraining:
                    existing_model = joblib.load(model_path)
                    model = incremental_training(barangay, existing_model, X, y)
                else:
                    model = train_new_model(barangay, X, y)

                joblib.dump(model, model_path)
                latest_version = ModelVersion.objects.filter(barangay=barangay).order_by('-version').first()
                new_version = latest_version.version + 1 if latest_version else 1
                ModelVersion.objects.create(
                    barangay=barangay,
                    version=new_version,
                    training_data_up_to=today,
                    total_training_samples=len(X)
                )
                print(f"📈 Created model v{new_version} for {barangay.name}")

            # Get the last known data as base for predictions
            last_row = X.iloc[-1:].copy()

            # 🔁 Predict for the next 3 weeks (cascading)
            for week_offset in range(0, 3):
                target_week = current_week + week_offset
                target_year = current_year
                if target_week > 52:
                    target_week -= 52
                    target_year += 1

                target_weather = get_historical_weather_fallback(target_year, target_week)

                # Update feature inputs using predicted or lagged values
                last_row['lag1_rainfall'] = target_weather['rainfall']
                last_row['lag2_rainfall'] = last_row['lag1_rainfall']
                last_row['temp_max'] = target_weather['temp_max']
                last_row['temp_min'] = target_weather['temp_min']
                last_row['wind_speed'] = target_weather['wind_speed']
                last_row['lag1_humidity'] = target_weather['humidity']

                # 🔮 Predict dengue cases
                predicted = max(0, float(model.predict(last_row)[0]))

                # 🧩 Compute confidence (updated version below)
                confidence = calculate_confidence(barangay, X, y, model, week_offset)

                # 🩸 Risk categorization
                if predicted >= 8:
                    risk_level = "Very High"
                elif predicted >= 5:
                    risk_level = "High"
                elif predicted >= 2:
                    risk_level = "Moderate"
                else:
                    risk_level = "Low"

                # 📈 Determine trend
                prev_week = target_week - 1 if target_week > 1 else 52
                prev_year = target_year if target_week > 1 else target_year - 1

                prev_prediction = PredictionResult.objects.filter(
                    barangay=barangay,
                    year_prediction=prev_year,
                    week_prediction=prev_week
                ).first()

                if prev_prediction:
                    if predicted > prev_prediction.numerical_risk_level:
                        trend = "up"
                    elif predicted < prev_prediction.numerical_risk_level:
                        trend = "down"
                    else:
                        trend = "neutral"
                else:
                    trend = "neutral"

                # 💾 Save to database
                PredictionResult.objects.update_or_create(
                    barangay=barangay,
                    year_prediction=target_year,
                    week_prediction=target_week,
                    defaults={
                        "numerical_risk_level": round(predicted, 2),
                        "confidence_score": round(confidence, 2),
                        "risk_level": risk_level,
                        "trend": trend,
                    }
                )

                print(f"✅ {barangay.name} | Week {target_week}: {predicted:.2f} cases ({risk_level}) | {confidence:.1f}% | Trend={trend}")

                # 🔁 Update lag for next iteration (cascade prediction)
                last_row['lag1_cases'] = predicted
                last_row['lag1_rainfall'] = target_weather['rainfall']
                last_row['lag2_rainfall'] = last_row['lag1_rainfall']
                last_row['lag1_humidity'] = target_weather['humidity']

                predictions.append({
                    "barangay": barangay.name,
                    "week": target_week,
                    "year": target_year,
                    "predicted_cases": round(predicted, 2),
                    "confidence": round(confidence, 2),
                    "risk_level": risk_level,
                    "trend": trend
                })

                successful_predictions += 1

        except Exception as e:
            print(f"❌ Error predicting for {barangay.name}: {str(e)}")
            failed_predictions += 1
            continue

    print(f"🎯 Prediction complete: {successful_predictions} successful, {failed_predictions} failed")
    return predictions


def debug_weekly_averages():
    """Check what WeeklyAverage data you have"""
    weekly_data = WeeklyAverage.objects.all().order_by('year', 'week')[:10]  # First 10 records
    
    print("=== WEEKLY AVERAGE DATA SAMPLE ===")
    for wa in weekly_data:
        print(f"{wa.year}-W{wa.week}: "
              f"Temp={wa.avg_temperature}, "
              f"Rain={wa.avg_rainfall_chance}, "
              f"Humidity={wa.avg_humidity}, "
              f"Wind={wa.avg_wind_speed}")
    
    # Check data counts
    total_weekly = WeeklyAverage.objects.count()
    years_with_data = WeeklyAverage.objects.values_list('year', flat=True).distinct()
    
    print(f"\n📊 Total WeeklyAverage records: {total_weekly}")
    print(f"📅 Years with data: {sorted(years_with_data)}")

# Call this to debug your WeeklyAverage data
# debug_weekly_averages()

def calculate_confidence(barangay, X, y, model, week_offset):
    """Improved confidence with softer decay and normalized performance scoring."""
    try:
        total_samples = len(X)
        data_quality = min(0.3, 0.3 * (total_samples / 50))  # up to 0.3 for good data

        # Model performance (MAE-based)
        if len(X) >= 10:
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            mae = mean_absolute_error(y_test, y_pred)
            y_range = max(1, y.max() - y.min())
            performance_score = max(0, 1 - (mae / (y_range * 0.7)))  # softened normalization
            model_performance = performance_score * 0.45
        else:
            model_performance = 0.15

        # Feature completeness
        important_features = ['lag1_cases', 'lag1_rainfall', 'temp_max', 'lag1_humidity']
        feature_coverage = len([f for f in important_features if f in X.columns]) / len(important_features)
        feature_strength = feature_coverage * 0.15

        # Historical consistency placeholder
        historical_consistency = 0.1

        # Combine and decay
        base_confidence = data_quality + model_performance + feature_strength + historical_consistency
        time_decay = week_offset * 0.05  # only -5% per week
        final_confidence = max(0.4, min(0.95, base_confidence - time_decay))
        percentage = round(final_confidence * 100, 2)

        print(f"🔍 {barangay.name} Confidence breakdown → Data={data_quality:.2f}, Model={model_performance:.2f}, "
              f"Features={feature_strength:.2f}, Final={percentage:.1f}%")

        return percentage

    except Exception as e:
        print(f"❌ Confidence error for {barangay.name}: {str(e)}")
        return max(0.4, 0.8 - week_offset * 0.05)