import os
import time
import imaplib
import email
import re
import datetime
import smtplib
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ================== LOGGING FUNCTION ==================
def log(msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")


# ================== CONFIG ==================
USERNAME = os.environ.get("EMAIL_USERNAME")
PASSWORD = os.environ.get("EMAIL_PASSWORD")
IMAP_SERVER = os.environ.get("IMAP_SERVER")
AXOS_USERNAME = os.environ.get("AXOS_USERNAME")
AXOS_PASSWORD = os.environ.get("AXOS_PASSWORD")



# ================== EMAIL FUNCTION ==================

def send_email_with_attachment(subject, body, file_path):

    FROM_EMAIL = os.environ.get("FROM_EMAIL")
    TO_EMAIL = os.environ.get("TO_EMAIL")
    SMTP_PASSWORD = os.environ.get("EMAIL_SMTP_APP_PASSWORD")
    
    if not FROM_EMAIL or not TO_EMAIL or not SMTP_PASSWORD:
        raise ValueError("❌ Missing FROM_EMAIL, TO_EMAIL, or EMAIL_SMTP_APP_PASSWORD in environment variables.")

    log("Preparing email with screenshot...")
    msg = MIMEMultipart()
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    with open(file_path, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition", f'attachment; filename={os.path.basename(file_path)}'
        )
        msg.attach(part)

    log("Sending email...")
    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(FROM_EMAIL, SMTP_PASSWORD)
    server.sendmail(FROM_EMAIL, TO_EMAIL, msg.as_string())
    server.quit()
    log("✅ Email sent successfully.")


# ================== OTP FETCH FUNCTION ==================
def fetch_latest_otp(wait_time=60, check_interval=5):
    log("Starting OTP fetch process...")
    end_time = time.time() + wait_time

    while time.time() < end_time:
        try:
            log("Connecting to IMAP server...")
            imap = imaplib.IMAP4_SSL(IMAP_SERVER)
            imap.login(USERNAME, PASSWORD)
            imap.select('"[Gmail]/Sent Mail"')

            status, messages = imap.search(None, "ALL")
            if status != "OK" or not messages[0]:
                log("No messages found or search failed. Retrying...")
                imap.logout()
                time.sleep(check_interval)
                continue

            email_ids = messages[0].split()
            latest_email_id = email_ids[-1]
            log(f"Latest email ID: {latest_email_id.decode()}")

            status, msg_data = imap.fetch(latest_email_id, "(RFC822)")
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            email_date = email.utils.parsedate_to_datetime(msg["Date"])
            age = (datetime.datetime.now(datetime.timezone.utc) - email_date).seconds
            log(f"Email timestamp: {email_date} (Age: {age}s)")

            if age > 180:
                log("Email too old. Waiting for a newer one...")
                imap.logout()
                time.sleep(check_interval)
                continue

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if (
                        part.get_content_type() == "text/plain"
                        and not part.get("Content-Disposition")
                    ):
                        body = part.get_payload(decode=True).decode()
                        break
            else:
                body = msg.get_payload(decode=True).decode()

            otp_match = re.search(r"\b\d{6}\b", body)
            imap.logout()

            if otp_match:
                otp_code = otp_match.group()
                log(f"✅ OTP found: {otp_code}")
                return otp_code
            else:
                log("No OTP found in email body. Retrying...")

        except Exception as e:
            log(f"Error during OTP fetch: {str(e)}")

        time.sleep(check_interval)

    log("❌ OTP not found within time limit")
    return None


# ================== SELENIUM LOGIN ==================
log("Initializing Chrome WebDriver...")
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("window-size=1920,1080")

driver = webdriver.Chrome(options=options)

try:
    log("Navigating to Axos login page...")
    driver.get("https://ws.axosclearing.com/?idp=Axos")

    log("Waiting for username field...")
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "b1-b4-InputField"))
    )

    log("Entering credentials...")
    driver.find_element(By.ID, "b1-b4-InputField").send_keys(AXOS_USERNAME)
    driver.find_element(By.ID, "b1-b5-InputField").send_keys(AXOS_PASSWORD)
    driver.find_element(By.ID, "b1-signInButton").click()

    log("Waiting for OTP input field...")
    otp_input = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.ID, "b1-b2-b5-InputField"))
    )

    otp = fetch_latest_otp()
    if not otp:
        raise Exception("OTP not received in time")

    log("Entering OTP...")
    otp_input.send_keys(otp)
    driver.find_element(By.ID, "b1-b2-SubmitButton").click()

    log("Checking for popup...")
    try:
        yes_button = WebDriverWait(driver, 8).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@class='popup-content']//button[normalize-space()='Yes']")
            )
        )
        yes_button.click()
        log("Popup detected → Clicked Yes")
    except:
        log("No popup appeared. Continuing...")

    log("Waiting 15 seconds for page to settle...")
    time.sleep(15)

    log("Checking for URL change to confirm login...")
    WebDriverWait(driver, 30).until_not(
        EC.url_to_be("https://ws.axosclearing.com/?idp=Axos")
    )

    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, "//body"))
    )

    log("✅ Login successful!")

    # Save screenshot
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_path = "screenshots"
    os.makedirs(folder_path, exist_ok=True)
    screenshot_path = os.path.join(folder_path, f"AXOS_Login_{timestamp}.png")
    driver.save_screenshot(screenshot_path)
    log(f"📸 Screenshot saved to: {screenshot_path}")

    # Send screenshot via email
    send_email_with_attachment(
        subject="Axos Login Screenshot",
        body="Attached is the latest Axos login screenshot.",
        file_path=screenshot_path,
    )

except Exception as e:
    log(f"❌ Login failed: {str(e)}")

finally:
    log("Closing browser...")
    driver.quit()


