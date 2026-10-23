"""
Supervisor Agent - Query Routing and Orchestration
Routes analytical queries to SQL Agent and unstructured queries to RAG.
Maintains backward compatibility with LangGraph when dependencies and credentials
are present, and provides deterministic routing fallback when credentials are not configured.
"""

import os
import re
import logging
from typing import TypedDict, Literal, Optional, Any, List
from pydantic import BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Safe optional imports for LangChain / LangGraph
try:
    from langchain_openai import ChatOpenAI
    from langgraph.graph import StateGraph, END
    HAS_LANGGRAPH = True
except ImportError:
    ChatOpenAI = None
    StateGraph = None
    END = None
    HAS_LANGGRAPH = False


# Define the state schema
class SupervisorState(TypedDict, total=False):
    """State for the supervisor graph."""
    query: str
    messages: list[str]
    next: str
    final_answer: str
    data: Optional[Any]
    sql_query: Optional[str]


# Define the routing schema for function calling
class RouteQuery(BaseModel):
    """Route a user query to the most relevant specialized agent."""
    destination: Literal["sql_agent", "rag_agent", "clarify"] = Field(
        ...,
        description="""The agent to route the query to:
        - 'sql_agent': For queries about specific numbers, sales, revenue, orders, products, inventory, customers, business metrics
        - 'rag_agent': For queries about policies, reports, documents, strategy, general knowledge
        - 'clarify': If the query is unclear or ambiguous, ask for clarification
        """
    )
    reasoning: str = Field(
        ...,
        description="Brief explanation of why this routing decision was made"
    )


class Supervisor:
    """
    Supervisor agent that routes queries to specialized agents using LLM-based decision making
    or deterministic fallback when credentials or dependencies are unconfigured.
    """

    def __init__(self):
        """Initialize supervisor with LLM routing or deterministic fallback."""
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.is_configured = self._is_valid_key(self.api_key)
        self.graph = None

        if HAS_LANGGRAPH and self.is_configured:
            try:
                self.llm = ChatOpenAI(
                    model="gpt-4o",
                    temperature=0,
                    openai_api_key=self.api_key
                )
                self.router = self.llm.with_structured_output(RouteQuery)
                self.routing_prompt = """You are an intelligent query router and manager for an enterprise business platform.
Analyze user queries and route them to:
**SQL_Agent**: For specific numbers, revenue, orders, customers, inventory, sales, products, campaigns, averages, counts, database queries.
**RAG_Agent**: For policies, uploaded reports, document summaries, guidelines, strategy.
**Clarify**: When intent is ambiguous."""
                self.graph = self._build_graph()
                logger.info("Supervisor initialized with LangGraph and OpenAI")
            except Exception as e:
                logger.warning(f"Could not initialize LangGraph supervisor: {str(e)}. Using fallback routing.")
                self.graph = None
        else:
            logger.info("Supervisor running in deterministic rule-based routing mode.")

    @staticmethod
    def _is_valid_key(key: Optional[str]) -> bool:
        if not key:
            return False
        clean = key.strip()
        if clean.startswith("your-") or clean.startswith("sk-placeholder") or "your-key" in clean:
            return False
        return clean.startswith("sk-") or clean.startswith("sk-proj-")

    def _build_graph(self):
        """Build the LangGraph state graph for supervisor routing."""
        workflow = StateGraph(SupervisorState)
        workflow.add_node("route", self._route_query)
        workflow.add_node("sql_agent", self._execute_sql_agent)
        workflow.add_node("rag_agent", self._execute_rag_agent)
        workflow.add_node("clarify", self._request_clarification)

        workflow.set_entry_point("route")
        workflow.add_conditional_edges(
            "route",
            lambda state: state.get("next", "sql_agent"),
            {
                "sql_agent": "sql_agent",
                "rag_agent": "rag_agent",
                "clarify": "clarify",
            }
        )
        workflow.add_edge("sql_agent", END)
        workflow.add_edge("rag_agent", END)
        workflow.add_edge("clarify", END)

        return workflow.compile()

    def _route_query(self, state: SupervisorState) -> SupervisorState:
        """Route the query using LLM."""
        query = state["query"]
        logger.info(f"Routing query: {query}")
        try:
            decision = self.router.invoke(
                f"{self.routing_prompt}\n\nUser Query: {query}\n\nRoute this query:"
            )
            state["next"] = decision.destination
            state["messages"].append(f"[Supervisor] Routing to {decision.destination}: {decision.reasoning}")
        except Exception as e:
            logger.warning(f"LLM routing failed: {str(e)}, falling back to deterministic routing")
            state["next"] = self._deterministic_route(query)
            state["messages"].append(f"[Supervisor] Fallback routing to {state['next']}")
        return state

    def _deterministic_route(self, query: str) -> str:
        """Rule-based routing when LLM is unavailable or unconfigured."""
        q = query.lower()
        sql_keywords = [
            "revenue", "sales", "order", "product", "customer", "inventory",
            "campaign", "reorder", "demand", "tier", "average", "aov", "count",
            "total", "sum", "units", "roas", "price", "spend", "sql", "select",
            "where", "table", "database", "region", "month", "smb", "enterprise"
        ]
        if any(re.search(r"\b" + kw + r"\b", q) for kw in sql_keywords) or q.startswith("select") or q.startswith("with"):
            return "sql_agent"
        return "rag_agent"

    def _execute_sql_agent(self, state: SupervisorState) -> SupervisorState:
        """Execute the SQL agent."""
        query = state["query"]
        logger.info("Executing SQL Agent")
        try:
            from agents.sql_agent import SQLAgent
            agent = SQLAgent()
            result = agent.query(query, return_data=True)

            state["final_answer"] = result["answer"]
            state["data"] = result.get("data")
            state["sql_query"] = result.get("sql_query")
            state["messages"].append(f"[SQL Agent] {result['answer']}")
        except Exception as e:
            logger.error(f"SQL Agent execution failed: {str(e)}")
            state["final_answer"] = f"Error executing SQL query: {str(e)}"
            state["messages"].append(f"[SQL Agent Error] {str(e)}")
        return state

    def _execute_rag_agent(self, state: SupervisorState) -> SupervisorState:
        """Execute the RAG agent."""
        query = state["query"]
        logger.info("Executing RAG Agent")
        try:
            from agents.rag_agent import RAGAgent
            agent = RAGAgent()
            result = agent.query(query)

            answer = result["answer"]
            if result.get("sources"):
                answer += f"\n\nSources: {', '.join(result['sources'])}"
            state["final_answer"] = answer
            state["messages"].append(f"[RAG Agent] {answer}")
        except Exception as e:
            logger.error(f"RAG Agent execution failed: {str(e)}")
            state["final_answer"] = f"Error accessing knowledge base: {str(e)}"
            state["messages"].append(f"[RAG Agent Error] {str(e)}")
        return state

    def _request_clarification(self, state: SupervisorState) -> SupervisorState:
        """Request clarification from the user."""
        clarification_message = (
            "I need a bit more information to help you effectively. Could you please clarify:\n"
            "- Are you asking about quantitative business data (revenue, orders, products, customers)?\n"
            "- Or are you asking about unstructured documents and policies (guidelines, reports)?"
        )
        state["final_answer"] = clarification_message
        state["messages"].append("[Supervisor] Requesting clarification")
        return state

    def query(self, user_query: str) -> dict:
        """Process a user query through graph or deterministic router."""
        initial_state: SupervisorState = {
            "query": user_query,
            "messages": [],
            "next": "",
            "final_answer": "",
            "data": None,
            "sql_query": None,
        }

        if self.graph:
            try:
                final_state = self.graph.invoke(initial_state)
                return {
                    "answer": final_state.get("final_answer", ""),
                    "reasoning": final_state.get("messages", []),
                    "data": final_state.get("data"),
                    "sql_query": final_state.get("sql_query"),
                }
            except Exception as e:
                logger.error(f"Graph invocation failed: {str(e)}")

        # Deterministic routing
        destination = self._deterministic_route(user_query)
        initial_state["next"] = destination
        initial_state["messages"].append(f"[Supervisor] Deterministic routing to {destination}")

        if destination == "sql_agent":
            final_state = self._execute_sql_agent(initial_state)
        elif destination == "rag_agent":
            final_state = self._execute_rag_agent(initial_state)
        else:
            final_state = self._request_clarification(initial_state)

        return {
            "answer": final_state.get("final_answer", ""),
            "reasoning": final_state.get("messages", []),
            "data": final_state.get("data"),
            "sql_query": final_state.get("sql_query"),
        }


def supervisor_node(state):
    """LangGraph node wrapper for supervisor backward compatibility."""
    query = state.get("query", "")
    supervisor = Supervisor()
    route = supervisor._deterministic_route(query)
    return {"next": route}
