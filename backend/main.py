from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import os
import sqlite3
from datetime import datetime
from fastapi import UploadFile, File
from dotenv import load_dotenv
import json
import logging

load_dotenv()

# Import the graph (not currently used - using Supervisor directly in /chat endpoint)
# from agents.graph import app as agent_app

app = FastAPI(title="DataScout Enterprise Platform", version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    thoughts: List[str]
    data: Optional[Dict[str, Any]] = None
    visual_artifact: Optional[str] = None

@app.get("/")
async def root():
    return {"message": "DataScout Enterprise Agent Swarm is Online"}

# --- Real Enterprise Endpoints ---

@app.get("/api/stats")
async def get_stats():
    conn = sqlite3.connect("datascout.db")
    cursor = conn.cursor()
    
    # Real counts
    cursor.execute("SELECT COUNT(*) FROM documents")
    doc_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM query_audit")
    query_count = cursor.fetchone()[0]
    
    # Mock revenue for now (or could be stored)
    revenue = "$2.4M" 
    
    conn.close()
    
    return {
        "revenue": revenue,
        "documents": doc_count,
        "queries": query_count,
        "agents_active": 4 # Supervisor, SQL, RAG, Visualizer
    }

@app.get("/api/documents")
async def get_documents():
    conn = sqlite3.connect("datascout.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """
    Upload a PDF document and process it for RAG pipeline.
    Processing happens in the background via Pinecone ingestion.
    """
    try:
        # Validate file type
        if not file.filename.endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Save file to disk
        file_location = f"reports/{file.filename}"
        os.makedirs("reports", exist_ok=True)
        
        with open(file_location, "wb+") as file_object:
            content = await file.read()
            file_object.write(content)
        
        logging.info(f"Saved file to {file_location}")
        
        # Record in database
        conn = sqlite3.connect("datascout.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO documents (name, size, upload_date, status) VALUES (?, ?, ?, ?)",
            (file.filename, f"{len(content)/1024:.1f} KB", datetime.now().strftime("%Y-%m-%d"), "processing")
        )
        doc_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        logging.info(f"Created database record with ID: {doc_id}")
        
        # Define background processing function
        def process_document_background(doc_id: int, file_path: str):
            """Background task to process PDF and ingest into Pinecone"""
            try:
                logging.info(f"Starting background processing for document ID: {doc_id}")
                
                # Import and call ingestion service
                from services.ingestion import process_pdf
                
                result = process_pdf(file_path)
                
                # Update database based on result
                conn = sqlite3.connect("datascout.db")
                cursor = conn.cursor()
                
                if result.get("success"):
                    cursor.execute(
                        "UPDATE documents SET status = 'processed' WHERE id = ?", 
                        (doc_id,)
                    )
                    logging.info(f"Document {doc_id} processed successfully: {result.get('message')}")
                else:
                    cursor.execute(
                        "UPDATE documents SET status = 'failed' WHERE id = ?", 
                        (doc_id,)
                    )
                    logging.error(f"Document {doc_id} processing failed: {result.get('error')}")
                
                conn.commit()
                conn.close()
                
            except Exception as e:
                logging.error(f"Background processing failed for document {doc_id}: {str(e)}", exc_info=True)
                
                # Update status to failed
                try:
                    conn = sqlite3.connect("datascout.db")
                    cursor = conn.cursor()
                    cursor.execute("UPDATE documents SET status = 'failed' WHERE id = ?", (doc_id,))
                    conn.commit()
                    conn.close()
                except Exception as db_error:
                    logging.error(f"Failed to update database status: {str(db_error)}")
        
        # Schedule background task
        if background_tasks:
            background_tasks.add_task(process_document_background, doc_id, file_location)
            logging.info(f"Scheduled background processing for document ID: {doc_id}")
        
        return {
            "success": True,
            "info": f"File '{file.filename}' uploaded successfully",
            "id": doc_id,
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Upload failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/agents/activity")
async def get_agent_activity():
    conn = sqlite3.connect("datascout.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM agent_logs ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/api/analytics/summary")
async def get_analytics_summary():
    """
    Get analytics summary with query counts and performance metrics.
    """
    try:
        conn = sqlite3.connect("datascout.db")
        cursor = conn.cursor()
        
        # Total queries
        cursor.execute("SELECT COUNT(*) as total FROM agent_logs")
        total_queries = cursor.fetchone()[0]
        
        # Average latency
        cursor.execute("SELECT AVG(duration_ms) as avg_latency FROM agent_logs WHERE duration_ms IS NOT NULL")
        avg_latency_result = cursor.fetchone()[0]
        avg_latency = round(avg_latency_result, 2) if avg_latency_result else 0
        
        # Queries by agent
        cursor.execute("""
            SELECT agent_name, COUNT(*) as count 
            FROM agent_logs 
            GROUP BY agent_name 
            ORDER BY count DESC
        """)
        queries_by_agent = [{"agent": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        # Recent activity (last 24 hours)
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM agent_logs 
            WHERE timestamp >= datetime('now', '-1 day')
        """)
        recent_queries = cursor.fetchone()[0]
        
        # Success rate
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                COUNT(*) as total
            FROM agent_logs
        """)
        success_data = cursor.fetchone()
        success_rate = round((success_data[0] / success_data[1] * 100), 1) if success_data[1] > 0 else 0
        
        conn.close()
        
        return {
            "total_queries": total_queries,
            "avg_latency_ms": avg_latency,
            "recent_queries_24h": recent_queries,
            "success_rate": success_rate,
            "queries_by_agent": queries_by_agent
        }
        
    except Exception as e:
        logging.error(f"Analytics summary failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history")
async def get_query_history():
    """
    Get recent query history from audit log.
    """
    try:
        conn = sqlite3.connect("datascout.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get last 50 queries from query_audit table
        cursor.execute("""
            SELECT id, query, result, timestamp 
            FROM query_audit 
            ORDER BY id DESC 
            LIMIT 50
        """)
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
        
    except Exception as e:
        logging.error(f"Query history failed: {str(e)}")
        # Return empty list if table doesn't exist yet
        return []

@app.get("/api/settings")
async def get_settings():
    """
    Get all user settings.
    """
    try:
        conn = sqlite3.connect("datascout.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT key, value FROM user_settings")
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to dictionary
        settings = {row["key"]: row["value"] for row in rows}
        
        return settings
        
    except Exception as e:
        logging.error(f"Get settings failed: {str(e)}")
        # Return default settings if table doesn't exist
        return {
            "openai_model": "gpt-4o",
            "theme": "dark",
            "notifications": "true",
            "auto_save": "true"
        }

class SettingsUpdate(BaseModel):
    settings: Dict[str, str]

@app.post("/api/settings")
async def update_settings(request: SettingsUpdate):
    """
    Update user settings.
    """
    try:
        conn = sqlite3.connect("datascout.db")
        cursor = conn.cursor()
        
        # Update each setting
        for key, value in request.settings.items():
            cursor.execute("""
                INSERT OR REPLACE INTO user_settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))
        
        conn.commit()
        conn.close()
        
        logging.info(f"Settings updated: {list(request.settings.keys())}")
        
        return {"success": True, "message": "Settings updated successfully"}
        
    except Exception as e:
        logging.error(f"Update settings failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main chat endpoint that routes queries through the Supervisor.
    Returns responses with optional visualization data.
    """
    try:
        # Log start
        start_time = datetime.now()
        logging.info(f"Chat request received: {request.message}")
        
        visual_artifact = ""
        sql_data = None
        
        # Check if OpenAI API key is properly configured
        api_key = os.getenv("OPENAI_API_KEY", "")
        is_openai_configured = bool(
            api_key 
            and (api_key.startswith("sk-") or api_key.startswith("sk-proj-")) 
            and not api_key.startswith("sk-placeholder") 
            and "your-key" not in api_key
        )

        if not is_openai_configured:
            response_text = "OpenAI API key is not configured. Please add a valid OPENAI_API_KEY to backend/.env to enable AI agents."
            reasoning = ["[Configuration] Missing or placeholder OPENAI_API_KEY in environment."]
        else:
            # Use the new Supervisor for intelligent routing
            try:
                from agents.supervisor import Supervisor
                
                supervisor = Supervisor()
                result = supervisor.query(request.message)
                
                response_text = result.get("answer", "I processed your request.")
                reasoning = result.get("reasoning", [])
                sql_data = result.get("data")  # Get structured data if available
                
            except Exception as supervisor_error:
                logging.error(f"Supervisor failed, using fallback: {str(supervisor_error)}")
                
                # Fallback: Try RAG agent directly
                try:
                    from agents.rag_agent import RAGAgent
                    rag = RAGAgent()
                    rag_result = rag.query(request.message)
                    response_text = rag_result["answer"]
                    if rag_result.get("sources"):
                        response_text += f"\n\nSources: {', '.join(rag_result['sources'])}"
                    reasoning = ["Routed to RAG agent (fallback)"]
                except Exception as rag_error:
                    logging.error(f"RAG fallback failed: {str(rag_error)}")
                    response_text = f"I encountered an error processing your request. Please try again."
                    reasoning = [f"Error: {str(rag_error)}"]
            
            # Generate visualization only if query seems data-related and real data exists
            visualization_keywords = ["show", "chart", "graph", "plot", "display", "compare", "trend", "sales", "revenue", "region", "by"]
            should_visualize = any(kw in request.message.lower() for kw in visualization_keywords)
            
            if should_visualize and sql_data and isinstance(sql_data, list) and len(sql_data) > 0:
                try:
                    from agents.visualizer_agent import VisualizerAgent
                    visualizer = VisualizerAgent()
                    chart_config = visualizer.generate_chart_config(sql_data, request.message)
                    visual_artifact = json.dumps(chart_config)
                    reasoning.append("[Visualizer] Generated chart from actual SQL data")
                except Exception as viz_error:
                    logging.warning(f"Visualization generation failed: {str(viz_error)}")
                    reasoning.append(f"[Visualizer] Could not generate chart: {str(viz_error)}")
        
        # Log activity
        duration = (datetime.now() - start_time).total_seconds() * 1000
        try:
            conn = sqlite3.connect("datascout.db")
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO agent_logs (agent_name, query, status, timestamp, duration_ms) VALUES (?, ?, ?, ?, ?)",
                ("Supervisor", request.message, "completed", start_time.isoformat(), int(duration))
            )
            conn.commit()
            conn.close()
        except Exception as db_error:
            logging.warning(f"Failed to log activity: {str(db_error)}")
        
        # Format thoughts for UI
        thoughts = reasoning if reasoning else [
            "Analyzing query...",
            "Processing request...",
            "Generating response..."
        ]
        
        return ChatResponse(
            response=response_text,
            thoughts=thoughts,
            data={},
            visual_artifact=visual_artifact
        )
        
    except Exception as e:
        logging.error(f"Chat endpoint error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- SQL Analytical Execution Endpoint ---

class SQLExecuteRequest(BaseModel):
    query: str

class SQLExecuteResponse(BaseModel):
    success: bool
    sql_query: Optional[str] = None
    columns: List[str] = []
    rows: List[Dict[str, Any]] = []
    row_count: int = 0
    execution_duration_ms: float = 0.0
    error: Optional[str] = None
    answer: str = ""

@app.post("/api/sql/query", response_model=SQLExecuteResponse)
async def query_sql_endpoint(request: SQLExecuteRequest):
    """
    Direct analytical query endpoint returning structured execution details,
    AST-validated SQL, column schema, and data rows.
    """
    try:
        from agents.sql_agent import SQLAgent
        agent = SQLAgent()
        res = agent.query(request.query, return_data=True)
        return SQLExecuteResponse(
            success=res["success"],
            sql_query=res.get("sql_query"),
            columns=res.get("columns", []),
            rows=res.get("rows", []),
            row_count=res.get("row_count", 0),
            execution_duration_ms=res.get("execution_duration_ms", 0.0),
            error=res.get("error"),
            answer=res.get("answer", "")
        )
    except Exception as e:
        logger.error(f"SQL endpoint error: {str(e)}", exc_info=True)
        return SQLExecuteResponse(
            success=False,
            sql_query=None,
            columns=[],
            rows=[],
            row_count=0,
            execution_duration_ms=0.0,
            error=str(e),
            answer=f"Error executing SQL query: {str(e)}"
        )

# --- Agent Execution Endpoints ---

class AgentExecuteRequest(BaseModel):
    agent_type: str  # sql, financial, compliance, research, or custom_id
    query: str

@app.post("/api/agents/execute")
async def execute_agent(request: AgentExecuteRequest):
    """Execute a specific agent with a query"""
    try:
        start_time = datetime.now()
        
        # Route to appropriate agent based on type
        if request.agent_type == "sql":
            from agents.sql_agent import run_sql_query
            result = run_sql_query(request.query)
            response = {
                "success": True,
                "agent_name": "SQL Expert",
                "response": result,
                "duration_ms": int((datetime.now() - start_time).total_seconds() * 1000)
            }
        
        elif request.agent_type == "financial":
            # Financial analyst uses SQL + analysis
            from agents.sql_agent import run_sql_query
            sql_result = run_sql_query(f"Analyze financial data for: {request.query}")
            response = {
                "success": True,
                "agent_name": "Financial Analyst",
                "response": f"Financial Analysis:\n{sql_result}\n\nKey Insights: This data shows trends based on the query.",
                "duration_ms": int((datetime.now() - start_time).total_seconds() * 1000)
            }
        
        elif request.agent_type == "research":
            # Market researcher uses RAG
            from agents.rag_agent import rag_agent_node
            rag_result = rag_agent_node({"query": request.query})
            response = {
                "success": True,
                "agent_name": "Market Researcher",
                "response": rag_result.get("messages", ["No results found"])[0],
                "duration_ms": int((datetime.now() - start_time).total_seconds() * 1000)
            }
        
        elif request.agent_type == "compliance":
            # Compliance officer uses RAG to scan documents
            from agents.rag_agent import rag_agent_node
            rag_result = rag_agent_node({"query": f"Compliance check: {request.query}"})
            response = {
                "success": True,
                "agent_name": "Compliance Officer",
                "response": f"Compliance Scan:\n{rag_result.get('messages', ['No compliance issues found'])[0]}",
                "duration_ms": int((datetime.now() - start_time).total_seconds() * 1000)
            }
        
        elif request.agent_type.startswith("custom_"):
            # Custom agent execution
            agent_id = int(request.agent_type.replace("custom_", ""))
            from agents.custom_agent import load_custom_agent, execute_custom_agent
            
            agent_config = load_custom_agent(agent_id)
            if not agent_config:
                raise HTTPException(status_code=404, detail="Custom agent not found")
            
            result = execute_custom_agent(agent_config, request.query)
            response = {
                **result,
                "duration_ms": int((datetime.now() - start_time).total_seconds() * 1000)
            }
        
        else:
            raise HTTPException(status_code=400, detail=f"Unknown agent type: {request.agent_type}")
        
        # Log activity
        conn = sqlite3.connect("datascout.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO agent_logs (agent_name, query, status, timestamp, duration_ms) VALUES (?, ?, ?, ?, ?)",
            (response.get("agent_name", "Unknown"), request.query, "completed", start_time.isoformat(), response.get("duration_ms", 0))
        )
        conn.commit()
        conn.close()
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Custom Agent CRUD

class CustomAgentCreate(BaseModel):
    name: str
    description: str
    system_prompt: str
    tools: List[str]  # ["sql", "rag"]

@app.post("/api/agents/custom")
async def create_custom_agent(agent: CustomAgentCreate):
    """Create a new custom agent"""
    try:
        conn = sqlite3.connect("datascout.db")
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO custom_agents (name, description, system_prompt, tools) VALUES (?, ?, ?, ?)",
            (agent.name, agent.description, agent.system_prompt, json.dumps(agent.tools))
        )
        agent_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return {"success": True, "agent_id": agent_id, "message": f"Custom agent '{agent.name}' created"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents/custom")
async def list_custom_agents():
    """List all custom agents"""
    try:
        conn = sqlite3.connect("datascout.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM custom_agents ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        
        agents = []
        for row in rows:
            agent = dict(row)
            agent['tools'] = json.loads(agent.get('tools', '[]'))
            agents.append(agent)
        
        return agents
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/agents/custom/{agent_id}")
async def delete_custom_agent(agent_id: int):
    """Delete a custom agent"""
    try:
        conn = sqlite3.connect("datascout.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM custom_agents WHERE id = ?", (agent_id,))
        conn.commit()
        conn.close()
        
        return {"success": True, "message": "Agent deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    # Verify database connection
    db_status = "connected"
    try:
        conn = sqlite3.connect("datascout.db")
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Check AI provider configuration
    api_key = os.getenv("OPENAI_API_KEY", "")
    is_openai_configured = bool(
        api_key 
        and (api_key.startswith("sk-") or api_key.startswith("sk-proj-")) 
        and not api_key.startswith("sk-placeholder") 
        and "your-key" not in api_key
    )
    
    pinecone_key = os.getenv("PINECONE_API_KEY", "")
    is_pinecone_configured = bool(
        pinecone_key 
        and not pinecone_key.startswith("your-key") 
        and "your-key" not in pinecone_key
    )
    
    return {
        "status": "healthy",
        "database": db_status,
        "ai_providers": {
            "openai": "configured" if is_openai_configured else "not_configured",
            "pinecone": "configured" if is_pinecone_configured else "not_configured"
        }
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
