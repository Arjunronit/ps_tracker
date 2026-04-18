import os
from dotenv import load_dotenv
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_google_genai import ChatGoogleGenerativeAI

# Load the variables from your .env file
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise EnvironmentError(
        "Missing GOOGLE_API_KEY environment variable. "
        "Create a .env file or export this value before running the app."
    )
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

def ask_gaming_agent(query: str) -> str:
    # 1. Connect to your database
    db = SQLDatabase.from_uri("sqlite:///smart_backlog.db")
    
    # 2. Initialize Gemini (gemini-2.5-flash is extremely fast for this)
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0)
    
    # 3. Create the agent with 'tool-calling' mode to prevent parsing crashes
    agent_executor = create_sql_agent(
        llm=llm, 
        db=db, 
        agent_type="tool-calling", # <-- THIS is the magic fix!
        verbose=True,
        handle_parsing_errors=True # <-- Failsafe so it never throws a 500 error again
    )
    
    try:
        # Run the agent and extract just the text output
        response = agent_executor.invoke({"input": query})
        return response.get("output", "I couldn't find an answer to that.")
    except Exception as e:
        print(f"Agent Error: {e}")
        return "I ran into a technical issue checking the database. Please try asking in a different way!"