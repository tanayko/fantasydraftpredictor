import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

def scrape_teams_selenium(url, season_type=2):
    """
    Scrape NFL team names using Selenium
    
    Parameters:
    - url: ESPN NFL stats URL
    - season_type: 2 for regular season, 3 for postseason
    
    Returns:
    - List of team names in order
    """
    print("Starting Selenium scraper for team names...")
    
    # Set up Chrome options for headless mode
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Initialize the Chrome driver with headless options
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )
    
    try:
        # Navigate to the URL
        driver.get(url)
        print(f"Navigating to {url}")
        
        # Wait for the page to load
        wait = WebDriverWait(driver, 10)
        table = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".Table__TBODY")))
        
        # Get all table rows
        rows = table.find_elements(By.TAG_NAME, "tr")
        
        # Initialize team names list
        team_names = []
        
        # Process each row to get team names
        for row in rows:
            # Get team name from the first cell
            team_cell = row.find_element(By.CSS_SELECTOR, "td:nth-child(1)")
            team_name = team_cell.text.strip()
            if team_name and team_name not in team_names:
                team_names.append(team_name)
        
        print(f"Found {len(team_names)} teams using Selenium")
        return team_names[:32]  # Return only the first 32 teams
    
    except Exception as e:
        print(f"An error occurred in Selenium scraper: {e}")
        return []
    
    finally:
        # Always close the driver
        driver.quit()
        print("Selenium driver closed")

def scrape_stats_bs4(url):
    """
    Scrape NFL team stats using BeautifulSoup
    
    Parameters:
    - url: ESPN NFL stats URL
    
    Returns:
    - DataFrame with team statistics (without team names)
    """
    print("Starting BeautifulSoup scraper for stats...")
    
    # Send a request to the URL
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Parse the HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Get column headers
        header_cells = soup.select('thead.Table__THEAD th')
        headers = []
        for header in header_cells:
            header_text = header.text.strip()
            if header_text and header_text not in headers:
                headers.append(header_text)
        
        # Get all table rows for stats
        rows = soup.select('tbody.Table__TBODY tr')
        
        # Extract data from each row
        all_data = []
        for row in rows[32:]:  # Skip the first 32 rows (they are team name rows)
            pattern = r'<div class="">([\d,\.]+)<\/div>'
            numbers = re.findall(pattern, str(row))
            if numbers:
                all_data.append([
                    float(val.strip('"\'').replace(',', '')) 
                    for val in numbers
                ])
        
        # Create the DataFrame with stats
        df = pd.DataFrame(all_data)
        
        # If headers exist, use them (excluding the first 'TEAM' header)
        if headers and len(headers) - 1 == df.shape[1]:  # -1 for the 'TEAM' column we'll add later
            df.columns = headers[1:]
        else:
            # Use generic column names if headers don't match
            df.columns = [f'STAT{i+1}' for i in range(df.shape[1])]
        
        print(f"Found stats data for {len(df)} teams using BeautifulSoup")
        return df
    
    except Exception as e:
        print(f"An error occurred in BeautifulSoup scraper: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()  # Return empty DataFrame on error

def combine_data(teams, stats_df, season):
    """
    Combine team names and stats into one DataFrame
    
    Parameters:
    - teams: List of team names
    - stats_df: DataFrame with stats (without team names)
    - season: Season year for filename
    
    Returns:
    - Combined DataFrame
    """
    print("Combining team names with stats data...")
    
    if not teams or stats_df.empty:
        print("Error: Missing team names or stats data.")
        return pd.DataFrame()
    
    # Ensure we have the same number of teams as stats rows
    if len(teams) != len(stats_df):
        print(f"Warning: Number of teams ({len(teams)}) doesn't match number of stats rows ({len(stats_df)})")
        
        # Adjust to the smaller length
        min_length = min(len(teams), len(stats_df))
        teams = teams[:min_length]
        stats_df = stats_df.iloc[:min_length]
    
    # Add teams as the first column
    combined_df = stats_df.copy()
    combined_df.insert(0, 'TEAM', teams)
    
    # Convert numeric columns to appropriate types
    for col in combined_df.columns:
        if col != 'TEAM':  # Exclude team name column
            try:
                # If values look like integers, convert to int, otherwise keep as float
                if combined_df[col].apply(lambda x: x.is_integer() if isinstance(x, float) else True).all():
                    combined_df[col] = combined_df[col].astype(int)
            except:
                pass  # Keep as is if conversion fails
    
    # Save to CSV
    output_file = f"./offensive_rtg_data/nfl_team_offense_stats_{season}.csv"
    combined_df.to_csv(output_file, index=False)
    print(f"Data successfully saved to {output_file}")
    
    return combined_df

def scrape_nfl_stats(season=2022):
    """
    Main function to scrape NFL team offensive statistics
    
    Parameters:
    - season: NFL season year (default: 2022)
    
    Returns:
    - DataFrame with team offensive statistics
    """
    # URL for offense stats
    url = f"https://www.espn.com/nfl/stats/team/_/season/{season}/seasontype/2"
    
    # Step 1: Get team names using Selenium
    teams = scrape_teams_selenium(url)
    
    # Step 2: Get stats data using BeautifulSoup
    stats_df = scrape_stats_bs4(url)
    
    # Step 3: Combine the data
    combined_df = combine_data(teams, stats_df, season)
    
    return combined_df

if __name__ == "__main__":
    # Run the scraper for multiple seasons
    for season in range(2018, 2024):  # This will loop from 2018 to 2023
        print(f"\n======= Scraping {season} NFL Season Data =======\n")
        nfl_stats = scrape_nfl_stats(season)
        
        # Display the first few rows
        if nfl_stats is not None and not nfl_stats.empty:
            print(f"\nFirst 5 rows of the {season} data:")
            print(nfl_stats.head())
        else:
            print(f"No data was scraped for {season}.")