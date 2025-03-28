import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import csv

def scrape_nfl_draft_data():
    # Create a map of team short names to long names
    team_name_map = {
        "ARI": "Arizona Cardinals",
        "ATL": "Atlanta Falcons",
        "BAL": "Baltimore Ravens",
        "BUF": "Buffalo Bills",
        "CAR": "Carolina Panthers",
        "CHI": "Chicago Bears",
        "CIN": "Cincinnati Bengals",
        "CLE": "Cleveland Browns",
        "DAL": "Dallas Cowboys",
        "DEN": "Denver Broncos",
        "DET": "Detroit Lions",
        "GNB": "Green Bay Packers",
        "HOU": "Houston Texans",
        "IND": "Indianapolis Colts",
        "JAX": "Jacksonville Jaguars",
        "KAN": "Kansas City Chiefs",
        "LAC": "Los Angeles Chargers",
        "LAR": "Los Angeles Rams",
        "LVR": "Las Vegas Raiders",
        "MIA": "Miami Dolphins",
        "MIN": "Minnesota Vikings",
        "NWE": "New England Patriots",
        "NOR": "New Orleans Saints",
        "NYG": "New York Giants",
        "NYJ": "New York Jets",
        "PHI": "Philadelphia Eagles",
        "PIT": "Pittsburgh Steelers",
        "SEA": "Seattle Seahawks",
        "SFO": "San Francisco 49ers",
        "TAM": "Tampa Bay Buccaneers",
        "TEN": "Tennessee Titans",
        "WAS": "Washington Commanders"
    }
    
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Initialize the Chrome driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    # URL to scrape
    url = "https://www.pro-football-reference.com/years/2024/draft.htm"
    
    try:
        # Navigate to the URL
        driver.get(url)
        
        # Wait for the table to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "drafts"))
        )
        
        # Get the page source after JavaScript execution
        html_content = driver.page_source
        
        # Parse the HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Find the draft table
        draft_table = soup.find("table", {"id": "drafts"})
        
        # Lists to store data
        draft_data = []
        
        # Get headers
        headers = []
        header_row = draft_table.find("thead").find_all("th")
        for header in header_row:
            # Get the column name from data-stat attribute or text
            if header.get("data-stat"):
                headers.append(header["data-stat"])
            else:
                headers.append(header.text.strip())
        
        # Get draft rows
        draft_rows = draft_table.find("tbody").find_all("tr")
        for row in draft_rows:
            # Skip header rows
            if "thead" in row.get("class", []):
                continue
                
            row_data = {}
            # Get cells in the row
            cells = row.find_all(["th", "td"])
            for i, cell in enumerate(cells):
                if i < len(headers):
                    # Get the data-stat attribute to identify the column
                    stat_type = cell.get("data-stat")
                    if stat_type:
                        # Extract player name
                        if stat_type == "player":
                            row_data["player"] = cell.text.strip()
                        # Convert team short name to long name
                        elif stat_type == "team":
                            team_short = cell.text.strip()
                            row_data["team"] = team_name_map.get(team_short, team_short)
                        else:
                            row_data[stat_type] = cell.text.strip()
            
            
            draft_data.append(row_data)
        
        # Create DataFrame
        df = pd.DataFrame(draft_data)
        
        # Save to CSV
        df.to_csv("nfl_draft_2024.csv", index=False)
        print(f"Data saved to nfl_draft_2024.csv. Total records: {len(draft_data)}")
        
        # Optionally print first few rows to verify
        print("\nFirst 5 records:")
        print(df.head(5))
        
    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        # Close the browser
        driver.quit()

if __name__ == "__main__":
    scrape_nfl_draft_data()