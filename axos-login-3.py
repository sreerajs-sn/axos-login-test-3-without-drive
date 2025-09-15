log("Initializing Chrome WebDriver...")
options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("window-size=1920,1080")

driver = webdriver.Chrome(options=options)

try:
    log("🚀 Launching Axos login automation...")

    log("🌐 Navigating to Axos login page...")
    driver.get("https://ws.axosclearing.com/?idp=Axos")

    log("🔍 Waiting for username field to appear...")
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.ID, "b1-b4-InputField"))
    )

    log("🧑‍💻 Entering username and password...")
    driver.find_element(By.ID, "b1-b4-InputField").send_keys(AXOS_USERNAME)
    driver.find_element(By.ID, "b1-b5-InputField").send_keys(AXOS_PASSWORD)
    driver.find_element(By.ID, "b1-signInButton").click()

    log("🔐 Waiting for OTP input field...")
    otp_input = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.ID, "b1-b2-b5-InputField"))
    )

    log("📨 Fetching OTP from email...")
    otp = fetch_latest_otp()
    if not otp:
        log("❌ OTP not received in time. Aborting login.")
        raise Exception("OTP not received in time")

    log(f"🔢 Entering OTP: {otp}")
    otp_input.send_keys(otp)
    driver.find_element(By.ID, "b1-b2-SubmitButton").click()

    log("🧼 Checking for post-login popup...")
    try:
        yes_button = WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((By.XPATH, "//div[@class='popup-content']//button[normalize-space()='Yes']"))
        )
        yes_button.click()
        log("✅ Popup detected and dismissed.")
    except:
        log("ℹ️ No popup appeared. Proceeding...")

    log("⏳ Waiting for page to settle...")
    time.sleep(15)

    log("🔄 Verifying URL change to confirm login...")
    WebDriverWait(driver, 30).until_not(
        EC.url_to_be("https://ws.axosclearing.com/?idp=Axos")
    )

    log("📄 Waiting for page body to load...")
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, "//body"))
    )

    log("✅ Login confirmed. Capturing screenshot...")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_path = "screenshots"
    os.makedirs(folder_path, exist_ok=True)
    screenshot_path = os.path.join(folder_path, f"AXOS_Login_{timestamp}.png")
    driver.save_screenshot(screenshot_path)
    log(f"📸 Screenshot saved to: {screenshot_path}")

    log("📧 Preparing to send screenshot via email...")
    send_email_with_attachment(
        subject="Axos Login Screenshot",
        body="Attached is the latest Axos login screenshot.",
        file_path=screenshot_path
    )

except Exception as e:
    log(f"❌ Exception occurred: {str(e)}")

finally:
    log("🛑 Closing browser and cleaning up...")
    driver.quit()
