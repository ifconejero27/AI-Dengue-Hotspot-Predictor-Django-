from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from backend.models import OTP
import secrets

def otp_send(otp_type, email):
    
    selected_type = otp_type
    target_email = email

    otp_code = otp_generate()
    prefix, template = otp_message(otp_type)
    subject = f"{prefix} - AI Dengue Hotspot Predictor Verification"
    body = template.format(otp_code=otp_code)

    try:
        # Send email
        send_mail(
            subject,
            body,
            "emailfromsettings@gmail.com",
            [target_email],
            fail_silently=False
        )

        # Save OTP to database
        OTP.objects.create(
            email=target_email,
            otp_code=otp_code,
            otp_type=selected_type,
            expires_at=timezone.now() + timezone.timedelta(minutes=10)
        )

        return True

    except Exception as e:
        return False


def otp_generate():
    while True:
        otp_code = str(secrets.randbelow(1000000)).zfill(6)
        if not OTP.objects.filter(otp_code=otp_code).exists():
            return otp_code
        
def otp_message(otp_type):
    otp_types = {
        'registration': 'Account Verification',
        'password_reset': 'Security Alert', 
        'login': 'Login Verification',
    }
    
    messages = {
        'registration': '''
AI Dengue Hotspot Predictor

We found that you're trying to create an account with AI Dengue Hotspot Predictor. Your verification code is required to complete the registration process.


Your account verification code is: {otp_code}


Security Recommendations:
- This OTP will expire in 10 minutes
- Never share this code with anyone
- Our team will NEVER ask for your OTP
- Delete this email after verification



You received this email because someone is attempting to register an account with your email address.

© 2025 AI Dengue Hotspot Predictor. All rights reserved.
''',
        'password_reset': '''
AI Dengue Hotspot Predictor

We detected a password reset request for your AI Dengue Hotspot Predictor account. Use this code to verify your identity and secure your account.


Your password reset verification code is: {otp_code}


Immediate Action Required:
- This code expires in 10 minutes  
- Do not share this with anyone
- Ensure you're on our official website
- Create a strong, unique password

Help us combat dengue through AI-powered hotspot prediction.

© 2025 AI Dengue Hotspot Predictor. All rights reserved.
''',
        'login': '''
AI Dengue Hotspot Predictor

We noticed a login attempt to your AI Dengue Hotspot Predictor account. Use this code to complete your secure login.


Your login verification code is: {otp_code}


Security Notice:
- Code valid for 10 minutes only
- Never share this authentication code
- Verify the website URL is correct
- Report suspicious login attempts

Access dengue prediction data and help create safer communities.

© 2025 AI Dengue Hotspot Predictor. All rights reserved.
'''
    }
    
    otp_prefix = otp_types.get(otp_type, 'Security Verification')
    message_template = messages.get(otp_type, 'Your verification code is: {otp_code}')
    
    return otp_prefix, message_template
    
def cleanup_expired_otps():
    """Delete all expired OTPs"""
    OTP.objects.filter(expires_at__lt=timezone.now()).delete()

def otp_verify(otp_type, email, otp_code):
    # Clean up expired OTPs
    cleanup_expired_otps()
    
    try:
        otp_entry = OTP.objects.get(
            email=email, 
            otp_code=otp_code, 
            otp_type=otp_type, 
            is_used=False
        )
        otp_entry.is_used = True
        otp_entry.save()
        return True
    except OTP.DoesNotExist:
        return False