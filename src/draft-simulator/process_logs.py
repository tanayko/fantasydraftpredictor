import os
import re
import pandas as pd
from pprint import pprint


def extract_data_from_log(log_text):
    # Extract Roster
    roster_pattern = r"AI_General_Manager Current Roster:\n[-]+\n(.*?)\n[-]+"
    roster_section = re.search(roster_pattern, log_text, re.DOTALL)

    roster_data = []
    if roster_section:
        lines = roster_section.group(1).strip().split("\n")
        current_pos = None
        for line in lines:
            if line.strip().endswith(":"):
                current_pos = line.strip().replace(":", "")
            elif re.match(r"\s*\d+\.\s+.+", line) and current_pos:
                player = re.sub(r"^\s*\d+\.\s+", "", line).split("(")[0].strip()
                roster_data.append({"Position": current_pos, "Player": player})

    # Extract Rankings
    rankings_pattern = r"TEAM RANKINGS BY FANTASY POINTS:\n[-]+\n.*?\n[-]+\n(.*?)$"
    rankings_section = re.search(rankings_pattern, log_text, re.DOTALL)

    rankings_data = []
    if rankings_section:
        lines = rankings_section.group(1).strip().split("\n")
        for line in lines:
            match = re.match(r"(\d+)\s+(.*?)\s{2,}([\d.]+)", line)
            if match:
                rank = int(match.group(1))
                team = match.group(2).strip()
                points = float(match.group(3))
                rankings_data.append({"Rank": rank, "Team": team, "Points": points})

    return roster_data, rankings_data


def extract_suffix(filename):
    # Extracts everything between the last underscore and `.log`
    match = re.search(r"_([a-zA-Z0-9]+)\.log$", filename)
    return match.group(1) if match else "0000"


def process_logs(folder_path, output_dir="draft_results"):
    os.makedirs(output_dir, exist_ok=True)

    for filename in os.listdir(folder_path):
        if filename.endswith(".log"):
            with open(os.path.join(folder_path, filename), "r") as f:
                content = f.read()
                roster, rankings = extract_data_from_log(content)

                print(f"\n=== From {filename} ===")
                print("Roster:")
                pprint(roster)
                print("Rankings:")
                pprint(rankings)

                suffix = extract_suffix(filename)

                roster_path = os.path.join(output_dir, f"rosters_{suffix}.csv")
                ranking_path = os.path.join(output_dir, f"rankings_{suffix}.csv")

                pd.DataFrame(roster).to_csv(roster_path, index=False)
                pd.DataFrame(rankings).to_csv(ranking_path, index=False)

                print(f"✅ Saved {roster_path} and {ranking_path}")


# Run it
process_logs("constrained_logs")
