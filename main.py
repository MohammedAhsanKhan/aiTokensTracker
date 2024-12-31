from db_operations import setup_tables
import time
import logging
from job import aiTrackerJob, trendingTokensJob
logging.basicConfig(level=logging.INFO)
from apscheduler.schedulers.background import BackgroundScheduler

def main():
    setup_tables()  # Set up the database tables if it doesn't exist
    scheduler = BackgroundScheduler()
    scheduler.add_job(aiTrackerJob, 'interval', minutes=1, id='ai_token_tracker')
    #scheduler.add_job(trendingTokensJob, 'interval', minutes=10, id='trending_token_tracker')
    scheduler.start()
    logging.info("schedulers started. Tracking tokens...")
    # Keep the program running and execute scheduled tasks
    try:
        while True:
            time.sleep(1)  # Keep the main thread alive
    except (KeyboardInterrupt, SystemExit):
        logging.info("Stopping schedulers...")
        scheduler.shutdown()
    

if __name__ == "__main__":
    main()