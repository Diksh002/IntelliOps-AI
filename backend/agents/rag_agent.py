"""
RAG Agent - Retrieval Augmented Generation
Handles document retrieval and question answering using Pinecone vector database.
"""

import os
import logging
from typing import Dict, List, Any
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGAgent:
    """
    RAG Agent for document retrieval and question answering.
    Uses Pinecone for vector storage and GPT-4o for generation.
    """
    
    def __init__(self):
        """Initialize the RAG agent with Pinecone vectorstore."""
        try:
            # Get credentials from environment
            self.api_key = os.getenv("OPENAI_API_KEY")
            self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
            self.index_name = os.getenv("PINECONE_INDEX_NAME", "datascout")
            self.pinecone_host = os.getenv("PINECONE_HOST")
            
            # Validate credentials
            if not self.api_key or not (self.api_key.startswith("sk-") or self.api_key.startswith("sk-proj-")):
                raise ValueError("Missing or invalid OpenAI API Key")
            
            if not self.pinecone_api_key:
                raise ValueError("Missing Pinecone API Key")
            
            # Initialize Pinecone client
            logger.info("Connecting to Pinecone...")
            pc = Pinecone(api_key=self.pinecone_api_key)
            
            # Connect to index
            if self.pinecone_host:
                self.index = pc.Index(name=self.index_name, host=self.pinecone_host)
            else:
                self.index = pc.Index(self.index_name)
            
            # Initialize embeddings (matching Pinecone index: 1024 dimensions)
            logger.info("Initializing embeddings...")
            self.embeddings = OpenAIEmbeddings(
                model="text-embedding-3-large",
                dimensions=1024,
                openai_api_key=self.api_key
            )
            
            # Create vectorstore
            self.vectorstore = PineconeVectorStore(
                index=self.index,
                embedding=self.embeddings
            )
            
            # Initialize LLM
            self.llm = ChatOpenAI(
                model="gpt-4o",
                temperature=0,
                openai_api_key=self.api_key
            )
            
            logger.info("RAG Agent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize RAG Agent: {str(e)}")
            raise
    
    def query(self, user_question: str) -> Dict[str, Any]:
        """
        Query the RAG system with a user question.
        
        Args:
            user_question: The user's question
            
        Returns:
            Dictionary with 'answer' and 'sources' keys
        """
        try:
            logger.info(f"Processing query: {user_question}")
            
            # Perform similarity search (k=3)
            retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3})
            docs = retriever.invoke(user_question)
            
            if not docs:
                return {
                    "answer": "I searched the knowledge base but couldn't find specific information matching your query.",
                    "sources": []
                }
            
            # Extract sources (unique filenames)
            sources = list(set([
                doc.metadata.get('source', 'Unknown')
                for doc in docs
            ]))
            
            # Build context from retrieved documents
            context = "\n\n".join([
                f"Source: {doc.metadata.get('source', 'Unknown')}\n"
                f"Page: {doc.metadata.get('page', 'N/A')}\n"
                f"Content: {doc.page_content}"
                for doc in docs
            ])
            
            # Create prompt for GPT-4o
            system_prompt = """You are a Senior Financial Analyst with access to enterprise documents.
Answer the user's question using ONLY the provided context from the retrieved documents.
If the answer is not in the context, clearly state that you don't know.
Always cite your sources by mentioning the document name (e.g., 'According to the Q3 Report...').
Be precise, professional, and comprehensive in your response."""
            
            prompt = f"""{system_prompt}

Context from retrieved documents:
{context}

User Question: {user_question}

Answer:"""
            
            # Get response from GPT-4o
            response = self.llm.invoke(prompt)
            
            logger.info(f"Query completed successfully. Sources: {sources}")
            
            return {
                "answer": response.content,
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"Query failed: {str(e)}", exc_info=True)
            return {
                "answer": f"Error processing query: {str(e)}",
                "sources": []
            }


# Backward compatibility: maintain the original function for LangGraph integration
def rag_agent_node(state):
    """
    LangGraph node wrapper for RAG agent.
    Maintains backward compatibility with existing graph implementation.
    """
    query = state.get("query")
    
    try:
        # Instantiate agent and query
        agent = RAGAgent()
        result = agent.query(query)
        
        # Format response for LangGraph
        answer = result["answer"]
        if result["sources"]:
            sources_text = "\n\nSources: " + ", ".join(result["sources"])
            answer += sources_text
        
        return {"messages": [answer]}
        
    except Exception as e:
        logger.error(f"RAG agent node failed: {str(e)}")
        return {"messages": [f"Error accessing Enterprise Knowledge Base: {str(e)}"]}
