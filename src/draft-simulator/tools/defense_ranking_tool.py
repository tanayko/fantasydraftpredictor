import pandas as pd

def analyze_defense_vs_position(defense_files_dict):
    """
    Analyze how each team's defense performs against specific positions.

    Parameters:
    -----------
    defense_files_dict : dict
        Dictionary with positions as keys and paths to defense vs position CSV files as values

    Returns:
    --------
    dict of pandas.DataFrame
        Dictionary with a dataframe for each position containing defense rankings
    """
    # Initialize dictionary to store results
    defense_analysis = {}

    # Process each position's data
    for position, file_path in defense_files_dict.items():
        try:
            # Read the CSV file
            df = pd.read_csv(file_path)

            # Clean up team names for consistency
            df['Team'] = df['Team'].str.strip()

            # Process based on position
            if position == 'QB':
                # For QBs, lower ranks are better for defense
                df['Defense_Rank'] = df['Rank']

                # Calculate a defense score (reverse of offensive performance)
                # Lower Avg fantasy points allowed = better defense
                df['Defense_Score'] = 33 - df['Rank']

                # Add key stats for QB defense
                df['Pass_Yds_Allowed'] = df['Yds']
                df['Pass_TD_Allowed'] = df['TD']
                df['QB_Rush_Yds_Allowed'] = df['Rush_Yds']

                # Select relevant columns
                cols = ['Team', 'Defense_Rank', 'Defense_Score', 'Avg',
                        'Pass_Yds_Allowed', 'Pass_TD_Allowed', 'Int',
                        'QB_Rush_Yds_Allowed']

            elif position == 'RB':
                # For RBs, lower ranks are better for defense
                df['Defense_Rank'] = df['Rank']

                # Calculate a defense score (reverse of offensive performance)
                df['Defense_Score'] = 33 - df['Rank']

                # Add key stats for RB defense
                df['Rush_Yds_Allowed'] = df['Yds']
                df['Rush_TD_Allowed'] = df['TD']
                df['RB_Rec_Allowed'] = df['Rec']
                df['RB_Rec_Yds_Allowed'] = df['Rec_Yds']

                # Select relevant columns
                cols = ['Team', 'Defense_Rank', 'Defense_Score', 'Avg',
                        'Rush_Yds_Allowed', 'Rush_TD_Allowed',
                        'RB_Rec_Allowed', 'RB_Rec_Yds_Allowed', 'Rec_TD']

            elif position == 'WR':
                # For WRs, lower ranks are better for defense
                df['Defense_Rank'] = df['Rank']

                # Calculate a defense score (reverse of offensive performance)
                df['Defense_Score'] = 33 - df['Rank']

                # Add key stats for WR defense
                df['WR_Rec_Allowed'] = df['Rec']
                df['WR_Targets_Allowed'] = df['Target']
                df['WR_Yds_Allowed'] = df['Rec_Yds']
                df['WR_TD_Allowed'] = df['Rec_TD']

                # Select relevant columns
                cols = ['Team', 'Defense_Rank', 'Defense_Score', 'Avg',
                        'WR_Rec_Allowed', 'WR_Targets_Allowed',
                        'WR_Yds_Allowed', 'WR_TD_Allowed']

            elif position == 'TE':
                # For TEs, lower ranks are better for defense
                df['Defense_Rank'] = df['Rank']

                # Calculate a defense score (reverse of offensive performance)
                df['Defense_Score'] = 33 - df['Rank']

                # Add key stats for TE defense
                df['TE_Rec_Allowed'] = df['Rec']
                df['TE_Targets_Allowed'] = df['Target']
                df['TE_Yds_Allowed'] = df['Yds']
                df['TE_TD_Allowed'] = df['TD']

                # Select relevant columns
                cols = ['Team', 'Defense_Rank', 'Defense_Score', 'Avg',
                        'TE_Rec_Allowed', 'TE_Targets_Allowed',
                        'TE_Yds_Allowed', 'TE_TD_Allowed']

            elif position == 'K':
                # For Ks, lower ranks are better for defense
                df['Defense_Rank'] = df['Rank']

                # Calculate a defense score (reverse of offensive performance)
                df['Defense_Score'] = 33 - df['Rank']

                # Add key stats for K defense
                df['PAT_Allowed'] = df['PAT_Made']
                df['FG_20_29_Allowed'] = df['FG_20_29']
                df['FG_30_39_Allowed'] = df['FG_30_39']
                df['FG_40_49_Allowed'] = df['FG_40_49']
                df['FG_50plus_Allowed'] = df['FG_50plus']

                # Select relevant columns
                cols = ['Team', 'Defense_Rank', 'Defense_Score', 'Avg',
                        'PAT_Allowed', 'FG_20_29_Allowed', 'FG_30_39_Allowed',
                        'FG_40_49_Allowed', 'FG_50plus_Allowed']

            elif position == 'DEF':
                # For DEF, this is actually team defense performance, not defense against defense
                df['Defense_Rank'] = df['Rank']

                # Higher rank is better for actual defense
                df['Defense_Score'] = df['Rank']

                # Key defensive stats
                df['Sacks'] = df['Sack']
                df['Interceptions'] = df['Int']
                df['Fumble_Recoveries'] = df['Fum_Rec']

                # Select relevant columns
                cols = ['Team', 'Defense_Rank', 'Defense_Score', 'Avg',
                        'Sacks', 'Interceptions', 'Fumble_Recoveries', 'Pts_Allow']

            else:
                # Generic processing for any other position
                df['Defense_Rank'] = df['Rank']
                df['Defense_Score'] = 33 - df['Rank']
                cols = ['Team', 'Defense_Rank', 'Defense_Score', 'Avg']

            # Filter to only existing columns
            cols = [col for col in cols if col in df.columns]

            # Create final dataframe with selected columns
            defense_df = df[cols].copy()

            # Sort by defense rank (lower is better, except for DEF position)
            if position != 'DEF':
                defense_df = defense_df.sort_values('Defense_Rank')
            else:
                defense_df = defense_df.sort_values('Defense_Rank', ascending=False)

            # Add to results dictionary
            defense_analysis[position] = defense_df

        except Exception as e:
            print(f"Error processing {position} defense data: {e}")

    return defense_analysis

def categorize_defenses(defense_analysis, num_categories=5):
    """
    Categorize defenses into tiers (e.g., "Great", "Good", "Average", "Bad", "Terrible").

    Parameters:
    -----------
    defense_analysis : dict
        Dictionary with defense analysis dataframes from analyze_defense_vs_position
    num_categories : int
        Number of categories to divide teams into

    Returns:
    --------
    dict of pandas.DataFrame
        Dictionary with dataframes containing categorized defenses
    """
    categorized_defenses = {}

    # Category labels from best to worst (for defenses against a position)
    if num_categories == 5:
        categories = ["Shutdown", "Strong", "Average", "Weak", "Exploitable"]
    elif num_categories == 3:
        categories = ["Strong", "Average", "Weak"]
    else:
        # Generate generic category names
        categories = [f"Tier {i + 1}" for i in range(num_categories)]

    for position, df in defense_analysis.items():
        if df.empty:
            continue

        df_copy = df.copy()

        # Calculate category boundaries
        n_teams = len(df_copy)
        teams_per_category = n_teams // num_categories
        remainder = n_teams % num_categories

        # Distribute teams into categories
        category_sizes = [teams_per_category] * num_categories

        # Distribute remainder teams one per category from the beginning
        for i in range(remainder):
            category_sizes[i] += 1

        # Add category column
        df_copy['Category'] = ""

        # Position in dataframe
        pos = 0

        # Special handling for DEF position (high rank is good)
        if position == 'DEF':
            # Sort by Defense_Rank descending (higher rank = better defense)
            df_copy = df_copy.sort_values('Defense_Rank', ascending=False)

            # Assign categories
            for i, size in enumerate(category_sizes):
                for j in range(size):
                    if pos < n_teams:
                        df_copy.iloc[pos, df_copy.columns.get_loc('Category')] = categories[i]
                        pos += 1
        else:
            # Sort by Defense_Rank ascending (lower rank = better defense)
            df_copy = df_copy.sort_values('Defense_Rank')

            # Assign categories
            for i, size in enumerate(category_sizes):
                for j in range(size):
                    if pos < n_teams:
                        df_copy.iloc[pos, df_copy.columns.get_loc('Category')] = categories[i]
                        pos += 1

        # Add to results
        categorized_defenses[position] = df_copy

    return categorized_defenses


def add_defense_matchup_to_players(player_data, defense_analysis, nfl_schedule):
    """
    Add overall schedule difficulty rating to player rankings.

    Parameters:
    -----------
    player_data : str or pandas.DataFrame
        Player rankings dataframe or JSON string
    defense_analysis : dict
        Dictionary with defense analysis dataframes from analyze_defense_vs_position
    nfl_schedule : dict
        Dictionary with team schedules from create_nfl_schedule()

    Returns:
    --------
    str or pandas.DataFrame
        Enhanced player data with overall schedule difficulty rating
    """
    import pandas as pd
    import json

    # Convert input to DataFrame if it's a JSON string
    if isinstance(player_data, str):
        player_df = pd.read_json(player_data, orient="records")
    else:
        player_df = player_data.copy()

    if player_df.empty or not defense_analysis:
        if isinstance(player_data, str):
            return player_data
        return player_df

    # Create a copy of the player dataframe
    enhanced_df = player_df.copy()

    # Create a lookup dictionary for each position
    defense_lookup = {}
    for position, df in defense_analysis.items():
        if df.empty:
            continue

        defense_lookup[position] = {}
        for _, row in df.iterrows():
            team = row['Team']
            # Store data for each team
            defense_lookup[position][team] = {
                'Defense_Rank': row['Defense_Rank'],
                'Defense_Score': row['Defense_Score']
            }

    # Team name mapping in case formats differ
    team_map = {
        'ARI': ['ARI', 'Arizona', 'Cardinals'],
        'ATL': ['ATL', 'Atlanta', 'Falcons'],
        'BAL': ['BAL', 'Baltimore', 'Ravens'],
        'BUF': ['BUF', 'Buffalo', 'Bills'],
        'CAR': ['CAR', 'Carolina', 'Panthers'],
        'CHI': ['CHI', 'Chicago', 'Bears'],
        'CIN': ['CIN', 'Cincinnati', 'Bengals'],
        'CLE': ['CLE', 'Cleveland', 'Browns'],
        'DAL': ['DAL', 'Dallas', 'Cowboys'],
        'DEN': ['DEN', 'Denver', 'Broncos'],
        'DET': ['DET', 'Detroit', 'Lions'],
        'GB': ['GB', 'Green Bay', 'Packers'],
        'HOU': ['HOU', 'Houston', 'Texans'],
        'IND': ['IND', 'Indianapolis', 'Colts'],
        'JAX': ['JAX', 'Jacksonville', 'Jaguars'],
        'KC': ['KC', 'Kansas City', 'Chiefs'],
        'LV': ['LV', 'Las Vegas', 'Raiders'],
        'LAC': ['LAC', 'Los Angeles Chargers', 'Chargers'],
        'LAR': ['LAR', 'Los Angeles Rams', 'Rams'],
        'MIA': ['MIA', 'Miami', 'Dolphins'],
        'MIN': ['MIN', 'Minnesota', 'Vikings'],
        'NE': ['NE', 'New England', 'Patriots'],
        'NO': ['NO', 'New Orleans', 'Saints'],
        'NYG': ['NYG', 'New York Giants', 'Giants'],
        'NYJ': ['NYJ', 'New York Jets', 'Jets'],
        'PHI': ['PHI', 'Philadelphia', 'Eagles'],
        'PIT': ['PIT', 'Pittsburgh', 'Steelers'],
        'SF': ['SF', 'San Francisco', '49ers'],
        'SEA': ['SEA', 'Seattle', 'Seahawks'],
        'TB': ['TB', 'Tampa Bay', 'Buccaneers'],
        'TEN': ['TEN', 'Tennessee', 'Titans'],
        'WAS': ['WAS', 'Washington', 'Commanders']
    }

    # Map to get from team code to team name variations
    team_to_variations = {}
    for code, variations in team_map.items():
        for variation in variations:
            team_to_variations[variation] = variations

    # For each player, calculate overall schedule difficulty
    for idx, player in enhanced_df.iterrows():
        team = player['Team']
        position = player['Pos']

        # Skip if position not in defense analysis or team not in schedule
        if position not in defense_lookup or team not in nfl_schedule:
            continue

        # Track total and count for averaging
        total_difficulty = 0
        matchup_count = 0

        # Check each week in schedule
        for week, opponent in nfl_schedule[team].items():
            # Skip bye weeks
            if opponent == 'BYE':
                continue

            # Find defense data for this opponent and position
            def_data = None

            # Try different variations of team name
            for team_var in team_to_variations.get(opponent, [opponent]):
                if team_var in defense_lookup[position]:
                    def_data = defense_lookup[position][team_var]
                    break

            if def_data:
                # Add to difficulty score
                defense_rank = def_data['Defense_Rank']

                # For position players, lower defense rank means tougher matchup
                # For DEF position, higher defense rank means tougher matchup
                if position == 'DEF':
                    # For DEF, scale from 0-100 (higher is better matchup)
                    matchup_score = (defense_rank / 32) * 100
                else:
                    # For offensive positions, scale from 0-100 (higher is better matchup)
                    # Lower defense rank (better defense) = harder matchup = lower score
                    matchup_score = ((33 - defense_rank) / 32) * 100

                total_difficulty += matchup_score
                matchup_count += 1

        # Calculate average difficulty if we have matchups
        if matchup_count > 0:
            avg_difficulty = total_difficulty / matchup_count
            enhanced_df.at[idx, 'Schedule_Difficulty_Score'] = round(avg_difficulty, 1)

            # Add text rating
            if position == 'DEF':
                # For DEF, higher score is better
                if avg_difficulty >= 80:
                    rating = 'Very Favorable'
                elif avg_difficulty >= 60:
                    rating = 'Favorable'
                elif avg_difficulty >= 40:
                    rating = 'Average'
                elif avg_difficulty >= 20:
                    rating = 'Difficult'
                else:
                    rating = 'Very Difficult'
            else:
                # For offensive positions, higher score is better
                if avg_difficulty >= 80:
                    rating = 'Very Favorable'
                elif avg_difficulty >= 60:
                    rating = 'Favorable'
                elif avg_difficulty >= 40:
                    rating = 'Average'
                elif avg_difficulty >= 20:
                    rating = 'Difficult'
                else:
                    rating = 'Very Difficult'

            enhanced_df.at[idx, 'Schedule_Rating'] = rating

    # Return in the same format as input
    if isinstance(player_data, str):
        return enhanced_df.to_json(orient="records", date_format="iso")
    return enhanced_df

def get_position_matchup_advantage(defense_analysis, team, position):
    """
    Get the matchup advantage for a specific team against a position.

    Parameters:
    -----------
    defense_analysis : dict
        Dictionary with defense analysis dataframes from analyze_defense_vs_position
    team : str
        Team abbreviation to analyze matchups against
    position : str
        Position to analyze ('QB', 'RB', 'WR', 'TE', 'K')

    Returns:
    --------
    dict
        Dictionary with matchup advantage information
    """
    if position not in defense_analysis or defense_analysis[position].empty:
        return {"error": f"No data available for {position} position"}

    # Get the defense data
    df = defense_analysis[position]

    # Find the team
    team_data = df[df['Team'] == team]

    if team_data.empty:
        # Try finding with partial match
        team_data = df[df['Team'].str.contains(team, case=False)]

    if team_data.empty:
        return {"error": f"Team {team} not found in {position} defense data"}

    # Get defense rank and category
    defense_rank = team_data['Defense_Rank'].values[0]

    result = {
        "team": team,
        "position": position,
        "defense_rank": int(defense_rank),
        "avg_fantasy_points_allowed": float(team_data['Avg'].values[0])
    }

    # Add category if available
    if 'Category' in team_data.columns:
        result["category"] = team_data['Category'].values[0]

    # Add position-specific stats
    if position == 'QB':
        if 'Pass_Yds_Allowed' in team_data.columns:
            result["pass_yards_allowed"] = float(team_data['Pass_Yds_Allowed'].values[0])
        if 'Pass_TD_Allowed' in team_data.columns:
            result["pass_td_allowed"] = float(team_data['Pass_TD_Allowed'].values[0])

    elif position == 'RB':
        if 'Rush_Yds_Allowed' in team_data.columns:
            result["rush_yards_allowed"] = float(team_data['Rush_Yds_Allowed'].values[0])
        if 'Rush_TD_Allowed' in team_data.columns:
            result["rush_td_allowed"] = float(team_data['Rush_TD_Allowed'].values[0])

    elif position == 'WR':
        if 'WR_Rec_Allowed' in team_data.columns:
            result["receptions_allowed"] = float(team_data['WR_Rec_Allowed'].values[0])
        if 'WR_Yds_Allowed' in team_data.columns:
            result["receiving_yards_allowed"] = float(team_data['WR_Yds_Allowed'].values[0])
        if 'WR_TD_Allowed' in team_data.columns:
            result["receiving_td_allowed"] = float(team_data['WR_TD_Allowed'].values[0])

    elif position == 'TE':
        if 'TE_Rec_Allowed' in team_data.columns:
            result["receptions_allowed"] = float(team_data['TE_Rec_Allowed'].values[0])
        if 'TE_Yds_Allowed' in team_data.columns:
            result["receiving_yards_allowed"] = float(team_data['TE_Yds_Allowed'].values[0])
        if 'TE_TD_Allowed' in team_data.columns:
            result["receiving_td_allowed"] = float(team_data['TE_TD_Allowed'].values[0])

    # Calculate advantage level
    if defense_rank <= 8:
        result["advantage"] = "Bad matchup - strong defense"
    elif defense_rank <= 16:
        result["advantage"] = "Below average matchup"
    elif defense_rank <= 24:
        result["advantage"] = "Above average matchup"
    else:
        result["advantage"] = "Great matchup - weak defense"

    return result


# Example usage
if __name__ == "__main__":
    # Example file paths for defense vs position data
    defense_files = {
        'QB': "data/pts-against-data/qb/nfl_fantasy_qb_data_2024.csv",
        'RB': "data/pts-against-data/rb/nfl_fantasy_rb_data_2024.csv",
        'WR': "data/pts-against-data/wr/nfl_fantasy_wr_data_2024.csv",
        'TE': "data/pts-against-data/te/nfl_fantasy_te_data_2024.csv",
        'K': "data/pts-against-data/k/nfl_fantasy_k_data_2024.csv",
        'DEF': "data/pts-against-data/def/nfl_fantasy_def_data_2024.csv"
    }

    # Analyze defense vs position
    defense_analysis = analyze_defense_vs_position(defense_files)

    # Categorize defenses
    categorized_defenses = categorize_defenses(defense_analysis)

    # Print results for each position
    for position, df in categorized_defenses.items():
        print(f"\n{position} Defense Rankings:")
        print(df[['Team', 'Defense_Rank', 'Avg', 'Category']].head(5))

        # Save to CSV
        df.to_csv(f"data/pts-against-data/{position}_Defense_Rankings.csv", index=False)
        print(f"Full rankings saved to {position}_Defense_Rankings.csv")

    # Example of checking specific matchups
    print("\nExample Matchup Analysis:")
    print(get_position_matchup_advantage(categorized_defenses, "SF", "RB"))
    print(get_position_matchup_advantage(categorized_defenses, "TB", "WR"))
    print(get_position_matchup_advantage(categorized_defenses, "KC", "TE"))