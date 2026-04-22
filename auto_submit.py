# auto_submit.py - Auto URL Submitter for GitHub Actions
import os, sys, json, logging, time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# ============ CONFIGURATION ============
PANEL_URL = "https://personal-fast-index.info/panel20/panel.php"
USERNAME = os.getenv("PANEL_USER", "")
PASSWORD = os.getenv("PANEL_PASS", "")
URLS_FILE = "pdf_urls.txt"
LOG_FILE = "submitted_urls.json"
MAX_RETRIES = 3
HEADLESS = True  # Always True for GitHub Actions

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("automation.log"), logging.StreamHandler()]
)

class FastURLSubmitter:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.submitted = self.load_submitted()
        
    def load_submitted(self):
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def save_submitted(self, url):
        if url not in self.submitted:
            self.submitted.append(url)
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.submitted, f, indent=2)
    
    def setup_driver(self):
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--window-size=1920,1080')
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.stylesheet": 2,
        }
        options.add_experimental_option("prefs", prefs)
        
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options
        )
        self.wait = WebDriverWait(self.driver, 12)

    def login(self):
        try:
            self.driver.get(PANEL_URL)
            username_field = self.wait.until(EC.presence_of_element_located((By.NAME, "login")))
            password_field = self.driver.find_element(By.NAME, "password")
            username_field.send_keys(USERNAME)
            password_field.send_keys(PASSWORD)
            password_field.submit()
            self.wait.until(EC.presence_of_element_located((By.NAME, "links")))
            logging.info("✅ Login successful")
            return True
        except Exception as e:
            logging.error(f"❌ Login failed: {e}")
            return False

    def submit_single_url(self, url):
        try:
            textarea = self.wait.until(EC.presence_of_element_located((By.NAME, "links")))
            textarea.clear()
            textarea.send_keys(url)
            submit_btn = self.driver.find_element(By.XPATH, "//button[text()='Import Links']")
            submit_btn.click()
            time.sleep(2)
            return True
        except Exception as e:
            logging.error(f"❌ Submission failed: {e}")
            return False

    def process_pending_urls(self, urls):
        pending = [u for u in urls if u not in self.submitted]
        if not pending:
            logging.info("🎉 No pending URLs. All done!")
            return True
            
        logging.info(f"📦 Pending: {len(pending)}/{len(urls)} URLs")
        
        if not self.login():
            return False
            
        for i, url in enumerate(pending, 1):
            logging.info(f"🔄 [{i}/{len(pending)}] {url[:50]}...")
            for attempt in range(MAX_RETRIES):
                if self.submit_single_url(url):
                    self.save_submitted(url)
                    logging.info(f"✅ Done: {url}")
                    break
                else:
                    logging.warning(f"⚠️ Retry {attempt+1}/{MAX_RETRIES}")
                    time.sleep(3)
            else:
                logging.error(f"❌ Failed: {url}")
            if i < len(pending):
                time.sleep(1.5)
        return True

    def close(self):
        if self.driver:
            time.sleep(1)
            self.driver.quit()

def main():
    if not USERNAME or not PASSWORD:
        logging.error("❌ Credentials not set! Check GitHub Secrets.")
        sys.exit(1)
        
    if not os.path.exists(URLS_FILE):
        logging.error(f"❌ {URLS_FILE} not found")
        sys.exit(1)
    
    with open(URLS_FILE, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip().startswith('http')]
    
    if not urls:
        logging.error("❌ No valid URLs")
        sys.exit(1)
    
    logging.info(f"🚀 Starting | URLs: {len(urls)}")
    
    submitter = FastURLSubmitter()
    try:
        submitter.setup_driver()
        submitter.process_pending_urls(urls)
    finally:
        submitter.close()
    
    logging.info("✨ Cycle complete")

if __name__ == "__main__":
    main()
