from django.contrib import admin
from .models import *

@admin.register(Barangay)
class BarangayAdmin(admin.ModelAdmin):
    list_display = ('name', 'latitude', 'longitude')
    search_fields = ('name',)

@admin.register(AccountManager)
class AccountManagerAdmin(admin.ModelAdmin):
    list_display = ('name', 'user_id', 'username', 'email', 'is_admin')
    search_fields = ('username', 'name', 'email')

@admin.register(UserData)
class UserDataAdmin(admin.ModelAdmin):
    list_display = ('name', 'user_id', 'user_account', 'username', 'email', 'barangay')
    list_filter = ('barangay', 'is_admin')
    search_fields = ('username', 'name', 'email')

@admin.register(AdminData)
class AdminDataAdmin(admin.ModelAdmin):
    list_display = ('name', 'admin_id', 'admin_account', 'username', 'name', 'email')
    search_fields = ('username', 'name', 'email')

@admin.register(WeatherData)
class WeatherDataAdmin(admin.ModelAdmin):
    list_display = ('barangay', 'date_recorded', 'temperature', 'humidity', 'rainfall')
    list_filter = ('barangay', 'date_recorded', 'data_source')
    search_fields = ('barangay__name',)

@admin.register(DengueCase)
class DengueCaseAdmin(admin.ModelAdmin):
    list_display = ('barangay', 'year_reported', 'week_reported', 'num_cases',)
    list_filter = ('barangay', 'year_reported', 'week_reported',)
    search_fields = ('barangay__name',)
    ordering = ('-year_reported', '-week_reported', 'barangay')

@admin.register(PredictionResult)
class PredictionResultAdmin(admin.ModelAdmin):
    list_display = ('barangay', 'created_at', 'week_prediction', 'numerical_risk_level', 'confidence_score')
    list_filter = ('barangay', 'created_at', 'numerical_risk_level')
    search_fields = ('barangay__name',)

@admin.register(LogHistory)
class LogHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'log_title', 'description', 'timestamp')
    list_filter = ('log_title', 'timestamp')
    search_fields = ('user__username', 'description')


# =======================
# Weather Models Admin
# =======================
@admin.register(CurrentWeather)
class CurrentWeatherAdmin(admin.ModelAdmin):
    list_display = ('location', 'time', 'rainfall_chance', 'temperature', 'humidity', 'is_day', 'wind_speed_10m', 'weather_code', 'created_at')
    list_filter = ('location', 'time', 'is_day')
    search_fields = ('location',)
    date_hierarchy = 'time'
    ordering = ('-time', 'location')
    readonly_fields = ('created_at',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()

@admin.register(HourlyForecast)
class HourlyForecastAdmin(admin.ModelAdmin):
    list_display = ('location', 'date', 'rainfall_chance', 'temperature_2m', 'relative_humidity_2m', 'wind_speed_10m', 'is_day', 'weather_code', 'created_at')
    list_filter = ('location', 'date', 'is_day')
    search_fields = ('location',)
    date_hierarchy = 'date'
    ordering = ('-date', 'location')
    readonly_fields = ('created_at',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()

@admin.register(DailyForecast)
class DailyForecastAdmin(admin.ModelAdmin):
    list_display = ('location', 'date', 'rainfall_chance_max', 'temperature_2m_max', 'temperature_2m_min', 'wind_speed_10m_max', 'avg_humidity', 'weather_code', 'created_at')
    list_filter = ('location', 'date')
    search_fields = ('location',)
    date_hierarchy = 'date'
    ordering = ('-date', 'location')
    readonly_fields = ('created_at',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()
    
@admin.register(HistoricalWeather)
class HistoricalWeatherAdmin(admin.ModelAdmin):
    list_display = ('location', 'date', 'weather_code', 'temperature_2m_max', 'temperature_2m_min', 'wind_speed_10m_max', 'created_at')
    list_filter = ('location', 'date')
    search_fields = ('location',)
    date_hierarchy = 'date'
    ordering = ('-date', 'location')
    readonly_fields = ('created_at',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()
    
@admin.register(WeeklyAverage)
class WeeklyAverageAdmin(admin.ModelAdmin):
    list_display = (
        'week_range_display', 
        'location', 
        'year', 
        'week', 
        'avg_temperature', 
        'avg_humidity',
        'avg_rainfall_chance',
        'total_rainy_days',
        'created_at'
    )
    
    list_filter = (
        'location',
        'year', 
        'week',
        'created_at',
    )
    
    search_fields = (
        'location',
        'year',
        'week',
    )
    
    readonly_fields = (
        'created_at',
        'updated_at',
    )
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('location', 'year', 'week', 'start_date', 'end_date')
        }),
        ('Weekly Averages', {
            'fields': (
                'avg_temperature', 
                'avg_humidity', 
                'avg_rainfall_chance', 
                'avg_wind_speed'
            )
        }),
        ('Additional Metrics', {
            'fields': (
                'total_rainy_days',
                'max_temperature',
                'min_temperature',
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def week_range_display(self, obj):
        return f"{obj.start_date} to {obj.end_date}"
    week_range_display.short_description = 'Week Range'
    week_range_display.admin_order_field = 'start_date'
    
    # Custom actions
    actions = ['recalculate_weekly_averages']
    
    def recalculate_weekly_averages(self, request, queryset):
        from .views import calculate_weekly_averages
        calculate_weekly_averages()
        self.message_user(request, "Weekly averages recalculated successfully!")
    recalculate_weekly_averages.short_description = "Recalculate selected weekly averages"
    
    # Customize the changelist view
    def changelist_view(self, request, extra_context=None):
        # Add some stats to the context
        extra_context = extra_context or {}
        extra_context['total_weeks'] = WeeklyAverage.objects.count()
        extra_context['latest_week'] = WeeklyAverage.objects.order_by('-year', '-week').first()
        return super().changelist_view(request, extra_context=extra_context)
    
    # Add custom methods to the model in admin
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-year', '-week')
    
# =======================
# End of Weather Models Admin
# =======================

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'recipient', 'subject', 'timestamp')
    list_filter = ('timestamp', 'sender', 'recipient')
    search_fields = ('sender', 'recipient',)
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)

@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ('email', 'otp_code', 'otp_type', 'created_at', 'expires_at', 'is_used')
    list_filter = ('otp_type', 'is_used', 'created_at')
    search_fields = ('email', 'otp_code')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

from django.contrib import admin
from .models import TemporaryUser

@admin.register(TemporaryUser)
class TemporaryUserAdmin(admin.ModelAdmin):
    list_display = [
        'username', 
        'get_full_name', 
        'email', 
        'barangay', 
        'status', 
        'created_at',
    ]
    
    list_filter = [
        'status',
        'barangay',
        'created_at',
    ]
    
    search_fields = [
        'first_name',
        'last_name', 
        'username',
        'email',
    ]
    
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'username', 'email')
        }),
        ('Location Information', {
            'fields': ('barangay',)
        }),
        ('Account Information', {
            'fields': ('password', 'status')
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
        }),
    )
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    get_full_name.short_description = 'Full Name'