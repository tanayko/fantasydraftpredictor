import pandas as pd
import numpy as np
import re


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
    pandas.DataFrame
        Combined dataframe with all players, their average ADP, and 2023 stats
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
    players_with_stats = final_df_with_stats[final_df_with_stats['2023_Fantasy_Points'].notna()].copy()
    if not players_with_stats.empty:
        players_with_stats = players_with_stats.sort_values('2023_Fantasy_Points', ascending=False)
        rank_mapping = {name: rank + 1 for rank, name in enumerate(players_with_stats['std_name'])}

        # Apply the overall 2023 rank
        final_df_with_stats['2023_Overall_Rank'] = final_df_with_stats['std_name'].map(rank_mapping)

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

    return final_df_with_stats


def save_combined_data(df, output_file):
    """
    Save the combined dataframe to a CSV file.

    Parameters:
    -----------
    df : pandas.DataFrame
        The combined dataframe to save
    output_file : str
        Path where the CSV file will be saved
    """
    df.to_csv(output_file, index=False)
    print(f"Combined data saved to {output_file}")


def find_players_by_name(df, name_part, case_sensitive=False):
    """
    Find players whose names contain the given string.

    Parameters:
    -----------
    df : pandas.DataFrame
        The dataframe containing player data
    name_part : str
        Part of name to search for
    case_sensitive : bool
        Whether to perform case-sensitive search

    Returns:
    --------
    pandas.DataFrame
        Filtered dataframe with matching players
    """
    if case_sensitive:
        return df[df['Name'].str.contains(name_part)]
    else:
        return df[df['Name'].str.contains(name_part, case=False)]


def find_players_by_position(df, position):
    """
    Find players of a specific position.

    Parameters:
    -----------
    df : pandas.DataFrame
        The dataframe containing player data
    position : str
        Position to filter by (e.g., 'QB', 'RB', 'WR', 'TE')

    Returns:
    --------
    pandas.DataFrame
        Filtered dataframe with players of the specified position
    """
    return df[df['Pos'] == position]


def find_players_by_team(df, team):
    """
    Find players from a specific team.

    Parameters:
    -----------
    df : pandas.DataFrame
        The dataframe containing player data
    team : str
        Team abbreviation to filter by (e.g., 'SF', 'DAL', 'NYG')

    Returns:
    --------
    pandas.DataFrame
        Filtered dataframe with players from the specified team
    """
    return df[df['Team'] == team]


def find_players_by_rank_range(df, min_rank, max_rank, column='Avg_Rank'):
    """
    Find players within a specific rank range.

    Parameters:
    -----------
    df : pandas.DataFrame
        The dataframe containing player data
    min_rank : int
        Minimum rank (inclusive)
    max_rank : int
        Maximum rank (inclusive)
    column : str
        Column to filter ranks by (default: 'Avg_Rank')

    Returns:
    --------
    pandas.DataFrame
        Filtered dataframe with players in the specified rank range
    """
    return df[(df[column] >= min_rank) & (df[column] <= max_rank)]


def find_2023_top_performers(df, position=None, min_games=8, top_n=10):
    """
    Find top performers from 2023 based on fantasy points per game.

    Parameters:
    -----------
    df : pandas.DataFrame
        The dataframe containing player data
    position : str, optional
        Position to filter by (e.g., 'QB', 'RB', 'WR', 'TE')
    min_games : int
        Minimum number of games played in 2023 to be considered
    top_n : int
        Number of top performers to return

    Returns:
    --------
    pandas.DataFrame
        Filtered dataframe with top performers
    """
    # Filter players with 2023 stats and minimum games
    df_with_stats = df[df['2023_Fantasy_Points'].notna()]

    if min_games > 0:
        df_with_stats = df_with_stats[df_with_stats['2023_Games_Played'] >= min_games]

    # Apply position filter if specified
    if position:
        df_with_stats = df_with_stats[df_with_stats['Pos'] == position]

    # Sort by average points
    df_sorted = df_with_stats.sort_values('2023_Avg_Points', ascending=False)

    # Return top N
    return df_sorted.head(top_n)


def find_biggest_risers(df, min_rank_2023=None, max_rank_2024=None, min_change=10):
    """
    Find players who have risen the most in rankings from 2023 to 2024.

    Parameters:
    -----------
    df : pandas.DataFrame
        The dataframe containing player data
    min_rank_2023 : int, optional
        Minimum 2023 rank to consider (to filter out unknowns who rose from very low ranks)
    max_rank_2024 : int, optional
        Maximum 2024 rank to consider (to focus on fantasy-relevant players)
    min_change : int
        Minimum rank improvement to be considered a significant riser

    Returns:
    --------
    pandas.DataFrame
        Filtered dataframe with players who have risen in rank
    """
    # Filter players with both 2023 and 2024 ranks
    df_with_ranks = df[df['2023_Overall_Rank'].notna()].copy()

    # Apply filters
    if min_rank_2023 is not None:
        df_with_ranks = df_with_ranks[df_with_ranks['2023_Overall_Rank'] <= min_rank_2023]

    if max_rank_2024 is not None:
        df_with_ranks = df_with_ranks[df_with_ranks['Overall_Rank'] <= max_rank_2024]

    # Filter by minimum change (positive numbers indicate improvement in rank)
    df_with_ranks = df_with_ranks[df_with_ranks['Rank_Change'] >= min_change]

    # Sort by rank change (largest improvement first)
    return df_with_ranks.sort_values('Rank_Change', ascending=False)


def find_biggest_fallers(df, min_rank_2024=None, max_rank_2023=None, min_change=10):
    """
    Find players who have fallen the most in rankings from 2023 to 2024.

    Parameters:
    -----------
    df : pandas.DataFrame
        The dataframe containing player data
    min_rank_2024 : int, optional
        Minimum 2024 rank to consider (to filter out players who fell out of relevance)
    max_rank_2023 : int, optional
        Maximum 2023 rank to consider (to focus on previously fantasy-relevant players)
    min_change : int
        Minimum rank decrease to be considered a significant faller

    Returns:
    --------
    pandas.DataFrame
        Filtered dataframe with players who have fallen in rank
    """
    # Filter players with both 2023 and 2024 ranks
    df_with_ranks = df[df['2023_Overall_Rank'].notna()].copy()

    # Apply filters
    if min_rank_2024 is not None:
        df_with_ranks = df_with_ranks[df_with_ranks['Overall_Rank'] >= min_rank_2024]

    if max_rank_2023 is not None:
        df_with_ranks = df_with_ranks[df_with_ranks['2023_Overall_Rank'] <= max_rank_2023]

    # Filter by minimum change (negative numbers indicate decrease in rank)
    df_with_ranks = df_with_ranks[df_with_ranks['Rank_Change'] <= -min_change]

    # Sort by rank change (largest decrease first)
    return df_with_ranks.sort_values('Rank_Change')


def get_positional_tiers(df, position, tier_size=12):
    """
    Divide players of a specific position into tiers based on average rank.

    Parameters:
    -----------
    df : pandas.DataFrame
        The dataframe containing player data
    position : str
        Position to filter by (e.g., 'QB', 'RB', 'WR', 'TE')
    tier_size : int
        Number of players in each tier

    Returns:
    --------
    dict of pandas.DataFrame
        Dictionary of dataframes, one for each tier
    """
    pos_df = find_players_by_position(df, position)
    pos_df = pos_df.sort_values('Avg_Rank')

    tiers = {}
    for i in range(0, len(pos_df), tier_size):
        tier_num = i // tier_size + 1
        end_idx = min(i + tier_size, len(pos_df))
        tiers[f'Tier {tier_num}'] = pos_df.iloc[i:end_idx]

    return tiers


# Example usage
if __name__ == "__main__":
    # File paths
    espn_file = "data/official_2024_fantasy_rankings/ESPN_Standard.csv"
    sleeper_file = "data/official_2024_fantasy_rankings/Sleeper_Standard.csv"
    yahoo_file = "data/official_2024_fantasy_rankings/Yahoo_Standard.csv"

    # Define position stats files
    stats_files = {
        'QB': "data/player_ranking_position_data/nfl_fantasy_QB_stats_2023.csv",
        'RB': "data/player_ranking_position_data/nfl_fantasy_RB_stats_2023.csv",
        'WR': "data/player_ranking_position_data/nfl_fantasy_WR_stats_2023.csv",
        'TE': "data/player_ranking_position_data/nfl_fantasy_TE_stats_2023.csv",
        'K': "data/player_ranking_position_data/nfl_fantasy_kickers.csv",
        'DST': "data/player_ranking_position_data/nfl_fantasy_defense.csv"
    }

    output_file = "Fantasy_Rankings_with_2023_Stats.csv"

    # Load and combine data
    combined_df = load_and_combine_fantasy_data(espn_file, sleeper_file, yahoo_file, stats_files)

    # Save combined data
    save_combined_data(combined_df, output_file)

    # Display first 10 players in the combined rankings
    print("\nTop 10 Players Overall with 2023 Rankings:")
    print(
        combined_df[['Overall_Rank', 'Name', 'Team', 'Pos', 'Avg_Rank', '2023_Overall_Rank', '2023_Pos_Rank',
                     'Rank_Change']].head(10))

    # Example of finding top performers from 2023
    print("\nTop 10 Fantasy Performers from 2023 (all positions):")
    top_performers = find_2023_top_performers(combined_df, top_n=10)
    print(top_performers[
              ['Name', 'Team', 'Pos', 'Avg_Rank', '2023_Overall_Rank', '2023_Fantasy_Points', '2023_Avg_Points']])

    # Position-specific 2023 top performers
    print("\nTop 5 QB Performers from 2023:")
    top_qbs = find_2023_top_performers(combined_df, position='QB', top_n=5)
    print(
        top_qbs[['Name', 'Team', 'Avg_Rank', '2023_Pos_Rank', '2023_Fantasy_Points', '2023_Pass_Yds', '2023_Pass_TD',
                 '2023_Rush_Yds']])

    print("\nTop 5 RB Performers from 2023:")
    top_rbs = find_2023_top_performers(combined_df, position='RB', top_n=5)
    print(top_rbs[['Name', 'Team', 'Avg_Rank', '2023_Pos_Rank', '2023_Fantasy_Points', '2023_Rush_Yds', '2023_Rush_TD',
                   '2023_Rec_Yds']])

    print("\nTop 5 WR Performers from 2023:")
    top_wrs = find_2023_top_performers(combined_df, position='WR', top_n=5)
    print(top_wrs[['Name', 'Team', 'Avg_Rank', '2023_Pos_Rank', '2023_Fantasy_Points', '2023_Rec', '2023_Rec_Yds',
                   '2023_Rec_TD']])

    print("\nTop 5 TE Performers from 2023:")
    top_tes = find_2023_top_performers(combined_df, position='TE', top_n=5)
    print(top_tes[['Name', 'Team', 'Avg_Rank', '2023_Pos_Rank', '2023_Fantasy_Points', '2023_Rec', '2023_Rec_Yds',
                   '2023_Rec_TD']])

    # Find biggest risers and fallers
    print("\nBiggest Risers from 2023 to 2024:")
    risers = find_biggest_risers(combined_df, min_rank_2023=100, max_rank_2024=50)
    print(risers[['Name', 'Team', 'Pos', 'Overall_Rank', '2023_Overall_Rank', 'Rank_Change']].head(10))

    print("\nBiggest Fallers from 2023 to 2024:")
    fallers = find_biggest_fallers(combined_df, max_rank_2023=50)
    print(fallers[['Name', 'Team', 'Pos', 'Overall_Rank', '2023_Overall_Rank', 'Rank_Change']].head(10))