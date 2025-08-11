# --- Hardening + telemetry off MUST come before crewai import ---
import os
os.environ["OTEL_SDK_DISABLED"] = "true"  # silence telemetry timeouts

from crewai import Agent, Crew, Task, LLM
import requests
import json
import re
from urllib.parse import quote
from dotenv import load_dotenv

# Load .env if available
load_dotenv()

# --- Config (normalized) ---
# Prefer env, else fallback to your current values
SERVICENOW_INSTANCE = ""
SERVICENOW_USER = ""
SERVICENOW_PASS =  ""

# --- LLM Setup ---
llm = LLM(
    model="ollama/tinyllama:1.1b-chat",
    api_base="http://localhost:11434"
)

# --- Agent Setup ---
agent = Agent(
    role="Incident Summarizer",
    goal="Generate an incident title and description from user-reported raw text",
    backstory="Expert ServiceNow analyst converting long reports into structured tickets.",
    llm=llm
)

# --- Task: Summary + Structure ---
task = Task(
    description=(
        "Based on the following user report, create:\n"
        "- A short incident title (max 10 words)\n"
        "- A clear incident description (2-3 sentences)\n\n"
        "User report:\n'''{{ report }}'''\n\n"
        "Respond in JSON format like exactly:\n"
        "{\"title\": \"...\", \"description\": \"...\"}"
    ),
    expected_output="JSON with incident title and description",
    agent=agent
)

# --- Crew Setup ---
crew = Crew(
    agents=[agent],
    tasks=[task],
    verbose=True
)

# --- Sample input (replace with real user text) ---
user_report = """
Hi, I'm facing an issue with the internal VPN. Every time I try to connect,
I get an error saying 'Unable to reach authentication server'. I've tried on both
my laptop and phone with no luck. It's been going on since last evening.
"""

# --- Helper: Coerce LLM text to JSON with a safe fallback ---
def coerce_incident_json(raw_text: str, fallback_source: str):
    """
    Extract first {...} JSON block from raw_text. If invalid/missing,
    build a reasonable title/description from fallback_source.
    """
    if not isinstance(raw_text, str):
        raw_text = str(raw_text or "")

    # Try to extract JSON object
    m = re.search(r'\{[\s\S]*\}', raw_text)
    if m:
        candidate = m.group(0)
        try:
            obj = json.loads(candidate)
            title = str(obj.get("title") or "").strip()
            desc = str(obj.get("description") or "").strip()
            if title and desc:
                return {"title": title, "description": desc}
        except Exception:
            pass

    # Heuristic fallback
    text = " ".join((fallback_source or "").split()).strip()
    if not text:
        text = "User reported an issue."

    # Title = first ~10 words or up to first period
    first_sentence = re.split(r'(?<=[.!?])\s+', text)[0]
    title_words = first_sentence.split()
    title = " ".join(title_words[:10]) or "User-reported Issue"

    # Description = first 2–3 sentences
    sentences = re.split(r'(?<=[.!?])\s+', text)
    description = " ".join(sentences[:3]) if sentences else text

    return {"title": title, "description": description}

# --- Run Agent ---
response = crew.kickoff(inputs={"report": user_report})
raw_llm_text = str(response).strip()
print("🧠 Raw LLM text:\n", raw_llm_text)

parsed = coerce_incident_json(raw_llm_text, fallback_source=user_report)
incident_title = parsed["title"]
incident_description = parsed["description"]

# --- Create Incident in ServiceNow (robust) ---
def create_servicenow_incident(title, description):
    url = f"{SERVICENOW_INSTANCE}/api/now/table/incident"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    payload = {
        "short_description": title,
        "description": description,
        "urgency": "2",
        "impact": "2"
    }

    r = requests.post(url, auth=(SERVICENOW_USER, SERVICENOW_PASS), headers=headers, json=payload, timeout=30)
    print("SN POST status:", r.status_code)
    content_type = r.headers.get("Content-Type", "")
    body = (r.text or "").strip()

    # Happy-path JSON
    if r.status_code in (200, 201) and "application/json" in content_type and body:
        try:
            data = r.json().get("result") or {}
            sys_id = data.get("sys_id")
            if sys_id:
                print("✅ Incident created!")
                print("🆔 Sys ID:", sys_id)
                print("🔗 View:", f"{SERVICENOW_INSTANCE}/nav_to.do?uri=incident.do?sys_id={sys_id}")
                return sys_id
        except Exception:
            pass

    # Location header fallback
    loc = r.headers.get("Location")
    if loc and "sys_id=" in loc:
        sys_id = loc.split("sys_id=")[-1].split("&")[0]
        print("✅ Incident created (from Location header)!")
        print("🆔 Sys ID:", sys_id)
        print("🔗 View:", f"{SERVICENOW_INSTANCE}/nav_to.do?uri=incident.do?sys_id={sys_id}")
        return sys_id

    # Lookup fallback by short_description
    q = f"short_description={quote(title)}^ORDERBYDESCsys_created_on"
    q_url = f"{SERVICENOW_INSTANCE}/api/now/table/incident?sysparm_query={q}&sysparm_limit=1"
    gr = requests.get(q_url, auth=(SERVICENOW_USER, SERVICENOW_PASS), headers={"Accept": "application/json"}, timeout=30)

    if gr.status_code == 200:
        try:
            result = gr.json().get("result") or []
            if result:
                sys_id = result[0]["sys_id"]
                print("✅ Incident created (via lookup)!")
                print("🆔 Sys ID:", sys_id)
                print("🔗 View:", f"{SERVICENOW_INSTANCE}/nav_to.do?uri=incident.do?sys_id={sys_id}")
                return sys_id
        except Exception:
            pass

    # Diagnostics
    print("❌ Could not confirm incident creation.")
    print("Response headers:", r.headers)
    print("Response body (first 500 chars):", body[:500])
    return None

# --- Execute ---
create_servicenow_incident(incident_title, incident_description)
