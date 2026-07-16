from django.urls import path
from . import views
from backend.zCode import otp

urlpatterns = [
    path('', views.home, name='home'),
    path('register/user/', views.register_user, name='register-user'),
    path('register/admin/', views.register_admin, name='register-admin'),
    path('register/', views.register, name='register'),
    
    path('login/admin/', views.login_admin, name='login-admin'),
    path('logout/', views.logout_user, name='logout'),
    path('panel/', views.panel, name='panel'),
    path('report/', views.report_view, name='report'),
    path('download_predictions_csv/', views.download_predictions_csv, name='download_predictions_csv'),
    path('forecast/', views.forecast, name='forecast'),
    path('admin-panel/', views.admin_panel, name='admin-panel'),
    path('save-forecast/', views.save_forecast_to_db_get, name='save_forecast_to_db_get'),
    path('logs/', views.log_history, name='log-history'),
    path('manage-user/', views.manage_user, name='manage-user'),
    path('create-user/', views.create_user, name='create-user'),
    path('edit-user/<int:user_id>/', views.edit_user, name='edit-user'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete-user'),
    path('create-user/', views.create_user, name='create-user'),
    path('edit-user/<int:user_id>/', views.edit_user, name='edit-user'),
    path('delete-user/<int:user_id>/', views.delete_user, name='delete-user'),
    path('predict/', views.predict_view, name='predict'),
    path('predict/run/', views.run_prediction_view, name='run-prediction'),
    path('admin/message/', views.admin_message, name='admin-message'),
    path('delete-message/<int:message_id>/', views.delete_message, name='delete-message'),
    path('mark-message-read/<int:message_id>/', views.mark_message_read, name='mark-message-read'),
    path('import-dengue-data/', views.import_dengue_data, name='import-dengue-data'),
    path('admin/dengue-cases/', views.dengue_case_table, name='dengue-case-table'),
    path('test-email/', views.test_email_send, name='test-email'),
    path('email/', views.email, name="email"),

    # utils
    path('download-template/', views.download_dengue_template, name='download-template'),
    path('edit-profile/', views.edit_profile, name='edit-profile'),
    path('edit-profile/<int:user_id>/', views.edit_user, name='edit-user'),
    path('change-password/', views.change_password, name='change-password'),
    path('change-password/<int:user_id>/', views.change_password, name='change-user-password'),
    path('refresh-weather/', views.refresh_weather_data, name='refresh-weather-data'), 

    # User related Paths
    path('login/', views.login_user, name='login'),
    path('user/dashboard/', views.dashboard, name='dashboard'),
    path('user/report/', views.user_report_view, name='user-report'),
    path('user/submit-manual-report/', views.submit_manual_report, name='submit-manual-report'),
    path('user/message/', views.user_message, name='user-message'),
    path('user/forecast/', views.user_forecast, name='user_forecast'),
    path('user/upload-csv-report/', views.upload_csv_report, name='upload-csv-report'),
    path('user/dengue-case/', views.user_dengue_case_table, name='user-dengue-case-table'),

    # Admin related Paths
    path('admin/pending-registrations/', views.pending_registrations, name='pending-registrations'),
    path('admin/approve-registration/<int:temp_user_id>/', views.approve_registration, name='approve-registration'),
    path('admin/reject-registration/<int:temp_user_id>/', views.reject_registration, name='reject-registration'),

    # OTP Authentication Paths
    path('otp-login/', views.otp_verify_login, name='otp-verify-login'),
    path('resend-otp/', views.resend_otp, name='resend-otp'),
    path('forgot-password/', views.forgot_password, name='forgot-password'),
    path('send-password-reset-otp/', views.send_password_reset_otp, name='send-password-reset-otp'),
    path('verify-password-reset-otp/', views.verify_password_reset_otp, name='verify-password-reset-otp'),
    path('reset-password/', views.reset_password, name='reset-password'),
    path('resend-password-reset-otp/', views.resend_password_reset_otp, name='resend-password-reset-otp'),
]