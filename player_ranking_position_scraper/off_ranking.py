import os
import time
import pandas as pd
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("fantasy_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("fantasy_scraper")

# Position mapping
POSITION_MAP = {
    1: "QB",
    2: "RB",
    3: "WR",
    4: "TE"
}

class NFLFantasyScraper:
    """Class to handle NFL fantasy stats scraping"""
    
    def __init__(self, output_dir='./player_ranking_data', headless=True):
        """Initialize the scraper with configurable options"""
        self.output_dir = output_dir
        self.headless = headless
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Output directory: {output_dir}")
        
        # Column mappings for different position groups
        self.column_mappings = {
            # Common stats for all positions
            'common': {
                'Rank': 'Rank',
                'Player': 'Player',
                'Team': 'Team',
                'Position': 'Position',
                'Opponent': 'Opponent',
                'Fantasy_Points': 'Fantasy_Points',
                'Games_Played': 'GP',
                'Avg_Points': 'AVG',
                'Total_Games_Played': 'TGP',
                'Total_Avg': 'TAVG',
                'Lost': 'Lost',
                '2PT': '2PT'
            },
            # QB specific stats
            'QB': {
                'Pass_Yds': 'Pass_Yds',
                'Pass_TD': 'Pass_TD',
                'Pass_Int': 'Pass_Int',
                'Rush_Yds': 'Rush_Yds',
                'Rush_TD': 'Rush_TD'
            },
            # RB specific stats
            'RB': {
                'Rush_Yds': 'Rush_Yds',
                'Rush_TD': 'Rush_TD',
                'Rec': 'Rec',
                'Rec_Yds': 'Rec_Yds',
                'Rec_TD': 'Rec_TD'
            },
            # WR/TE specific stats
            'WR_TE': {
                'Rec': 'Rec',
                'Rec_Yds': 'Rec_Yds',
                'Rec_TD': 'Rec_TD',
                'Rush_Yds': 'Rush_Yds',
                'Rush_TD': 'Rush_TD'
            }
        }
    
    def get_webdriver(self):
        """Set up and return a configured WebDriver instance"""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument("--headless")
        
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        
        # Add user agent to avoid detection
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            return driver
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {str(e)}")
            raise
    
    def scrape_fantasy_stats(self, position=1, season=2023, max_retries=3):
        """
        Scrape NFL Fantasy scoring leaders with all stats
        
        Parameters:
            position (int): Position ID (1=QB, 2=RB, 3=WR, 4=TE, 5=K, 6=DEF)
            season (int): Season year
            max_retries (int): Maximum number of retry attempts
        
        Returns:
            DataFrame with complete scoring leaders data
        """
        position_name = POSITION_MAP.get(position, f"pos{position}")
        logger.info(f"Scraping data for {position_name} in {season} season")
        
        # URL with parameters
        url = f"https://fantasy.nfl.com/research/scoringleaders?position={position}&sort=pts&statCategory=stats&statSeason={season}&statType=seasonStats"
        
        # Initialize the WebDriver
        driver = self.get_webdriver()
        
        retry_count = 0
        while retry_count < max_retries:
            try:
                # Load the page
                logger.info(f"Loading {url}")
                driver.get(url)
                
                # Wait for the table to load
                wait = WebDriverWait(driver, 30)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".tableType-player tbody tr")))
                
                # Give time for JavaScript to fully render
                time.sleep(5)
                
                # Get page source and parse with BeautifulSoup
                html = driver.page_source
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract the data
                players_data = self._extract_player_data(soup, position_name)
                
                if not players_data:
                    logger.warning("No player data found, retrying...")
                    retry_count += 1
                    time.sleep(3)
                    continue
                
                # Create DataFrame
                df = pd.DataFrame(players_data)
                
                # Clean and process data
                df = self._process_dataframe(df, position_name)
                
                # Print preview
                logger.info(f"Successfully scraped {len(players_data)} players")
                if not df.empty:
                    logger.info(f"Columns: {df.columns.tolist()}")
                    logger.info(f"\nFirst 5 players:\n{df.head(5)}")
                
                # Save to CSV
                output_file = os.path.join(self.output_dir, f"nfl_fantasy_{position_name}_stats_{season}.csv")
                df.to_csv(output_file, index=False)
                logger.info(f"Data saved to {output_file}")
                
                return df
            
            except Exception as e:
                logger.error(f"Error on attempt {retry_count + 1}: {str(e)}")
                retry_count += 1
                time.sleep(5)  # Wait before retry
                
                if retry_count >= max_retries:
                    logger.error("Max retries exceeded")
                    import traceback
                    logger.error(traceback.format_exc())
                    return None
            
            finally:
                if retry_count >= max_retries - 1:
                    driver.quit()
    
    def _extract_player_data(self, soup, position_name):
        """Extract player data from the parsed HTML"""
        players_data = []
        
        # Find the main stats table
        table = soup.find("table", class_="tableType-player")
        
        if not table:
            logger.error("Table not found in the HTML!")
            return players_data
        
        # Get table headers to identify columns
        headers = []
        header_row = table.find("tr", class_="tablehead")
        if header_row:
            header_cells = header_row.find_all("th")
            headers = [cell.get_text(strip=True) for cell in header_cells]
            logger.info(f"Table headers: {headers}")
        
        # Get all rows except the header row
        player_rows = table.find_all("tr")[1:]  # Skip header row
        
        for row in player_rows:
            player_info = {}
            
            # Get rank
            rank_cell = row.find("td", class_="first")
            if rank_cell:
                player_info["Rank"] = rank_cell.get_text(strip=True)
            
            # Get player name
            player_cell = row.find("a", class_="playerName")
            if player_cell:
                player_info["Player"] = player_cell.get_text(strip=True)
            
            # Extract team and position
            team_pos = row.find("em")
            if team_pos:
                team_pos_text = team_pos.get_text(strip=True)
                if " - " in team_pos_text:
                    team, pos = team_pos_text.split(" - ")
                    player_info["Team"] = team
                    player_info["Position"] = pos
            
            # Get opponent
            opp_cell = row.find("td", class_="opp")
            if opp_cell:
                player_info["Opponent"] = opp_cell.get_text(strip=True)
            
            # Get all stat cells systematically
            stat_cells = row.find_all("td")
            
            # Position-specific stats extraction based on position
            if position_name in ["QB", "RB", "WR", "TE"]:
                self._extract_position_stats(row, player_info, position_name)
            
            # Get fantasy points and averages
            pts_cell = row.find("td", class_="pts")
            if pts_cell:
                player_info["Fantasy_Points"] = pts_cell.get_text(strip=True)
            
            gp_cell = row.find("td", class_="gp")
            if gp_cell:
                player_info["Games_Played"] = gp_cell.get_text(strip=True)
            
            avg_cell = row.find("td", class_="avg")
            if avg_cell:
                player_info["Avg_Points"] = avg_cell.get_text(strip=True)
            
            # Fix for TAVG column - get from the last columns
            if len(stat_cells) >= 2:
                # The last two cells are typically TGP and TAVG
                tgp_cell = stat_cells[-2]
                tavg_cell = stat_cells[-1]
                
                # Extract TGP (Total Games Played)
                if "Total_Games_Played" not in player_info:
                    player_info["Total_Games_Played"] = tgp_cell.get_text(strip=True)
                
                # Extract TAVG (Total Average)
                if "Total_Avg" not in player_info:
                    player_info["Total_Avg"] = tavg_cell.get_text(strip=True)
            
            # Add to our collection if we have player name
            if player_info.get("Player"):
                players_data.append(player_info)
        
        return players_data
    
    def _extract_position_stats(self, row, player_info, position_name):
        """Extract position-specific stats"""
        # Common stats for all positions
        self._extract_common_stats(row, player_info)
        
        # Position-specific stats
        if position_name == "QB":
            # QB Stats: Pass yards, TDs, INTs, Rush yards, Rush TDs
            pass_yds_cell = row.find("td", attrs={"class": lambda x: x and "stat_5" in x})
            if pass_yds_cell:
                player_info["Pass_Yds"] = pass_yds_cell.get_text(strip=True)
            
            pass_td_cell = row.find("td", attrs={"class": lambda x: x and "stat_6" in x})
            if pass_td_cell:
                player_info["Pass_TD"] = pass_td_cell.get_text(strip=True)
            
            pass_int_cell = row.find("td", attrs={"class": lambda x: x and "stat_7" in x})
            if pass_int_cell:
                player_info["Pass_Int"] = pass_int_cell.get_text(strip=True)
        
        # Both QB, RB, WR, TE have rushing stats
        rush_yds_cell = row.find("td", attrs={"class": lambda x: x and "stat_14" in x})
        if rush_yds_cell:
            player_info["Rush_Yds"] = rush_yds_cell.get_text(strip=True)
        
        rush_td_cell = row.find("td", attrs={"class": lambda x: x and "stat_15" in x})
        if rush_td_cell:
            player_info["Rush_TD"] = rush_td_cell.get_text(strip=True)
        
        # RB, WR, TE have receiving stats
        if position_name in ["RB", "WR", "TE"]:
            rec_cell = row.find("td", attrs={"class": lambda x: x and "stat_20" in x})
            if rec_cell:
                player_info["Rec"] = rec_cell.get_text(strip=True)
            
            rec_yds_cell = row.find("td", attrs={"class": lambda x: x and "stat_21" in x})
            if rec_yds_cell:
                player_info["Rec_Yds"] = rec_yds_cell.get_text(strip=True)
            
            rec_td_cell = row.find("td", attrs={"class": lambda x: x and "stat_22" in x})
            if rec_td_cell:
                player_info["Rec_TD"] = rec_td_cell.get_text(strip=True)
    
    def _extract_common_stats(self, row, player_info):
        """Extract stats common to all positions"""
        # Misc stats like fumbles, 2-point conversions
        fum_td_cell = row.find("td", attrs={"class": lambda x: x and "fumTD" in x})
        if fum_td_cell:
            player_info["Fum_TD"] = fum_td_cell.get_text(strip=True)
        
        two_pt_cell = row.find("td", attrs={"class": lambda x: x and "2PT" in x})
        if two_pt_cell:
            player_info["2PT"] = two_pt_cell.get_text(strip=True)
        
        lost_cell = row.find("td", class_="lost")
        if lost_cell:
            player_info["Lost"] = lost_cell.get_text(strip=True)
    
    def _process_dataframe(self, df, position_name):
        """Process and clean the DataFrame"""
        # Remove unnecessary columns
        if "Opponent" in df.columns:
            df = df.drop("Opponent", axis=1)
        
        # Convert numeric columns to proper types
        numeric_columns = [
            "Rank", "Fantasy_Points", "Games_Played", "Avg_Points", 
            "Total_Games_Played", "Total_Avg"
        ]
        
        position_specific_columns = {
            "QB": ["Pass_Yds", "Pass_TD", "Pass_Int", "Rush_Yds", "Rush_TD"],
            "RB": ["Rush_Yds", "Rush_TD", "Rec", "Rec_Yds", "Rec_TD"],
            "WR": ["Rec", "Rec_Yds", "Rec_TD", "Rush_Yds", "Rush_TD"],
            "TE": ["Rec", "Rec_Yds", "Rec_TD", "Rush_Yds", "Rush_TD"]
        }
        
        # Add position-specific columns to numeric columns list
        if position_name in position_specific_columns:
            numeric_columns.extend(position_specific_columns[position_name])
        
        # Convert and clean numeric data
        for col in numeric_columns:
            if col in df.columns:
                # Convert string values to numeric
                df[col] = df[col].apply(self._clean_numeric)
        
        return df
    
    def _clean_numeric(self, value):
        """Clean and convert numeric values"""
        if pd.isna(value) or value == "-":
            return 0
        
        # Remove any non-numeric characters except decimal point
        if isinstance(value, str):
            # Extract numeric part (handle cases like '239.30')
            match = re.search(r'(\d+\.\d+|\d+)', value)
            if match:
                return float(match.group(1))
            return 0
        
        return value
    
    def scrape_multiple_positions(self, positions=None, season=2023, concurrent=False):
        """
        Scrape data for multiple positions
        
        Parameters:
            positions (list): List of position IDs to scrape
            season (int): Season year
            concurrent (bool): Whether to use concurrent scraping
        
        Returns:
            Dictionary with position names as keys and DataFrames as values
        """
        if positions is None:
            positions = [1, 2, 3, 4]  # Default: QB, RB, WR, TE
        
        results = {}
        
        if concurrent and len(positions) > 1:
            # Use ThreadPoolExecutor for concurrent scraping
            logger.info("Using concurrent scraping for multiple positions")
            with ThreadPoolExecutor(max_workers=len(positions)) as executor:
                # Create a dictionary of futures to position names
                future_to_position = {
                    executor.submit(self.scrape_fantasy_stats, position, season): 
                    POSITION_MAP.get(position, f"pos{position}") 
                    for position in positions
                }
                
                # Process completed futures
                for future in future_to_position:
                    position_name = future_to_position[future]
                    try:
                        df = future.result()
                        if df is not None:
                            results[position_name] = df
                    except Exception as e:
                        logger.error(f"Error scraping {position_name}: {str(e)}")
        else:
            # Sequential scraping
            for position in positions:
                position_name = POSITION_MAP.get(position, f"pos{position}")
                logger.info(f"\n--- Scraping {position_name} ---")
                df = self.scrape_fantasy_stats(position=position, season=season)
                if df is not None:
                    results[position_name] = df
        
        return results
    
    def combine_position_data(self, results):
        """Combine data from multiple positions into a single DataFrame"""
        if not results:
            logger.warning("No position data to combine")
            return None
        
        combined_df = pd.DataFrame()
        
        for position_name, df in results.items():
            if combined_df.empty:
                combined_df = df.copy()
            else:
                combined_df = pd.concat([combined_df, df], ignore_index=True)
        
        # Sort by fantasy points
        if "Fantasy_Points" in combined_df.columns:
            combined_df = combined_df.sort_values(by="Fantasy_Points", ascending=False)
            combined_df = combined_df.reset_index(drop=True)
        
        return combined_df

def main():
    """Main function to run the scraper"""
    try:
        # Create scraper instance
        scraper = NFLFantasyScraper(output_dir='./fantasy_data_2023')
        
        # Default to scraping all positions
        logger.info("\nStarting scraper for all positions...")
        
        # Get command line arguments (if provided)
        import sys
        
        # Check if season argument is provided
        season = 2023  # Default season
        if len(sys.argv) > 1:
            try:
                season = int(sys.argv[1])
                logger.info(f"Using season: {season}")
            except ValueError:
                logger.warning(f"Invalid season: {sys.argv[1]}, using default: {season}")
        
        # Check if specific positions are requested
        positions = [1, 2, 3, 4]  # Default: QB, RB, WR, TE
        if len(sys.argv) > 2:
            try:
                positions = [int(pos) for pos in sys.argv[2].split(',')]
                position_names = [POSITION_MAP.get(pos, f"pos{pos}") for pos in positions]
                logger.info(f"Scraping positions: {position_names}")
            except ValueError:
                logger.warning(f"Invalid positions: {sys.argv[2]}, using default")
        
        # Scrape the data (with concurrent=True for faster processing)
        results = scraper.scrape_multiple_positions(positions=positions, season=season, concurrent=True)
        
        # Combine all position data
        all_players = scraper.combine_position_data(results)
        
        if all_players is not None:
            # Save combined data
            output_file = os.path.join(scraper.output_dir, f"nfl_fantasy_all_positions_{season}.csv")
            all_players.to_csv(output_file, index=False)
            logger.info(f"Combined data saved to {output_file}")
            
            # Print summary
            logger.info("\nScraping Summary:")
            for position_name, df in results.items():
                logger.info(f"  - {position_name}: {len(df)} players")
            logger.info(f"  - Total: {len(all_players)} players")
        
        logger.info("\nScraping completed successfully!")
        
    except Exception as e:
        logger.error(f"An error occurred in the main function: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)