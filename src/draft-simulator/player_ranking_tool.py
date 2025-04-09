import pandas as pd
import numpy as np
import re
import json


def load_and_combine_fantasy_data(espn_file, sleeper_file, yahoo_file, stats_files):
    """
    Load and combine fantasy football data from ESPN, Sleeper, Yahoo, and 2023 stats.

    Parameters:
    -----------
    espn_file : str
        Path to the ESPN rankings CSV file
    sleeper_file : str
        Path to the Sleeper rankings CSV file
    yahoo_file : str
        Path to the Yahoo rankings CSV file
    stats_files : dict
        Dictionary with position as keys and paths to stats CSV files as values

    Returns:
    --------
    str
        JSON string containing combined data with all players, their average ADP, and 2023 stats
    """
    # Load the ADP CSV files
    espn_df = pd.read_csv(espn_file)
    sleeper_df = pd.read_csv(sleeper_file)
    yahoo_df = pd.read_csv(yahoo_file)

    # Clean up the dataframes - remove unnamed columns if present
    cols_to_drop = [col for col in espn_df.columns if 'Unnamed' in col or col == '']
    espn_df = espn_df.drop(columns=cols_to_drop, errors='ignore')

    cols_to_drop = [col for col in sleeper_df.columns if 'Unnamed' in col or col == '']
    sleeper_df = sleeper_df.drop(columns=cols_to_drop, errors='ignore')

    cols_to_drop = [col for col in yahoo_df.columns if 'Unnamed' in col or col == '']
    yahoo_df = yahoo_df.drop(columns=cols_to_drop, errors='ignore')

    # Create new dataframes with standardized columns for merging
    espn_slim = espn_df[['Name', 'Team', 'BYE', 'Pos', 'ADP', 'FantasyPros']].copy()
    espn_slim['ESPN_Rank'] = espn_df['ESPN']

    sleeper_slim = sleeper_df[['Name', 'Team', 'BYE', 'Pos', 'ADP', 'FantasyPros']].copy()
    sleeper_slim['Sleeper_Rank'] = sleeper_df['SleeperRank']

    yahoo_slim = yahoo_df[['Name', 'Team', 'BYE', 'Pos', 'ADP', 'FantasyPros']].copy()
    yahoo_slim['Yahoo_Rank'] = yahoo_df['YahooXRank']

    # Merge the dataframes using outer join to include all players
    # First merge ESPN and Sleeper
    merged_df = pd.merge(
        espn_slim,
        sleeper_slim,
        on=['Name', 'Team', 'Pos'],
        how='outer',
        suffixes=('_ESPN', '_Sleeper')
    )

    # Then merge with Yahoo
    final_df = pd.merge(
        merged_df,
        yahoo_slim,
        on=['Name', 'Team', 'Pos'],
        how='outer',
        suffixes=('', '_Yahoo')
    )

    # Clean up BYE weeks (use ESPN's if available, otherwise use Sleeper's, then Yahoo's)
    final_df['BYE'] = final_df['BYE_ESPN'].fillna(final_df['BYE_Sleeper']).fillna(final_df['BYE'])

    # Clean up ADP and FantasyPros (same approach)
    final_df['ADP'] = final_df['ADP_ESPN'].fillna(final_df['ADP_Sleeper']).fillna(final_df['ADP'])
    final_df['FantasyPros'] = final_df['FantasyPros_ESPN'].fillna(final_df['FantasyPros_Sleeper']).fillna(
        final_df['FantasyPros'])

    # Drop redundant columns
    cols_to_drop = ['BYE_ESPN', 'BYE_Sleeper', 'ADP_ESPN', 'ADP_Sleeper', 'FantasyPros_ESPN', 'FantasyPros_Sleeper']
    final_df = final_df.drop(columns=cols_to_drop, errors='ignore')

    # Calculate average rank across platforms
    final_df['Avg_Rank'] = final_df[['ESPN_Rank', 'Sleeper_Rank', 'Yahoo_Rank']].mean(axis=1, skipna=True).round(1)

    # Sort by average rank
    final_df = final_df.sort_values('Avg_Rank')

    # Add overall rank column
    final_df.insert(0, 'Overall_Rank', range(1, len(final_df) + 1))

    # Load and process each position's stats dataframes
    stats_dfs = {}
    position_ranks = {}  # Dictionary to store position ranks from 2023

    for pos, file_path in stats_files.items():
        if file_path:
            try:
                df = pd.read_csv(file_path)

                # Clean up column names
                df.columns = [col.strip() for col in df.columns]

                # Store positional ranks before processing
                if 'Rank' in df.columns and 'Player' in df.columns:
                    rank_map = dict(zip(df['Player'], df['Rank']))
                    position_ranks[pos] = rank_map

                # Process specific to position
                if pos in ['QB', 'RB', 'WR', 'TE']:
                    # Standardize column names
                    df = df.rename(columns={
                        'Player': 'Name',
                        'Fantasy_Points': '2023_Fantasy_Points',
                        'Games_Played': '2023_Games_Played',
                        'Avg_Points': '2023_Avg_Points',
                        'Rank': '2023_Pos_Rank'  # Rename the rank column
                    })

                    # Fix the Team/Position swap if needed (noticed in sample data)
                    if df.iloc[0]['Team'] in ['QB', 'RB', 'WR', 'TE']:
                        temp = df['Team'].copy()
                        df['Team'] = df['Position']
                        df['Position'] = temp

                    # Extract key stats based on position
                    if pos == 'QB':
                        df['2023_Pass_Yds'] = df['Pass_Yds']
                        df['2023_Pass_TD'] = df['Pass_TD']
                        df['2023_Pass_Int'] = df['Pass_Int']
                        df['2023_Rush_Yds'] = df['Rush_Yds']
                        df['2023_Rush_TD'] = df['Rush_TD']
                    elif pos == 'RB':
                        df['2023_Rush_Yds'] = df['Rush_Yds']
                        df['2023_Rush_TD'] = df['Rush_TD']
                        df['2023_Rec'] = df['Rec']
                        df['2023_Rec_Yds'] = df['Rec_Yds']
                        df['2023_Rec_TD'] = df['Rec_TD']
                    elif pos in ['WR', 'TE']:
                        df['2023_Rec'] = df['Rec']
                        df['2023_Rec_Yds'] = df['Rec_Yds']
                        df['2023_Rec_TD'] = df['Rec_TD']

                    # Keep only relevant columns for merging
                    columns_to_keep = ['Name', 'Team', '2023_Fantasy_Points', '2023_Games_Played', '2023_Avg_Points']

                    # Add the rank column if it exists
                    if '2023_Pos_Rank' in df.columns:
                        columns_to_keep.append('2023_Pos_Rank')

                    # Add other 2023 stats columns
                    columns_to_keep.extend([col for col in df.columns if col.startswith('2023_') and col not in
                                            ['2023_Fantasy_Points', '2023_Games_Played', '2023_Avg_Points',
                                             '2023_Pos_Rank']])

                    df = df[columns_to_keep]

                elif pos == 'K':
                    # Rename columns for kickers
                    df = df.rename(columns={
                        'Player': 'Name',
                        'Fantasy_Points': '2023_Fantasy_Points',
                        'GP': '2023_Games_Played',
                        'AVG': '2023_Avg_Points',
                        'PAT_Made': '2023_PAT_Made',
                        'FG_Made_0-19': '2023_FG_Made_0-19',
                        'FG_Made_20-29': '2023_FG_Made_20-29',
                        'FG_Made_30-39': '2023_FG_Made_30-39',
                        'FG_Made_40-49': '2023_FG_Made_40-49',
                        'FG_Made_50+': '2023_FG_Made_50+',
                        'Rank': '2023_Pos_Rank'  # Rename the rank column
                    })

                    # Keep only relevant columns
                    columns_to_keep = ['Name', 'Team', '2023_Fantasy_Points', '2023_Games_Played', '2023_Avg_Points',
                                       '2023_PAT_Made', '2023_FG_Made_0-19', '2023_FG_Made_20-29',
                                       '2023_FG_Made_30-39', '2023_FG_Made_40-49', '2023_FG_Made_50+']

                    # Add the rank column if it exists
                    if '2023_Pos_Rank' in df.columns:
                        columns_to_keep.append('2023_Pos_Rank')

                    df = df[columns_to_keep]

                elif pos == 'DST':
                    # For defense, team is both the identifier and the team
                    df = df.rename(columns={
                        'Fantasy_Points': '2023_Fantasy_Points',
                        'GP': '2023_Games_Played',
                        'AVG': '2023_Avg_Points',
                        'Sack': '2023_Sacks',
                        'Int': '2023_Int',
                        'Fum Rec': '2023_Fum_Rec',
                        'Saf': '2023_Safety',
                        'TD': '2023_TD',
                        'Pts Allow': '2023_Pts_Allow',
                        'Rank': '2023_Pos_Rank'  # Rename the rank column
                    })

                    # Create a Name column for merging
                    df['Name'] = df['Team'] + ' D/ST'

                    # Keep only relevant columns
                    columns_to_keep = ['Name', 'Team', '2023_Fantasy_Points', '2023_Games_Played', '2023_Avg_Points',
                                       '2023_Sacks', '2023_Int', '2023_Fum_Rec', '2023_Safety', '2023_TD',
                                       '2023_Pts_Allow']

                    # Add the rank column if it exists
                    if '2023_Pos_Rank' in df.columns:
                        columns_to_keep.append('2023_Pos_Rank')

                    df = df[columns_to_keep]

                stats_dfs[pos] = df
            except Exception as e:
                print(f"Error processing {pos} stats: {e}")
                stats_dfs[pos] = None

    # Merge stats with ADP data
    final_df_with_stats = final_df.copy()

    # Helper function for matching names with variations
    def standardize_name(name):
        # Remove suffixes like Jr., Sr., II, III
        name = re.sub(r'\s+(Jr\.|Sr\.|II|III|IV)$', '', name)
        # Remove periods and apostrophes
        name = name.replace('.', '').replace("'", '')
        return name.lower().strip()

    # Add standardized name for matching
    final_df_with_stats['std_name'] = final_df_with_stats['Name'].apply(standardize_name)

    # Add 2023 position rank column
    final_df_with_stats['2023_Pos_Rank'] = None

    # Initialize 2023 stats columns that we'll be using later
    final_df_with_stats['2023_Fantasy_Points'] = None
    final_df_with_stats['2023_Games_Played'] = None
    final_df_with_stats['2023_Avg_Points'] = None

    # Process for each position and merge stats
    for pos, stats_df in stats_dfs.items():
        if stats_df is not None:
            # Add standardized name column to stats dataframe
            stats_df['std_name'] = stats_df['Name'].apply(standardize_name)

            # Merge on standardized name and team if possible
            if 'Team' in stats_df.columns:
                # Try to match on team and name first
                stats_df_with_team = stats_df.copy()
                stats_df_with_team['Team'] = stats_df_with_team['Team'].astype(str).str.upper()

                # Create a mapping from standard name to stats row
                name_to_stats = {}
                for _, row in stats_df.iterrows():
                    name_to_stats[row['std_name']] = row

                # Add stats to final dataframe
                for idx, row in final_df_with_stats.iterrows():
                    std_name = row['std_name']

                    # Only apply position-specific stats to matching positions
                    current_pos = row['Pos']
                    if pos == current_pos or (pos == 'DST' and current_pos == 'DST'):
                        # Check if player has stats for 2023
                        if std_name in name_to_stats:
                            stats_row = name_to_stats[std_name]

                            # Add all stats columns
                            for col in stats_df.columns:
                                if col.startswith('2023_'):
                                    final_df_with_stats.at[idx, col] = stats_row[col]

    # Calculate an overall 2023 rank for players with fantasy points
    # Check if the column exists and has any non-null values
    if '2023_Fantasy_Points' in final_df_with_stats.columns and final_df_with_stats[
        '2023_Fantasy_Points'].notna().any():
        players_with_stats = final_df_with_stats[final_df_with_stats['2023_Fantasy_Points'].notna()].copy()
        if not players_with_stats.empty:
            players_with_stats = players_with_stats.sort_values('2023_Fantasy_Points', ascending=False)
            rank_mapping = {name: rank + 1 for rank, name in enumerate(players_with_stats['std_name'])}

            # Apply the overall 2023 rank
            final_df_with_stats['2023_Overall_Rank'] = final_df_with_stats['std_name'].map(rank_mapping)
    else:
        print("Warning: No 2023 fantasy points data found for any players.")

    # Drop the standardized name column
    final_df_with_stats = final_df_with_stats.drop(columns=['std_name'])

    # Clean up the final dataframe columns
    column_order = [
        'Overall_Rank', 'Name', 'Team', 'Pos', 'BYE',
        'ESPN_Rank', 'Sleeper_Rank', 'Yahoo_Rank', 'Avg_Rank',
        'ADP', 'FantasyPros'
    ]

    # Add 2023 rank columns first if they exist
    if '2023_Overall_Rank' in final_df_with_stats.columns:
        column_order.append('2023_Overall_Rank')
    if '2023_Pos_Rank' in final_df_with_stats.columns:
        column_order.append('2023_Pos_Rank')

    # Add all other 2023 stats columns
    stats_columns = [col for col in final_df_with_stats.columns if col.startswith('2023_')
                     and col not in ['2023_Overall_Rank', '2023_Pos_Rank']]
    column_order.extend(stats_columns)

    # Ensure all columns in column_order exist in the dataframe
    column_order = [col for col in column_order if col in final_df_with_stats.columns]

    # Reorder columns
    final_df_with_stats = final_df_with_stats[column_order]

    # Add Year-over-Year Rank Change if we have 2023 Overall Rank
    if '2023_Overall_Rank' in final_df_with_stats.columns:
        final_df_with_stats['Rank_Change'] = final_df_with_stats['2023_Overall_Rank'] - final_df_with_stats[
            'Overall_Rank']
        # Move this column right after the ranks
        cols = final_df_with_stats.columns.tolist()
        rank_change_idx = cols.index('Rank_Change')
        overall_rank_2023_idx = cols.index('2023_Overall_Rank')
        cols.insert(overall_rank_2023_idx + 1, cols.pop(rank_change_idx))
        final_df_with_stats = final_df_with_stats[cols]

    # Convert DataFrame to JSON
    # Use orient="records" to get a list of objects
    json_data = final_df_with_stats.to_json(orient="records", date_format="iso")

    return json_data


def save_combined_data(json_data, output_file):
    """
    Save the combined JSON data to a file.

    Parameters:
    -----------
    json_data : str
        The combined data in JSON format
    output_file : str
        Path where the JSON file will be saved
    """
    # If output_file doesn't end with .json, ensure it has the right extension
    if not output_file.endswith('.json'):
        output_file = output_file.replace('.csv', '.json') if output_file.endswith('.csv') else output_file + '.json'

    # Write the JSON data to the file
    with open(output_file, 'w') as f:
        f.write(json_data)

    print(f"Combined data saved to {output_file}")


def find_players_by_name(df, name_part, case_sensitive=False):
    """
    Find players whose names contain the given string.

    Parameters:
    -----------
    df : pandas.DataFrame or str
        The dataframe containing player data or a JSON string
    name_part : str
        Part of name to search for
    case_sensitive : bool
        Whether to perform case-sensitive search

    Returns:
    --------
    str
        JSON string with matching players
    """
    # Convert JSON to DataFrame if needed
    if isinstance(df, str):
        df = pd.read_json(df, orient="records")

    if case_sensitive:
        results = df[df['Name'].str.contains(name_part)]
    else:
        results = df[df['Name'].str.contains(name_part, case=False)]

    # Convert results to JSON
    return results.to_json(orient="records", date_format="iso")


def find_players_by_position(df, position):
    """
    Find players of a specific position.

    Parameters:
    -----------
    df : pandas.DataFrame or str
        The dataframe containing player data or a JSON string
    position : str
        Position to filter by (e.g., 'QB', 'RB', 'WR', 'TE')

    Returns:
    --------
    str
        JSON string with players of the specified position
    """
    # Convert JSON to DataFrame if needed
    if isinstance(df, str):
        df = pd.read_json(df, orient="records")

    results = df[df['Pos'] == position]

    # Convert results to JSON
    return results.to_json(orient="records", date_format="iso")


def find_players_by_team(df, team):
    """
    Find players from a specific team.

    Parameters:
    -----------
    df : pandas.DataFrame or str
        The dataframe containing player data or a JSON string
    team : str
        Team abbreviation to filter by (e.g., 'SF', 'DAL', 'NYG')

    Returns:
    --------
    str
        JSON string with players from the specified team
    """
    # Convert JSON to DataFrame if needed
    if isinstance(df, str):
        df = pd.read_json(df, orient="records")

    results = df[df['Team'] == team]

    # Convert results to JSON
    return results.to_json(orient="records", date_format="iso")


def find_players_by_rank_range(df, min_rank, max_rank, column='Avg_Rank'):
    """
    Find players within a specific rank range.

    Parameters:
    -----------
    df : pandas.DataFrame or str
        The dataframe containing player data or a JSON string
    min_rank : int
        Minimum rank (inclusive)
    max_rank : int
        Maximum rank (inclusive)
    column : str
        Column to filter ranks by (default: 'Avg_Rank')

    Returns:
    --------
    str
        JSON string with players in the specified rank range
    """
    # Convert JSON to DataFrame if needed
    if isinstance(df, str):
        df = pd.read_json(df, orient="records")

    results = df[(df[column] >= min_rank) & (df[column] <= max_rank)]

    # Convert results to JSON
    return results.to_json(orient="records", date_format="iso")


def find_2023_top_performers(df, position=None, min_games=8, top_n=10):
    """
    Find top performers from 2023 based on fantasy points per game.

    Parameters:
    -----------
    df : pandas.DataFrame or str
        The dataframe containing player data or a JSON string
    position : str, optional
        Position to filter by (e.g., 'QB', 'RB', 'WR', 'TE')
    min_games : int
        Minimum number of games played in 2023 to be considered
    top_n : int
        Number of top performers to return

    Returns:
    --------
    str
        JSON string with top performers
    """
    # Convert JSON to DataFrame if needed
    if isinstance(df, str):
        df = pd.read_json(df, orient="records")

    # Check if 2023 stats columns exist
    if '2023_Fantasy_Points' not in df.columns:
        print("Warning: No 2023 fantasy points data found in dataset.")
        return json.dumps([])

    # Filter players with 2023 stats and minimum games
    df_with_stats = df[df['2023_Fantasy_Points'].notna()]

    if min_games > 0 and '2023_Games_Played' in df.columns:
        df_with_stats = df_with_stats[df_with_stats['2023_Games_Played'] >= min_games]

    # Apply position filter if specified
    if position:
        df_with_stats = df_with_stats[df_with_stats['Pos'] == position]

    # Sort by average points if column exists
    if '2023_Avg_Points' in df.columns and not df_with_stats.empty:
        df_sorted = df_with_stats.sort_values('2023_Avg_Points', ascending=False)
    elif '2023_Fantasy_Points' in df.columns and not df_with_stats.empty:
        df_sorted = df_with_stats.sort_values('2023_Fantasy_Points', ascending=False)
    else:
        df_sorted = df_with_stats

    # Return top N
    results = df_sorted.head(top_n)

    # Convert results to JSON
    return results.to_json(orient="records", date_format="iso")


def get_positional_tiers(df, position, tier_size=12):
    """
    Divide players of a specific position into tiers based on average rank.

    Parameters:
    -----------
    df : pandas.DataFrame or str
        The dataframe containing player data or a JSON string
    position : str
        Position to filter by (e.g., 'QB', 'RB', 'WR', 'TE')
    tier_size : int
        Number of players in each tier

    Returns:
    --------
    dict
        Dictionary with tier names as keys and JSON strings as values
    """
    # Convert JSON to DataFrame if needed
    if isinstance(df, str):
        df = pd.read_json(df, orient="records")

    # Get players at the specified position
    pos_df = df[df['Pos'] == position]
    pos_df = pos_df.sort_values('Avg_Rank')

    tiers = {}
    for i in range(0, len(pos_df), tier_size):
        tier_num = i // tier_size + 1
        end_idx = min(i + tier_size, len(pos_df))
        tier_data = pos_df.iloc[i:end_idx]
        tiers[f'Tier {tier_num}'] = tier_data.to_json(orient="records", date_format="iso")

    # Return a JSON string of the entire tier structure
    return json.dumps(tiers)


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

        # If data is a dictionary (e.g., for tiers)
        elif isinstance(data, dict):
            result = ""
            for key, value in data.items():
                tier_data = json.loads(value)
                if limit and len(tier_data) > limit:
                    tier_data = tier_data[:limit]
                    tier_suffix = f"\n... and {len(json.loads(value)) - limit} more players in this tier"
                else:
                    tier_suffix = ""

                result += f"\n{key}:\n{json.dumps(tier_data, indent=2)}{tier_suffix}\n"
            return result

        return json.dumps(data, indent=2)
    except:
        return "Invalid JSON format or error parsing JSON"


# Example usage
if __name__ == "__main__":
    # File paths
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

    output_file = "tools/data/official_2024_fantasy_rankings/Fantasy_Rankings_with_2023_Stats.json"

    # Load and combine data
    combined_json = load_and_combine_fantasy_data(espn_file, sleeper_file, yahoo_file, stats_files)

    # Save combined data
    save_combined_data(combined_json, output_file)

    # Parse JSON back to dictionary for demonstration
    combined_data = json.loads(combined_json)

    # Display first 10 players in the combined rankings
    print("\nTop 10 Players Overall with 2023 Rankings:")
    top_10_players = combined_data[:10]
    for player in top_10_players:
        rank_change = player.get('Rank_Change', 'N/A')
        print(
            f"{player['Overall_Rank']}. {player['Name']} ({player['Team']}, {player['Pos']}) - Avg Rank: {player['Avg_Rank']}, 2023 Rank: {player.get('2023_Overall_Rank', 'N/A')}, Change: {rank_change}")

    # Example of finding top performers from 2023
    print("\nTop 10 Fantasy Performers from 2023 (all positions):")
    top_performers_json = find_2023_top_performers(combined_json, top_n=10)
    top_performers = json.loads(top_performers_json)

    if top_performers:
        for player in top_performers:
            print(
                f"{player['Name']} ({player['Team']}, {player['Pos']}) - 2023 Points: {player.get('2023_Fantasy_Points', 'N/A')}, Avg: {player.get('2023_Avg_Points', 'N/A')}")
    else:
        print("No 2023 fantasy performers found.")
