from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import traceback
import os
import regex as re

def setup_driver():
    print("Setting up the Chrome WebDriver...")
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'})
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        print("WebDriver setup successful!")
        return driver
    except Exception as e:
        print(f"Error setting up WebDriver: {e}")
        traceback.print_exc()
        return None

def scrape_nfl_fantasy_qb_data(year):
    url = f"https://fantasy.nfl.com/research/pointsagainst?position=1&statCategory=pointsAgainst&statSeason={year}&statType=seasonPointsAgainst&statWeek=18"
    
    print(f"Scraping data for year: {year}")
    driver = setup_driver()
    if not driver:
        return None
    
    try:
        print(f"Navigating to URL: {url}")
        driver.get(url)
        
        # Wait longer for the page to load
        print("Waiting for page to fully load...")
        time.sleep(5)
        
        # Try to find the table
        print("Looking for the data table...")
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CLASS_NAME, "tableType-player"))
            )
            print("Found table with class 'tableType-player'")
            table = driver.find_element(By.CLASS_NAME, "tableType-player")
        except Exception as e:
            print(f"Could not find table by class name: {e}")
            tables = driver.find_elements(By.TAG_NAME, "table")
            if tables:
                print(f"Found {len(tables)} tables. Using the first one.")
                table = tables[0]
            else:
                print("No tables found on the page.")
                return None
        
        # Find all rows
        rows = table.find_elements(By.CSS_SELECTOR, "tr.odd, tr.even")
        print(f"Found {len(rows)} data rows")
        
        # Extract data
        data = []
        for i, row in enumerate(rows):
            try:
                # Directly locate the team name div/text - based on the screenshot
                try:
                    # Looking for the team name text that appears next to the logo
                    # First try the most specific method
                    team_elements = row.find_elements(By.XPATH, ".//div[@class='teamName']")
                    
                    if team_elements:
                        complete_team_text = team_elements[0].text.strip()
                        print(f"Row {i+1}: Found team text: '{complete_team_text}'")
                        team_name = complete_team_text
                    else:
                        # Try another method if the first one fails
                        team_cells = row.find_elements(By.CSS_SELECTOR, "td:first-child")
                        if team_cells:
                            team_name = team_cells[0].text.strip()
                            print(f"Row {i+1}: Found team name from first cell: '{team_name}'")
                        else:
                            # Last resort - get whole row text and parse
                            row_text = row.text.strip().split('\n')[0]
                            print(f"Row {i+1}: Using full row text: '{row_text}'")
                            team_name = row_text
                except Exception as e:
                    print(f"Row {i+1}: Error getting team name: {e}")
                    team_name = f"Unknown Team {i+1}"
                
                # After extracting the team_name string, add this:
                if "Defense" in team_name:
                    # Remove "Defense" and everything after it
                    team_name = re.sub(r'Defense[\s\S]*$', '', team_name).strip()

                # Get all cells and extract data
                cells = row.find_elements(By.TAG_NAME, "td")
                
                if len(cells) >= 13:
                    team_data = {
                        'Team': team_name,
                        'Avg': cells[1].text.strip(),
                        'Rank': cells[2].text.strip(),
                        'Comp': cells[3].text.strip(),
                        'Att': cells[4].text.strip(),
                        'Yds': cells[5].text.strip(),
                        'Int': cells[6].text.strip(),
                        'TD': cells[7].text.strip(),
                        'Rush_Att': cells[8].text.strip(),
                        'Rush_Yds': cells[9].text.strip(),
                        'Rush_TD': cells[10].text.strip(),
                        'RZ_Touch': cells[11].text.strip(),
                        'RZ_G2G': cells[12].text.strip(),
                        'Year': year  # Add year to the data
                    }
                    
                    print(f"Row {i+1}: Extracted data for {team_name}")
                    data.append(team_data)
                else:
                    print(f"Row {i+1}: Not enough cells found ({len(cells)}), skipping")
            
            except Exception as e:
                print(f"Error processing row {i+1}: {e}")
                traceback.print_exc()
        
        # Create DataFrame
        if data:
            print(f"Creating DataFrame with {len(data)} teams")
            df = pd.DataFrame(data)
            return df
        else:
            print("No data collected")
            return None
            
    except Exception as e:
        print(f"Error during scraping: {e}")
        traceback.print_exc()
        return None
    finally:
        print("Closing WebDriver...")
        driver.quit()

def save_data_to_csv(df, year, output_dir):
    try:
        if df is not None and not df.empty:
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Define the filename with year
            filename = os.path.join(output_dir, f'nfl_fantasy_qb_data_{year}.csv')
            
            df.to_csv(filename, index=False)
            print(f"Data successfully saved to {filename}")
            print(f"Saved {len(df)} rows and {len(df.columns)} columns")
            return filename
        else:
            print("No data to save - DataFrame is empty or None")
            return None
    except Exception as e:
        print(f"Error saving data to CSV: {e}")
        traceback.print_exc()
        return None

def main():
    # Define the output directory relative to script location
    output_dir = "./pts-against-data/qb/"
    
    # Create a master dataframe to hold data from all years
    all_years_data = pd.DataFrame()
    
    # Years to scrape
    years_to_scrape = range(2020, 2025)  # 2020-2024
    
    print("Starting NFL Fantasy QB Points Against data scraper...")
    print(f"Time started: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Output directory: {os.path.abspath(output_dir)}")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Scrape data for each year
    for year in years_to_scrape:
        print(f"\n{'='*50}")
        print(f"Processing year {year}")
        print(f"{'='*50}")
        
        df = scrape_nfl_fantasy_qb_data(year)
        
        if df is not None and not df.empty:
            print(f"\nScraping successful for year {year}!")
            print("\nPreview of the data:")
            print(df.head())
            print(f"\nTotal teams scraped for {year}: {len(df)}")
            
            # Save individual year data
            save_data_to_csv(df, year, output_dir)
            
            # Append to master dataframe
            all_years_data = pd.concat([all_years_data, df], ignore_index=True)
            
            # Sleep between years to avoid being throttled
            if year != years_to_scrape[-1]:  # Don't sleep after the last year
                sleep_time = 5  # seconds
                print(f"Sleeping for {sleep_time} seconds before next year...")
                time.sleep(sleep_time)
        else:
            print(f"Scraping failed for year {year}")
    
    # Save combined data if we have any
    if not all_years_data.empty:
        combined_filename = os.path.join(output_dir, 'nfl_fantasy_qb_data_all_years.csv')
        all_years_data.to_csv(combined_filename, index=False)
        print(f"\nCombined data for all years saved to {combined_filename}")
        print(f"Total records: {len(all_years_data)}")
    
    print(f"\nTime finished: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("Scraping completed!")

if __name__ == "__main__":
    main()