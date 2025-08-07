from crewai import Agent, Crew, Task, LLM

# Connect to your local TinyLlama via Ollama
llm = LLM(
    model="ollama/tinyllama:1.1b-chat",         # This is the correct format
    api_base="http://localhost:11434",          # Default Ollama API endpoint
    temperature=0.7                             # Optional: adjust creativity
)

# Define the Agent
agent = Agent(
    role="Incident Classifier",
    goal="Classify IT incidents into categories like phishing, access issue, etc.",
    backstory=(
        "An experienced ServiceNow analyst who handles incoming IT incidents "
        "and routes them to the correct team based on the incident content."
    ),
    llm=llm
)

# Define the Task
task = Task(
    description="Classify this incident: '{{ incident }}'",
    expected_output="A short label such as: 'Phishing', 'Network Issue', 'Login Problem', etc.",
    agent=agent
)

# Create Crew
crew = Crew(
    agents=[agent],
    tasks=[task],
    verbose=True
)

# Run with example input
result = crew.kickoff(inputs={"incident": "Employee received an email asking for credentials from unknown sender"})
print("\n✅ Classification Result:", result)
