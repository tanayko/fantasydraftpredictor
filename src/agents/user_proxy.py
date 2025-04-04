# Create a UserProxyAgent without Docker
from autogen import UserProxyAgent



def prompt_agent(agent, message, human_input_mode="ALWAYS"):
    """
    Have a chat with the agent.
    
    Args:
        agent: The agent to chat with
        message: The message to send to the agent
        human_input_mode: The input mode for the agent (default is "ALWAYS")
    """

    user_proxy = UserProxyAgent(
        name="User",
        human_input_mode=human_input_mode,
        max_consecutive_auto_reply=10,
        code_execution_config={
            "work_dir": "workspace",
            "use_docker": False  # Explicitly disable Docker
        }
    )

    user_proxy.initiate_chat(agent, message=message)
