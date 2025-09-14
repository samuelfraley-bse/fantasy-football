from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# launch browser
driver = webdriver.Chrome()
driver.get("https://fantasy.espn.com/football/fantasycast?leagueId=31028552")

wait = WebDriverWait(driver, 20)

# wait for "Chance to Win" section to appear
wait.until(EC.presence_of_element_located((By.XPATH, "//div[text()='Chance to Win']")))

# get the matchup container that holds the team names + percentages
matchup_container = driver.find_element(
    By.XPATH,
    "//div[text()='Chance to Win']/ancestor::div[contains(@class, 'matchupContainer')]"
)

# extract the two team names
team_names = [el.text for el in matchup_container.find_elements(By.CSS_SELECTOR, "div.ScoreCell__TeamName")]

# extract the two win probabilities
percents = [el.text for el in matchup_container.find_elements(By.CSS_SELECTOR, "div.totalPerc")]

# print results
for team, pct in zip(team_names, percents):
    print(f"{team}: {pct}")

driver.quit()
