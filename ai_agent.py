import os
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.agent_toolkits import SQLDatabaseToolkit

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise EnvironmentError(
        "Missing GOOGLE_API_KEY environment variable. "
        "Create a .env file or export this value before running the app."
    )
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

def ask_gaming_agent(user_query: str):
    db = SQLDatabase.from_uri("sqlite:///smart_backlog.db")
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)
    
    # --- The V2 Prompt Optimization ---
    custom_prefix = """You are an expert PlayStation database assistant. 
    You already know the exact schema of the 'games_backlog' table. Do NOT use tools to list tables or check the schema.
    
    Schema: 
    CREATE TABLE games_backlog (
        game TEXT, system TEXT, tier TEXT, status TEXT, added TEXT, 
        removed TEXT, months REAL, release TEXT, age REAL, metacritic REAL, 
        user REAL, completion TEXT, genre TEXT, "notes_/_original_system" TEXT, 
        streaming TEXT, local_multiplayer TEXT
    );

    🎮 CRITICAL BUSINESS RULES FOR RECOMMENDATIONS:
    The 'status' column contains exactly three possible values:
    1. 'Active': The game is currently available to play.
    2. 'Leaving Soon': The game is leaving the service this month. If the user asks for a recommendation or what to play next, ALWAYS prioritize suggesting these games first due to urgency.
    3. 'Removed': The game is gone. NEVER recommend these games unless the user specifically asks about the history of removed games.

    Only use the sql_db_query tool to execute SQL queries. Never hallucinate game titles.
    """
    
    toolkit = SQLDatabaseToolkit(db=db, llm=llm)
    agent_executor = create_sql_agent(
        llm=llm, 
        toolkit=toolkit, 
        prefix=custom_prefix, 
        verbose=True
    )
    
    print("Thinking...")
    response = agent_executor.invoke({"input": user_query})
    return response["output"]

if __name__ == "__main__":
    print("🎮 Gemini Gaming Agent (V2) Initialized!\n")
    
    # Let's test your new rule!
    question = "suggest some games which has rating above 8"
    print(f"User: {question}")
    
    answer = ask_gaming_agent(question)
    
    print("\n=======================")
    print(f"Agent: {answer}")