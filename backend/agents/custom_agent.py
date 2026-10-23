import os
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool
from langchain.prompts import PromptTemplate
import sqlite3
import json

def load_custom_agent(agent_id: int):
    """Load a custom agent configuration from database"""
    conn = sqlite3.connect("datascout.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM custom_agents WHERE id = ?", (agent_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return None
    
    return dict(row)

def execute_custom_agent(agent_config: dict, query: str):
    """Execute a custom agent with the given query"""
    api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key or api_key == "sk-placeholder" or api_key.startswith("your-") or not (api_key.startswith("sk-") or api_key.startswith("sk-proj-")):
        return {"error": "OpenAI API key is not configured. Please add a valid OPENAI_API_KEY to backend/.env."}
    
    try:
        # Parse enabled tools
        enabled_tools = json.loads(agent_config.get("tools", "[]"))
        
        # Build tools list
        tools = []
        
        if "sql" in enabled_tools:
            from .sql_agent import run_sql_query
            sql_tool = Tool(
                name="SQL_Database",
                func=lambda q: run_sql_query(q),
                description="Useful for querying the financial database. Input should be a natural language question."
            )
            tools.append(sql_tool)
        
        if "rag" in enabled_tools:
            from .rag_agent import rag_agent_node
            rag_tool = Tool(
                name="Document_Search",
                func=lambda q: str(rag_agent_node({"query": q}).get("messages", [""])[0]),
                description="Useful for searching enterprise documents and reports. Input should be a question about documents."
            )
            tools.append(rag_tool)
        
        # Create LLM with custom system prompt
        llm = ChatOpenAI(model="gpt-4o", temperature=0)
        
        # Create agent prompt template
        template = """You are {agent_name}.

{system_prompt}

You have access to the following tools:

{tools}

Tool names: {tool_names}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought: {agent_scratchpad}"""

        prompt = PromptTemplate(
            template=template,
            input_variables=["input", "agent_scratchpad"],
            partial_variables={
                "agent_name": agent_config["name"],
                "system_prompt": agent_config["system_prompt"],
                "tools": "\n".join([f"{tool.name}: {tool.description}" for tool in tools]),
                "tool_names": ", ".join([tool.name for tool in tools])
            }
        )
        
        # Create and run agent
        agent = create_react_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(
            agent=agent, 
            tools=tools, 
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5
        )
        
        result = agent_executor.invoke({"input": query})
        return {
            "success": True,
            "response": result.get("output", str(result)),
            "agent_name": agent_config["name"]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "agent_name": agent_config["name"]
        }
