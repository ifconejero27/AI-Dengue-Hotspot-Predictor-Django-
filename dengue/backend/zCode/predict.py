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
    
# ==========================================================

# =============================================================================
# LINEAR REGRESSION IMPLEMENTATION - ADDED BELOW EXISTING CODE
# =============================================================================

# Global model directory for linear models
LINEAR_MODEL_DIR = os.path.join(settings.BASE_DIR, 'linear_models')
os.makedirs(LINEAR_MODEL_DIR, exist_ok=True)

# Store linear predictions in memory (not database)
linear_predictions_cache = {}

def prepare_linear_training_data(barangay):
    """Prepare features and targets for Linear Regression training"""
    # Get all historical data
    historical_cases = DengueCase.objects.filter(
        barangay=barangay
    ).order_by('year_reported', 'week_reported')

    if not historical_cases.exists():
        return None, None, None

    df_cases = pd.DataFrame(list(historical_cases.values(
        'year_reported', 'week_reported', 'num_cases'
    )))

    weather_data = []
    
    for _, row in df_cases.iterrows():
        year = row['year_reported']
        week = row['week_reported']
        
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
        return None, None, None

    # Create features for linear regression
    try:
        # Lag features (same as RF for fair comparison)
        merged['lag1_cases'] = merged['num_cases'].shift(1)
        merged['lag1_rainfall'] = merged['rainfall'].shift(1)
        merged['lag2_rainfall'] = merged['rainfall'].shift(2)
        merged['lag1_temp_max'] = merged['temp_max'].shift(1)
        merged['lag1_humidity'] = merged['humidity'].shift(1)
        
        # Additional features that work well with linear models
        merged['temp_range'] = merged['temp_max'] - merged['temp_min']
        merged['rain_temp_interaction'] = merged['rainfall'] * merged['temp_max']
        
        merged = merged.dropna()
    except Exception as e:
        print(f"Error creating features for {barangay.name}: {str(e)}")
        return None, None, None

    if merged.empty:
        return None, None, None

    # Prepare features and target
    feature_columns = [
        'lag1_cases', 'lag1_rainfall', 'lag2_rainfall', 
        'temp_max', 'temp_min', 'wind_speed', 'lag1_humidity',
        'temp_range', 'rain_temp_interaction'
    ]
    
    # Only use columns that exist
    available_columns = [col for col in feature_columns if col in merged.columns]
    
    if not available_columns:
        print(f"❌ No features available for {barangay.name}")
        return None, None, None

    X = merged[available_columns]
    y = merged['num_cases']
    
    # Scale features for linear regression
    from sklearn.preprocessing import StandardScaler
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    print(f"📊 Linear training data for {barangay.name}: {len(X)} samples, {len(available_columns)} features")
    
    return X_scaled, y, scaler

def train_linear_model(barangay, X, y):
    """Train Linear Regression model with regularization options"""
    try:
        if len(X) < 5:
            print(f"⚠️ Not enough data for {barangay.name}, using simple Linear Regression")
            from sklearn.linear_model import LinearRegression
            model = LinearRegression()
            model.fit(X, y)
            return model, 'linear_simple'
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        # Try different linear models
        from sklearn.linear_model import LinearRegression, Ridge, Lasso
        from sklearn.model_selection import cross_val_score
        from sklearn.metrics import r2_score
        
        models = {
            'linear': LinearRegression(),
            'ridge': Ridge(alpha=1.0, random_state=42),
            'lasso': Lasso(alpha=0.1, random_state=42, max_iter=1000)
        }
        
        best_model = None
        best_score = float('inf')
        best_name = ''
        
        for name, model in models.items():
            # Cross-validation to select best model
            cv_scores = -cross_val_score(model, X_train, y_train, 
                                       cv=min(3, len(X_train)-1), 
                                       scoring='neg_mean_absolute_error')
            avg_mae = cv_scores.mean()
            
            if avg_mae < best_score:
                best_score = avg_mae
                best_model = model
                best_name = name
        
        # Train the best model
        best_model.fit(X_train, y_train)
        
        # Calculate final performance
        y_pred = best_model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        print(f"✅ Linear Model ({best_name}) trained for {barangay.name} - MAE: {mae:.2f}, R²: {r2:.2f}")
        
        return best_model, best_name
        
    except Exception as e:
        print(f"❌ Error training linear model for {barangay.name}: {str(e)}")
        from sklearn.linear_model import LinearRegression
        model = LinearRegression()
        model.fit(X, y)
        return model, 'linear_fallback'

def calculate_linear_confidence(barangay, X, y, model, week_offset):
    """Calculate confidence for linear regression predictions"""
    try:
        from sklearn.metrics import r2_score
        # R² based confidence
        y_pred = model.predict(X)
        r2 = max(0, r2_score(y, y_pred))
        
        # Data quantity confidence
        data_confidence = min(0.5, len(X) / 40)
        
        # Feature significance
        if hasattr(model, 'coef_'):
            coef_variation = np.std(model.coef_) / (np.mean(np.abs(model.coef_)) + 1e-8)
            feature_confidence = min(0.3, 0.3 / (1.0 + coef_variation))
        else:
            feature_confidence = 0.15
        
        # Combine confidence factors
        base_confidence = (r2 * 0.4 + data_confidence * 0.4 + feature_confidence * 0.2)
        time_decay = week_offset * 0.08
        
        final_confidence = max(0.3, min(0.9, base_confidence - time_decay))
        percentage = round(final_confidence * 100, 2)
        
        print(f"🔍 LINEAR {barangay.name} Confidence → R²={r2:.2f}, Data={data_confidence:.2f}, Final={percentage:.1f}%")
        
        return percentage
        
    except Exception as e:
        print(f"❌ Linear confidence error for {barangay.name}: {str(e)}")
        return max(30, 70 - week_offset * 10)

def predict_with_linear_regression():
    """Main Linear Regression prediction function - Stores results in memory, not database"""
    barangays = Barangay.objects.all()
    today = datetime.now().date()
    current_year = today.year
    current_week = today.isocalendar()[1]

    predictions = []
    successful_predictions = 0
    failed_predictions = 0

    print(f"🚀 Starting LINEAR REGRESSION prediction for {len(barangays)} barangays...")
    
    # Clear previous linear predictions
    global linear_predictions_cache
    linear_predictions_cache = {}

    for barangay in barangays:
        try:
            model_path = os.path.join(LINEAR_MODEL_DIR, f"linear_model_{barangay.barangay_id}.pkl")
            scaler_path = os.path.join(LINEAR_MODEL_DIR, f"scaler_{barangay.barangay_id}.pkl")

            # Prepare training data with scaling
            X, y, scaler = prepare_linear_training_data(barangay)
            if X is None or len(X) < 3:
                print(f"⚠️ Insufficient data for {barangay.name}, skipping linear prediction")
                failed_predictions += 1
                continue

            # Train or load linear model
            needs_retraining = should_retrain_model(barangay)
            if os.path.exists(model_path) and os.path.exists(scaler_path) and not needs_retraining:
                model = joblib.load(model_path)
                scaler = joblib.load(scaler_path)
                print(f"📁 Using existing linear model for {barangay.name}")
            else:
                model, model_type = train_linear_model(barangay, X, y)
                joblib.dump(model, model_path)
                joblib.dump(scaler, scaler_path)
                print(f"📈 Created linear model for {barangay.name}")

            # Get the last known data point
            if len(X) > 0:
                last_features = X[-1:].copy()
            else:
                print(f"❌ No features available for {barangay.name}")
                failed_predictions += 1
                continue

            # Predict for next 3 weeks
            for week_offset in range(0, 3):
                target_week = current_week + week_offset
                target_year = current_year
                if target_week > 52:
                    target_week -= 52
                    target_year += 1

                # Update features for prediction
                weather = get_historical_weather_fallback(target_year, target_week)
                
                # Update feature values (simplified)
                if last_features.shape[1] >= 7:
                    last_features[0, 1] = weather['rainfall']  # lag1_rainfall
                    last_features[0, 2] = last_features[0, 1]  # lag2_rainfall
                    last_features[0, 3] = weather['temp_max']  # temp_max
                    last_features[0, 4] = weather['temp_min']  # temp_min
                    last_features[0, 5] = weather['wind_speed']  # wind_speed
                    last_features[0, 6] = weather['humidity']   # lag1_humidity

                # Make prediction
                predicted = max(0, float(model.predict(last_features)[0]))
                confidence = calculate_linear_confidence(barangay, X, y, model, week_offset)

                # Risk categorization
                if predicted >= 8:
                    risk_level = "Very High"
                elif predicted >= 5:
                    risk_level = "High"
                elif predicted >= 2:
                    risk_level = "Moderate"
                else:
                    risk_level = "Low"

                # Store prediction in memory (NOT database)
                prediction_key = f"{barangay.barangay_id}_{target_year}_{target_week}"
                linear_predictions_cache[prediction_key] = {
                    "barangay": barangay,
                    "barangay_name": barangay.name,
                    "year": target_year,
                    "week": target_week,
                    "predicted_cases": round(predicted, 2),
                    "confidence": round(confidence, 2),
                    "risk_level": risk_level,
                }

                print(f"📊 LINEAR {barangay.name} | Week {target_week}: {predicted:.2f} cases ({risk_level}) | {confidence:.1f}%")

                predictions.append({
                    "barangay": barangay.name,
                    "week": target_week,
                    "year": target_year,
                    "predicted_cases": round(predicted, 2),
                    "confidence": round(confidence, 2),
                    "risk_level": risk_level,
                })

                successful_predictions += 1

                # Update for next prediction (cascade)
                last_features[0, 0] = predicted  # Update lag1_cases

        except Exception as e:
            print(f"❌ Linear regression error for {barangay.name}: {str(e)}")
            failed_predictions += 1
            continue

    print(f"🎯 LINEAR PREDICTION complete: {successful_predictions} successful, {failed_predictions} failed")
    return predictions

# =============================================================================
# MODEL COMPARISON FUNCTIONS - ADDED BELOW EXISTING CODE
# =============================================================================

def compare_model_confidence():
    """Compare and print confidence scores between Linear Regression (from memory) and Random Forest (from database)"""
    
    barangays = Barangay.objects.all()
    today = datetime.now().date()
    current_year = today.year
    current_week = today.isocalendar()[1]
    
    print("=" * 70)
    print("🤖 MODEL CONFIDENCE COMPARISON")
    print("=" * 70)
    
    comparison_results = []
    
    for barangay in barangays:
        try:
            # Get Random Forest prediction from database
            rf_pred = PredictionResult.objects.filter(
                barangay=barangay,
                year_prediction=current_year,
                week_prediction=current_week
            ).first()
            
            # Get Linear Regression prediction from memory cache
            linear_pred_key = f"{barangay.barangay_id}_{current_year}_{current_week}"
            linear_pred = linear_predictions_cache.get(linear_pred_key)
            
            if linear_pred and rf_pred:
                # Both models have predictions
                comparison_results.append({
                    'barangay': barangay.name,
                    'linear_risk': linear_pred['risk_level'],
                    'linear_confidence': linear_pred['confidence'],
                    'rf_risk': rf_pred.risk_level,
                    'rf_confidence': rf_pred.confidence_score,
                    'linear_cases': linear_pred['predicted_cases'],
                    'rf_cases': rf_pred.numerical_risk_level
                })
                
                # Color coding for confidence differences
                conf_diff = rf_pred.confidence_score - linear_pred['confidence']
                if conf_diff > 20:
                    conf_indicator = "🟢 RF +"
                elif conf_diff > 10:
                    conf_indicator = "🟡 RF +"
                elif conf_diff < -20:
                    conf_indicator = "🔴 LINEAR +"
                elif conf_diff < -10:
                    conf_indicator = "🟠 LINEAR +"
                else:
                    conf_indicator = "⚪ TIE"
                
                print(f"🏘️  {barangay.name:.<20} Linear: {linear_pred['risk_level']:.<10} {linear_pred['confidence']:>3}% | "
                      f"R.Forest: {rf_pred.risk_level:.<10} {rf_pred.confidence_score:>3}% {conf_indicator}")
                      
            elif linear_pred and not rf_pred:
                # Only Linear has prediction
                print(f"🏘️  {barangay.name:.<20} Linear: {linear_pred['risk_level']:.<10} {linear_pred['confidence']:>3}% | "
                      f"R.Forest: {'NO DATA':.<10} {'--':>3}% 🔶")
                      
            elif not linear_pred and rf_pred:
                # Only RF has prediction
                print(f"🏘️  {barangay.name:.<20} Linear: {'NO DATA':.<10} {'--':>3}% | "
                      f"R.Forest: {rf_pred.risk_level:.<10} {rf_pred.confidence_score:>3}% 🔶")
                      
            else:
                # No predictions
                print(f"🏘️  {barangay.name:.<20} Linear: {'NO DATA':.<10} {'--':>3}% | "
                      f"R.Forest: {'NO DATA':.<10} {'--':>3}% ❌")
                      
        except Exception as e:
            print(f"❌ Error comparing {barangay.name}: {str(e)}")
    
    # Print summary statistics
    if comparison_results:
        print("\n" + "=" * 70)
        print("📊 SUMMARY STATISTICS")
        print("=" * 70)
        
        import pandas as pd
        df = pd.DataFrame(comparison_results)
        
        avg_linear_conf = df['linear_confidence'].mean()
        avg_rf_conf = df['rf_confidence'].mean()
        avg_linear_cases = df['linear_cases'].mean()
        avg_rf_cases = df['rf_cases'].mean()
        
        print(f"📈 Average Confidence:")
        print(f"   Linear Regression: {avg_linear_conf:.1f}%")
        print(f"   Random Forest:     {avg_rf_conf:.1f}%")
        print(f"   Difference:        {avg_rf_conf - avg_linear_conf:+.1f}%")
        
        print(f"\n🔢 Average Predicted Cases:")
        print(f"   Linear Regression: {avg_linear_cases:.2f} cases")
        print(f"   Random Forest:     {avg_rf_cases:.2f} cases")
        print(f"   Difference:        {avg_rf_cases - avg_linear_cases:+.2f} cases")
        
        # Count risk level agreements
        risk_agreement = len(df[df['linear_risk'] == df['rf_risk']])
        total_comparisons = len(df)
        agreement_rate = (risk_agreement / total_comparisons) * 100
        
        print(f"\n🤝 Risk Level Agreement: {risk_agreement}/{total_comparisons} ({agreement_rate:.1f}%)")
        
        # Confidence winners
        linear_wins = len(df[df['linear_confidence'] > df['rf_confidence']])
        rf_wins = len(df[df['rf_confidence'] > df['linear_confidence']])
        ties = len(df[df['linear_confidence'] == df['rf_confidence']])
        
        print(f"\n🏆 Confidence Comparison:")
        print(f"   Linear Regression wins: {linear_wins} barangays")
        print(f"   Random Forest wins:     {rf_wins} barangays")
        print(f"   Ties:                   {ties} barangays")
        
        return df
    else:
        print("❌ No comparison data available. Make sure both models have run successfully.")
        return None

# =============================================================================
# SINGLE COMMAND TO RUN BOTH MODELS AND COMPARE
# =============================================================================

def compare_linear_vs_random_forest():
    """
    SINGLE COMMAND: Run both Linear Regression and Random Forest predictions,
    then show comparison table with all results
    """
    print("🎯" * 60)
    print("🚀 SINGLE COMMAND: LINEAR REGRESSION vs RANDOM FOREST COMPARISON")
    print("🎯" * 60)
    
    # Step 1: Run Linear Regression predictions (stores in memory)
    print("\n" + "="*60)
    print("📊 STEP 1: RUNNING LINEAR REGRESSION PREDICTIONS")
    print("="*60)
    linear_results = predict_with_linear_regression()
    
    # Step 2: Run Random Forest predictions (stores in database)
    print("\n" + "="*60)
    print("🌳 STEP 2: RUNNING RANDOM FOREST PREDICTIONS")
    print("="*60)
    rf_results = predict_dengue_risk()
    
    # Step 3: Show comparison table
    print("\n" + "="*60)
    print("📋 STEP 3: COMPARISON TABLE - LINEAR vs RANDOM FOREST")
    print("="*60)
    comparison_df = compare_model_confidence()
    
    print("\n" + "✅" * 60)
    print("✅ COMPARISON COMPLETE! Both models have been run and compared.")
    print("✅" * 60)
    
    return {
        'linear_results': linear_results,
        'rf_results': rf_results,
        'comparison': comparison_df
    }

# =============================================================================
# USAGE EXAMPLES - ADDED AT THE END
# =============================================================================

if __name__ == "__main__":
    # SINGLE COMMAND: Run this one function to compare both models
    compare_linear_vs_random_forest()
    
    # Alternative individual functions (uncomment if needed):
    # predict_dengue_risk()                    # Run only Random Forest
    # predict_with_linear_regression()         # Run only Linear Regression