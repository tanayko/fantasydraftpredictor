import re


def extract_player_name_from_output(output_text):
    """
    Extract the player name from the head drafter agent's final decision message.

    Args:
        output_text (str): The output text from the group chat conversation

    Returns:
        str: The name of the chosen player, or None if no match is found
    """
    # Try multiple patterns to match different message formats

    # Pattern 1: Looks for "my fantasy football team is **PlayerName**"
    match = re.search(r'my fantasy football team is\s+\*\*(.*?)\*\*(?:\.|,)?\s*TERMINATE', output_text)
    if match:
        player_name = match.group(1)
        return player_name.strip()

    # Pattern 2: Original pattern - "I choose **PlayerName**"
    match = re.search(r'I choose (?:\*\*)?(.*?)(?:\*\*)?\.\s*TERMINATE', output_text)
    if match:
        player_name = match.group(1)
        # Remove any remaining markdown if present
        player_name = re.sub(r'\*\*', '', player_name)
        return player_name.strip()

    # Pattern 3: Most general pattern - looks for bold text right before TERMINATE
    match = re.search(r'\*\*(.*?)\*\*(?:\.|,|\s)*TERMINATE', output_text)
    if match:
        player_name = match.group(1)
        return player_name.strip()

    # Pattern 4: Very flexible - looks for name in final message
    lines = output_text.strip().split('\n')
    for i in range(len(lines) - 1, -1, -1):
        if "TERMINATE" in lines[i]:
            # Check the last few lines before TERMINATE for player names
            for j in range(max(0, i - 5), i + 1):
                # Look for bold text in this line
                bold_match = re.search(r'\*\*(.*?)\*\*', lines[j])
                if bold_match:
                    return bold_match.group(1).strip()

    return None


# Example usage for testing:
if __name__ == "__main__":
    sample_output = """
    chat_manager: Now, I have all the top players:
    - **QB**: Trevor Lawrence
    - **RB**: Najee Harris
    - **WR**: DeVonta Smith
    To summarize:
    - Trevor Lawrence was the best at quarterback.
    - Najee Harris was the best at running back.
    - DeVonta Smith was the best at wide receiver.
    Considering this, I will finalize my pick. The chosen player for my fantasy football team is 
    **Trevor Lawrence**.
    TERMINATE
    """

    player_name = extract_player_name_from_output(sample_output)
    print(f"Extracted player name: {player_name}")