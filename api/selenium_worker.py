from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from io import BytesIO
from PIL import Image
import easyocr
import time
import re

# OCR ўқувчиси
reader = easyocr.Reader(['en'])

def clean_text(text: str) -> str:
    """Faqat A-Z harflarini qoldiradi"""
    return re.sub(r'[^A-Z]', '', text.upper())

def run_vote_process(phone_number: str) -> bool:
    url = "https://openbudget.uz/boards/initiatives/initiative/52/dfefaa89-426a-4cfb-8353-283a581d3840"

    # Oxylabs прокси
    USERNAME = "davronov_xhrj7-cc-UZ-sessid-openbudget1"
    PASSWORD = "Davronov_1997"
    proxy_url = f"http://customer-{USERNAME}:{PASSWORD}@pr.oxylabs.io:7777"

    seleniumwire_options = {
        'proxy': {
            'http': proxy_url,
            'https': proxy_url,
            'no_proxy': 'localhost,127.0.0.1'
        }
    }

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(options=chrome_options, seleniumwire_options=seleniumwire_options)

    try:
        driver.get(url)
        time.sleep(3)

        # Telefon raqamini kiritish
        phone_input = driver.find_element(By.CSS_SELECTOR, "input[type='tel']")
        phone_input.send_keys(phone_number)

        # CAPTCHA A va B rasmlari
        imgA = driver.find_element(By.XPATH, "//div[contains(text(),'Расм А')]/following::img[1]")
        imgB = driver.find_element(By.XPATH, "//div[contains(text(),'Расм Б')]/following::img[1]")

        # Screenshot olish
        imgA_png = Image.open(BytesIO(imgA.screenshot_as_png))
        imgB_png = Image.open(BytesIO(imgB.screenshot_as_png))

        # OCR natijalari
        textA = [clean_text(t) for t in reader.readtext(imgA_png, detail=0)]
        resultsB = reader.readtext(imgB_png)

        print("✅ Captcha A:", textA)

        # B rasm o‘lchamlari
        b_width, b_height = imgB_png.size

        actions = ActionChains(driver)
        clicked = False

        for (bbox, txt, prob) in resultsB:
            txt_clean = clean_text(txt)
            if txt_clean and txt_clean in textA:
                # bbox markazi
                x = (bbox[0][0] + bbox[2][0]) / 2
                y = (bbox[0][1] + bbox[2][1]) / 2
                # Normalizatsiya
                x_norm = x / b_width
                y_norm = y / b_height
                actions.move_to_element_with_offset(
                    imgB,
                    x_norm * imgB.size['width'],
                    y_norm * imgB.size['height']
                ).click().perform()
                clicked = True
                print(f"✅ Topildi: {txt_clean}")
                time.sleep(0.5)

        if not clicked:
            print("❌ Harf topilmadi, captcha yangilash kerak!")
            refresh_btn = driver.find_element(By.CSS_SELECTOR, "img[alt='reload']")
            refresh_btn.click()
            time.sleep(2)
            return run_vote_process(phone_number)  # qayta urinib ko‘ramiz

        # SMS yuborish tugmasi
        submit_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        submit_btn.click()

        # ✅ Captcha muvaffaqiyatini tekshirish
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='number']"))
            )
            print("🎉 Captcha muvaffaqiyatli, SMS kodi maydoni chiqdi!")
            return True
        except:
            # xato xabarni tekshirish
            error_msgs = driver.find_elements(By.XPATH, "//*[contains(text(),'хато') or contains(text(),'xato')]")
            if error_msgs:
                print("❌ Captcha noto‘g‘ri, qayta urinib ko‘rilmoqda...")
                refresh_btn = driver.find_element(By.CSS_SELECTOR, "img[alt='reload']")
                refresh_btn.click()
                time.sleep(2)
                return run_vote_process(phone_number)
            else:
                print("⚠️ CAPTCHA natijasi aniqlanmadi")
                return False

    except Exception as e:
        print("❌ Xatolik:", e)
        return False
    finally:
        driver.quit()
