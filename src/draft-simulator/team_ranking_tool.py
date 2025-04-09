import pandas as pd
import numpy as np
import json
from io import StringIO


def analyze_team_offenses(offense_files_dict):
    """
    Combine and analyze team offense data across multiple years.

    Parameters:
    -----------
    offense_files_dict : dict
        Dictionary with years as keys and paths to offense stats CSV files as values

    Returns:
    --------
    str
        JSON string containing comprehensive team offense dataset with trends and rankings
    """
    # Initialize a dictionary to store dataframes for each year
    yearly_dfs = {}

    # Load each year's data
    for year, file_path in offense_files_dict.items():
        try:
            df = pd.read_csv(file_path)

            # Clean up team names for consistency
            df['TEAM'] = df['TEAM'].str.strip()

            # Add year column
            df['Year'] = year

            # Add to dictionary
            yearly_dfs[year] = df

        except Exception as e:
            print(f"Error loading offense data for {year}: {e}")

    # Combine all years into a single dataframe
    if not yearly_dfs:
        return json.dumps([])  # Return empty JSON array if no data was loaded

    all_years_df = pd.concat(yearly_dfs.values(), ignore_index=True)

    # Create team abbreviation mappings if needed
    team_name_map = {
        'Arizona Cardinals': 'ARI',
        'Atlanta Falcons': 'ATL',
        'Baltimore Ravens': 'BAL',
        'Buffalo Bills': 'BUF',
        'Carolina Panthers': 'CAR',
        'Chicago Bears': 'CHI',
        'Cincinnati Bengals': 'CIN',
        'Cleveland Browns': 'CLE',
        'Dallas Cowboys': 'DAL',
        'Denver Broncos': 'DEN',
        'Detroit Lions': 'DET',
        'Green Bay Packers': 'GB',
        'Houston Texans': 'HOU',
        'Indianapolis Colts': 'IND',
        'Jacksonville Jaguars': 'JAX',
        'Kansas City Chiefs': 'KC',
        'Las Vegas Raiders': 'LV',
        'Los Angeles Chargers': 'LAC',
        'Los Angeles Rams': 'LAR',
        'Miami Dolphins': 'MIA',
        'Minnesota Vikings': 'MIN',
        'New England Patriots': 'NE',
        'New Orleans Saints': 'NO',
        'New York Giants': 'NYG',
        'New York Jets': 'NYJ',
        'Philadelphia Eagles': 'PHI',
        'Pittsburgh Steelers': 'PIT',
        'San Francisco 49ers': 'SF',
        'Seattle Seahawks': 'SEA',
        'Tampa Bay Buccaneers': 'TB',
        'Tennessee Titans': 'TEN',
        'Washington Commanders': 'WAS'
    }

    # Add team abbreviations if needed (checking if teams are already in abbreviation format)
    if not all(len(team) <= 4 for team in all_years_df['TEAM'].unique()):
        # Teams are in full name format, so add abbreviations
        all_years_df['Team_Abbr'] = all_years_df['TEAM'].map(team_name_map)
    else:
        # Teams are already in abbreviation format
        all_years_df['Team_Abbr'] = all_years_df['TEAM']

    # Calculate additional metrics
    all_years_df['Pass_Run_Ratio'] = all_years_df['Passing'] / all_years_df['Rushing']
    all_years_df['Yards_Per_Point'] = all_years_df['YDS'] / all_years_df['PTS']
    all_years_df['Offensive_Efficiency'] = all_years_df['PTS'] / all_years_df['YDS'] * 100  # Points per 100 yards

    # Create a pivot table to analyze trends by team
    team_trends = all_years_df.pivot_table(
        index='Team_Abbr',
        columns='Year',
        values=['YDS/G', 'PTS/G', 'Passing', 'Rushing', 'Pass_Run_Ratio', 'Offensive_Efficiency'],
        aggfunc='mean'
    )

    # Flatten the multi-level columns
    team_trends.columns = [f'{col[0]}_{col[1]}' for col in team_trends.columns]

    # Reset index to make Team_Abbr a regular column
    team_trends = team_trends.reset_index()

    # Calculate trend metrics (focusing on most recent years)
    recent_years = sorted(offense_files_dict.keys())[-3:]  # Last 3 years

    for metric in ['YDS/G', 'PTS/G', 'Pass_Run_Ratio']:
        # Create columns for most recent year
        most_recent_year = max(offense_files_dict.keys())
        team_trends[f'{metric}_Recent'] = team_trends[f'{metric}_{most_recent_year}']

        # Calculate 3-year average
        avg_cols = [f'{metric}_{year}' for year in recent_years]
        team_trends[f'{metric}_3YR_Avg'] = team_trends[avg_cols].mean(axis=1)

        # Calculate year-over-year change (most recent 2 years)
        if len(recent_years) >= 2:
            year1, year2 = recent_years[-2:]
            team_trends[f'{metric}_YoY_Change'] = (
                    team_trends[f'{metric}_{year2}'] - team_trends[f'{metric}_{year1}']
            )

        # Calculate trend direction (positive or negative over 3 years)
        if len(recent_years) >= 3:
            # Simple linear regression slope for trend
            x = np.array(recent_years).astype(float)
            trends = {}

            for team in team_trends['Team_Abbr']:
                y_values = []
                for year in recent_years:
                    col = f'{metric}_{year}'
                    if col in team_trends.columns:
                        val = team_trends.loc[team_trends['Team_Abbr'] == team, col].values[0]
                        y_values.append(val)
                    else:
                        y_values.append(np.nan)

                if not any(np.isnan(y_values)):
                    y = np.array(y_values)
                    slope, _ = np.polyfit(x, y, 1)
                    trends[team] = slope
                else:
                    trends[team] = np.nan

            team_trends[f'{metric}_Trend'] = team_trends['Team_Abbr'].map(trends)

    # Create summary metrics for the most recent year
    most_recent_df = yearly_dfs[most_recent_year]

    # Rank teams by key metrics
    most_recent_df['Passing_Rank'] = most_recent_df['Passing'].rank(ascending=False)
    most_recent_df['Rushing_Rank'] = most_recent_df['Rushing'].rank(ascending=False)
    most_recent_df['Total_Offense_Rank'] = most_recent_df['YDS/G'].rank(ascending=False)
    most_recent_df['Scoring_Rank'] = most_recent_df['PTS/G'].rank(ascending=False)

    # Calculate pass-friendliness and rush-friendliness scores
    most_recent_df['Pass_Friendly_Score'] = (
            (33 - most_recent_df['Passing_Rank']) * 0.7 +
            (33 - most_recent_df['Total_Offense_Rank']) * 0.3
    )

    most_recent_df['Rush_Friendly_Score'] = (
            (33 - most_recent_df['Rushing_Rank']) * 0.7 +
            (33 - most_recent_df['Total_Offense_Rank']) * 0.3
    )

    # Add team abbreviations
    if 'Team_Abbr' not in most_recent_df.columns:
        if not all(len(team) <= 4 for team in most_recent_df['TEAM'].unique()):
            most_recent_df['Team_Abbr'] = most_recent_df['TEAM'].map(team_name_map)
        else:
            most_recent_df['Team_Abbr'] = most_recent_df['TEAM']

    # Select relevant columns for the final summary
    summary_cols = [
        'Team_Abbr', 'YDS/G', 'PTS/G', 'Passing', 'Rushing',
        'Passing_Rank', 'Rushing_Rank', 'Total_Offense_Rank', 'Scoring_Rank',
        'Pass_Friendly_Score', 'Rush_Friendly_Score'
    ]

    team_summary = most_recent_df[summary_cols].copy()

    # Merge with trend data
    final_offense_df = pd.merge(
        team_summary,
        team_trends,
        on='Team_Abbr',
        how='left'
    )

    # Calculate overall offense quality score
    final_offense_df['Offense_Quality_Score'] = (
            (33 - final_offense_df['Total_Offense_Rank']) * 0.4 +
            (33 - final_offense_df['Scoring_Rank']) * 0.6
    )

    # Calculate offense stability score (lower variation is more stable)
    if len(recent_years) >= 3:
        # Calculate coefficient of variation for points per game over 3 years
        for team in final_offense_df['Team_Abbr']:
            pts_values = []
            for year in recent_years:
                col = f'PTS/G_{year}'
                if col in team_trends.columns:
                    mask = team_trends['Team_Abbr'] == team
                    if any(mask):
                        pts_values.append(team_trends.loc[mask, col].values[0])

            if pts_values:
                cv = np.std(pts_values) / np.mean(pts_values) if np.mean(pts_values) > 0 else np.nan
                final_offense_df.loc[final_offense_df['Team_Abbr'] == team, 'Offense_Stability'] = 100 - (cv * 100)

    # Convert DataFrame to JSON
    return final_offense_df.to_json(orient="records", date_format="iso")


def add_offense_context_to_rankings(player_data, offense_data):
    """
    Add team offensive metrics to player rankings.

    Parameters:
    -----------
    player_data : str or pandas.DataFrame
        Player rankings dataframe or JSON string
    offense_data : str or pandas.DataFrame
        Team offense metrics dataframe from analyze_team_offenses or JSON string

    Returns:
    --------
    str
        JSON string containing enhanced player data with offensive context
    """
    # Convert input to DataFrames if they are JSON strings
    if isinstance(player_data, str):
        player_df = pd.read_json(player_data, orient="records")
    else:
        player_df = player_data

    if isinstance(offense_data, str):
        offense_df = pd.read_json(offense_data, orient="records")
    else:
        offense_df = offense_data

    if 'Team' not in player_df.columns or offense_df.empty:
        return player_df.to_json(orient="records", date_format="iso")

    # Make a copy to avoid modifying original
    enhanced_df = player_df.copy()

    # Get team abbreviation column name from offense_df
    team_col = 'Team_Abbr' if 'Team_Abbr' in offense_df.columns else 'TEAM'

    # Create a mapping dictionary from team abbreviations to offense metrics
    offense_dict = {}
    for _, row in offense_df.iterrows():
        team_abbr = row[team_col]
        offense_dict[team_abbr] = row.to_dict()

    # Add offensive context columns based on position
    for idx, player in enhanced_df.iterrows():
        team = player['Team']
        position = player['Pos']

        # Skip if team not found in offense data
        if team not in offense_dict:
            continue

        team_offense = offense_dict[team]

        # Add general offensive metrics
        enhanced_df.at[idx, 'Team_Offense_Rank'] = team_offense.get('Total_Offense_Rank', np.nan)
        enhanced_df.at[idx, 'Team_Scoring_Rank'] = team_offense.get('Scoring_Rank', np.nan)
        enhanced_df.at[idx, 'Team_Offense_Quality'] = team_offense.get('Offense_Quality_Score', np.nan)

        # Position-specific offensive context
        if position == 'QB':
            # QBs benefit from overall offensive quality and passing volume
            enhanced_df.at[idx, 'Position_Opportunity_Score'] = (
                    team_offense.get('Pass_Friendly_Score', 0) * 0.8 +
                    team_offense.get('Offense_Quality_Score', 0) * 0.2
            )

            # Add passing volume metrics
            enhanced_df.at[idx, 'Team_Passing_Rank'] = team_offense.get('Passing_Rank', np.nan)
            enhanced_df.at[idx, 'Team_Pass_Volume'] = team_offense.get('Passing', np.nan)

        elif position == 'RB':
            # RBs benefit from rushing volume and game script (scoring leads to more rushes)
            enhanced_df.at[idx, 'Position_Opportunity_Score'] = (
                    team_offense.get('Rush_Friendly_Score', 0) * 0.7 +
                    team_offense.get('Offense_Quality_Score', 0) * 0.3
            )

            # Add rushing volume metrics
            enhanced_df.at[idx, 'Team_Rushing_Rank'] = team_offense.get('Rushing_Rank', np.nan)
            enhanced_df.at[idx, 'Team_Rush_Volume'] = team_offense.get('Rushing', np.nan)

        elif position == 'WR':
            # WRs benefit from passing volume and overall offense quality
            enhanced_df.at[idx, 'Position_Opportunity_Score'] = (
                    team_offense.get('Pass_Friendly_Score', 0) * 0.7 +
                    team_offense.get('Offense_Quality_Score', 0) * 0.3
            )

            # Add passing volume metrics
            enhanced_df.at[idx, 'Team_Passing_Rank'] = team_offense.get('Passing_Rank', np.nan)
            enhanced_df.at[idx, 'Team_Pass_Volume'] = team_offense.get('Passing', np.nan)

        elif position == 'TE':
            # TEs benefit from passing volume but differently than WRs
            enhanced_df.at[idx, 'Position_Opportunity_Score'] = (
                    team_offense.get('Pass_Friendly_Score', 0) * 0.6 +
                    team_offense.get('Offense_Quality_Score', 0) * 0.4
            )

            # Add passing volume metrics
            enhanced_df.at[idx, 'Team_Passing_Rank'] = team_offense.get('Passing_Rank', np.nan)
            enhanced_df.at[idx, 'Team_Pass_Volume'] = team_offense.get('Passing', np.nan)

        elif position == 'K':
            # Kickers benefit from good offenses that might stall in red zone
            enhanced_df.at[idx, 'Position_Opportunity_Score'] = (
                    team_offense.get('Offense_Quality_Score', 0) * 0.8 +
                    team_offense.get('Yards_Per_Point', 0) * 0.2  # Higher is better for kickers
            )

        elif position == 'DST':
            # Not directly related to offensive stats, but can add for completeness
            enhanced_df.at[idx, 'Team_Offense_Quality'] = team_offense.get('Offense_Quality_Score', np.nan)

    # Normalize opportunity scores
    if 'Position_Opportunity_Score' in enhanced_df.columns:
        # Group by position and normalize within position
        for pos in enhanced_df['Pos'].unique():
            mask = enhanced_df['Pos'] == pos

            if sum(mask) > 0:
                scores = enhanced_df.loc[mask, 'Position_Opportunity_Score']
                min_score = scores.min()
                max_score = scores.max()

                if max_score > min_score:  # Avoid division by zero
                    normalized = (scores - min_score) / (max_score - min_score) * 100
                    enhanced_df.loc[mask, 'Position_Opportunity_Score'] = normalized

    # Convert DataFrame to JSON
    return enhanced_df.to_json(orient="records", date_format="iso")


def identify_favorable_offensive_situations(offense_data, position='WR'):
    """
    Find teams with favorable offensive environments for specific positions.

    Parameters:
    -----------
    offense_data : str or pandas.DataFrame
        Team offense metrics dataframe from analyze_team_offenses or JSON string
    position : str
        Position to analyze ('QB', 'RB', 'WR', 'TE', 'K')

    Returns:
    --------
    str
        JSON string containing ranked list of teams by position favorability
    """
    # Convert input to DataFrame if it's a JSON string
    if isinstance(offense_data, str):
        offense_df = pd.read_json(offense_data, orient="records")
    else:
        offense_df = offense_data

    if offense_df.empty:
        return json.dumps([])

    # Get team abbreviation column name from offense_df
    team_col = 'Team_Abbr' if 'Team_Abbr' in offense_df.columns else 'TEAM'

    # Make a copy of offense dataframe for analysis
    teams_df = offense_df.copy()

    # Create position-specific favorability score
    if position == 'QB':
        # QBs benefit from passing volume, offensive quality, and positive trends
        teams_df['Position_Favorability'] = (
                (33 - teams_df['Passing_Rank']) * 0.4 +
                (33 - teams_df['Total_Offense_Rank']) * 0.3 +
                (33 - teams_df['Scoring_Rank']) * 0.3
        )

        # Adjust for trend if available
        if 'PTS/G_Trend' in teams_df.columns:
            # Normalize trend to 0-10 scale
            max_trend = teams_df['PTS/G_Trend'].max()
            min_trend = teams_df['PTS/G_Trend'].min()

            if max_trend > min_trend:  # Avoid division by zero
                teams_df['Trend_Factor'] = (
                        (teams_df['PTS/G_Trend'] - min_trend) / (max_trend - min_trend) * 10
                )

                # Add trend factor with a weight of 20%
                teams_df['Position_Favorability'] = (
                        teams_df['Position_Favorability'] * 0.8 +
                        teams_df['Trend_Factor'] * 2
                )

        # Relevant metrics to include in output
        metrics = [
            team_col, 'Passing', 'Passing_Rank', 'YDS/G', 'PTS/G',
            'Total_Offense_Rank', 'Scoring_Rank', 'Position_Favorability'
        ]

    elif position == 'RB':
        # RBs benefit from rushing volume, offensive quality, and positive game scripts
        teams_df['Position_Favorability'] = (
                (33 - teams_df['Rushing_Rank']) * 0.5 +
                (33 - teams_df['Scoring_Rank']) * 0.3 +  # Better scoring = better game scripts
                (33 - teams_df['Total_Offense_Rank']) * 0.2
        )

        # Adjust for Pass/Run ratio - more run-heavy teams favor RBs
        if 'Pass_Run_Ratio_Recent' in teams_df.columns:
            # Convert to percentile (lower ratio = more favorable for RBs)
            pass_run_ranks = teams_df['Pass_Run_Ratio_Recent'].rank(ascending=True)
            max_rank = pass_run_ranks.max()

            teams_df['Run_Heavy_Factor'] = (pass_run_ranks / max_rank) * 10

            # Add run-heavy factor with a weight of 20%
            teams_df['Position_Favorability'] = (
                    teams_df['Position_Favorability'] * 0.8 +
                    teams_df['Run_Heavy_Factor'] * 2
            )

        # Relevant metrics to include in output
        metrics = [
            team_col, 'Rushing', 'Rushing_Rank', 'YDS/G', 'PTS/G',
            'Total_Offense_Rank', 'Scoring_Rank', 'Position_Favorability'
        ]

    elif position == 'WR':
        # WRs benefit from passing volume and offensive quality
        teams_df['Position_Favorability'] = (
                (33 - teams_df['Passing_Rank']) * 0.6 +
                (33 - teams_df['Total_Offense_Rank']) * 0.2 +
                (33 - teams_df['Scoring_Rank']) * 0.2
        )

        # Adjust for Pass/Run ratio - more pass-heavy teams favor WRs
        if 'Pass_Run_Ratio_Recent' in teams_df.columns:
            # Convert to percentile (higher ratio = more favorable for WRs)
            pass_run_ranks = teams_df['Pass_Run_Ratio_Recent'].rank(ascending=False)
            max_rank = pass_run_ranks.max()

            teams_df['Pass_Heavy_Factor'] = (pass_run_ranks / max_rank) * 10

            # Add pass-heavy factor with a weight of 20%
            teams_df['Position_Favorability'] = (
                    teams_df['Position_Favorability'] * 0.8 +
                    teams_df['Pass_Heavy_Factor'] * 2
            )

        # Relevant metrics to include in output
        metrics = [
            team_col, 'Passing', 'Passing_Rank', 'YDS/G', 'PTS/G',
            'Total_Offense_Rank', 'Scoring_Rank', 'Position_Favorability'
        ]

    elif position == 'TE':
        # TEs benefit from passing volume, but in a different way than WRs
        teams_df['Position_Favorability'] = (
                (33 - teams_df['Passing_Rank']) * 0.5 +
                (33 - teams_df['Scoring_Rank']) * 0.3 +
                (33 - teams_df['Total_Offense_Rank']) * 0.2
        )

        # Relevant metrics to include in output
        metrics = [
            team_col, 'Passing', 'Passing_Rank', 'YDS/G', 'PTS/G',
            'Total_Offense_Rank', 'Scoring_Rank', 'Position_Favorability'
        ]

    elif position == 'K':
        # Kickers benefit from good offenses that might stall in red zone
        # Calculate yards per point (higher means more field goals vs TDs)
        if 'YDS' in teams_df.columns and 'PTS' in teams_df.columns:
            teams_df['Yards_Per_Point'] = teams_df['YDS'] / teams_df['PTS']

            # Normalize yards per point
            max_ypp = teams_df['Yards_Per_Point'].max()
            min_ypp = teams_df['Yards_Per_Point'].min()

            if max_ypp > min_ypp:  # Avoid division by zero
                teams_df['YPP_Factor'] = (
                        (teams_df['Yards_Per_Point'] - min_ypp) / (max_ypp - min_ypp) * 10
                )
            else:
                teams_df['YPP_Factor'] = 5  # Default middle value
        else:
            teams_df['YPP_Factor'] = 5

        teams_df['Position_Favorability'] = (
                (33 - teams_df['Total_Offense_Rank']) * 0.6 +  # Good offense gets in FG range
                teams_df['YPP_Factor'] * 0.4  # Higher yards per point suggests more FGs
        )

        # Relevant metrics to include in output
        metrics = [
            team_col, 'YDS/G', 'PTS/G', 'Yards_Per_Point',
            'Total_Offense_Rank', 'Scoring_Rank', 'Position_Favorability'
        ]

    else:
        # Default generic favorability
        teams_df['Position_Favorability'] = (
                (33 - teams_df['Total_Offense_Rank']) * 0.5 +
                (33 - teams_df['Scoring_Rank']) * 0.5
        )

        # Relevant metrics to include in output
        metrics = [
            team_col, 'YDS/G', 'PTS/G',
            'Total_Offense_Rank', 'Scoring_Rank', 'Position_Favorability'
        ]

    # Select only metrics that exist in the dataframe
    available_metrics = [m for m in metrics if m in teams_df.columns]

    # Create the final ranked dataframe
    result_df = teams_df[available_metrics].sort_values('Position_Favorability', ascending=False)

    # Add rank column
    result_df.insert(0, 'Favorability_Rank', range(1, len(result_df) + 1))

    # Convert DataFrame to JSON
    return result_df.to_json(orient="records", date_format="iso")


# Helper function to convert JSON to human-readable format for display
def json_to_readable(json_str, limit=10):
    """
    Convert JSON string to a readable format for display.

    Parameters:
    -----------
    json_str : str
        JSON string to convert
    limit : int
        Maximum number of records to include

    Returns:
    --------
    str
        Human-readable string representation of the JSON data
    """
    try:
        data = json.loads(json_str)

        # If data is a list of records
        if isinstance(data, list):
            if limit and len(data) > limit:
                data = data[:limit]
                suffix = f"\n... and {len(json.loads(json_str)) - limit} more records"
            else:
                suffix = ""

            formatted = json.dumps(data, indent=2)
            return formatted + suffix

        # If data is a dictionary
        elif isinstance(data, dict):
            return json.dumps(data, indent=2)

        return json.dumps(data, indent=2)
    except:
        return "Invalid JSON format or error parsing JSON"


def save_json_data(json_data, output_file):
    """
    Save the JSON data to a file.

    Parameters:
    -----------
    json_data : str
        The data in JSON format
    output_file : str
        Path where the JSON file will be saved
    """
    # If output_file doesn't end with .json, ensure it has the right extension
    if not output_file.endswith('.json'):
        output_file = output_file.replace('.csv', '.json') if output_file.endswith('.csv') else output_file + '.json'

    # Write the JSON data to the file
    with open(output_file, 'w') as f:
        f.write(json_data)

    print(f"Data saved to {output_file}")


# These functions integrate with your existing code, so you can use them like this:
if __name__ == "__main__":
    # Example paths for team offense stats files
    offense_files = {
        2018: "tools/data/offensive_rtg_data/nfl_team_offense_stats_2018.csv",
        2019: "tools/data/offensive_rtg_data/nfl_team_offense_stats_2019.csv",
        2020: "tools/data/offensive_rtg_data/nfl_team_offense_stats_2020.csv",
        2021: "tools/data/offensive_rtg_data/nfl_team_offense_stats_2021.csv",
        2022: "tools/data/offensive_rtg_data/nfl_team_offense_stats_2022.csv",
        2023: "tools/data/offensive_rtg_data/nfl_team_offense_stats_2023.csv"
    }

    # Analyze team offenses
    offense_json = analyze_team_offenses(offense_files)

    # Save team offense analysis
    save_json_data(offense_json, "tools/data/offensive_rtg_data/Team_Offense_Analysis.json")
    print("Team offense analysis saved to Team_Offense_Analysis.json")

    # Parse JSON back to list for demonstration
    offense_data = json.loads(offense_json)
    print(f"\nAnalyzed {len(offense_data)} team offenses")

    # Files for player rankings
    espn_file = "tools/data/official_2024_fantasy_rankings/ESPN_Standard.csv"
    sleeper_file = "tools/data/official_2024_fantasy_rankings/Sleeper_Standard.csv"
    yahoo_file = "tools/data/official_2024_fantasy_rankings/Yahoo_Standard.csv"

    # Define position stats files
    stats_files = {
        'QB': "tools/data/player_ranking_position_data/nfl_fantasy_QB_stats_2023.csv",
        'RB': "tools/data/player_ranking_position_data/nfl_fantasy_RB_stats_2023.csv",
        'WR': "tools/data/player_ranking_position_data/nfl_fantasy_WR_stats_2023.csv",
        'TE': "tools/data/player_ranking_position_data/nfl_fantasy_TE_stats_2023.csv",
        'K': "tools/data/player_ranking_position_data/nfl_fantasy_kickers.csv",
        'DST': "tools/data/player_ranking_position_data/nfl_fantasy_defense.csv"
    }

    # Load and combine player data from the player_ranking_tool
    from player_ranking_tool import load_and_combine_fantasy_data

    player_json = load_and_combine_fantasy_data(espn_file, sleeper_file, yahoo_file, stats_files)

    # Add offensive context to player rankings
    enhanced_player_json = add_offense_context_to_rankings(player_json, offense_json)

    # Save enhanced player rankings
    save_json_data(enhanced_player_json, "tools/data/offensive_rtg_data/Fantasy_Rankings_with_Offense_Context.json")
    print("Enhanced player rankings saved to Fantasy_Rankings_with_Offense_Context.json")

    # Identify favorable situations for each position
    for position in ['QB', 'RB', 'WR', 'TE', 'K']:
        favorable_json = identify_favorable_offensive_situations(offense_json, position)
        save_json_data(favorable_json, f"data/offensive_rtg_data/Favorable_Teams_for_{position}.json")
        print(f"Favorable teams for {position} saved to Favorable_Teams_for_{position}.json")

        # Print top 5 favorable teams for each position
        print(f"\nTop 5 teams for {position}:")
        favorable_data = json.loads(favorable_json)
        for team in favorable_data[:5]:
            # Use the appropriate team column (could be 'Team_Abbr' or 'TEAM')
            team_abbr = team.get('Team_Abbr', team.get('TEAM', 'Unknown'))
            favorability = team['Position_Favorability']
            rank = team['Favorability_Rank']
            print(f"{rank}. {team_abbr} - Favorability Score: {favorability:.2f}")