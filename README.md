# SysSentinel: B2B IT Alert Resolution Orchestrator

**SysSentinel** is an automated, multi-agent IT Incident Resolution Orchestrator built for the **Google Cloud Rapid Agent Hackathon (Track 1: Build - Net-New Agents)**. It dynamically triages incoming alerts, searches historical incident documentation (RAG), runs diagnostics on remote servers using custom tools, and generates safe patch scripts to resolve incidents.

## 🚀 Key Features

* **Multi-Agent Orchestration:** Composes three specialized agents (Triage, Knowledge Base, and Diagnostic/Patch) to collaborate and resolve complex production alerts.
* **Simulated Diagnostic Tools:** Directly queries server metrics, check connection states, and lists running processes to verify issues in real-time.
* **Smart Fallbacks:** Configured to run out-of-the-box in simulated/mock mode without requiring active Google Cloud billing credentials, while fully supporting live Gemini and ADK configurations.
* **Declarative Resolution:** Recommends targeted, safe patches (e.g. log cleanups, DB session terminations) rather than generic checklists.

---

## 🛠️ Architecture

```
                  [ Incoming Alert / CLI Input ]
                                |
                                v
                       +------------------+
                       |   Triage Agent   | -> Classifies Category, Severity, Target Host
                       +------------------+
                                |
                                v
                       +------------------+
                       |    RAG Agent     | -> Searches historical tickets & past resolutions
                       +------------------+
                                |
                                v
                       +------------------+
                       | Diagnostic Agent | -> Runs local shell diagnostics & compiles patch script
                       +------------------+
                                |
                                v
                  [ Final Incident Report & Patch ]
```

---

## 💻 Setup & Installation

### 1. Prerequisites

Make sure you have **Python 3.10+** and **Git** installed on your system. 

If Python is not installed, install it using:
```bash
# On Windows (via WinGet)
winget install Python.Python.3.11

# On macOS
brew install python@3.11
```

### 2. Clone the Repository & Configure Env

Clone the project and create your environment configuration:

```bash
cd WEB.GOOGLE.Hackaton
python -m venv venv
# On Windows
.\venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. API Credentials (Optional)

Create a `.env` file in the project root to utilize the live Gemini models:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```
*Note: If no API key is specified, SysSentinel will gracefully execute in simulated mock mode for zero-cost evaluation.*

---

## 🏃 Run Instructions

### Process an Alert (Default)
Run the script to process the default database timeout incident:
```bash
python app/main.py
```

### Process a Custom Alert
Analyze a specific server alerts using the `--alert` flag:
```bash
# Example 1: CPU and log issue on web server
python app/main.py --alert "CPU usage exceeds 95% on server prod-web-02"

# Example 2: Database issues
python app/main.py --alert "Database connection timeout in prod-db-01"
```

### Run Unit Tests
Validate tool logic and agent matching algorithms:
```bash
python -m unittest app/test_agents.py
```
