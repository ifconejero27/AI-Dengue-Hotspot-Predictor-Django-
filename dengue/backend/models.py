from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import MinValueValidator, MaxValueValidator



class Barangay(models.Model):
    barangay_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Barangays"


class CustomUserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        if not username:
            raise ValueError('Users must have a username')
            
        user = self.model(
            email=self.normalize_email(email),
            username=username,
            **extra_fields
        )
        
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra_fields):
        user = self.create_user(
            email=email,
            username=username,
            password=password,
            **extra_fields
        )
        user.is_admin = True
        user.save(using=self._db)
        return user



class AccountManager(AbstractBaseUser, PermissionsMixin):
    user_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=50, unique=True)
    is_admin = models.BooleanField(default=False)
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'name']
    
    def __str__(self):
        return self.username
    
    def has_perm(self, perm, obj=None):
        return True
    
    def has_module_perms(self, app_label):
        return True
    
    @property
    def is_staff(self):
        return self.is_admin
    
    class Meta:
        verbose_name_plural = "Account Manager"


class UserData(models.Model):
    user_id = models.AutoField(primary_key=True)
    user_account = models.ForeignKey(AccountManager, on_delete=models.CASCADE, null=True, blank=True)
    barangay = models.ForeignKey(Barangay, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    
    objects = CustomUserManager()
    
    def __str__(self):
        return self.username
    
    class Meta:
        verbose_name_plural = "User Data"

class TemporaryUser(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)
    barangay = models.ForeignKey(Barangay, on_delete=models.CASCADE)
    password = models.CharField(max_length=128)  # Store hashed password
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.username})"


class AdminData(models.Model):
    admin_id = models.AutoField(primary_key=True)
    admin_account = models.ForeignKey(AccountManager, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=128)
    is_admin = models.BooleanField(default=False)
    
    def __str__(self):
        return self.username
    
    class Meta:
        verbose_name_plural = "Admin Data"


class WeatherData(models.Model):
    DATA_SOURCE_CHOICES = [
        ('PAGASA', 'Philippine Atmospheric, Geophysical and Astronomical Services Administration'),
        ('LOCAL', 'Local Weather Station'),
        ('OTHER', 'Other Source'),
    ]
    
    weather_id = models.AutoField(primary_key=True)
    barangay = models.ForeignKey(Barangay, on_delete=models.CASCADE)
    date_recorded = models.DateField()
    time_recorded = models.TimeField()
    temperature = models.DecimalField(max_digits=4, decimal_places=1)  # in Celsius
    humidity = models.DecimalField(max_digits=4, decimal_places=1)  # percentage
    rainfall = models.DecimalField(max_digits=6, decimal_places=2)  # in mm
    windspeed = models.DecimalField(max_digits=5, decimal_places=2)  # in km/h
    data_source = models.CharField(max_length=10, choices=DATA_SOURCE_CHOICES)
    
    def __str__(self):
        return f"{self.barangay.name} - {self.date_recorded}"
    
    class Meta:
        verbose_name_plural = "Weather Data"
        unique_together = ('barangay', 'date_recorded', 'time_recorded')

# =======================
# Dengue Case Model

class DengueCase(models.Model):
    dengue_case_id = models.AutoField(primary_key=True)
    barangay = models.ForeignKey(Barangay, on_delete=models.CASCADE)
    year_reported = models.PositiveIntegerField()
    week_reported = models.PositiveIntegerField()
    num_cases = models.PositiveIntegerField()
    # risk_level = models.CharField(max_length=20, blank=True)
    
    def __str__(self):
        return f"{self.barangay.name} - {self.week_reported} {self.year_reported}: {self.num_cases} cases"
    
    class Meta:
        verbose_name_plural = "Dengue Cases"

# =======================
# Prediction Result Model

class PredictionResult(models.Model):
    prediction_result_id = models.AutoField(primary_key=True)
    barangay = models.ForeignKey(Barangay, on_delete=models.CASCADE)
    year_prediction = models.PositiveIntegerField()
    week_prediction = models.PositiveIntegerField()
    numerical_risk_level = models.PositiveIntegerField()
    confidence_score = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(1)]
    )
    risk_level = models.CharField(max_length=20)
    trend = models.CharField(max_length=10, default='neutral')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.barangay.name} - {self.year_prediction} Week {self.week_prediction}: {self.risk_level}"
    
    class Meta:
        verbose_name_plural = "Prediction Results"
        unique_together = ('barangay', 'year_prediction', 'week_prediction')  # CHANGED THIS

# =======================
# Log History Model
class LogHistory(models.Model):
    LOG_TYPE_CHOICES = [
        ('LOGIN', 'Account Login'),
        ('REGISTER', 'Account Registration'),
        ('MODIFY', 'Account Modification'),
        ('DELETE', 'Account Deletion'),
        ('PREDICTION', 'Prediction Made'),
        ('DATA_ENTRY', 'Data Entry'),
        ('SYSTEM', 'System Event'),
    ]
    
    log_id = models.AutoField(primary_key=True)
    user = models.CharField(max_length=20)
    log_title = models.CharField(max_length=20, choices=LOG_TYPE_CHOICES)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.log_title} - {self.timestamp}"
    
    class Meta:
        verbose_name_plural = "Log History"




# =======================
# Weather tables

class CurrentWeather(models.Model):
    location = models.CharField(max_length=100, db_index=True)
    rainfall_chance = models.FloatField()
    temperature = models.FloatField()
    humidity = models.FloatField()
    is_day = models.BooleanField()
    wind_speed_10m = models.FloatField()
    weather_code = models.FloatField()
    time = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('location', 'time')
        indexes = [
            models.Index(fields=['location', 'time']),
        ]

    def __str__(self):
        return f"{self.location} at {self.time}: {self.rainfall_chance}% chance of rain"

class HourlyForecast(models.Model):
    location = models.CharField(max_length=100, db_index=True)
    date = models.DateTimeField(db_index=True)
    temperature_2m = models.FloatField()
    rainfall_chance = models.FloatField()
    wind_speed_10m = models.FloatField()
    relative_humidity_2m = models.FloatField()
    is_day = models.BooleanField()
    weather_code = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('location', 'date')
        indexes = [
            models.Index(fields=['location', 'date']),
        ]

    def __str__(self):
        return f"{self.location} at {self.date}: {self.rainfall_chance}% chance of rain"

class DailyForecast(models.Model):
    location = models.CharField(max_length=100, db_index=True)
    date = models.DateField(db_index=True)
    rainfall_chance_max = models.FloatField()
    temperature_2m_max = models.FloatField(null=True, blank=True)
    temperature_2m_min = models.FloatField()
    wind_speed_10m_max = models.FloatField()
    weather_code = models.FloatField()
    avg_humidity = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('location', 'date')
        indexes = [
            models.Index(fields=['location', 'date']),
        ]

    def __str__(self):
        return f"{self.location} on {self.date}: {self.rainfall_chance_max}% max chance of rain"
    
class HistoricalWeather(models.Model):
    location = models.CharField(max_length=100, db_index=True, default="Malabon")  # Default location
    date = models.DateField(db_index=True)  # Date of the weather data
    weather_code = models.FloatField()  # Weather condition code
    temperature_2m_max = models.FloatField()  # Maximum temperature (°C)
    temperature_2m_min = models.FloatField()  # Minimum temperature (°C)
    wind_speed_10m_max = models.FloatField()  # Maximum wind speed (km/h)
    created_at = models.DateTimeField(auto_now_add=True)  # Timestamp for record creation

    class Meta:
        unique_together = ('location', 'date')  # Ensure no duplicate entries for the same location and date
        indexes = [
            models.Index(fields=['location', 'date']),
        ]
        verbose_name_plural = "Historical Weather Data"

    def __str__(self):
        return f"{self.location} on {self.date}: Max Temp {self.temperature_2m_max}°C, Min Temp {self.temperature_2m_min}°C"
    
# =======================
# messaging model

class Message(models.Model):
    sender = models.CharField(max_length=100)
    recipient = models.CharField(max_length=100)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    def __str__(self):
        return f"From: {self.sender} To: {self.recipient} Subject: {self.subject}"
    
    class Meta:
        verbose_name_plural = "Messages"
        ordering = ['-timestamp']

# =======================
# weekly average

class WeeklyAverage(models.Model):
    weekly_id = models.AutoField(primary_key=True)
    location = models.CharField(max_length=100, default="Malabon")
    year = models.PositiveIntegerField()
    week = models.PositiveIntegerField()  # Week number 1-52
    start_date = models.DateField()  # First day of the week
    end_date = models.DateField()    # Last day of the week
    
    # Weekly averages
    avg_temperature = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    avg_humidity = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    avg_rainfall_chance = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    avg_wind_speed = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    # Additional metrics
    total_rainy_days = models.PositiveIntegerField(default=0)  # Days with high rainfall chance
    max_temperature = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    min_temperature = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Weekly Averages"
        unique_together = ('location', 'year', 'week')
        ordering = ['-year', '-week']
    
    def __str__(self):
        return f"{self.location} - {self.year} Week {self.week}"
    
    def week_range(self):
        return f"{self.start_date} to {self.end_date}"
    
    # Add this to your existing models.py
class ModelVersion(models.Model):
    model_version_id = models.AutoField(primary_key=True)
    barangay = models.ForeignKey(Barangay, on_delete=models.CASCADE)
    version = models.IntegerField(default=1)
    training_data_up_to = models.DateField()
    accuracy_score = models.FloatField(null=True, blank=True)
    total_training_samples = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Model Versions"
        unique_together = ('barangay', 'version')

    def __str__(self):
        return f"{self.barangay.name} - v{self.version}"
    

# =======================
# OTP Model

class OTP(models.Model):
    otp_type = models.CharField(max_length=30)
    email = models.EmailField()
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    is_used = models.BooleanField(default=False)
    
    def __str__(self):
        return f"OTP for {self.email} - Code: {self.otp_code} - Used: {self.is_used}"
    
    class Meta:
        verbose_name_plural = "OTP Codes"