
## Instructions for running agents related examples

### API key setup

1. Copy `../env.example` to `../.env` if you have not already.
2. Set `GOOGLE_API_KEY` in `src/.env` to a real key from [Google AI Studio](https://aistudio.google.com/apikey) (starts with `AIza`).
3. The placeholder `<your key>` will not work and causes `API_KEY_INVALID`.

### Usage
Run the following commands from the <strong>gemini-adk</strong> folder

#### Run the basic_agent from command line
```bash
uv run agent_runner.py
```

#### Run the agents (basic_agent, agent_doubleword) with adk commands

With adk web command
```bash
adk web agents
```

Run agent_doubleword using adk run command
```bash
adk run agents/agent_doubleword
```

Run agent using adk run command
```bash
adk run agents/basic_agent
```