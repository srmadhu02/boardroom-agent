# boardroom-agent

Simple ReAct agent
Agent generated with `agents-cli` version `0.5.0`

## Project Structure

```
boardroom-agent/
├── app/         # Core agent code
│   ├── agent.py               # Main agent logic
│   ├── agent_runtime_app.py    # Agent Runtime application logic
│   └── app_utils/             # App utilities and helpers
├── tests/                     # Unit, integration, and load tests
├── GEMINI.md                  # AI-assisted development guide
└── pyproject.toml             # Project dependencies
```

> 💡 **Tip:** Use [Gemini CLI](https://github.com/google-gemini/gemini-cli) for AI-assisted development - project context is pre-configured in `GEMINI.md`.

## Requirements

Before you begin, ensure you have:
- **uv**: Python package manager (used for all dependency management in this project) - [Install](https://docs.astral.sh/uv/getting-started/installation/) ([add packages](https://docs.astral.sh/uv/concepts/dependencies/) with `uv add <package>`)
- **agents-cli**: Agents CLI - Install with `uv tool install google-agents-cli`
- **Google Cloud SDK**: For GCP services - [Install](https://cloud.google.com/sdk/docs/install)


## Quick Start

Install `agents-cli` and its skills if not already installed:

```bash
uvx google-agents-cli setup
```

Install required packages:

```bash
agents-cli install
```

Test the agent with a local web server:

```bash
agents-cli playground
```

You can also use features from the [ADK](https://adk.dev/) CLI with `uv run adk`.

## Commands

| Command              | Description                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------- |
| `agents-cli install` | Install dependencies using uv                                                         |
| `agents-cli playground` | Launch local development environment                                                  |
| `agents-cli lint`    | Run code quality checks                                                               |
| `agents-cli eval`    | Evaluate agent behavior (generate, grade, analyze, and more — see `agents-cli eval --help`) |
| `uv run pytest tests/unit tests/integration` | Run unit and integration tests                                                        |
| `agents-cli deploy`  | Deploy agent to Agent Runtime                                                                |
| `agents-cli publish gemini-enterprise` | Register deployed agent to Gemini Enterprise                    |

## 🛠️ Project Management

| Command | What It Does |
|---------|--------------|
| `agents-cli scaffold enhance` | Add CI/CD pipelines and Terraform infrastructure |
| `agents-cli infra cicd` | One-command setup of entire CI/CD pipeline + infrastructure |
| `agents-cli scaffold upgrade` | Auto-upgrade to latest version while preserving customizations |

---

## Development

Edit your agent logic in `app/agent.py` and test with `agents-cli playground` - it auto-reloads on save.

## Deployment

```bash
gcloud config set project <your-project-id>
agents-cli deploy
```

## Output
<img width="1354" height="658" alt="boardroom1" src="https://github.com/user-attachments/assets/3818779e-1a16-4927-b177-1b471e66bce5" />

<img width="1350" height="543" alt="boardroom2" src="https://github.com/user-attachments/assets/c74108f1-b50a-4641-a503-1476fd3d7dc3" />

<img width="1360" height="684" alt="boardroom3" src="https://github.com/user-attachments/assets/e29f99bf-480c-4549-90a7-cd630fdd2489" />

<img width="1365" height="641" alt="boardroom4" src="https://github.com/user-attachments/assets/a59852a9-4a34-49a9-9c09-48ca3599ccdd" />

<img width="1365" height="674" alt="boardroom5" src="https://github.com/user-attachments/assets/0f1baab7-5ed5-4632-8ab8-24d1968e15c6" />

<img width="1363" height="663" alt="boardroom6" src="https://github.com/user-attachments/assets/fbc11b4b-033a-4488-8f17-ef62752b1e59" />

<img width="1348" height="452" alt="boardroom7" src="https://github.com/user-attachments/assets/1a8d8191-1935-4208-9d41-59bbf20a1574" />

<img width="1348" height="639" alt="boardroom8" src="https://github.com/user-attachments/assets/3e198b71-6cea-409c-ad9c-a0c550cd80ce" />

<img width="1339" height="599" alt="boardroom9" src="https://github.com/user-attachments/assets/404f515b-c566-47fb-b1ba-efafc2baa274" />

<img width="1365" height="628" alt="boardroom10" src="https://github.com/user-attachments/assets/d759e0d7-2ca7-4b8e-82bb-b86a3e3242f0" />

<img width="1365" height="632" alt="boardroom11" src="https://github.com/user-attachments/assets/99ca9c69-674a-483c-adf7-e0426356f5d3" />

<img width="1365" height="654" alt="boardroom12" src="https://github.com/user-attachments/assets/15d24f80-63b0-49b7-8eb6-b2beaf487043" />


To add CI/CD and Terraform, run `agents-cli scaffold enhance`.
To set up your production infrastructure, run `agents-cli infra cicd`.

## Observability

Built-in telemetry exports to Cloud Trace, BigQuery, and Cloud Logging.
