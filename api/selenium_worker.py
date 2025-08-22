
import easyocr

# OCR reader
reader = easyocr.Reader(['en'])
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from io import BytesIO
from PIL import Image
import time, re, shutil, traceback
import chromedriver_autoinstaller

# Matndan faqat lotin harflarini olish funksiyasi
def clean_text(text: str) -> str:
    return re.sub(r'[^A-Z]', '', text.upper())

def run_vote_process(phone_number: str, retries: int = 3) -> bool:
    url = "https://openbudget.uz/boards/initiatives/initiative/52/dfefaa89-426a-4cfb-8353-283a581d3840"
    print("🔎 Boshlanmoqda... Telefon raqami:", phone_number)

    # Chromium ning to'liq yo'lini aniqlaymiz
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    print("📍 Chromium path:", chrome_path)

    # Chromedriverni o‘rnatamiz (mos versiyani yuklaydi)
    try:
        chromedriver_autoinstaller.install()
        print("✅ Chromedriver avtomatik o‘rnatildi")
    except Exception as e:
        print("❌ Chromedriver o‘rnatishda muammo:", repr(e))
        traceback.print_exc()
        return False

    # Chrome uchun parametrlar
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

    # Brauzerni ishga tushiramiz
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

        # Sahifadagi ovoz berish bo‘limida 2 ta .vote elementi bor (Telegram va SMS).
        # Ikkinchi .vote element – SMS orqali tugmasi.
        try:
            votes = WebDriverWait(driver, 30).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.vote"))
            )
            if len(votes) < 2:
                print("❌ vote elementlari topilmadi")
                return False
            sms_button = votes[1]  # ikkinchi vote elementi SMS uchun
            driver.execute_script("arguments[0].click();", sms_button)
            print("📌 Sms orqali tugmasi bosildi")
        except Exception as e:
            print("❌ Sms orqali tugmasini topib bo‘lmadi:", repr(e))
            driver.save_screenshot("sms_button_error.png")
            return False

        # Telefon raqami inputini kutish va kiritish
        phone_input = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='tel']"))
        )
        print("✅ Telefon raqami input topildi")
        phone_input.send_keys(phone_number)
        print("📲 Telefon raqami kiritildi")

        # CAPTCHA rasmlarini olish (ular 'Расм А' va 'Расм Б' matni tagida joylashgan)
        imgA_elem = driver.find_element(By.XPATH, "//div[contains(text(),'Расм А')]/following::img[1]")
        imgB_elem = driver.find_element(By.XPATH, "//div[contains(text(),'Расм Б')]/following::img[1]")

        imgA_png = Image.open(BytesIO(imgA_elem.screenshot_as_png))
        imgB_png = Image.open(BytesIO(imgB_elem.screenshot_as_png))

        # Rasm fayllarini saqlash – foydalanuvchi ko‘ra olishi va o‘zi yechishi uchun
        imgA_path = "captcha_A.png"
        imgB_path = "captcha_B.png"
        imgA_png.save(imgA_path)
        imgB_png.save(imgB_path)
        print(f"🖼️ CAPTCHA A va B rasmlari saqlandi: {imgA_path}, {imgB_path}")
        print("📝 CAPTCHA rasmlarini ko‘rib, Rasm A harflarining juftligini Rasm B dan tanlang va qo‘lda bosing.")

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
        # SMS yuborish tugmasini bosish (faollashganda)
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()
        print("📨 SMS yuborildi, kod kutilmoqda...")

        # SMS kod maydonini kutish
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
