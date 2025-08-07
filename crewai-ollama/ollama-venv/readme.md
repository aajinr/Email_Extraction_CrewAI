#  CrewAI + Ollama Integration (TinyLlama) — Windows Setup Guide

This project sets up [CrewAI](https://github.com/joaomdmoura/crewai) using a **local LLM served via [Ollama](https://ollama.com/)** (specifically `tinyllama:1.1b-chat`) to classify IT incidents. It’s designed for low-resource machines (≤ 4 GB free RAM).

---

##  Requirements

- Windows 10/11
- Python 3.8+ installed and added to PATH
- Git Bash or PowerShell
- ~3.5 GB RAM free for `tinyllama:1.1b-chat`

---

## Setup Instructions

### 1. Install Python & Create Virtual Environment

```bash
# Create and enter your project folder
mkdir crewai-ollama && cd crewai-ollama

# Create virtual environment
python -m venv ollama-venv

# Activate venv:
# PowerShell
.\ollama-venv\Scripts\Activate.ps1
# OR Git Bash
source ollama-venv/Scripts/activate
