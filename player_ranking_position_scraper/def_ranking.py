import time
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

def scrape_nfl_fantasy_defense():
    """
    Scrape NFL Fantasy Football defense data from the NFL Fantasy website.
    """
    # URL for defense data
    url = "https://fantasy.nfl.com/research/scoringleaders?position=8&statCategory=stats&statSeason=2023&statType=seasonStats&statWeek=18"
    
    # Set up Selenium with headless Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Initialize the driver
    driver = webdriver.Chrome(options=chrome_options)
    
    try:
        # Load the page
        print("Accessing NFL Fantasy Defense page...")
        driver.get(url)
        
        # Wait for the table to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.tableType-player"))
        )
        
        # Let the page fully render
        time.sleep(2)
        
        # Get the page source
        html_content = driver.page_source
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find the table
        table = soup.select_one("table.tableType-player")
        
        if not table:
            print("Table not found. The page structure might have changed.")
            return None
            
        # Extract the headers based on the table structure seen in the screenshot
        column_headers = []
        
        # Main columns (from the provided screenshot)
        column_headers = [
            "Rank", "Team", "Opp", 
            "Sack", "Int", "Fum Rec", "Saf", "TD", "Def Ret", "TD Allow", "Pts Allow",  
            "Fantasy_Points", "GP", "AVG", "TGP", "TAVG"
        ]
        
        print(f"Column headers: {column_headers}")
        
        # Extract data from rows
        rows_data = []
        
        for row in table.select("tbody tr"):
            cells = row.select("td")
            if not cells:
                continue
                
            row_data = []
            
            # Rank
            rank = cells[0].get_text(strip=True)
            row_data.append(rank)
            
            # Team Name and DEF designation
            team_cell = cells[1]
            team_name_elem = team_cell.select_one("a")
            team_name = team_name_elem.get_text(strip=True) if team_name_elem else ""
            
            # Sometimes there's a "DEF" designation below the team name
            # We'll ignore it as it's redundant for defense data
            row_data.append(team_name)
            
            # Process each remaining cell in the row
            for i in range(2, len(cells)):
                cell_text = cells[i].get_text(strip=True)
                row_data.append(cell_text)
            
            rows_data.append(row_data)
            
        # Create DataFrame, adjusting the headers to match the number of columns in the data
        if rows_data:
            sample_row_len = len(rows_data[0])
            print(f"Sample row length: {sample_row_len}")
            print(f"Headers length: {len(column_headers)}")
            
            # Adjust headers to match data length if needed
            while len(column_headers) < sample_row_len:
                column_headers.append(f"Extra_Column_{len(column_headers)}")
            while len(column_headers) > sample_row_len:
                column_headers.pop()
                
            df = pd.DataFrame(rows_data, columns=column_headers)
            print(f"Successfully scraped data for {len(df)} defense teams")
            return df
        else:
            print("No data rows found")
            return None
    
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        # Close the driver
        driver.quit()

def save_to_csv(df, filename="./player_ranking_position_data/nfl_fantasy_defense.csv"):
    """Save the DataFrame to a CSV file"""
    if df is not None:
        # Remove the opponents column if it exists
        if 'Opp' in df.columns:
            df = df.drop(columns=['Opp'])
            print("Removed 'Opp' column from the data")
        
        # Make sure the directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        df.to_csv(filename, index=False)
        print(f"Data saved to {filename}")
    else:
        print("No data to save")

if __name__ == "__main__":
    # Scrape the data
    defense_df = scrape_nfl_fantasy_defense()
    
    # Save to CSV
    if defense_df is not None:
        save_to_csv(defense_df)
        
        # Display the first few rows
        print("\nFirst few rows of the data:")
        print(defense_df.head())