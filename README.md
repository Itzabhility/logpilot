# logpilot
A personal AI log agent that syncs work and life tasks into Notion, tracks time, and stores backup logs for GitHub-based contribution tracking. Powered by Python, OpenAI, and Notion API.

############################

# LogPilot 🧠📘  
*Your personal AI-powered life and work log agent.*

LogPilot helps you effortlessly log work and personal activities using natural language — all through ChatGPT or CLI. It auto-structures your logs, stores them in Notion, and saves backups locally to track your productivity via GitHub's contribution graph.

---

## 🚀 Features

- ✍️ Log anything via plain text or ChatGPT
- 🧠 NLP-powered parsing and task classification
- 🗃️ Structured storage in Notion (via Notion API)
- 🕓 Tracks estimated vs actual task durations
- 🔁 Consolidates scattered updates under one task
- 🧑‍💻 Local Markdown backups for GitHub version control
- 📊 Future: Streamlit dashboard with time tracking and Kanban view

---

## 🛠️ Tech Stack

| Layer         | Tools/Tech |
|---------------|------------|
| AI Interface  | OpenAI GPT-4 / ChatGPT |
| Logging Logic | Python + NLP |
| Storage       | Notion API, Markdown, GitHub |
| Dashboard     | (Optional) Streamlit or React (WIP) |

---

## 📁 Directory Structure

logpilot/

├── notion_logger.py       # Pushes logs to Notion

├── log_parser.py          # Parses raw input into structured fields

├── logs/                  # Markdown backups (for GitHub tracking)

├── .env.example           # API key placeholder

├── requirements.txt       # Dependencies

└── README.md              # You’re reading it

