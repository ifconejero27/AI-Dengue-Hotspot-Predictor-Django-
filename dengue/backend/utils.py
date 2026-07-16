import openmeteo_requests
import pandas as pd
import numpy as np
import requests_cache
from retry_requests import retry
from backend.models import Barangay
from django.http import JsonResponse


cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

def get_weather_forecast(barangay_id=None, latitude=None, longitude=None):
    """
    Get weather forecast data for a specific location
    
    Args:
        barangay_id: ID of the barangay to get forecast for
        latitude: Latitude coordinate (optional if barangay_id is provided)
        longitude: Longitude coordinate (optional if barangay_id is provided)
    
    Returns:
        Dictionary with forecast data or error message
    """
    try:
      
        if barangay_id:
            try:
                barangay = Barangay.objects.get(pk=barangay_id)
                latitude = barangay.latitude
                longitude = barangay.longitude
            except Barangay.DoesNotExist:
                return {'error': 'Barangay not found'}
    
        if latitude is None or longitude is None:
            return {'error': 'Coordinates are required'}

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": float(latitude),
            "longitude": float(longitude),
            "hourly": ["temperature_2m", "relative_humidity_2m", "precipitation", "rain", "showers"],
            "timezone": "Asia/Manila",
            "past_days": 7,  # Reduced from 92 to avoid too much data
            "forecast_days": 7,  # Reduced from 16 to avoid too much data
        }
        
        responses = openmeteo.weather_api(url, params=params)
        response = responses[0]
  
        hourly = response.Hourly()
        hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
        hourly_relative_humidity_2m = hourly.Variables(1).ValuesAsNumpy()
        hourly_precipitation = hourly.Variables(2).ValuesAsNumpy()
        hourly_rain = hourly.Variables(3).ValuesAsNumpy()
        hourly_showers = hourly.Variables(4).ValuesAsNumpy()
        
 
        try:
            time_data = pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left"
            )
        except Exception as e:
            return {'error': f'Failed to process time data: {str(e)}'}
   
        valid_indices = ~pd.isna(time_data)
        
        if not any(valid_indices):
            return {'error': 'No valid time data received from API'}
  
        valid_dates = time_data[valid_indices]
        valid_temperature = hourly_temperature_2m[valid_indices]
        valid_humidity = hourly_relative_humidity_2m[valid_indices]
        valid_precipitation = hourly_precipitation[valid_indices]
        valid_rain = hourly_rain[valid_indices]
        valid_showers = hourly_showers[valid_indices]

        forecast_data = []
        for i in range(len(valid_dates)):

            forecast_data.append({
                "datetime": valid_dates[i].isoformat() if not pd.isna(valid_dates[i]) else None,
                "temperature_2m": float(valid_temperature[i]) if not pd.isna(valid_temperature[i]) else None,
                "relative_humidity_2m": float(valid_humidity[i]) if not pd.isna(valid_humidity[i]) else None,
                "precipitation": float(valid_precipitation[i]) if not pd.isna(valid_precipitation[i]) else None,
                "rain": float(valid_rain[i]) if not pd.isna(valid_rain[i]) else None,
                "showers": float(valid_showers[i]) if not pd.isna(valid_showers[i]) else None
            })
        
        return {
            "success": True,
            "location": {
                "latitude": response.Latitude(),
                "longitude": response.Longitude(),
                "elevation": response.Elevation(),
                "timezone": response.Timezone(),
            },
            "forecast": forecast_data,
            "count": len(forecast_data)
        }
        
    except Exception as e:
        return {'error': f'Failed to fetch weather data: {str(e)}'}