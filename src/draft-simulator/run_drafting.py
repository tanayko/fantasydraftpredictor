# NOTE: multi-threaded version
import subprocess
from concurrent.futures import ThreadPoolExecutor


def run_script():
    subprocess.run(["python3", "llm_draft_auto_drafting.py"])


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(lambda _: run_script(), range(20))


"""
#NOTE: single threaded version
import subprocess

for _ in range(20):
    subprocess.run(["python3", "llm_draft_auto_drafting.py"])
"""
