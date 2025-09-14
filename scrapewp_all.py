from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

driver = webdriver.Chrome()
driver.get("https://fantasy.espn.com/football/fantasycast?leagueId=31028552")

wait = WebDriverWait(driver, 20)

# wait for scoreboard tabs (the small boxes at the top)
wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.ScoreboardMatchups__Item")))

# grab all matchup tabs
tabs = driver.find_elements(By.CSS_SELECTOR, "div.ScoreboardMatchups__Item")
print("Tabs found:", len(tabs))

for i in range(len(tabs)):
    # re-grab tabs each loop (because DOM refreshes after a click)
    tabs = driver.find_elements(By.CSS_SELECTOR, "div.ScoreboardMatchups__Item")

    # click the i-th tab
    driver.execute_script("arguments[0].click();", tabs[i])
    time.sleep(2)  # allow page to update

    # now scrape the visible matchup
    matchup = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.container.gameBorder")))

    team_names = [el.text.strip() for el in matchup.find_elements(By.CSS_SELECTOR, "span.teamName")]
    percents = [el.text.strip() for el in matchup.find_elements(By.CSS_SELECTOR, "div.totalPerc")]

    if team_names and percents:
        for t, p in zip(team_names, percents):
            print(f"{t}: {p}")
        print("-" * 30)

driver.quit()
