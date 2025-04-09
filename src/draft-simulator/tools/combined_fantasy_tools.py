import json
from player_ranking_tool import load_and_combine_fantasy_data
from team_ranking_tool import analyze_team_offenses, add_offense_context_to_rankings, json_to_readable
from defense_ranking_tool import analyze_defense_vs_position, categorize_defenses, add_defense_matchup_to_players
from nfl_schedule import create_nfl_schedule

# File paths for player rankings
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

# Files for team offense stats
offense_files_dict = {
    2021: "data/offensive_rtg_data/nfl_team_offense_stats_2021.csv",
    2022: "data/offensive_rtg_data/nfl_team_offense_stats_2022.csv",
    2023: "data/offensive_rtg_data/nfl_team_offense_stats_2023.csv"
}

# Files for defense vs position data
defense_files = {
    'QB': "data/pts-against-data/qb/nfl_fantasy_qb_data_2024.csv",
    'RB': "data/pts-against-data/rb/nfl_fantasy_rb_data_2024.csv",
    'WR': "data/pts-against-data/wr/nfl_fantasy_wr_data_2024.csv",
    'TE': "data/pts-against-data/te/nfl_fantasy_te_data_2024.csv",
    'K': "data/pts-against-data/k/nfl_fantasy_k_data_2024.csv",
    'DEF': "data/pts-against-data/def/nfl_fantasy_def_data_2024.csv"
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


def find_player_stats(name):
    """Find and display a player's stats including schedule difficulty"""
    players = json.loads(final_player_json)
    player = None

    for p in players:
        if name.lower() in p.get("Name", "").lower():
            player = p
            break

    if player:
        print(f"\nStats for {player['Name']}:")
        print(f"Position: {player['Pos']}")
        print(f"Team: {player['Team']}")
        print(f"Overall Rank: {player['Overall_Rank']}")

        # Show schedule difficulty data if available
        if 'Schedule_Difficulty_Score' in player:
            print(f"Schedule Difficulty Score: {player['Schedule_Difficulty_Score']}")
        if 'Schedule_Rating' in player:
            print(f"Schedule Rating: {player['Schedule_Rating']}")

        # Return the full player data
        return player
    else:
        print(f"Player '{name}' not found.")
        return None


# Example usage
player_data = find_player_stats("Garrett Wilson")

# Optionally, print the complete player data as JSON
if player_data:
    print("\nComplete player data:")
    print(json.dumps(player_data, indent=2))