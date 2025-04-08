import autogen
from autogen import AssistantAgent, UserProxyAgent, register_function
import os

OPENAI_API_KEY = os.getenv("API_KEY")

# --------------------------
# ✅ Mock player metrics
# --------------------------
player_metrics = {
    "Ja'Marr Chase": 3.2,
    "Jaylen Waddle": 9.3,
    "Rashod Bateman": 7.5,
}


# --------------------------
# ✅ Tool function
# --------------------------
def get_player_metric(name: str) -> dict:
    print(f"[✅ TOOL CALLED]: get_player_metric('{name}')")
    return {"name": name, "metric": player_metrics.get(name, None)}


# --------------------------
# ✅ Assistant agent
# --------------------------
assistant = AssistantAgent(
    name="WRSelector",
    system_message=(
        "You are an expert in fantasy football wide receivers. "
        "You must call the `get_player_metric` tool to evaluate players. "
        "Do not guess or use prior knowledge. "
        "Compare metrics returned by the tool and return the best wide receiver.\n\n"
        "include TERMINATE in your response to end the conversation.\n\n"
        "the last thing should be the name of the player you select.\n\n"
    ),
    llm_config={
        "config_list": [
            {
                "model": "gpt-4o",  # Updated to correct OpenAI model
                "api_key": OPENAI_API_KEY,
                "base_url": "https://api.openai.com/v1",
            }
        ],
        "temperature": 0,
    },
)

# --------------------------
# ✅ UserProxyAgent with clean termination
# --------------------------
user_proxy = UserProxyAgent(
    name="User",
    code_execution_config=False,
    llm_config=False,
    human_input_mode="TERMINATE",
    is_termination_msg=lambda msg: (
        msg is not None
        and "content" in msg
        and msg["content"] is not None
        and "TERMINATE" in msg["content"]
    ),
)

# --------------------------
# ✅ Ensure the tool is registered only once
register_function(
    get_player_metric,
    caller=assistant,
    executor=user_proxy,
    name="get_player_metric",
    description="Returns the metric for a given player",
)

# --------------------------
# ✅ Run chat
# --------------------------
if __name__ == "__main__":
    user_proxy.initiate_chat(
        assistant,
        message="""
Here are the wide receivers available for drafting:
- Ja'Marr Chase
- Jaylen Waddle
- Rashod Bateman

You have next draft pick.
""",
        max_consecutive_auto_reply=5,
    )
