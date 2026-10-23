from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List, Dict, Any
import operator

class AgentState(TypedDict):
    query: str
    messages: Annotated[List[str], operator.add]
    data: Dict[str, Any]
    visual_artifact: str
    next: str

from .supervisor import supervisor_node
from .sql_agent import run_sql_query
from .rag_agent import rag_agent_node
from .visualizer_agent import visualizer_node

# Wrapper for SQL agent to fit graph node signature
def sql_node_wrapper(state):
    query = state.get("query")
    result = run_sql_query(query)
    # Assume result contains data we can visualize
    return {"messages": [str(result)], "data": {"raw": str(result)}}

workflow = StateGraph(AgentState)

workflow.add_node("supervisor", supervisor_node)
workflow.add_node("sql_agent", sql_node_wrapper)
workflow.add_node("rag_agent", rag_agent_node)
workflow.add_node("visualizer_agent", visualizer_node)

workflow.set_entry_point("supervisor")

workflow.add_conditional_edges(
    "supervisor",
    lambda x: x["next"],
    {
        "sql_agent": "sql_agent",
        "rag_agent": "rag_agent",
    }
)

workflow.add_edge("sql_agent", "visualizer_agent")
workflow.add_edge("rag_agent", END)
workflow.add_edge("visualizer_agent", END)

app = workflow.compile()
