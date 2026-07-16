from django_apscheduler.jobstores import DjangoJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from backend.zCode.predict import predict_dengue_risk

scheduler = BackgroundScheduler()
scheduler.add_jobstore(DjangoJobStore(), "default")

def run_weekly_prediction():
    print("🟢 Running dengue prediction job...")
    results = predict_dengue_risk()
    for barangay, predicted_cases, confidence, risk in results:
        print(f"Predicted {predicted_cases:.2f} cases in {barangay} | Confidence: {confidence}% | Risk: {risk}")

def start_scheduler():
    if not scheduler.get_job('weekly_dengue_prediction'):
  
        scheduler.add_job (
            run_weekly_prediction,
            trigger='interval',
            days=7,
            id='weekly_dengue_prediction',
            replace_existing=True,
            max_instances=1
        )
        print("🟢 Weekly dengue prediction job scheduled for testing (every 1 minute).")
    scheduler.start()
    print("🟢 APScheduler started.")

