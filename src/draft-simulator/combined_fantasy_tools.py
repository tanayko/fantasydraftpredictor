import json
from typing import Dict, List, Optional, Union, Any
from player_ranking_tool import load_and_combine_fantasy_data
from team_ranking_tool import analyze_team_offenses, add_offense_context_to_rankings, json_to_readable
from defense_ranking_tool import analyze_defense_vs_position, categorize_defenses, add_defense_matchup_to_players
from nfl_schedule import create_nfl_schedule

# File paths for player rankings
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

# Files for team offense stats
offense_files_dict = {
    2021: "tools/data/offensive_rtg_data/nfl_team_offense_stats_2021.csv",
    2022: "tools/data/offensive_rtg_data/nfl_team_offense_stats_2022.csv",
    2023: "tools/data/offensive_rtg_data/nfl_team_offense_stats_2023.csv"
}

# Files for defense vs position data
defense_files = {
    'QB': "tools/data/pts-against-data/qb/nfl_fantasy_qb_data_2024.csv",
    'RB': "tools/data/pts-against-data/rb/nfl_fantasy_rb_data_2024.csv",
    'WR': "tools/data/pts-against-data/wr/nfl_fantasy_wr_data_2024.csv",
    'TE': "tools/data/pts-against-data/te/nfl_fantasy_te_data_2024.csv",
    'K': "tools/data/pts-against-data/k/nfl_fantasy_k_data_2024.csv",
    'DEF': "tools/data/pts-against-data/def/nfl_fantasy_def_data_2024.csv"
}

# From player_ranking_tool.py
print("Step 1: Loading and combining player rankings...")
player_json = load_and_combine_fantasy_data(espn_file, sleeper_file, yahoo_file, stats_files)

# From team_ranking_tool.py
print("Step 2: Analyzing team offensive data...")
offense_json = analyze_team_offenses(offense_files_dict)

# Use them together
print("Step 3: Adding offensive context to player rankings...")
enhanced_player_json = add_offense_context_to_rankings(player_json, offense_json)

# Analyze defense vs position data
print("Step 4: Analyzing defense vs position data...")
defense_analysis = analyze_defense_vs_position(defense_files)
categorized_defenses = categorize_defenses(defense_analysis)

# Get NFL schedule
print("Step 5: Loading NFL schedule...")
nfl_schedule = create_nfl_schedule()

# Add schedule difficulty to enhanced player data
print("Step 6: Adding schedule difficulty to player rankings...")
final_player_json = add_defense_matchup_to_players(enhanced_player_json, categorized_defenses, nfl_schedule)

# Save the final result
with open("final_rankings_with_schedule.json", "w") as f:
    f.write(final_player_json)
print("Final rankings saved to final_rankings_with_schedule.json")


def find_player_stats(name: str, return_json: bool = True) -> Union[Dict[str, Any], str, None]:
    """
    Find and display a player's stats including schedule difficulty

    Args:
        name (str): Player name to search for
        return_json (bool): If True, returns player data as JSON string. Defaults to True.

    Returns:
        Union[Dict[str, Any], str, None]: Player data dictionary, JSON string if return_json=True, or None if not found
    """
    players = json.loads(final_player_json)
    player = None

    for p in players:
        if name.lower() in p.get("Name", "").lower():
            player = p
            break

    if player:
        if not return_json:
            print(f"\nStats for {player['Name']}:")
            print(f"Position: {player['Pos']}")
            print(f"Team: {player['Team']}")
            print(f"Overall Rank: {player['Overall_Rank']}")

            # Show schedule difficulty data if available
            if 'Schedule_Difficulty_Score' in player:
                print(f"Schedule Difficulty Score: {player['Schedule_Difficulty_Score']}")
            if 'Schedule_Rating' in player:
                print(f"Schedule Rating: {player['Schedule_Rating']}")

        # Return the full player data (as dict or JSON string)
        return json.dumps(player) if return_json else player
    else:
        print(f"Player '{name}' not found.")
        result = {"error": f"Player '{name}' not found."}
        return json.dumps(result) if return_json else None


def get_players_by_position(position: str, limit: Optional[int] = None,
                           sort_by: str = "Overall_Rank",
                           return_json: bool = True) -> Union[List[Dict[str, Any]], str]:
    """
    Return a list of players filtered by position.

    Args:
        position (str): Position to filter by (QB, RB, WR, TE, K, DST)
        limit (Optional[int], optional): Limit the number of results. Defaults to None (all players).
        sort_by (str, optional): Field to sort by. Defaults to "Overall_Rank".
        return_json (bool): If True, returns data as JSON string. Defaults to True.

    Returns:
        Union[List[Dict[str, Any]], str]: List of player dictionaries matching the position, or JSON string if return_json=True
    """
    players = json.loads(final_player_json)
    position = position.upper()  # Normalize input to uppercase

    # Filter players by position
    position_players = [p for p in players if p.get("Pos", "").upper() == position]

    # Sort players by the specified field
    try:
        position_players.sort(key=lambda x: float(x.get(sort_by, 999)) if x.get(sort_by) is not None else 999)
    except (ValueError, TypeError):
        # Fall back to string comparison if numerical sort fails
        position_players.sort(key=lambda x: str(x.get(sort_by, "")))

    # Apply limit if specified
    if limit and isinstance(limit, int) and limit > 0:
        position_players = position_players[:limit]

    # Return as JSON string or list of dictionaries
    return json.dumps(position_players) if return_json else position_players


def display_position_rankings(position: str, limit: int = 10,
                             sort_by: str = "Overall_Rank",
                             return_json: bool = True) -> Union[List[Dict[str, Any]], str, None]:
    """
    Display player rankings for a specific position.

    Args:
        position (str): Position to filter by (QB, RB, WR, TE, K, DST)
        limit (int, optional): Limit the number of results. Defaults to 10.
        sort_by (str, optional): Field to sort by. Defaults to "Overall_Rank".
        return_json (bool): If True, returns data as JSON string. Defaults to True.

    Returns:
        Union[List[Dict[str, Any]], str, None]: List of player dictionaries, JSON string if return_json=True, or None if error
    """
    players = get_players_by_position(position, limit, sort_by, return_json=False)

    if not players:
        error_msg = f"No players found for position: {position.upper()}"
        print(error_msg)

        if return_json:
            return json.dumps({"error": error_msg})
        return None

    if not return_json:
        print(f"\nTop {len(players)} {position.upper()} Rankings (sorted by {sort_by}):")
        print("-" * 60)

        # Print header
        print(f"{'Rank':<5} {'Name':<25} {'Team':<5} {'Schedule':<10}")
        print("-" * 60)

        # Print each player
        for i, player in enumerate(players, 1):
            name = player.get("Name", "Unknown")
            team = player.get("Team", "N/A")
            schedule_rating = player.get("Schedule_Rating", "N/A")

            print(f"{i:<5} {name:<25} {team:<5} {schedule_rating:<10}")

    # Format data for better JSON response
    if return_json:
        return json.dumps({
            "position": position.upper(),
            "sort_by": sort_by,
            "count": len(players),
            "players": players
        })

    return players


def display_position_rankings_with_filtering(position: str, limit: int = 10,
                                             excluded_players: List[str] = None,
                                             sort_by: str = "Overall_Rank",
                                             return_json: bool = True) -> Union[List[Dict[str, Any]], str, None]:
    """
    Display player rankings for a specific position, excluding certain players (e.g., already drafted).

    Args:
        position (str): Position to filter by (QB, RB, WR, TE, K, DST)
        limit (int, optional): Limit the number of results. Defaults to 10.
        excluded_players (List[str], optional): List of player names to exclude. Defaults to None.
        sort_by (str, optional): Field to sort by. Defaults to "Overall_Rank".
        return_json (bool): If True, returns data as JSON string. Defaults to True.

    Returns:
        Union[List[Dict[str, Any]], str, None]: List of player dictionaries, JSON string if return_json=True, or None if error
    """
    # Get players by position
    players = get_players_by_position(position, None, sort_by, return_json=False)

    if not players:
        error_msg = f"No players found for position: {position.upper()}"
        print(error_msg)

        if return_json:
            return json.dumps({"error": error_msg})
        return None

    # Apply exclusion filter if provided
    if excluded_players and isinstance(excluded_players, list):
        # Convert excluded names to lowercase for case-insensitive matching
        excluded_lower = [name.lower() for name in excluded_players]

        # Filter out excluded players
        filtered_players = [
            player for player in players
            if player.get("Name", "").lower() not in excluded_lower
        ]

        # If all players were filtered out, return an empty result
        if not filtered_players:
            message = f"All {position.upper()} players were excluded by filter"
            print(message)

            if return_json:
                return json.dumps({
                    "position": position.upper(),
                    "sort_by": sort_by,
                    "count": 0,
                    "excluded_count": len(players),
                    "players": []
                })
            return []

        players = filtered_players

    # Apply limit after filtering
    if limit and isinstance(limit, int) and limit > 0:
        players = players[:limit]

    if not return_json:
        print(f"\nTop {len(players)} {position.upper()} Rankings (sorted by {sort_by}):")
        print("-" * 60)

        # Print header
        print(f"{'Rank':<5} {'Name':<25} {'Team':<5} {'Schedule':<10}")
        print("-" * 60)

        # Print each player
        for i, player in enumerate(players, 1):
            name = player.get("Name", "Unknown")
            team = player.get("Team", "N/A")
            schedule_rating = player.get("Schedule_Rating", "N/A")

            print(f"{i:<5} {name:<25} {team:<5} {schedule_rating:<10}")

    # Format data for better JSON response
    if return_json:
        return json.dumps({
            "position": position.upper(),
            "sort_by": sort_by,
            "count": len(players),
            "filtered": True if excluded_players else False,
            "excluded_count": len(excluded_players) if excluded_players else 0,
            "players": players
        })

    return players

# Example usage
if __name__ == "__main__":
    # Example: find a specific player and return as JSON
    player_json = find_player_stats("Garrett Wilson", return_json=True)
    print("\nPlayer data as JSON:")
    print(player_json)

    # Example: get top 5 QBs as JSON
    qbs_json = display_position_rankings("QB", limit=5, return_json=True)
    print("\nTop 5 QBs as JSON:")
    print(qbs_json)