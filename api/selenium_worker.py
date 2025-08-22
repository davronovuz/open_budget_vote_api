import easyocr
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from io import BytesIO
from PIL import Image
import time, re, shutil, traceback
import chromedriver_autoinstaller

# OCR reader
reader = easyocr.Reader(['en'])

# Matndan faqat lotin harflarini olish funksiyasi
def clean_text(text: str) -> str:
    return re.sub(r'[^A-Z]', '', text.upper())


def run_vote_process(phone_number: str, retries: int = 3) -> bool:
    url = "https://openbudget.uz/boards/initiatives/initiative/52/dfefaa89-426a-4cfb-8353-283a581d3840"
    print("🔎 Boshlanmoqda... Telefon raqami:", phone_number)

    # Chromium yo‘li
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    print("📍 Chromium path:", chrome_path)

    # Chromedriver
    try:
        chromedriver_autoinstaller.install()
        print("✅ Chromedriver avtomatik o‘rnatildi")
    except Exception as e:
        print("❌ Chromedriver muammo:", repr(e))
        traceback.print_exc()
        return False

    # Chrome opts
    chrome_options = Options()
    chrome_options.binary_location = chrome_path
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
    )

    try:
        driver = webdriver.Chrome(options=chrome_options)
        print("🚀 Chrome ishga tushdi")
    except Exception as e:
        print("❌ Chrome ishga tushmadi:", repr(e))
        traceback.print_exc()
        return False

    try:
        driver.get(url)
        print("🌍 Saytga kirildi:", url)

        # === 1) "Sms orqali" tugmasi bosish ===
        sms_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//div[contains(@class,'vote')]//span[contains(text(),'Sms orqali')]")
            )
        )
        driver.execute_script("arguments[0].click();", sms_button)
        print("📌 Sms orqali tugmasi bosildi")
        driver.save_screenshot("step_sms_button.png")

        # === 2) Telefon raqami input ===
        phone_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='tel']"))
        )
        phone_input.send_keys(phone_number)
        print("📲 Telefon raqami kiritildi")
        driver.save_screenshot("step_phone_input.png")

        # === 3) Captcha ===
        imgA_elem = driver.find_element(By.XPATH, "//div[contains(text(),'Расм А')]/following::img[1]")
        imgB_elem = driver.find_element(By.XPATH, "//div[contains(text(),'Расм Б')]/following::img[1]")

        imgA_png = Image.open(BytesIO(imgA_elem.screenshot_as_png))
        imgB_png = Image.open(BytesIO(imgB_elem.screenshot_as_png))

        imgA_png.save("captcha_A.png")
        imgB_png.save("captcha_B.png")
        print("🖼️ Captcha rasmlari saqlandi")

        # OCR
        textA = [clean_text(t) for t in reader.readtext(imgA_png, detail=0) if clean_text(t)]
        resultsB = [(bbox, clean_text(txt)) for (bbox, txt, prob) in reader.readtext(imgB_png) if clean_text(txt)]

        print("✅ Captcha A:", textA)
        print("✅ Captcha B:", [t for _, t in resultsB])

        clicked = False
        for (bbox, txt_clean) in resultsB:
            if txt_clean in textA:
                # bboxdan markaziy koordinata topib click qilish
                x = int((bbox[0][0] + bbox[2][0]) / 2)
                y = int((bbox[0][1] + bbox[2][1]) / 2)
                webdriver.ActionChains(driver).move_to_element_with_offset(imgB_elem, x, y).click().perform()
                print(f"🖱️ Captcha bosildi: {txt_clean}")
                clicked = True
                driver.save_screenshot("step_captcha_click.png")
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

        # === 4) SMS yuborish tugmasi ===
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()
        print("📨 SMS yuborildi, kod kutilmoqda...")
        driver.save_screenshot("step_sms_sent.png")

        # === 5) SMS kod maydonini kutish ===
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='number']"))
        )
        print("🎉 Captcha muvaffaqiyatli, SMS kodi maydoni chiqdi!")
        return True

    except Exception as e:
        print("❌ Umumiy xatolik:", repr(e))
        driver.save_screenshot("error_screenshot.png")
        traceback.print_exc()
        return False

    finally:
        driver.quit()
        print("🔒 Chrome yopildi")
