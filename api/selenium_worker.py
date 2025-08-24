import time, base64, shutil
from dataclasses import dataclass
from typing import Dict, Any

import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException

from .selenium_registry import set_driver, get_driver, pop_driver

INITIATIVE_URL = (
    "https://openbudget.uz/boards/initiatives/initiative/52/"
    "dfefaa89-426a-4cfb-8353-283a581d3840"
)

@dataclass
class CaptchaBInfo:
    width: int
    height: int
    image_b64: str  # PNG base64 (raw, headersiz)

def _create_driver(headless: bool = True) -> webdriver.Chrome:
    chrome_path = shutil.which("chromium") or shutil.which("chromium-browser")
    try:
        chromedriver_autoinstaller.install()
    except Exception:
        pass
    opts = Options()
    if chrome_path:
        opts.binary_location = chrome_path
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-software-rasterizer")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
    )
    d = webdriver.Chrome(options=opts)
    d.set_window_size(1280, 900)
    return d

def _js_click(drv, el):
    drv.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    drv.execute_script("arguments[0].click();", el)

def _safe_click(drv, el):
    try:
        el.click()
    except ElementClickInterceptedException:
        _js_click(drv, el)

def _wait_any_clickable(wait: WebDriverWait, locs):
    last = None
    for by, sel in locs:
        try:
            return wait.until(EC.element_to_be_clickable((by, sel)))
        except TimeoutException as e:
            last = e
    raise last or TimeoutException("Clickable element not found")

def _open_sms_modal(drv):
    w = WebDriverWait(drv, 25)
    w.until(EC.presence_of_all_elements_located((By.TAG_NAME, "body")))
    sms_btn = _wait_any_clickable(w, (
        (By.XPATH, "//button[contains(translate(., 'SMSсмс', 'smsсмс'),'sms')]"),
        (By.XPATH, "//div[contains(., 'Sms') or contains(., 'Смс')]/ancestor::button"),
        (By.XPATH, "//div[@class='vote']//button[.//span[contains(translate(., 'SMSсмс','smsсмс'),'sms')]]"),
    ))
    _safe_click(drv, sms_btn)

def _fill_phone(drv, phone: str):
    inp = WebDriverWait(drv, 20).until(EC.presence_of_element_located((
        By.XPATH, "//input[@type='tel' or contains(@placeholder,'998') or @inputmode='tel']"
    )))
    inp.clear()
    inp.send_keys(phone)

def _find_captcha_b(drv):
    w = WebDriverWait(drv, 20)
    candidates = (
        (By.XPATH, "//*[contains(., 'Расм Б')]/following::*[self::img or self::canvas or self::div][1]"),
        (By.XPATH, "//div[contains(@class,'captcha')]//*[contains(.,'Расм Б')]/following::*[self::img or self::canvas or self::div][1]"),
        (By.XPATH, "//div[contains(@class,'captcha')]//*[self::img or self::canvas or self::div][last()]"),
    )
    for by, sel in candidates:
        try:
            return w.until(EC.visibility_of_element_located((by, sel)))
        except TimeoutException:
            pass
    raise TimeoutException("Rasm B topilmadi")

def _get_b_info_and_shot(drv) -> CaptchaBInfo:
    imgB = _find_captcha_b(drv)
    png = imgB.screenshot_as_png
    image_b64 = base64.b64encode(png).decode("ascii")
    rect: Dict[str, Any] = drv.execute_script("""
        const el = arguments[0];
        const r = el.getBoundingClientRect();
        return {w: Math.round(r.width), h: Math.round(r.height)};
    """, imgB)
    return CaptchaBInfo(width=int(rect["w"]), height=int(rect["h"]), image_b64=image_b64)

def _click_b_at(drv, x: int, y: int):
    imgB = _find_captcha_b(drv)
    ActionChains(drv).move_to_element_with_offset(imgB, int(x), int(y)).click().perform()

def _click_send_sms(drv):
    btn = _wait_any_clickable(WebDriverWait(drv, 20), (
        (By.XPATH, "//button[not(@disabled) and (contains(translate(., 'SMSсмс', 'smsсмс'),'sms') or contains(., 'юбориш') or contains(., 'jo'))]"),
        (By.CSS_SELECTOR, "button[type='submit']:not([disabled])"),
    ))
    _safe_click(drv, btn)

def _wait_otp_input(drv, timeout=25):
    WebDriverWait(drv, timeout).until(EC.presence_of_element_located((
        By.XPATH, "//input[@type='number' or @inputmode='numeric' or contains(@autocomplete,'one-time')]"
    )))

def _enter_otp_and_submit(drv, code: str):
    otp = WebDriverWait(drv, 15).until(EC.presence_of_element_located((
        By.XPATH, "//input[@type='number' or @inputmode='numeric' or contains(@autocomplete,'one-time')]"
    )))
    otp.clear()
    otp.send_keys(code)
    sub = _wait_any_clickable(WebDriverWait(drv, 15), (
        (By.XPATH, "//button[not(@disabled) and (contains(., 'tasdiq') or contains(., 'Тасдиқ') or contains(., 'OK') or contains(., 'Ok') or contains(., 'ОК'))]"),
        (By.CSS_SELECTOR, "button[type='submit']:not([disabled])"),
    ))
    _safe_click(drv, sub)

# ---- public API ----
def start_vote_session(vote_id: int, phone: str) -> CaptchaBInfo:
    d = _create_driver(headless=True)
    d.get(INITIATIVE_URL)
    _open_sms_modal(d)
    _fill_phone(d, phone)
    info = _get_b_info_and_shot(d)
    set_driver(vote_id, d)
    return info

def click_captcha_and_send_sms(vote_id: int, x: int, y: int) -> None:
    d = get_driver(vote_id)
    if not d:
        raise RuntimeError("Driver session not found (vote expired or not started)")
    _click_b_at(d, x, y)
    _click_send_sms(d)
    _wait_otp_input(d, timeout=25)

def verify_otp(vote_id: int, code: str) -> bool:
    d = get_driver(vote_id)
    if not d:
        raise RuntimeError("Driver session not found")
    _enter_otp_and_submit(d, code)
    time.sleep(2)
    return True

def close_vote_session(vote_id: int):
    d = pop_driver(vote_id)
    if d:
        try: d.quit()
        except Exception: pass
