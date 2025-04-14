import pandas as pd

ttl_csv_path = "./tools/data/FantasyPros_Fantasy_Football_Points_PPR.csv"  # 🔁 Replace with actual path
ttl_df = pd.read_csv(ttl_csv_path)

print(ttl_df["Player"])
ttl_df = ttl_df.dropna(axis=1, how="all")
