import pandas as pd
import numpy as np


def load_and_combine_fantasy_data(espn_file, sleeper_file, yahoo_file):
    """
    Load and combine fantasy football data from ESPN, Sleeper, and Yahoo.

    Parameters:
    -----------
    espn_file : str
        Path to the ESPN rankings CSV file
    sleeper_file : str
        Path to the Sleeper rankings CSV file
    yahoo_file : str
        Path to the Yahoo rankings CSV file

    Returns:
    --------
    pandas.DataFrame
        Combined dataframe with all players and their average ADP
    """
    espn_df = pd.read_csv(espn_file)
    sleeper_df = pd.read_csv(sleeper_file)
    yahoo_df = pd.read_csv(yahoo_file)

    cols_to_drop = [col for col in espn_df.columns if 'Unnamed' in col or col == '']
    espn_df = espn_df.drop(columns=cols_to_drop, errors='ignore')

    cols_to_drop = [col for col in sleeper_df.columns if 'Unnamed' in col or col == '']
    sleeper_df = sleeper_df.drop(columns=cols_to_drop, errors='ignore')

    cols_to_drop = [col for col in yahoo_df.columns if 'Unnamed' in col or col == '']
    yahoo_df = yahoo_df.drop(columns=cols_to_drop, errors='ignore')

    espn_slim = espn_df[['Name', 'Team', 'BYE', 'Pos', 'ADP', 'FantasyPros']].copy()
    espn_slim['ESPN_Rank'] = espn_df['ESPN']

    sleeper_slim = sleeper_df[['Name', 'Team', 'BYE', 'Pos', 'ADP', 'FantasyPros']].copy()
    sleeper_slim['Sleeper_Rank'] = sleeper_df['SleeperRank']

    yahoo_slim = yahoo_df[['Name', 'Team', 'BYE', 'Pos', 'ADP', 'FantasyPros']].copy()
    yahoo_slim['Yahoo_Rank'] = yahoo_df['YahooXRank']

    merged_df = pd.merge(
        espn_slim,
        sleeper_slim,
        on=['Name', 'Team', 'Pos'],
        how='outer',
        suffixes=('_ESPN', '_Sleeper')
    )

    final_df = pd.merge(
        merged_df,
        yahoo_slim,
        on=['Name', 'Team', 'Pos'],
        how='outer',
        suffixes=('', '_Yahoo')
    )

    final_df['BYE'] = final_df['BYE_ESPN'].fillna(final_df['BYE_Sleeper']).fillna(final_df['BYE'])

    final_df['ADP'] = final_df['ADP_ESPN'].fillna(final_df['ADP_Sleeper']).fillna(final_df['ADP'])
    final_df['FantasyPros'] = final_df['FantasyPros_ESPN'].fillna(final_df['FantasyPros_Sleeper']).fillna(
        final_df['FantasyPros'])

    cols_to_drop = ['BYE_ESPN', 'BYE_Sleeper', 'ADP_ESPN', 'ADP_Sleeper', 'FantasyPros_ESPN', 'FantasyPros_Sleeper']
    final_df = final_df.drop(columns=cols_to_drop, errors='ignore')

    final_df['Avg_Rank'] = final_df[['ESPN_Rank', 'Sleeper_Rank', 'Yahoo_Rank']].mean(axis=1, skipna=True).round(1)

    final_df = final_df.sort_values('Avg_Rank')

    final_df.insert(0, 'Overall_Rank', range(1, len(final_df) + 1))

    final_df = final_df[[
        'Overall_Rank', 'Name', 'Team', 'Pos', 'BYE', 'ESPN_Rank',
        'Sleeper_Rank', 'Yahoo_Rank', 'Avg_Rank', 'ADP', 'FantasyPros'
    ]]

    return final_df


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
    espn_file = "official_2024_fantasy_rankings/ESPN_Standard.csv"
    sleeper_file = "official_2024_fantasy_rankings/Sleeper_Standard.csv"
    yahoo_file = "official_2024_fantasy_rankings/Yahoo_Standard.csv"
    output_file = "official_2024_fantasy_rankings/Combined_Fantasy_Rankings.csv"

    # Load and combine data
    combined_df = load_and_combine_fantasy_data(espn_file, sleeper_file, yahoo_file)

    # Save combined data
    save_combined_data(combined_df, output_file)

    # Display first 10 players in the combined rankings
    print("\nTop 10 Players Overall:")
    print(combined_df.head(10))

    # Example of finding players
    print("\nQuarterbacks in top 50:")
    qbs = find_players_by_position(
        find_players_by_rank_range(combined_df, 1, 50),
        'QB'
    )
    print(qbs)

    print("\nPlayers with 'Jones' in their name:")
    jones_players = find_players_by_name(combined_df, "Jones")
    print(jones_players)

    # Example of getting positional tiers
    rb_tiers = get_positional_tiers(combined_df, 'RB')
    print("\nRB Tier 1:")
    print(rb_tiers['Tier 1'][['Name', 'Team', 'Avg_Rank']])
