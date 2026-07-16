from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.http import JsonResponse, HttpResponse
import csv
from .models import *
import openmeteo_requests
import pandas as pd
import requests_cache
from retry_requests import retry
from datetime import datetime
import pytz
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from backend.zCode.otp import *

def home(request):
    return render(request, 'home.html')

def register(request):
    if request.method == 'POST':
        user_name = request.POST.get('name')
        user_email = request.POST.get('email')
        user_username = request.POST.get('username')
        user_password = request.POST.get('password')
        barangay_id = request.POST.get('barangay')
        is_admin = request.POST.get('is_admin')

        if not all([user_name, user_email, user_username, user_password]):
           
            return JsonResponse({'success': False, 'message': 'All fields are required.'})

        User = get_user_model()
        if User.objects.filter(username=user_username).exists():
           
            return JsonResponse({'success': False, 'message': 'username already exists.'})
        if User.objects.filter(email=user_email).exists():
          
            return JsonResponse({'success': False, 'message': 'email already exists.'})
        

        if is_admin == 'true':
            user = User.objects.create_user(
                name=user_name,
                email=user_email,
                username=user_username,
                password=user_password,
                is_admin=True
            )

            try:
                user_intance = AccountManager.objects.get(pk=user.user_id)
            except AccountManager.DoesNotExist:
                messages.error(request, "User account not found.")
                return redirect('register-admin')
               

            AdminData.objects.create(
                admin_account=user_intance,
                username=user_username,
                name=user_name,
                email=user_email,
                is_admin=True
            )
        else:
            user = User.objects.create_user(
                name=user_name,
                email=user_email,
                username=user_username,
                password=user_password,
                is_admin=False
            )

            try:
                barangay_instance = Barangay.objects.get(pk=barangay_id)
            except Barangay.DoesNotExist:
                messages.error(request, "Invalid barangay selected.")
                return redirect('register-user')
              
            
            try:
                user_intance = AccountManager.objects.get(pk=user.user_id)
            except AccountManager.DoesNotExist:
                messages.error(request, "User account not found.")
                return redirect('register-user')
               

            UserData.objects.create(
                user_account=user_intance,
                barangay=barangay_instance,
                name=user_name,
                email=user_email,
                username=user_username,
                is_active=True,
                is_admin=False
            )

        desc = f'{"Admin" if is_admin == "true" else "User"} account successfully created for [{user.name}].'
        history_logger(request, user.name, 'REGISTER', desc)

        user.save()
        return redirect('manage-user')

    return JsonResponse({'success': False, 'message': 'Invalid request.'})

def is_admin(user):
    return user.is_authenticated and user.is_staff

def register_user(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        username = request.POST.get('username')
        email = request.POST.get('email')
        barangay_id = request.POST.get('barangay')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        
        # Basic validation
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('register-user')
        
        # Check if username or email already exists in TemporaryUser
        if TemporaryUser.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('register-user')
        
        if TemporaryUser.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect('register-user')
        
        
        if AccountManager.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect('register-user')
        
        try:

            barangay_instance = Barangay.objects.get(pk=barangay_id)
            
            temporary_user = TemporaryUser.objects.create(
                first_name=first_name,
                last_name=last_name,
                username=username,
                email=email,
                barangay=barangay_instance,
                password=make_password(password), 
                status='pending'
            )

            send_mail(
                "Registration - AI Dengue Hotspot Predictor",
                f"""Dear {first_name} {last_name},

Your registration request has been received and is pending admin approval.

Once approved, you will receive another email with login instructions.

Thank you for registering with AI Dengue Hotspot Predictor.

Best regards,
System Administrator""",
                "emailfromsettings@gmail.com",
                [email],
                fail_silently=False
            )
            
            messages.success(request, "Registration submitted successfully! Please wait for admin approval.")
            return redirect('register-user')
            
        except Barangay.DoesNotExist:
            messages.error(request, "Invalid barangay selected.")
        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
    
  
    barangays = Barangay.objects.all()
    return render(request, 'register_user.html', {'barangays': barangays})

def registration_success(request):
    return render(request, 'registration/success.html')

def register_admin(request):
    return render(request, 'register_admin.html')

from django.contrib.auth.decorators import login_required, user_passes_test

def admin_required(user):
    return user.is_authenticated and user.is_admin

@login_required
@user_passes_test(admin_required)
def pending_registrations(request):
    pending_users = TemporaryUser.objects.filter(status='pending').order_by('-created_at')
    return render(request, 'admin/pending_registrations.html', {'pending_users': pending_users})

@login_required
@user_passes_test(admin_required)
def approve_registration(request, temp_user_id):
    try:
        temp_user = TemporaryUser.objects.get(id=temp_user_id, status='pending')
        
        User = get_user_model()
        
       
        user = User.objects.create_user(
            name=f"{temp_user.first_name} {temp_user.last_name}",
            email=temp_user.email,
            username=temp_user.username,
            password=temp_user.password, 
            is_admin=False
        )

  
        try:
            user_instance = AccountManager.objects.get(pk=user.user_id)
        except AccountManager.DoesNotExist:
            messages.error(request, "User account not found.")
            return redirect('pending-registrations')


        UserData.objects.create(
            user_account=user_instance,
            barangay=temp_user.barangay,
            name=f"{temp_user.first_name} {temp_user.last_name}",
            email=temp_user.email,
            username=temp_user.username,
            is_active=True,
            is_admin=False
        )

        temp_user.status = 'approved'
        temp_user.save()

      
        desc = f'User registration approved for [{temp_user.first_name} {temp_user.last_name}].'
        history_logger(request, request.user.name, 'APPROVE_REGISTRATION', desc)

    
        messages.success(request, f"User {temp_user.username} approved successfully!")
        
    except TemporaryUser.DoesNotExist:
        messages.error(request, "Registration request not found.")
    except Exception as e:
        messages.error(request, f"Error approving registration: {str(e)}")
    
    return redirect('pending-registrations')

@login_required
@user_passes_test(admin_required)
def reject_registration(request, temp_user_id):
    try:
        temp_user = TemporaryUser.objects.get(id=temp_user_id, status='pending')
        temp_user.status = 'rejected'
        temp_user.save()

        desc = f'User registration rejected for [{temp_user.first_name} {temp_user.last_name}].'
        history_logger(request, request.user.name, 'REJECT_REGISTRATION', desc)


        messages.success(request, f"User {temp_user.username} registration rejected.")
        
    except TemporaryUser.DoesNotExist:
        messages.error(request, "Registration request not found.")
    
    return redirect('pending-registrations')


def logout_user(request):
    logout(request)
    return redirect('home')

def history_logger(request, user, title, description):
    LogHistory.objects.create(
        user=user,
        log_title=title,
        description=description
    )

def panel(request):
    if not request.user.is_authenticated:
        return redirect('login-admin')
    
    user = request.user
    if not user.is_admin:
        messages.error(request, "You do not have permission to access this page.")
        logout(request)
        return redirect('login')
    
    messages.info(request, 'Welcome to the dashboard, {}!'.format(user.username))
    
    return render(request, 'panel.html')

def report_view(request):
    user = request.user
    predictions = PredictionResult.objects.select_related('barangay').order_by('-prediction_result_id')
    
    unique_years = PredictionResult.objects.values_list('year_prediction', flat=True).distinct().order_by('-year_prediction')
    

    week_range = range(1, 53)
    
    return render(request, 'report.html', {
        'predictions': predictions,
        'unique_years': unique_years,
        'week_range': week_range,
        'admin_user': user.username,
        'admin_name': user.name,
    })

def download_predictions_csv(request):
    predictions = PredictionResult.objects.select_related('barangay').order_by('-prediction_result_id')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="prediction_results.csv"'

    writer = csv.writer(response)
    writer.writerow(['Barangay', 'Date', 'Risk Level','Numerical Risk', 'Confidence Score'])
    for p in predictions:
        writer.writerow([
            p.barangay.name if p.barangay else '',
            p.created_at.strftime('%Y-%m-%d'),
            p.risk_level,
            p.numerical_risk_level,
            str(p.confidence_score)
        ])
    return response
    

def forecast(request):
    """Display weather forecast from database with fallback to API"""
    user = request.user
    
    try:
      
        context = get_weather_from_database()
        
    
        if is_weather_data_stale():
          
            update_weather_data_async()
            
    except Exception as e:
       
        print(f"Error getting weather from database: {e}")
        context = get_weather_from_api_fallback()
    
    context.update({
        'admin_user': user.username,
        'admin_name': user.name,
    })
    
    return render(request, 'forecast.html', context)

def user_forecast(request):
    """Display weather forecast from database for regular users"""
    user_name = get_userInfo(request, 'name')
    user_username = get_userInfo(request, 'username')
    user_barangay = get_userInfo(request, 'barangay')
    
    try:
 
        context = get_weather_from_database()
    
        if is_weather_data_stale():
       
            update_weather_data_async()
            
    except Exception as e:
  
        print(f"Error getting weather from database: {e}")
        context = get_weather_from_api_fallback()
    
    context.update({
        'user_name': user_name,
        'user_username': user_username,
        'user_barangay': user_barangay,
        'data_source': context.get('data_source', 'database')
    })
    
    return render(request, 'user/forecast.html', context)

import pytz
from django.utils import timezone

def get_weather_from_database():
    """Get the latest weather data from database with Manila timezone"""
    manila_tz = pytz.timezone('Asia/Manila')
    
    try:
  
        now_manila = timezone.now().astimezone(manila_tz)
        
   
        current_weather = CurrentWeather.objects.all().order_by('-time').first()
        
       
        hourly_future = HourlyForecast.objects.filter(
            date__gte=now_manila
        ).order_by('date')[:24]
        
        if not hourly_future:
       
            hourly_future = HourlyForecast.objects.all().order_by('-date')[:24]
        

        daily_future = DailyForecast.objects.filter(
            date__gte=now_manila.date()
        ).order_by('date')[:15]
        
        if not daily_future:
    
            daily_future = DailyForecast.objects.all().order_by('-date')[:15]
        
   
        current_data = format_current_weather(current_weather, manila_tz) if current_weather else None
        hourly_list = format_hourly_forecast(hourly_future, manila_tz) if hourly_future else []
        daily_list = format_daily_forecast(daily_future, manila_tz) if daily_future else []
        
        return {
            'current': current_data,
            'hourly_list': hourly_list,
            'daily_list': daily_list,
            'data_source': 'database'
        }
        
    except Exception as e:
        print(f"Error getting weather from database: {e}")
        return {
            'current': None,
            'hourly_list': [],
            'daily_list': [],
            'data_source': 'database_error'
        }

def format_current_weather(current_weather, timezone=None):
    """Format current weather data for template with timezone support"""
    if timezone:

        manila_time = current_weather.time.astimezone(timezone)
        formatted_time = manila_time.strftime('%a %d %b %Y %I:%M %p')
    else:
        formatted_time = current_weather.time.strftime('%a %d %b %Y %I:%M %p')
    
    return {
        'location': current_weather.location if current_weather else "Unknown",
        'time': formatted_time,
        'temperature': round(current_weather.temperature, 1),
        'rainfall_chance': round(current_weather.rainfall_chance, 1),
        'humidity': round(current_weather.humidity, 1),
        'wind_speed_10m': round(current_weather.wind_speed_10m, 1),
        'weather_code': current_weather.weather_code,
        'is_day': current_weather.is_day,
        'updated_at': current_weather.created_at.astimezone(timezone).strftime('%Y-%m-%d %H:%M:%S') if timezone else current_weather.created_at.strftime('%Y-%m-%d %H:%M:%S')
    }

def format_hourly_forecast(hourly_forecast, timezone=None):
    """Format hourly forecast data for template with timezone support"""
    formatted_data = []
    for hour in hourly_forecast:
        if timezone:
     
            manila_date = hour.date.astimezone(timezone)
            formatted_date = manila_date.strftime('%a %d %b %Y %I:%M %p')
        else:
            formatted_date = hour.date.strftime('%a %d %b %Y %I:%M %p')
            
        formatted_data.append({
            'date': formatted_date,
            'temperature_2m': round(hour.temperature_2m, 1),
            'precipitation_probability': round(hour.rainfall_chance, 1),
            'relative_humidity_2m': round(hour.relative_humidity_2m, 1),
            'wind_speed_10m': round(hour.wind_speed_10m, 1),
            'weather_code': hour.weather_code,
            'is_day': hour.is_day,
            'location': hour.location
        })
    

    formatted_data.sort(key=lambda x: x['date'])
    return formatted_data

def format_daily_forecast(daily_forecast, timezone=None):
    """Format daily forecast data for template with timezone support"""
    formatted_data = []
    for day in daily_forecast:

        formatted_date = day.date.strftime('%a %d %b %Y')
            
        formatted_data.append({
            'date': formatted_date,
            'temperature_2m_max': round(day.temperature_2m_max, 1) if day.temperature_2m_max else None,
            'temperature_2m_min': round(day.temperature_2m_min, 1),
            'precipitation_probability_max': round(day.rainfall_chance_max, 1),
            'wind_speed_10m_max': round(day.wind_speed_10m_max, 1),
            'weather_code': day.weather_code,
            'avg_humidity': round(day.avg_humidity, 1) if day.avg_humidity else None,
            'location': day.location
        })
    

    formatted_data.sort(key=lambda x: x['date'])
    return formatted_data

def is_weather_data_stale():
    """Check if weather data needs updating using Manila timezone"""
    manila_tz = pytz.timezone('Asia/Manila')
    now_manila = timezone.now().astimezone(manila_tz)
    
   
    current_weather = CurrentWeather.objects.all().order_by('-time').first()
    
    if not current_weather:
        return True
    

    current_weather_time_manila = current_weather.created_at.astimezone(manila_tz)
    time_diff = now_manila - current_weather_time_manila
    
    return time_diff.total_seconds() > 3600 

def update_weather_data_async():
    """Update weather data in background (non-blocking)"""
    import threading
    
    def update_task():
        try:
            forecast_to_db()
            print("Weather data updated successfully in background")
        except Exception as e:
            print(f"Background weather update failed: {e}")
  
    thread = threading.Thread(target=update_task)
    thread.daemon = True
    thread.start()

def get_weather_from_api_fallback():
    """Fallback to API if database data is unavailable"""
    try:
        forecast_to_db()
        return get_weather_from_database()
    except Exception as e:
        
        print(f"API fallback failed: {e}")
        return {
            'current': get_current_weather(),
            'hourly_list': get_hourly_forecast(),
            'daily_list': get_daily_forecast(),
            'data_source': 'api_fallback'
        }

@require_POST
@login_required
def refresh_weather_data(request):
    """Manual endpoint to refresh weather data - accessible to all authenticated users"""
    try:
        forecast_to_db()
    except Exception as e:
        messages.error(request, f"Failed to refresh weather data: {str(e)}")
  
    if request.user.is_admin:
        return redirect('forecast')
    else:
        return redirect('user_forecast')


def get_current_weather():
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 14.6733,
        "longitude": 120.9397,
        "current": [
            "temperature_2m", "relative_humidity_2m", "precipitation_probability",
            "is_day", "wind_speed_10m", "weather_code"
        ],
        "timezone": "Asia/Manila",
    }
    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]
    current = response.Current()
   
    utc_dt = pd.to_datetime(current.Time(), unit="s", utc=True)
    manila_tz = pytz.timezone("Asia/Manila")
    local_dt = utc_dt.tz_convert(manila_tz)

    formatted_dt = local_dt.strftime('%a %d %b %Y %I:%M %p')
    weather_data = {
        "location": "Malabon",
        "rainfall_chance": round(current.Variables(2).Value(), 1),
        "temperature": round(current.Variables(0).Value(), 1),
        "humidity": round(current.Variables(1).Value(), 1),
        "is_day": current.Variables(3).Value(),
        "wind_speed_10m": round(current.Variables(4).Value(), 1),
        "weather_code": current.Variables(5).Value(),
        "time": formatted_dt,
    }
    return weather_data

def get_hourly_forecast():
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 14.6733,
        "longitude": 120.9397,
        "hourly": [
            "temperature_2m", "precipitation_probability", "wind_speed_10m",
            "relative_humidity_2m", "is_day", "weather_code"
        ],
        "timezone": "Asia/Manila",
    }
    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]
    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()
    hourly_precipitation_probability = hourly.Variables(1).ValuesAsNumpy()
    hourly_wind_speed_10m = hourly.Variables(2).ValuesAsNumpy()
    hourly_relative_humidity_2m = hourly.Variables(3).ValuesAsNumpy()
    hourly_is_day = hourly.Variables(4).ValuesAsNumpy()
    hourly_weather_code = hourly.Variables(5).ValuesAsNumpy()
    date_range = pd.date_range(
        start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
        end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=hourly.Interval()),
        inclusive="left"
    )

  
    manila_tz = pytz.timezone("Asia/Manila")
    date_range = date_range.tz_convert(manila_tz)

    length = min(
        len(date_range),
        len(hourly_temperature_2m),
        len(hourly_precipitation_probability),
        len(hourly_wind_speed_10m),
        len(hourly_relative_humidity_2m),
        len(hourly_is_day),
        len(hourly_weather_code)
    )
    hourly_data = {
        "date": date_range[:length],
        "temperature_2m": hourly_temperature_2m[:length],
        "precipitation_probability": hourly_precipitation_probability[:length],
        "wind_speed_10m": hourly_wind_speed_10m[:length],
        "relative_humidity_2m": hourly_relative_humidity_2m[:length],
        "is_day": hourly_is_day[:length],
        "weather_code": hourly_weather_code[:length],
    }
    hourly_dataframe = pd.DataFrame(data=hourly_data)
    hourly_24 = hourly_dataframe.head(24)
    hourly_list = hourly_24.to_dict(orient='records')
    for row in hourly_list:
        if isinstance(row['date'], pd.Timestamp):
       
            row['date'] = row['date'].strftime('%a %d %b %Y %I:%M %p')
        row['temperature_2m'] = round(row['temperature_2m'], 1)
        row['precipitation_probability'] = round(row['precipitation_probability'], 1)
        row['wind_speed_10m'] = round(row['wind_speed_10m'], 1)
        row['relative_humidity_2m'] = round(row['relative_humidity_2m'], 1)
    return hourly_list

def calculate_humidity_averages():
    """
    Calculate average humidity from 24 hourly values for each date
    """
    from django.db.models import Avg
   
    daily_without_humidity = DailyForecast.objects.filter(avg_humidity__isnull=True)
    
    for daily in daily_without_humidity:
   
        hourly_for_date = HourlyForecast.objects.filter(date__date=daily.date)
        
        print(f"Date: {daily.date}, Found {hourly_for_date.count()} hourly records")
    
        hourly_avg = hourly_for_date.aggregate(avg_humidity=Avg('relative_humidity_2m'))
        
        avg_value = hourly_avg['avg_humidity']
        print(f"Calculated average humidity: {avg_value}")
        

        if avg_value is not None:
            daily.avg_humidity = round(avg_value, 2)
            daily.save()
            print(f"Updated DailyForecast for {daily.date} with avg humidity: {daily.avg_humidity}")


def get_daily_forecast():
    cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": 14.6733,
        "longitude": 120.9397,
        "daily": [
            "precipitation_probability_max", "temperature_2m_max", "temperature_2m_min",
            "wind_speed_10m_max", "weather_code",
        ],
        "forecast_days": 15,
        "timezone": "Asia/Manila",
    }
    responses = openmeteo.weather_api(url, params=params)
    response = responses[0]
    daily = response.Daily()
    daily_precipitation_probability_max = daily.Variables(0).ValuesAsNumpy()
    daily_temperature_2m_max = daily.Variables(1).ValuesAsNumpy()
    daily_temperature_2m_min = daily.Variables(2).ValuesAsNumpy()
    daily_wind_speed_10m_max = daily.Variables(3).ValuesAsNumpy()
    daily_weather_code = daily.Variables(4).ValuesAsNumpy()
    daily_date_range = pd.date_range(
        start=pd.to_datetime(daily.Time(), unit="s", utc=True),
        end=pd.to_datetime(daily.TimeEnd(), unit="s", utc=True),
        freq=pd.Timedelta(seconds=daily.Interval()),
        inclusive="left"
    )
  
    manila_tz = pytz.timezone("Asia/Manila")
    daily_date_range = daily_date_range.tz_convert(manila_tz)
    daily_length = min(
        len(daily_date_range),
        len(daily_precipitation_probability_max),
        len(daily_temperature_2m_max),
        len(daily_temperature_2m_min),
        len(daily_wind_speed_10m_max),
        len(daily_weather_code)
    )
    daily_data = {
        "date": daily_date_range[:daily_length],
        "precipitation_probability_max": daily_precipitation_probability_max[:daily_length],
        "temperature_2m_max": daily_temperature_2m_max[:daily_length],
        "temperature_2m_min": daily_temperature_2m_min[:daily_length],
        "wind_speed_10m_max": daily_wind_speed_10m_max[:daily_length],
        "weather_code": daily_weather_code[:daily_length],
    }
    daily_dataframe = pd.DataFrame(data=daily_data)
    daily_list = daily_dataframe.to_dict(orient='records')
    for row in daily_list:
        if isinstance(row['date'], pd.Timestamp):
 
            row['date'] = row['date'].strftime('%a %d %b %Y')
        row['precipitation_probability_max'] = round(row['precipitation_probability_max'], 1)
        row['temperature_2m_max'] = round(row['temperature_2m_max'], 1)
        row['temperature_2m_min'] = round(row['temperature_2m_min'], 1)
        row['wind_speed_10m_max'] = round(row['wind_speed_10m_max'], 1)
    return daily_list

def calculate_weekly_averages():
    """
    Calculate weekly averages from daily data and save to WeeklyAverage model
    """
    from django.db.models import Avg, Max, Min
    from datetime import timedelta

    daily_data = DailyForecast.objects.all().order_by('date')
    
    if not daily_data.exists():
        print("No daily data found")
        return
    
    weekly_data = {}

    for daily in daily_data:
        year = daily.date.isocalendar()[0]
        week = daily.date.isocalendar()[1]
        week_key = f"{year}-{week}"
        
        if week_key not in weekly_data:
    
            start_date = daily.date - timedelta(days=daily.date.weekday())
            end_date = start_date + timedelta(days=6)
            
            weekly_data[week_key] = {
                'year': year,
                'week': week,
                'start_date': start_date,
                'end_date': end_date,
                'temperatures': [],
                'humidity': [],
                'rainfall': [],
                'wind_speed': [],
                'dates': []
            }

        if daily.temperature_2m_max:
            weekly_data[week_key]['temperatures'].append(float(daily.temperature_2m_max))
        if daily.avg_humidity:
            weekly_data[week_key]['humidity'].append(float(daily.avg_humidity))
        if daily.rainfall_chance_max:
            weekly_data[week_key]['rainfall'].append(float(daily.rainfall_chance_max))
        if daily.wind_speed_10m_max:
            weekly_data[week_key]['wind_speed'].append(float(daily.wind_speed_10m_max))
        
        weekly_data[week_key]['dates'].append(daily.date)

    for week_key, data in weekly_data.items():

        avg_temp = sum(data['temperatures']) / len(data['temperatures']) if data['temperatures'] else None
        avg_humidity = sum(data['humidity']) / len(data['humidity']) if data['humidity'] else None
        avg_rainfall = sum(data['rainfall']) / len(data['rainfall']) if data['rainfall'] else None
        avg_wind = sum(data['wind_speed']) / len(data['wind_speed']) if data['wind_speed'] else None

        max_temp = max(data['temperatures']) if data['temperatures'] else None
        min_temp = min(data['temperatures']) if data['temperatures'] else None
        total_rainy_days = len([r for r in data['rainfall'] if r > 50]) if data['rainfall'] else 0  # Days with >50% rain chance
        
  
        WeeklyAverage.objects.update_or_create(
            location="Malabon",
            year=data['year'],
            week=data['week'],
            defaults={
                'start_date': data['start_date'],
                'end_date': data['end_date'],
                'avg_temperature': round(avg_temp, 2) if avg_temp else None,
                'avg_humidity': round(avg_humidity, 2) if avg_humidity else None,
                'avg_rainfall_chance': round(avg_rainfall, 2) if avg_rainfall else None,
                'avg_wind_speed': round(avg_wind, 2) if avg_wind else None,
                'max_temperature': round(max_temp, 2) if max_temp else None,
                'min_temperature': round(min_temp, 2) if min_temp else None,
                'total_rainy_days': total_rainy_days,
            }
        )
        
        print(f"Week {data['year']}-{data['week']}: {data['start_date']} to {data['end_date']}")
        print(f"  Days: {len(data['dates'])} | Temp: {round(avg_temp, 1) if avg_temp else 'N/A'}°C | Humidity: {round(avg_humidity, 1) if avg_humidity else 'N/A'}%")
        print()
    
    print(f"Weekly averages calculated for {len(weekly_data)} weeks")

def calculate_recent_weekly_averages():
    """
    Automatically calculate weekly averages for the last 3 weeks if they don't exist
    """
    from datetime import datetime, timedelta
    from django.db.models import Avg, Max, Min
    
    today = datetime.now().date()
    current_year = today.isocalendar()[0]
    current_week = today.isocalendar()[1]
    
    weeks_to_check = []
    for i in range(3):  
        week_offset = today - timedelta(weeks=i)
        year = week_offset.isocalendar()[0]
        week = week_offset.isocalendar()[1]
        weeks_to_check.append((year, week))
    
    print(f"Checking weeks: {weeks_to_check}")
    
    for year, week in weeks_to_check:
   
        if WeeklyAverage.objects.filter(year=year, week=week).exists():
            print(f"Week {year}-{week} already exists, skipping...")
            continue
        
    
        sample_date = None
        daily_in_week = DailyForecast.objects.filter(
            date__week=week,
            date__year=year
        ).first()
        
        if daily_in_week:
            sample_date = daily_in_week.date
        else:
   
            sample_date = today - timedelta(weeks=weeks_to_check.index((year, week)))
        
        start_date = sample_date - timedelta(days=sample_date.weekday())
        end_date = start_date + timedelta(days=6)
  
        daily_data = DailyForecast.objects.filter(
            date__range=[start_date, end_date]
        )
        
        if not daily_data.exists():
            print(f"No daily data found for week {year}-{week} ({start_date} to {end_date})")
            continue
   
        temperatures = []
        humidity = []
        rainfall = []
        wind_speed = []
        
        for daily in daily_data:
            if daily.temperature_2m_max:
                temperatures.append(float(daily.temperature_2m_max))
            if daily.avg_humidity:
                humidity.append(float(daily.avg_humidity))
            if daily.rainfall_chance_max:
                rainfall.append(float(daily.rainfall_chance_max))
            if daily.wind_speed_10m_max:
                wind_speed.append(float(daily.wind_speed_10m_max))

        avg_temp = sum(temperatures) / len(temperatures) if temperatures else None
        avg_humidity = sum(humidity) / len(humidity) if humidity else None
        avg_rainfall = sum(rainfall) / len(rainfall) if rainfall else None
        avg_wind = sum(wind_speed) / len(wind_speed) if wind_speed else None
        
        max_temp = max(temperatures) if temperatures else None
        min_temp = min(temperatures) if temperatures else None
        total_rainy_days = len([r for r in rainfall if r > 50]) if rainfall else 0
        

        WeeklyAverage.objects.create(
            location="Malabon",
            year=year,
            week=week,
            start_date=start_date,
            end_date=end_date,
            avg_temperature=round(avg_temp, 2) if avg_temp else None,
            avg_humidity=round(avg_humidity, 2) if avg_humidity else None,
            avg_rainfall_chance=round(avg_rainfall, 2) if avg_rainfall else None,
            avg_wind_speed=round(avg_wind, 2) if avg_wind else None,
            max_temperature=round(max_temp, 2) if max_temp else None,
            min_temperature=round(min_temp, 2) if min_temp else None,
            total_rainy_days=total_rainy_days,
        )
        
        print(f"✅ Created weekly average for {year}-{week}: {start_date} to {end_date}")
        print(f"   Days: {len(daily_data)} | Temp: {round(avg_temp, 1) if avg_temp else 'N/A'}°C | Humidity: {round(avg_humidity, 1) if avg_humidity else 'N/A'}%")
    
    print("Recent weekly averages check completed!")


def forecast_to_db():
    current_weather_data = get_current_weather()
    hourly_forecast_data = get_hourly_forecast()
    daily_forecast_data = get_daily_forecast()

    CurrentWeather.objects.update_or_create(
        location=current_weather_data['location'],
        time=datetime.strptime(current_weather_data['time'], '%a %d %b %Y %I:%M %p'),
        defaults={
            'rainfall_chance': current_weather_data['rainfall_chance'],
            'temperature': current_weather_data['temperature'],
            'humidity': current_weather_data['humidity'],
            'is_day': current_weather_data['is_day'],
            'wind_speed_10m': current_weather_data['wind_speed_10m'],
            'weather_code': current_weather_data['weather_code'],
        }
    )

    for hour in hourly_forecast_data:
        HourlyForecast.objects.update_or_create(
            location="Malabon",
            date=datetime.strptime(hour['date'], '%a %d %b %Y %I:%M %p'),
            defaults={
                'temperature_2m': hour['temperature_2m'],
                'rainfall_chance': hour['precipitation_probability'],
                'wind_speed_10m': hour['wind_speed_10m'],
                'relative_humidity_2m': hour['relative_humidity_2m'],
                'is_day': hour['is_day'],
                'weather_code': hour['weather_code'],
            }
        )

    for day in daily_forecast_data:
        DailyForecast.objects.update_or_create(
            location="Malabon",
            date=datetime.strptime(day['date'], '%a %d %b %Y'),
            defaults={
                'rainfall_chance_max': day['precipitation_probability_max'],
                'temperature_2m_max': day['temperature_2m_max'],
                'temperature_2m_min': day['temperature_2m_min'],
                'wind_speed_10m_max': day['wind_speed_10m_max'],
                'weather_code': day['weather_code'],
            }
        )
    
    calculate_recent_humidity()
   
    calculate_recent_weekly_averages()
    
    print("Weather data has been updated in the database.")

def calculate_recent_humidity():
    """
    Calculate average humidity for DailyForecast records from the last 7 days
    """
    from django.db.models import Avg
    from datetime import datetime, timedelta
    
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=7)
  
    recent_daily = DailyForecast.objects.filter(date__range=[start_date, end_date])
    
    for daily in recent_daily:
  
        hourly_avg = HourlyForecast.objects.filter(
            date__date=daily.date
        ).aggregate(avg_humidity=Avg('relative_humidity_2m'))
        
        if hourly_avg['avg_humidity'] is not None:
            daily.avg_humidity = round(hourly_avg['avg_humidity'], 2)
            daily.save()
            print(f"Updated humidity for {daily.date}: {daily.avg_humidity}%")



def save_forecast_to_db_get(request):
    try:
        forecast_to_db()
        messages.success(request, "Weather data successfully saved to database.")
    except Exception as e:
        messages.error(request, f"Error saving weather data: {str(e)}")
    return redirect('test-forecast')



def admin_panel(request):
    if not request.user.is_authenticated:
        return redirect('login-admin')
    
    user = request.user
    if not user.is_admin:
        messages.error(request, "You do not have permission to access this page.")
        logout(request)
        return redirect('login')

    current_date = datetime.now()
    current_year = current_date.year
    current_week = current_date.isocalendar().week
    
    next_week = current_week + 1
    next_next_week = current_week + 2
    
    prediction_result = PredictionResult.objects.filter(
        year_prediction=current_year,
        week_prediction=current_week
    ).select_related('barangay').order_by('barangay__name')

    next_week_predictions = PredictionResult.objects.filter(
        year_prediction=current_year,
        week_prediction=next_week
    ).select_related('barangay').order_by('barangay__name')

    next_next_week_predictions = PredictionResult.objects.filter(
        year_prediction=current_year,
        week_prediction=next_next_week
    ).select_related('barangay').order_by('barangay__name')

    weather_data = get_current_weather()
    is_admin = request.user.is_admin

    return render(request, 'admin-panel.html', {
        'weather': weather_data,
        'prediction_result': prediction_result,
        'next_week_predictions': next_week_predictions,
        'next_next_week_predictions': next_next_week_predictions,
        'latest_year': current_year,
        'latest_week': current_week,
        'is_admin': is_admin,
        'current_week': current_week,
        'next_week': next_week,
        'next_next_week': next_next_week,
        'admin_user': user.username,
        'admin_name': user.name,
    })

# =====================================
# log history view
def log_history(request):
    if not request.user.is_authenticated:
        return redirect('login-admin')
    
    user = request.user
    if not user.is_admin:
        messages.error(request, "You do not have permission to access this page.")
        logout(request)
        return redirect('login')

    logs = LogHistory.objects.order_by('-timestamp')  
    return render(request, 'log_history.html', {
        'logs': logs,
        'admin_user': user.username,
        'admin_name': user.name,
    })

# ====================================
# manage user

def manage_user(request):
    if not request.user.is_authenticated or not request.user.is_admin:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('login-admin')
    User = get_user_model()
    users = User.objects.all()
    user_data = UserData.objects.all()
    Barangays = Barangay.objects.all()

    user = request.user
    return render(request, 'manage-user.html', {
        'users': users,
        'user_datas': user_data, 
        'barangays': Barangays,
        'admin_user': user.username,
        'admin_name': user.name,
    })

def create_user(request):
    if request.method == 'POST':
        User = get_user_model()
        name = request.POST.get('name')
        email = request.POST.get('email')
        username = request.POST.get('username')
        password = request.POST.get('password')
        is_admin = request.POST.get('is_admin') == 'on'
        if not all([name, email, username, password]):
            messages.error(request, "All fields are required.")
            return redirect('manage-user')
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('manage-user')
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect('manage-user')
        user = User.objects.create_user(
            name=name,
            email=email,
            username=username,
            password=password,
            is_admin=is_admin
        )
        desc = f'{"Admin" if is_admin == "true" else "User"} account successfully created for [{user.name}].'
        history_logger(request, user.name, 'REGISTER', desc)
        messages.success(request, "User created successfully.")
        return redirect('manage-user')
    return redirect('manage-user')


from django.core.exceptions import PermissionDenied

@login_required
def edit_profile(request):
    """User editing their own profile"""
    user_to_edit = request.user
    is_editing_self = True

  
    user_data = None
    user_type = 'user'
    
    try:
        if user_to_edit.is_admin:
            user_data = AdminData.objects.get(admin_account=user_to_edit)
            user_type = 'admin'
        else:
            user_data = UserData.objects.get(user_account=user_to_edit)
            user_type = 'user'
    except (AdminData.DoesNotExist, UserData.DoesNotExist):
        user_data = None

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        username = request.POST.get('username')

        if not all([name, email, username]):
            messages.error(request, "All fields are required.")
            return redirect('edit-profile')

        try:
   
            user_to_edit.name = name
            user_to_edit.email = email
            user_to_edit.username = username
            user_to_edit.save()

    
            if user_data:
                user_data.name = name
                user_data.email = email
                user_data.username = username
                user_data.save()
            else:
 
                if user_to_edit.is_admin:
                    user_data = AdminData.objects.create(
                        admin_account=user_to_edit,
                        username=username,
                        name=name,
                        email=email,
                        is_admin=True
                    )
                else:
               
                    barangay_instance = Barangay.objects.first() 
                    
                    user_data = UserData.objects.create(
                        user_account=user_to_edit,
                        barangay=barangay_instance,
                        name=name,
                        email=email,
                        username=username,
                        is_active=True,
                        is_admin=False
                    )


            desc = f'User [{user_to_edit.name}] updated their own profile information.'
            history_logger(request, user_to_edit.name, 'UPDATE_PROFILE', desc)
            messages.success(request, "Your profile has been updated successfully!")
            return redirect('edit-profile')

        except Exception as e:
            error_msg = f"Error updating profile: {str(e)}"
            messages.error(request, error_msg)
            history_logger(request, user_to_edit.name, 'UPDATE_PROFILE_ERROR', error_msg)
            return redirect('edit-profile')


    context = {
        'user': user_to_edit,
        'user_data': user_data,
        'user_type': user_type,
    }
    

    if user_to_edit.is_admin:
        context.update({
            'admin_user': user_to_edit.username,
            'admin_name': user_to_edit.name,
        })
    else:

        user_barangay_name = None
        if user_data and user_data.barangay:
            user_barangay_name = user_data.barangay.name
            
        context.update({
            'user_name': user_to_edit.name or user_to_edit.username,
            'user_username': user_to_edit.username,
            'user_barangay': user_barangay_name,
        })

    return render(request, 'edit_profile.html', context)

@login_required
def edit_user(request, user_id):
    """Admin editing another user's profile"""
    if not request.user.is_admin:
        raise PermissionDenied("You do not have permission to edit other users.")
    
    User = get_user_model()
    user_to_edit = get_object_or_404(User, pk=user_id)
    is_editing_self = (user_to_edit == request.user)

    user_data = None
    user_type = 'user'
    
    try:
        if user_to_edit.is_admin:
            user_data = AdminData.objects.get(admin_account=user_to_edit)
            user_type = 'admin'
        else:
            user_data = UserData.objects.get(user_account=user_to_edit)
            user_type = 'user'
    except (AdminData.DoesNotExist, UserData.DoesNotExist):
        user_data = None

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        username = request.POST.get('username')
     
        barangay_id = request.POST.get('barangay') if not user_to_edit.is_admin else None
        
     
        if not all([name, email, username]):
            messages.error(request, "All fields are required.")
            return redirect('edit-user', user_id=user_id)

        try:
        
            user_to_edit.name = name
            user_to_edit.email = email
            user_to_edit.username = username
            user_to_edit.save()

       
            if user_data:
                user_data.name = name
                user_data.email = email
                user_data.username = username
                
             
                if not user_to_edit.is_admin and barangay_id:
                    try:
                        barangay_instance = Barangay.objects.get(pk=barangay_id)
                        user_data.barangay = barangay_instance
                    except Barangay.DoesNotExist:
                        messages.error(request, "Invalid barangay selected.")
                        return redirect('edit-user', user_id=user_id)
                
                user_data.save()
            else:
          
                if user_to_edit.is_admin:
                    user_data = AdminData.objects.create(
                        admin_account=user_to_edit,
                        username=username,
                        name=name,
                        email=email,
                        is_admin=True
                    )
                else:
               
                    barangay_instance = Barangay.objects.first()
                    if barangay_id:
                        try:
                            barangay_instance = Barangay.objects.get(pk=barangay_id)
                        except Barangay.DoesNotExist:
                            pass
                    
                    user_data = UserData.objects.create(
                        user_account=user_to_edit,
                        barangay=barangay_instance,
                        name=name,
                        email=email,
                        username=username,
                        is_active=True,
                        is_admin=False
                    )

            # Log the action
            desc = f'Admin [{request.user.name}] updated user [{user_to_edit.name}]\'s profile.'
            history_logger(request, request.user.name, 'UPDATE_USER', desc)
            messages.success(request, f"User {user_to_edit.name} updated successfully!")
            return redirect('manage-user')

        except Exception as e:
            error_msg = f"Error updating user data: {str(e)}"
            messages.error(request, error_msg)
            history_logger(request, request.user.name, 'UPDATE_USER_ERROR', error_msg)
            return redirect('edit-user', user_id=user_id)

   
    barangays = Barangay.objects.all() if not user_to_edit.is_admin else None
    
  
    context = {
        'user': user_to_edit,
        'user_data': user_data,
        'barangays': barangays,
        'user_type': user_type,
        'is_editing_self': is_editing_self,
        'is_admin_editing': True,
        'admin_user': request.user.username,
        'admin_name': request.user.name,
    }

    return render(request, 'edit-user.html', context)

def delete_user(request, user_id):
    User = get_user_model()
    user = get_object_or_404(User, pk=user_id)
    user.delete()
    desc = f'{"Admin" if user.is_admin == "true" else "User"} [{user.name}] successfully deleted from database.'
    history_logger(request, user.name, 'DELETE', desc)
    messages.success(request, "User deleted successfully.")
    return redirect('manage-user')

# ====================================
# dengue prediction view

from backend.zCode.predict import *

def predict_view(request):
    # get latest year/week from PredictionResult table
    latest = PredictionResult.objects.order_by('-year_prediction', '-week_prediction').first()
    if latest:
        latest_year = latest.year_prediction
        latest_week = latest.week_prediction
        predictions = PredictionResult.objects.filter(
            year_prediction=latest_year,
            week_prediction=latest_week
        ).select_related('barangay').order_by('-confidence_score')
    else:
        latest_year = latest_week = None
        predictions = PredictionResult.objects.none()


    print("Predictions count:", predictions.count() if hasattr(predictions, "count") else len(predictions))
    for p in predictions[:10]:
        print(p.barangay.name, p.year_prediction, p.week_prediction, p.confidence_score)

    return render(request, 'predict.html', {
        'predictions': predictions,
        'latest_year': latest_year,
        'latest_week': latest_week,
    })

@require_POST
def run_prediction_view(request):

    if not request.user.is_authenticated or not getattr(request.user, "is_admin", False):
        messages.error(request, "You do not have permission to run predictions.")
        return redirect('login-admin')

    try:
        
        from backend.zCode.predict import fetch_historical_weather, predict_dengue_risk


        predict_dengue_risk()

        messages.success(request, "Prediction process completed successfully.")
    except Exception as e:
        messages.error(request, f"Prediction failed: {e}")

    return redirect('predict') 


def dashboard(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    if request.user.is_admin:
        messages.error(request, "Admin users must access the admin panel.")
        return redirect('login-admin')

    user_barangay_id = get_userInfo(request, 'barangay_id')
 
    latest_case = PredictionResult.objects.order_by('-year_prediction', '-week_prediction').first()
    if latest_case:
        latest_year = latest_case.year_prediction
        latest_week = latest_case.week_prediction
        
        current_week = datetime.now().isocalendar().week
        next_week = current_week + 1 if current_week < 52 else 1
        next_next_week = current_week + 2 if current_week < 51 else (2 if current_week == 52 else 1)
     
        user_prediction = PredictionResult.objects.filter(
            barangay_id=user_barangay_id,
            year_prediction=latest_year,
            week_prediction=current_week
        ).first()
        user_prediction_next = PredictionResult.objects.filter(
            barangay_id=user_barangay_id,
            year_prediction=latest_year,
            week_prediction=next_week
        ).first()
        user_prediction_next_next = PredictionResult.objects.filter(
            barangay_id=user_barangay_id,
            year_prediction=latest_year,
            week_prediction=next_next_week
        ).first()
      
        if not user_prediction:
            user_prediction = PredictionResult.objects.filter(
                barangay_id=user_barangay_id
            ).order_by('-created_at').first()
    else:
        latest_year = None
        latest_week = None
        current_week = None
        next_week = None
        next_next_week = None
        user_prediction = None

    latest_dengue_cases = DengueCase.objects.filter(
        barangay_id=user_barangay_id
    ).order_by('-year_reported', '-week_reported')[:5]

    weather_data = get_current_weather()

    prediction_result = PredictionResult.objects.filter(
        year_prediction=latest_year
    )

    user_name = get_userInfo(request, 'name')
    user_username = get_userInfo(request, 'username')
    user_barangay = get_userInfo(request, 'barangay')
    user_barangay_lat = get_userInfo(request, 'barangay_lat')
    user_barangay_long = get_userInfo(request, 'barangay_long')
    is_admin = request.user.is_admin

    return render(request, 'user/dashboard.html', {
        'weather': weather_data,
        'user_prediction': user_prediction,
        'user_prediction_next': user_prediction_next,
        'user_prediction_next_next': user_prediction_next_next,
        'prediction_result': prediction_result,
        'latest_year': latest_year,
        'latest_week': latest_week,
        'user_name': user_name,
        'user_username': user_username,
        'user_barangay': user_barangay,
        'user_barangay_lat': user_barangay_lat,
        'user_barangay_long': user_barangay_long,
        'is_admin': is_admin,
        'latest_dengue_cases': latest_dengue_cases,
        'current_week': current_week,
        'next_week': next_week,
        'next_next_week': next_next_week,
    })

def get_userInfo(request, col):

    # Fetch UserData for the current user
    try:
        user_data = UserData.objects.get(user_account=request.user)  # Changed from user to user_account
    except UserData.DoesNotExist:
        user_data = None

    user_info = {
        'name': getattr(request.user, 'name', request.user.username),  # Fallback to username
        'username': request.user.username,
        'email': request.user.email,
        'barangay': user_data.barangay.name if user_data and user_data.barangay else None,
        'barangay_id': user_data.barangay.barangay_id if user_data and user_data.barangay else None,
        'barangay_lat': user_data.barangay.latitude if user_data and user_data.barangay else None,
        'barangay_long': user_data.barangay.longitude if user_data and user_data.barangay else None,
    }
    return user_info.get(col, None)


# =======================
# user/ report view

def user_report_view(request):
    # Order predictions A-Z by barangay name
    prediction_result = PredictionResult.objects.select_related('barangay').order_by('barangay__name')
    
    user_name = get_userInfo(request, 'name')
    user_username = get_userInfo(request, 'username')
    user_barangay = get_userInfo(request, 'barangay')

    return render(request, 'user/report.html', {
        'predictions': prediction_result,
        'user_name': user_name,
        'user_username': user_username,
        'user_barangay': user_barangay,
    })

def upload_csv_report(request):
    if request.method == 'POST':
        print("POST data:", request.POST)  # Debug
        print("FILES data:", request.FILES)  # Debug
        
        csv_file = request.FILES.get('file')
        year = request.POST.get('year')
        
        print(f"File: {csv_file}, Year: {year}")  # Debug
        
        # Check if file exists
        if not csv_file:
            messages.error(request, 'No file was selected')
            return redirect('user-report')
        
        # Check if year is provided
        if not year:
            messages.error(request, 'Please specify the year')
            return redirect('user-report')
        
        # Validate file type
        if not csv_file.name.lower().endswith('.csv'):
            messages.error(request, 'Please upload a CSV file')
            return redirect('user-report')
            
        try:
            # Process the file
            data_set = csv_file.read().decode('UTF-8')
            io_string = io.StringIO(data_set)
                
            success_count, error_count = process_dengue_csv(io_string, year)
                
            messages.success(
                request, 
                f'Successfully imported {success_count} records. {error_count} errors.'
            )
                
        except Exception as e:
            messages.error(request, f'Error processing file: {str(e)}')
            print(f"Error: {str(e)}")  # Debug
    
    return redirect('user-report')

def submit_manual_report(request):
    if request.method == 'POST':
        # Debug: Log incoming POST data
        print(f"DEBUG: POST data - year='{request.POST.get('year')}', week='{request.POST.get('week')}', cases='{request.POST.get('cases')}'")  # Simple print for quick console debug

        year = request.POST.get('year')
        week = request.POST.get('week')
        case_str = request.POST.get('cases', '')  # Get cases as string, default to empty

        # Validation: Check required fields
        if not year or not week:
            messages.error(request, "Year and week are required.")
            return redirect('user-report')

        try:
            year = int(year)
            week = int(week)
            # Handle cases: Convert to int, default to 0 if empty or invalid
            case = int(case_str) if case_str and case_str.strip() else 0
            # Debug: Log parsed values
            print(f"DEBUG: Parsed - year={year}, week={week}, cases={case}")
        except ValueError as e:
            messages.error(request, "Year, week, and cases must be valid integers.")
            print(f"DEBUG ERROR: ValueError - {e}")
            return redirect('user-report')  # Consistent redirect to form page on error

        # Get user's barangay (assuming get_userInfo is defined and returns the barangay object or ID)
        user_barangay = get_userInfo(request, 'barangay_id')
        if not user_barangay:
            messages.error(request, "Unable to determine your barangay. Please contact support.")
            print("DEBUG ERROR: User barangay is None or invalid.")
            return redirect('user-report')

        # Debug: Log barangay
        print(f"DEBUG: User barangay = {user_barangay}")

        try:
            user_data = UserData.objects.get(user_account=request.user)  # Changed from user to user_account
        except UserData.DoesNotExist:
            user_data = None

        # Check existence: Include barangay in filter to avoid duplicates per user/barangay
        is_exist = DengueCase.objects.filter(
            barangay=get_userInfo(request, 'barangay_id'),
            year_reported=year,
            week_reported=week
        ).exists()


        if is_exist:
            messages.warning(request, f"A report for {year} week {week} in your barangay already exists.")
            print(f"DEBUG: Duplicate report exists for year={year}, week={week}, barangay={user_barangay}")
            
            # update existing report instead
            DengueCase.objects.update_or_create(
                barangay=user_data.barangay,
                year_reported=year,
                week_reported=week,
                num_cases=case,
            )

        else:
            # Create the report
            DengueCase.objects.create(
                barangay=user_data.barangay,
                year_reported=year,
                week_reported=week,
                num_cases=case,
            )
            messages.success(request, f"Report for {year} week {week} submitted successfully with {case} case(s).")
            print(f"DEBUG: New report created - year={year}, week={week}, cases={case}, barangay={user_barangay}")

    # Fallback redirect (shouldn't reach here on POST success, but for safety)
    return redirect('user-report')


def download_dengue_template(request):
    """Download a CSV template for dengue data"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="dengue_template.csv"'
    
    writer = csv.writer(response)
    
    # Create template headers (WEEK 1 to WEEK 10)
    headers = ['BARANGAY'] + [f'WEEK {i}' for i in range(1, 11)]
    writer.writerow(headers)
    
    # Add example row
    example_row = ['Your Barangay Name'] + ['0'] * 10
    writer.writerow(example_row)
    
    return response

# =======================
# messaging functionality

def user_message(request):
    admins = AdminData.objects.select_related('admin_account').all()
    messages = Message.objects.filter(
        Q(recipient=request.user.username) | Q(sender=request.user.username)
    ).order_by('-timestamp')

    if request.method == 'POST':
        sender = request.user.username  # Use username instead of user object
        sender_barangay = get_userInfo(request, 'barangay')
        sender_merge = f"{sender} ({sender_barangay})" if sender_barangay else sender
        recipient = request.POST.get('recipient')
        subject = request.POST.get('subject')
        message_body = request.POST.get('message')  # Renamed to avoid conflict with messages variable

        Message.objects.create(
            sender=sender,  # Use the formatted sender string
            recipient=recipient,
            subject=subject,
            body=message_body
        )
        return redirect('user-message')

    user_name = get_userInfo(request, 'name')
    user_username = get_userInfo(request, 'username')
    user_barangay = get_userInfo(request, 'barangay')

    return render(request, 'user/message.html', {
        'admins': admins,
        'messages': messages,
        'user_name': user_name,
        'user_username': user_username,
        'user_barangay': user_barangay,
    })

def admin_message(request):
    users = UserData.objects.select_related('user_account').all()
    messages = Message.objects.filter(
        Q(recipient=request.user.username) | Q(sender=request.user.username)
    ).order_by('-timestamp')

    if request.method == 'POST':
        sender = request.user.username  # Use username instead of user object
        sender_barangay = get_userInfo(request, 'barangay')
        sender_merge = f"{sender} ({sender_barangay})" if sender_barangay else sender
        recipient = request.POST.get('recipient')
        subject = request.POST.get('subject')
        message_body = request.POST.get('message')  # Renamed to avoid conflict

        Message.objects.create(
            sender=sender,  # Use the formatted sender string
            recipient=recipient,
            subject=subject,
            body=message_body
        )
        return redirect('admin-message')

    user = request.user
    return render(request, 'message.html', {
        'users': users,
        'messages': messages,
        'admin_user': user.username,
        'admin_name': user.name,
    })

@require_POST
@csrf_exempt
def delete_message(request, message_id):
    try:
        message = Message.objects.get(id=message_id)
        
        # Optional: Check if the user has permission to delete this message
        # Only allow deletion if the user is either the sender or recipient
        if (message.sender == request.user.username or 
            message.recipient == request.user.username or
            request.user.username in message.sender or
            request.user.username in message.recipient):
            
            message.delete()
            return JsonResponse({'status': 'success', 'message': 'Message deleted successfully'})
        else:
            return JsonResponse({'status': 'error', 'message': 'You do not have permission to delete this message'})
            
    except Message.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Message not found'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@require_POST
@csrf_exempt
def mark_message_read(request, message_id):
    if request.method == 'POST':
        try:
            message = Message.objects.get(id=message_id)
            message.is_read = True
            message.save()
            return JsonResponse({'status': 'success'})
        except Message.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Message not found'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})


# test import funtion

import csv
import io
from django.db import transaction
from .forms import DengueDataImportForm

def import_dengue_data(request):
    if request.method == 'POST':
        form = DengueDataImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            year = form.cleaned_data['year']
            
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Please upload a CSV file')
                return redirect('import-dengue-data')
            
            try:
                data_set = csv_file.read().decode('UTF-8')
                io_string = io.StringIO(data_set)
                
                success_count, error_count = process_dengue_csv(io_string, year)
                
                messages.success(
                    request, 
                    f'Successfully imported {success_count} records. {error_count} errors.'
                )
                
            except Exception as e:
                messages.error(request, f'Error processing file: {str(e)}')
                
            return redirect('import-dengue-data')  # Redirect to cases list view
    
    else:
        form = DengueDataImportForm()
    
    return render(request, 'import_dengue_data.html', {'form': form})

def process_dengue_csv(io_string, year):
    reader = csv.DictReader(io_string)
    success_count = 0
    error_count = 0
    
    with transaction.atomic():
        for row in reader:
            try:
                barangay_name = row.get('BARANGAY', '').strip()
                if not barangay_name:
                    continue
                
                barangay, created = Barangay.objects.get_or_create(
                    name=barangay_name,
                    defaults={'name': barangay_name}
                )
                
                for week_num in range(1, 53):
                    week_column = f'WEEK {week_num}'
                    if week_column in row:
                        try:
                            num_cases = int(row[week_column]) if row[week_column].strip() else 0
                        except (ValueError, TypeError):
                            num_cases = 0
                        
                            
                        DengueCase.objects.update_or_create(
                            barangay=barangay,
                            year_reported=year,
                            week_reported=week_num,
                            num_cases=num_cases,
                        )
                        success_count += 1
                            
            except Exception as e:
                error_count += 1
                # Log the error if you have logging setup
                print(f"Error processing row: {str(e)}")
    
    return success_count, error_count

# =======================
# dengue case table view

def dengue_case_table(request):
    cases = DengueCase.objects.select_related('barangay').order_by('-year_reported', '-week_reported', 'barangay__name')
    
    # Get unique years for filter dropdown
    unique_years = DengueCase.objects.values_list('year_reported', flat=True).distinct().order_by('-year_reported')
    
    # Create week range for filter (1-52)
    week_range = range(1, 53)
    
    user_name = get_userInfo(request, 'name')
    user_username = get_userInfo(request, 'username')

    return render(request, 'dengue_case.html', {
        'cases': cases,
        'unique_years': unique_years,
        'week_range': week_range,
        'user_name': user_name,
        'user_username': user_username,
    })

def user_dengue_case_table(request):
    cases = DengueCase.objects.select_related('barangay').order_by('-year_reported', '-week_reported', 'barangay__name')
    
    # Get unique years for filter dropdown
    unique_years = DengueCase.objects.values_list('year_reported', flat=True).distinct().order_by('-year_reported')
    
    # Create week range for filter (1-52)
    week_range = range(1, 53)
    
    user_name = get_userInfo(request, 'name')
    user_username = get_userInfo(request, 'username')
    user_barangay = get_userInfo(request, 'barangay')

    return render(request, 'user/dengue_case.html', {
        'cases': cases,
        'unique_years': unique_years,
        'week_range': week_range,
        'user_name': user_name,
        'user_username': user_username,
        'user_barangay': user_barangay,
    })


# =======================
# SMTP email test view

from django.core.mail import send_mail
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def test_email_send(request):
    """Simple email tester view"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            recipient_email = data.get('email', '')
            
            if not recipient_email:
                return JsonResponse({
                    'success': False,
                    'message': 'Email address is required'
                })
            
            # Test email content
            subject = "Dengue System - SMTP Test Email"
            message = """
            Hello!
            
            This is a test email from your Dengue Prediction System.
            
            If you're receiving this, your SMTP configuration is working correctly!
            
            Best regards,
            Dengue Prediction System Team
            """
            
            html_message = """
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                    .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                    .header { background: #2c3e50; color: white; padding: 20px; text-align: center; border-radius: 8px; }
                    .content { padding: 20px; background: #f8f9fa; border-radius: 8px; margin: 20px 0; }
                    .footer { text-align: center; color: #666; font-size: 14px; }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🌡️ Dengue Prediction System</h1>
                    </div>
                    <div class="content">
                        <h2>SMTP Test Successful! ✅</h2>
                        <p>Hello there!</p>
                        <p>This is a <strong>test email</strong> from your Dengue Prediction System.</p>
                        <p>If you're reading this, your <strong>SMTP email configuration is working perfectly!</strong></p>
                        <p>You can now proceed to implement the OTP system with confidence.</p>
                    </div>
                    <div class="footer">
                        <p>Best regards,<br>Dengue Prediction System Team</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Try to send email
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient_email],
                html_message=html_message,
                fail_silently=False,
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Test email sent successfully to {recipient_email}'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Failed to send email: {str(e)}'
            })
    
    # GET request - show email test form
    return render(request, 'test_email.html')

# Create your views here.
from backend.zCode.otp import otp_send

def email(request):
    # Call otp_send and handle its response
    response = otp_send(request)
    
    # If it's a JsonResponse (from POST), return it directly
    if hasattr(response, 'status_code') and response.status_code in [200, 400, 405, 500]:
        return response
    
    # If it's a render response (from GET), return it
    return response

def login_user(request):
    if request.user.is_authenticated:
        if request.user.is_admin:
            return redirect('admin-panel')
        else:
            return redirect('dashboard')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_admin:
                messages.error(request, "Admin users must log in through the admin panel.")
                return redirect('login-admin')
            
            # Clean up any previous session data safely
            request.session.pop('pending_user_id', None)
            request.session.pop('pending_user_email', None)
            
            # Send OTP and redirect to verification
            email = user.email
            otp_sent = otp_send('login', email)
            
            if otp_sent:
                # Store in session
                request.session['pending_user_id'] = user.user_id
                request.session['pending_user_email'] = email
                messages.success(request, "OTP code has sent on your email address")
                history_logger(request, user.name, 'LOGIN', f'User [{user.name}] successfully logged in.')
                return redirect('otp-verify-login')
            else:
                messages.error(request, "Failed to send OTP. Please try again.")
                return redirect('login')
        else:
            messages.error(request, "Invalid username or password.")
            return redirect('login')

    return render(request, 'login.html')

def login_admin(request):
    if request.user.is_authenticated:
        if request.user.is_admin:
            return redirect('admin-panel')
        else:
            return redirect('dashboard')
    
    if request.method == 'POST':
        
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            if not user.is_admin:
                # Regular user
                messages.error(request, "Regular users must log in through the user dashboard.")
                return redirect('login')
            
            # Send OTP and redirect to verification
            email = user.email
            otp_sent = otp_send('login', email)

            if otp_sent:
                # Store in session (this just works)
                request.session['pending_user_id'] = user.user_id
                request.session['pending_user_email'] = email
                history_logger(request, user.name, 'LOGIN', f'Admin [{user.name}] successfully logged in.')
                return redirect('otp-verify-login')  # Go to OTP entry page
            else:
                messages.error(request, "Failed to send OTP. Please try again.")
                return redirect('login')  
        else:
            messages.error(request, "Invalid username or password.")
            return redirect('login-admin')

    return render(request, 'login_admin.html')

def otp_verify_login(request):
    """Handle OTP verification for login"""
    if request.method == 'POST':
        otp_code = request.POST.get('otp_code')
        email = request.session.get('pending_user_email')
        
        if not email or not otp_code:
            messages.error(request, "Invalid verification request.")
            return redirect('login')
        
        # Verify OTP using your existing function
        if otp_verify('login', email, otp_code):
            # OTP valid - log the user in
            user_id = request.session.get('pending_user_id')
            user = get_user_model().objects.get(user_id=user_id)
            login(request, user)
            
            # Clean up session
            del request.session['pending_user_id']
            del request.session['pending_user_email']
            
            if user.is_admin:
                return redirect('admin-panel')
            else:
                return redirect('dashboard')
        else:
            messages.error(request, "Invalid or expired OTP.")
            return render(request, 'user/otp_login.html')
    
    # GET request - show OTP entry form
    return render(request, 'user/otp_login.html')

def resend_otp(request):
    if request.method == 'POST':
        email = request.session.get('pending_user_email')
        if email:
            otp_sent = otp_send('login', email)
            if otp_sent:
                return JsonResponse({'success': True, 'message': 'OTP resent successfully'})
        return JsonResponse({'success': False, 'message': 'Failed to resend OTP'})
    return JsonResponse({'success': False, 'message': 'Invalid request'})

# =======================
# otp reset password

from django.contrib.auth.hashers import make_password

def forgot_password(request):
    """Show forgot password form"""
    return render(request, 'forgot_password.html')

def send_password_reset_otp(request):
    """Send OTP for password reset"""
    if request.method == 'POST':
        email = request.POST.get('email')
        
        if not email:
            return JsonResponse({'success': False, 'message': 'Email is required'})
        
        # Check if user exists
        User = get_user_model()
        try:
            user = User.objects.get(email=email)
            
            # Send OTP
            otp_sent = otp_send('password_reset', email)
            
            if otp_sent:
                # Store in session
                request.session['reset_password_email'] = email
                request.session['reset_password_user_id'] = user.user_id
                return JsonResponse({'success': True, 'message': 'OTP sent to your email'})
            else:
                return JsonResponse({'success': False, 'message': 'Failed to send OTP'})
                
        except User.DoesNotExist:
            # Still return success to prevent email enumeration
            return JsonResponse({'success': True, 'message': 'If the email exists, OTP has been sent'})

def verify_password_reset_otp(request):
    """Verify OTP and show password reset form"""
    if request.method == 'POST':
        otp_code = request.POST.get('otp_code')
        email = request.session.get('reset_password_email')
        
        if not email or not otp_code:
            messages.error(request, "Invalid verification request.")
            return redirect('forgot-password')
        
        # Verify OTP
        if otp_verify('password_reset', email, otp_code):
            # OTP valid - allow password reset
            request.session['otp_verified'] = True
            messages.success(request, "OTP verified. You can now reset your password.")
            return redirect('reset-password')
        else:
            messages.error(request, "Invalid or expired OTP.")
            return render(request, 'verify_reset_otp.html')
    
    # GET request - show OTP verification form
    if not request.session.get('reset_password_email'):
        messages.error(request, "Please request a password reset first.")
        return redirect('forgot-password')
    
    return render(request, 'verify_reset_otp.html')

def reset_password(request):
    """Handle password reset after OTP verification"""
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        email = request.session.get('reset_password_email')
        
        if not request.session.get('otp_verified'):
            messages.error(request, "OTP verification required.")
            return redirect('forgot-password')
        
        if not new_password or not confirm_password:
            messages.error(request, "All fields are required.")
            return render(request, 'reset_password.html')
        
        if new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, 'reset_password.html')
        
        if len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return render(request, 'reset_password.html')
        
        try:
            User = get_user_model()
            user = User.objects.get(email=email)
            
            # Update password
            user.password = make_password(new_password)
            user.save()
            
            # Log the action
            history_logger(request, user.name, 'PASSWORD_RESET', f'User [{user.name}] reset their password.')
            
            # Clean up session
            del request.session['reset_password_email']
            del request.session['reset_password_user_id']
            del request.session['otp_verified']
            
            messages.success(request, "Password reset successfully! You can now login with your new password.")
            if user.is_admin:
                return redirect('login-admin')
            else:
                return redirect('login')
            
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect('forgot-password')
    
    # GET request - show password reset form
    if not request.session.get('otp_verified'):
        messages.error(request, "OTP verification required.")
        return redirect('forgot-password')
    
    return render(request, 'reset_password.html')

def resend_password_reset_otp(request):
    """Resend password reset OTP"""
    if request.method == 'POST':
        email = request.session.get('reset_password_email')
        
        if email:
            otp_sent = otp_send('password_reset', email)
            if otp_sent:
                return JsonResponse({'success': True, 'message': 'OTP resent successfully'})
        
        return JsonResponse({'success': False, 'message': 'Failed to resend OTP'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})

# ======================
# edit profile

# Edit Profile Views
@login_required
def edit_profile(request):
    """Edit user profile information"""
    try:
        # Get user data based on user type
        if request.user.is_admin:
            user_data = AdminData.objects.get(admin_account=request.user)
            user_type = 'admin'
        else:
            user_data = UserData.objects.get(user_account=request.user)
            user_type = 'user'
    except (AdminData.DoesNotExist, UserData.DoesNotExist):
        user_data = None
        user_type = 'user'

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        username = request.POST.get('username')
        
        # Basic validation
        if not all([name, email, username]):
            messages.error(request, "All fields are required.")
            return redirect('edit-profile')

        try:
            # Update main user account
            request.user.name = name
            request.user.email = email
            request.user.username = username
            request.user.save()

            # Update user-specific data
            if user_data:
                user_data.name = name
                user_data.email = email
                user_data.username = username
                user_data.save()

            # Log the profile update
            desc = f'User [{request.user.name}] updated their profile information.'
            history_logger(request, request.user.name, 'UPDATE_PROFILE', desc)

            messages.success(request, "Profile updated successfully!")
            return redirect('edit-profile')

        except Exception as e:
            messages.error(request, f"Error updating profile: {str(e)}")
            return redirect('edit-profile')

    # GET request - show edit form (no barangays needed)
    
    context = {
        'user_data': user_data,
        'user_type': user_type,
    }
    
    # Add user-specific context
    if request.user.is_admin:
        context.update({
            'admin_user': request.user.username,
            'admin_name': request.user.name,
        })
    else:
        context.update({
            'user_name': get_userInfo(request, 'name'),
            'user_username': get_userInfo(request, 'username'),
            'user_barangay': get_userInfo(request, 'barangay'),
        })

    return render(request, 'edit_profile.html', context)


from django.contrib.auth import update_session_auth_hash
@login_required
def change_password(request):
    """User changing their own password"""
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        # Validation
        if not all([current_password, new_password, confirm_password]):
            messages.error(request, "All password fields are required.")
            return redirect('edit-profile')

        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect('edit-profile')

        if len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect('edit-profile')

        # Verify current password
        user = authenticate(username=request.user.username, password=current_password)
        if user is not None:
            # Change password using make_password
            user.password = make_password(new_password)
            user.save()

            # Update session auth hash
            update_session_auth_hash(request, user)

            # Log the action
            desc = f'User [{user.name}] changed their password.'
            history_logger(request, user.name, 'CHANGE_PASSWORD', desc)
            messages.success(request, "Password changed successfully!")
        else:
            messages.error(request, "Current password is incorrect.")

    return redirect('edit-profile')

@login_required
def change_user_password(request, user_id):
    """Admin changing another user's password"""
    if not request.user.is_admin:
        raise PermissionDenied("You do not have permission to change other users' passwords.")
    
    if request.method == 'POST':
        User = get_user_model()
        user_to_change = get_object_or_404(User, pk=user_id)
        
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        # Validation
        if not all([new_password, confirm_password]):
            messages.error(request, "All password fields are required.")
            return redirect('edit-user', user_id=user_id)

        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect('edit-user', user_id=user_id)

        if len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
            return redirect('edit-user', user_id=user_id)

        try:
            # Change password using make_password
            user_to_change.password = make_password(new_password)
            user_to_change.save()

            # Log the action
            desc = f'Admin [{request.user.name}] changed password for user [{user_to_change.name}].'
            history_logger(request, request.user.name, 'CHANGE_USER_PASSWORD', desc)
            messages.success(request, f"Password for {user_to_change.name} changed successfully!")
            
        except Exception as e:
            error_msg = f"Error changing password: {str(e)}"
            messages.error(request, error_msg)
            history_logger(request, request.user.name, 'CHANGE_USER_PASSWORD_ERROR', error_msg)

    return redirect('edit-user', user_id=user_id)