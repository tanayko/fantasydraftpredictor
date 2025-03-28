import os
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

def scrape_fantasy_stats(position=1, season=2023):
    """
    Scrape NFL Fantasy scoring leaders with all stats
    
    Parameters:
        position (int): Position ID (1=QB, 2=RB, 3=WR, 4=TE)
        season (int): Season year
    
    Returns:
        DataFrame with complete scoring leaders data
    """
    # Create output directory
    output_dir = './player_ranking_position_data'
    os.makedirs(output_dir, exist_ok=True)
    
    position_name = get_position_name(position)
    print(f"Scraping data for {position_name}...")
    
    # URL with parameters
    url = f"https://fantasy.nfl.com/research/scoringleaders?position={position}&sort=pts&statCategory=stats&statSeason={season}&statType=seasonStats"
    
    # Configure Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Initialize the WebDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        # Load the page
        print(f"Loading {url}")
        driver.get(url)
        
        # Wait for the table to load
        wait = WebDriverWait(driver, 30)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".tableType-player tbody tr")))
        
        # Give time for JavaScript to fully render
        time.sleep(5)
        
        # Get page source and parse with BeautifulSoup
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find the main stats table
        table = soup.find("table", class_="tableType-player")
        
        if not table:
            print("Table not found!")
            return None
        
        # Extract all data
        players_data = []
        
        # Get all rows except the header row
        player_rows = table.find_all("tr")[1:]  # Skip header row
        
        for row in player_rows:
            player_info = {}
            
            # Get rank
            rank_cell = row.find("td", class_="first")
            if rank_cell:
                player_info["Rank"] = rank_cell.text.strip()
            
            # Get player name, team and position
            player_cell = row.find("a", class_="playerName")
            if player_cell:
                player_info["Player"] = player_cell.text.strip()
            
            # Extract team and position
            team_pos = row.find("em")
            if team_pos:
                team_pos_text = team_pos.text.strip()
                if " - " in team_pos_text:
                    team, pos = team_pos_text.split(" - ")
                    player_info["Team"] = team
                    player_info["Position"] = pos
            
            # Get opponent
            opp_cell = row.find("td", class_="opp")
            if opp_cell:
                player_info["Opponent"] = opp_cell.text.strip()
            
            # Extract all the stat columns
            # Passing stats
            pass_yds_cell = row.find("td", attrs={"class": lambda x: x and "stat_5" in x})
            if pass_yds_cell:
                player_info["Pass_Yds"] = pass_yds_cell.text.strip()
            
            pass_td_cell = row.find("td", attrs={"class": lambda x: x and "stat_6" in x})
            if pass_td_cell:
                player_info["Pass_TD"] = pass_td_cell.text.strip()
            
            pass_int_cell = row.find("td", attrs={"class": lambda x: x and "stat_7" in x})
            if pass_int_cell:
                player_info["Pass_Int"] = pass_int_cell.text.strip()
            
            # Rushing stats
            rush_yds_cell = row.find("td", attrs={"class": lambda x: x and "stat_14" in x})
            if rush_yds_cell:
                player_info["Rush_Yds"] = rush_yds_cell.text.strip()
            
            rush_td_cell = row.find("td", attrs={"class": lambda x: x and "stat_15" in x})
            if rush_td_cell:
                player_info["Rush_TD"] = rush_td_cell.text.strip()
            
            # Receiving stats
            rec_cell = row.find("td", attrs={"class": lambda x: x and "stat_20" in x})
            if rec_cell:
                player_info["Rec"] = rec_cell.text.strip()
            
            rec_yds_cell = row.find("td", attrs={"class": lambda x: x and "stat_21" in x})
            if rec_yds_cell:
                player_info["Rec_Yds"] = rec_yds_cell.text.strip()
            
            rec_td_cell = row.find("td", attrs={"class": lambda x: x and "stat_22" in x})
            if rec_td_cell:
                player_info["Rec_TD"] = rec_td_cell.text.strip()
            
            # Misc stats
            fum_td_cell = row.find("td", attrs={"class": lambda x: x and "td fumTD" in x})
            if fum_td_cell:
                player_info["Fum_TD"] = fum_td_cell.text.strip()
            
            two_pt_cell = row.find("td", attrs={"class": lambda x: x and "2PT" in x})
            if two_pt_cell:
                player_info["2PT"] = two_pt_cell.text.strip()
            
            lost_cell = row.find("td", class_="lost")
            if lost_cell:
                player_info["Lost"] = lost_cell.text.strip()
            
            # Fantasy points
            pts_cell = row.find("td", class_="pts")
            if pts_cell:
                player_info["Fantasy_Points"] = pts_cell.text.strip()
            
            # Average points stats
            gp_cell = row.find("td", class_="gp")
            if gp_cell:
                player_info["Games_Played"] = gp_cell.text.strip()
            
            avg_cell = row.find("td", class_="avg")
            if avg_cell:
                player_info["Avg_Points"] = avg_cell.text.strip()
            
            # Alternative method to extract stats for reliability
            # Get all TD cells
            td_cells = row.find_all("td")
            if len(td_cells) >= 20:  # Make sure we have enough cells
                # Map the index to stat names - adjust based on the actual table
                stat_mapping = {
                    0: "Rank",
                    1: "Player",
                    2: "Opponent",
                    3: "Pass_Yds",
                    4: "Pass_TD",
                    5: "Pass_Int",
                    6: "Rush_Yds",
                    7: "Rush_TD",
                    8: "Rec",
                    9: "Rec_Yds",
                    10: "Rec_TD",
                    11: "Fum_TD",
                    12: "2PT",
                    13: "Lost",
                    14: "Fantasy_Points",
                    15: "Games_Played",
                    16: "Avg_Points",
                    17: "TGP",
                    18: "TAVG"
                }
                
                # Fill in any missing stats using the cell index
                for i, cell in enumerate(td_cells):
                    if i in stat_mapping and stat_mapping[i] not in player_info:
                        player_info[stat_mapping[i]] = cell.text.strip()
            
            # Add to our collection
            if player_info.get("Player"):
                players_data.append(player_info)
        
        # Create DataFrame
        df = pd.DataFrame(players_data)
        if "Opponent" in df.columns:
            df = df.drop("Opponent", axis=1)
        
        # Print preview
        print(f"\nSuccessfully scraped {len(players_data)} players")
        if not df.empty:
            print(f"Columns: {df.columns.tolist()}")
            print("\nFirst 5 players:")
            print(df.head(5))
        
        # Save to CSV
        output_file = os.path.join(output_dir, f"nfl_fantasy_{position_name}_stats_{season}.csv")
        df.to_csv(output_file, index=False)
        print(f"\nData saved to {output_file}")
        
        return df
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return None
    
    finally:
        driver.quit()

def scrape_multiple_positions(positions=[1, 2, 3, 4], season=2023):
    """Scrape data for multiple positions"""
    results = {}
    
    for position in positions:
        position_name = get_position_name(position)
        print(f"\n--- Scraping {position_name} ---")
        df = scrape_fantasy_stats(position=position, season=season)
        if df is not None:
            results[position_name] = df
    
    return results

def get_position_name(position_id):
    """Convert position ID to name"""
    positions = {
        1: "QB",
        2: "RB",
        3: "WR",
        4: "TE",
    }
    return positions.get(position_id, f"pos{position_id}")

def main():
    
    # Uncomment to scrape all positions
    print("\nStarting scraper for all positions...")
    scrape_multiple_positions()

if __name__ == "__main__":
    main()