# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    StaleElementReferenceException, TimeoutException, ElementClickInterceptedException
)
import time, re, csv, datetime, os
import tempfile
import chromedriver_autoinstaller  # pip install chromedriver-autoinstaller

URL = "https://fantasy.espn.com/football/fantasycast?leagueId=31028552"
OUTFILE = "fantasycast_ctw.csv"

# ----------- setup -----------
opts = webdriver.ChromeOptions()
opts.add_argument("--window-size=1400,1000")
opts.add_argument("--disable-gpu")
opts.add_argument("--no-default-browser-check")
opts.add_argument("--no-first-run")
opts.add_argument("--lang=es-ES")

# headless flags for GitHub Actions (also fine locally)
opts.add_argument("--headless=new")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--no-sandbox")

# ✅ give Chrome a UNIQUE profile dir every run (prevents "already in use")
unique_profile = tempfile.mkdtemp(prefix="selenium-profile-")
opts.add_argument(f"--user-data-dir={unique_profile}")

# ✅ ensure a matching ChromeDriver is present on the runner
chromedriver_autoinstaller.install()

# ❌ DO NOT pass Service() here — let Selenium auto-find the binary we just installed
driver = webdriver.Chrome(options=opts)
wait = WebDriverWait(driver, 30)

driver.get(URL)
print(f"[info] Using user-data-dir: {unique_profile}")


# ----------- consent -----------
def dismiss_consent(max_wait=25):
    end = time.time() + max_wait
    btn_x = [
        "//button[normalize-space()='Aceptar']",
        "//button[contains(., 'Aceptar todo') or contains(., 'Aceptar todas')]",
        "//button[contains(., 'Estoy de acuerdo') or contains(., 'Consentir') or contains(., 'Continuar')]",
        "//span[normalize-space()='Aceptar']/ancestor::button",
        "//button[normalize-space()='Accept']",
        "//button[contains(., 'Accept All') or contains(., 'Agree') or contains(., 'Continue')]",
        "//span[normalize-space()='Accept']/ancestor::button",
    ]
    iframe_sel = (
        "iframe[id^='sp_message_iframe'],iframe[title*='privacy' i],"
        "iframe[title*='consent' i],iframe[src*='consent' i],iframe[src*='privacy' i]"
    )
    while time.time() < end:
        driver.switch_to.default_content()
        for xp in btn_x:
            els = driver.find_elements(By.XPATH, xp)
            if els:
                driver.execute_script("arguments[0].click();", els[0]); return True
        for fr in driver.find_elements(By.CSS_SELECTOR, iframe_sel):
            try:
                driver.switch_to.frame(fr)
                for xp in btn_x:
                    els = driver.find_elements(By.XPATH, xp)
                    if els:
                        driver.execute_script("arguments[0].click();", els[0]); return True
            finally:
                driver.switch_to.default_content()
        time.sleep(0.3)
    return False

print(f"[info] Consent dismissed? {dismiss_consent()}")

# ----------- find the fantasy iframe by visible text anchor -----------
def switch_into_matchup_iframe():
    for _ in range(3):
        time.sleep(2.0)
    driver.switch_to.default_content()

    def has_ctw():
        try:
            return bool(driver.find_elements(By.XPATH, "//*[contains(normalize-space(),'Chance to Win')]"))
        except Exception:
            return False

    if has_ctw():
        return True

    def dfs(depth=0, max_depth=4):
        if depth > max_depth:
            return False
        frames = driver.find_elements(By.TAG_NAME, "iframe")
        for i in range(len(frames)):
            try:
                driver.switch_to.default_content()
                frames = driver.find_elements(By.TAG_NAME, "iframe")
                if i >= len(frames):
                    continue
                f = frames[i]
                driver.switch_to.frame(f)
                if has_ctw():
                    return True
                if dfs(depth+1, max_depth):
                    return True
            except StaleElementReferenceException:
                continue
            finally:
                driver.switch_to.parent_frame()
        return False

    return dfs()

if not switch_into_matchup_iframe():
    raise RuntimeError("Could not find the FantasyCast iframe with 'Chance to Win'")

wait.until(EC.visibility_of_element_located((By.XPATH, "//*[contains(normalize-space(),'Chance to Win')]")))
print("[info] In matchup iframe.")

# ----------- scraping helpers -----------
def get_current_team_names():
    panel = WebDriverWait(driver, 15).until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(normalize-space(),'Chance to Win')]/ancestor::*[self::div or self::section][1]")
        )
    )
    cand = []
    cand += panel.find_elements(By.CSS_SELECTOR, "span.teamName")
    cand += panel.find_elements(By.XPATH, ".//h1|.//h2|.//h3|.//span[contains(@class,'TeamName')]")
    names, seen_local = [], set()
    for e in cand:
        t = (e.text or "").strip()
        if t and t not in seen_local:
            names.append(t); seen_local.add(t)
        if len(names) == 2:
            break
    return names[0], names[1]

def get_ctw_percents():
    panel = WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located(
            (By.XPATH, "//*[contains(normalize-space(),'Chance to Win')]/ancestor::*[self::div or self::section][1]")
        )
    )
    percs = [e.text.strip() for e in panel.find_elements(By.CSS_SELECTOR, "div.totalPerc") if e.text.strip()]
    if len(percs) < 2:
        extra = [e.text.strip() for e in panel.find_elements(By.XPATH, ".//*[contains(text(),'%')]")]
        percs = [p for p in extra if '%' in p][:2]
    while len(percs) < 2:
        percs.append("")
    return percs[0], percs[1]

def get_unique_data_ids():
    ids = set()
    for n in driver.find_elements(By.XPATH, "//div[contains(@class,'Thumbnails__Item') and contains(@class,'pointer') and @data-id]"):
        did = n.get_attribute("data-id")
        if did and did.isdigit():
            ids.add(int(did))
    return sorted(ids)

def activate_pill_by_id(did):
    try:
        before = get_current_team_names()
    except Exception:
        before = None

    link, slide_container = None, None
    for _ in range(4):
        links = driver.find_elements(
            By.XPATH,
            f"//div[contains(@class,'Thumbnails__Item') and @data-id='{did}']//a[contains(@class,'ScoreCell__Link')]"
        )
        if links:
            link = links[-1]
            try:
                slide_container = driver.find_element(
                    By.XPATH, f"//div[contains(@class,'Thumbnails__Item') and @data-id='{did}']"
                )
            except Exception:
                pass
            break
        time.sleep(0.2)

    if not link:
        raise TimeoutException(f"No clickable link for data-id={did}")

    driver.execute_script("""
      const el = arguments[0];
      try { el.scrollIntoView({block:'nearest', inline:'center'}); } catch(e){}
    """, link)

    try:
        driver.execute_script("arguments[0].click();", link)
    except Exception:
        try: link.click()
        except Exception: pass

    for _ in range(24):
        try:
            if slide_container:
                cls = slide_container.get_attribute("class") or ""
                if "selected" in cls or "Thumbnails__Item--active" in cls:
                    return True
            if before:
                now = get_current_team_names()
                if now != before:
                    return True
        except StaleElementReferenceException:
            return True
        time.sleep(0.33)
    return False

# ----------- CSV setup -----------
if not os.path.exists(OUTFILE):
    with open(OUTFILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "teamA", "pctA", "teamB", "pctB"])

def scrape_current():
    a, b = get_current_team_names()
    p1, p2 = get_ctw_percents()
    ts = datetime.datetime.now().isoformat(timespec="seconds")

    # print
    print(f"{a}: {p1}")
    print(f"{b}: {p2}")
    print("-" * 30)

    # append to CSV
    with open(OUTFILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([ts, a, p1, b, p2])

    return (a, b)

# ----------- scrape all matchups -----------
seen_pairs = set()
try:
    seen_pairs.add(scrape_current())
except Exception as e:
    print(f"[warn] initial scrape failed: {e}")

all_ids = get_unique_data_ids()
print(f"[info] data-ids found: {all_ids}")

for did in all_ids:
    try:
        ok = activate_pill_by_id(did)
        time.sleep(0.5)
        pair = scrape_current()
        if pair not in seen_pairs:
            seen_pairs.add(pair)
    except Exception as e:
        print(f"[warn] data-id {did} failed: {e}")

driver.quit()
