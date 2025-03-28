import time
import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

def scrape_nfl_fantasy_kickers():
    # URL for kicker data
    url = "https://fantasy.nfl.com/research/scoringleaders?position=7&statCategory=stats&statSeason=2023&statType=seasonStats&statWeek=18"
    
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
        print("Accessing NFL Fantasy Kickers page...")
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
            
        # Get all header rows
        header_rows = table.select("thead tr")
        
        # Main column headers
        main_headers = []
        if header_rows:
            for th in header_rows[0].select("th"):
                header_text = th.get_text(strip=True)
                if not header_text:
                    header_text = "Column"
                main_headers.append(header_text)
                
        print(f"Main headers: {main_headers}")
        
        # Get subheaders if they exist
        sub_headers = []
        if len(header_rows) > 1:
            for th in header_rows[1].select("th"):
                sub_header = th.get_text(strip=True)
                if not sub_header:
                    sub_header = "Sub"
                sub_headers.append(sub_header)
                
        print(f"Sub headers: {sub_headers}")
        
        # Create full column names by combining main headers and subheaders
        # For the NFL Fantasy table structure, we need to match main headers with their subheaders
        final_headers = []
        
        # Handle first columns (Rank, Player, Opp)
        final_headers.append("Rank")
        final_headers.append("Player")
        final_headers.append("Team")  # We'll split Player into Player and Team
        final_headers.append("Opp")   # Will be removed later
        
        # Handle PAT section
        final_headers.append("PAT_Made")
        
        # Handle FG Made section
        final_headers.append("FG_Made_0-19")
        final_headers.append("FG_Made_20-29")
        final_headers.append("FG_Made_30-39")
        final_headers.append("FG_Made_40-49")
        final_headers.append("FG_Made_50+")
        
        # Handle Fantasy Points section
        final_headers.append("Fantasy_Points")
        
        # Handle Average Points section
        final_headers.append("GP")
        final_headers.append("AVG")
        final_headers.append("TGP")
        final_headers.append("TAVG")
            
        print(f"Final headers: {final_headers}")
        
        # Extract data from rows
        rows_data = []
        
        for row in table.select("tbody tr"):
            cells = row.select("td")
            if not cells:
                continue
                
            row_data = []
            
            # Rank (first column)
            rank = cells[0].get_text(strip=True)
            row_data.append(rank)
            
            # Player Name and Team (second column)
            player_cell = cells[1]
            player_name_elem = player_cell.select_one("a")
            player_name = player_name_elem.get_text(strip=True) if player_name_elem else ""
            row_data.append(player_name)
            
            # Extract team
            team_elem = player_cell.select_one("em")
            team_info = ""
            if team_elem:
                team_text = team_elem.get_text(strip=True)
                # Team info comes in format "K - TEAM"
                if " - " in team_text:
                    team_info = team_text.split(" - ")[1]
                else:
                    team_info = team_text
            row_data.append(team_info)
            
            # Opponent (third column)
            opp = cells[2].get_text(strip=True) if len(cells) > 2 else ""
            row_data.append(opp)
            
            # Remaining cells - just add the text data
            for i in range(3, len(cells)):
                cell_text = cells[i].get_text(strip=True)
                row_data.append(cell_text)
            
            rows_data.append(row_data)
            
        # Create DataFrame, adjusting the headers to match the number of columns in the data
        if rows_data:
            sample_row_len = len(rows_data[0])
            print(f"Sample row length: {sample_row_len}")
            print(f"Headers length: {len(final_headers)}")
            
            # Adjust headers to match data length if needed
            while len(final_headers) < sample_row_len:
                final_headers.append(f"Extra_Column_{len(final_headers)}")
            while len(final_headers) > sample_row_len:
                final_headers.pop()
                
            df = pd.DataFrame(rows_data, columns=final_headers)
            print(f"Successfully scraped data for {len(df)} kickers")
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

def save_to_csv(df, filename="./player_ranking_position_data/nfl_fantasy_kickers.csv"):
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
    kicker_df = scrape_nfl_fantasy_kickers()
    
    # Save to CSV
    if kicker_df is not None:
        save_to_csv(kicker_df)
        
        # Display the first few rows
        print("\nFirst few rows of the data:")
        print(kicker_df.head())