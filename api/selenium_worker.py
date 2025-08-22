from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from io import BytesIO
from PIL import Image
import easyocr
import time, re, shutil, traceback
import chromedriver_autoinstaller

# OCR reader
reader = easyocr.Reader(['en'])

def clean_text(text: str) -> str:
    return re.sub(r'[^A-Z]', '', text.upper())

def run_vote_process(phone_number: str, retries: int = 3) -> bool:
    url = "https://openbudget.uz/boards/initiatives/initiative/52/dfefaa89-426a-4cfb-8353-283a581d3840"
    print("🔎 Boshlanmoqda.. Telefon raqami:", phone_number)

    # Chromium path
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    print("📍 Chromium path:", chrome_path)

    # ChromeDriver o‘rnatish
    try:
        chromedriver_autoinstaller.install()
        print("✅ Chromedriver avtomatik o‘rnatildi")
    except Exception as e:
        print("❌ Chromedriver o‘rnatishda muammo:", repr(e))
        traceback.print_exc()
        return False

    chrome_options = Options()
    chrome_options.binary_location = chrome_path
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36")

    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("🚀 Chrome ishga tushdi")
    except Exception as e:
        print("❌ Chrome ishga tushmadi:", repr(e))
        traceback.print_exc()
        return False

    try:
        driver.get(url)
        driver.implicitly_wait(10)
        print("🌍 Saytga kirildi:", url)

        # "Sms orqali" tugmasini topib bosish
        try:
            sms_span = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//button[contains(@class,'vote')]//span[contains(text(),'Sms orqali')]")
                )
            )
            sms_button = sms_span.find_element(By.XPATH, "./ancestor::button")
            driver.execute_script("arguments[0].click();", sms_button)
            print("📌 Sms orqali tugmasi bosildi")
        except Exception as e:
            print("❌ Sms orqali tugmasi topilmadi:", repr(e))
            driver.save_screenshot("sms_button_error.png")
            return False

        # Telefon raqami inputini kutish
        phone_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='tel']"))
        )
        print("✅ Telefon raqami input topildi")
        phone_input.send_keys(phone_number)
        print("📲 Telefon raqami kiritildi")

        # CAPTCHA rasmlarini olish
        imgA = driver.find_element(By.XPATH, "//div[contains(text(),'Расм А')]/following::img[1]")
        imgB = driver.find_element(By.XPATH, "//div[contains(text(),'Расм Б')]/following::img[1]")

        imgA_png = Image.open(BytesIO(imgA.screenshot_as_png))
        imgB_png = Image.open(BytesIO(imgB.screenshot_as_png))

        # OCR
        textA = [clean_text(t) for t in reader.readtext(imgA_png, detail=0) if clean_text(t)]
        resultsB = [(bbox, clean_text(txt)) for (bbox, txt, prob) in reader.readtext(imgB_png) if clean_text(txt)]

        print("✅ Captcha A:", textA)
        print("✅ Captcha B:", [t for _, t in resultsB])

        clicked = False
        for (bbox, txt_clean) in resultsB:
            if txt_clean in textA:
                driver.execute_script("arguments[0].click();", imgB)
                print(f"🖱️ Topildi va bosildi: {txt_clean}")
                clicked = True
                time.sleep(1)
                break

        if not clicked:
            print("❌ Harf topilmadi")
            if retries > 0:
                print("🔄 Qayta urinilmoqda...")
                driver.find_element(By.CSS_SELECTOR, "img[alt='reload']").click()
                time.sleep(2)
                driver.quit()
                return run_vote_process(phone_number, retries - 1)
            return False

        # SMS yuborish
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()
        print("📨 SMS yuborildi, kod kutilmoqda...")

        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='number']"))
        )
        print("🎉 Captcha muvaffaqiyatli yechildi, SMS kodi maydoni chiqdi!")
        return True

    except Exception as e:
        print("❌ Umumiy xatolik:", repr(e))
        driver.save_screenshot("error_screenshot.png")
        traceback.print_exc()
        return False
    finally:
        driver.quit()
        print("🔒 Chrome yopildi")
