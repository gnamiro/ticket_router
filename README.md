# 📨 Ticket Support Router (LangGraph + Local LLM)

This project demonstrates a production-oriented ticket routing system built with LangGraph and LangChain, using a local, free LLM (Ollama).
It classifies support tickets, estimates urgency, routes them to the correct queue, and escalates uncertain cases to human review using conditional graph logic.

The goal is to show how LLM workflows can be designed to be robust, interpretable, and safe, not just “LLM-in-a-loop”.

-------

# ✨ Key Features
- Shared state graph for end-to-end ticket processing

- LLM-powered nodes:

    - Ticket classification (category + confidence)

    - Urgency assessment (level + score)

    - Routing decision (queue + handler level)

- Conditional branching based on confidence and risk

- Human-in-the-loop (HITL) escalation for low-confidence or high-impact cases

- Failure-safe design with fallbacks (no hard crashes)

- 100% free & local — runs with Ollama (no API keys)

-------
# 🧠 Architecture Overview

```bash
START
  ↓
Classifier (category + confidence)
  ↓
[ Confidence Gate ]
  ├── low confidence → Human Review → END
  └── sufficient confidence
        ↓
     Urgency Assessment
        ↓
     Router (queue + handler)
        ↓
       END
```

- Most tickets follow a fast linear path

- Only uncertain or risky tickets branch into human review

-----
# ⚙️ Setup Instructions

## 1️⃣ Create and activate a virtual environment
```bash
python -m venv .venv
# Windows
.\.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate
```

## 2️⃣ Install Python dependencies
```bash
pip install langgraph langchain langchain-ollama pydantic
```

## 3️⃣ Install Ollama and a free model
Download Ollama from:
👉 https://ollama.com/download

Then pull a lightweight model:
```bash
ollama pull phi3:mini
```
----
## ▶️ Running the Project
```bash
python run.py
```
You’ll see:

- the final routing decision

- confidence and urgency levels

- an event log showing each step taken

----
# 📊 Future Improvements

- Telemetry:

    - per-node latency

    - confidence distributions

    - human override rates

- Feedback loop:

    - store human corrections

    - evaluate routing accuracy

- UI for human review (Zendesk / Jira / Slack integration)

- Model comparison or prompt evaluation