# LLM-powered fantasy drafter

## Relevant Folders & Files
- `src/draft-simulator/llm_draft_auto_drafting.py` - contains the draft simulator and can be run to simulate a draft.
- `src/draft-simulator/drafter_multi_agent.py`- contains the logic and architecture for the llm drafter
- `src/draft-simulator/constrained_logs` - cleaned up version of logs which llm drafter include group chat conversations, selections, and final team 
- `src/draft-simulator/prompts` - prompts for all agents involved including head drafter, position agents (both extractors and analyzers)
- `src/draft-simulator/draft_results` - data and analysis for draft simulations 

### How to run:
To run, create a `.env` folder in `src/draft-simulator` with an environment variable called `OPENAI_API_KEY` with your API key and `BASE_URL` from wherever you can get a hosted gpt-4o-mini.
Next, navigate to `src/draft-simulator`. From there, run `llm_draft_auto_drafting.py` for a single run, or `run_drafting.py` for multiple concurrent runs (can change how many you want at a time).