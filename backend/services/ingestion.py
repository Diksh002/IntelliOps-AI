"""
Document Ingestion Service
Handles PDF processing and vector database ingestion for RAG pipeline.
"""

import os
import logging
from typing import Dict, Any
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


def process_pdf(file_path: str) -> Dict[str, Any]:
    """
    Process a PDF file and ingest it into Pinecone vector database.
    
    Args:
        file_path: Path to the PDF file to process
        
    Returns:
        Dictionary with processing status and details
    """
    try:
        logger.info(f"Starting PDF processing for: {file_path}")
        
        # Validate file exists
        if not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
        # Extract filename for metadata
        filename = Path(file_path).name
        
        # Step 1: Load PDF using PyPDFLoader
        logger.info("Loading PDF document...")
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        
        if not documents:
            error_msg = "No content extracted from PDF"
            logger.warning(error_msg)
            return {"success": False, "error": error_msg}
        
        logger.info(f"Loaded {len(documents)} pages from PDF")
        
        # Step 2: Split text into chunks
        logger.info("Splitting document into chunks...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        chunks = text_splitter.split_documents(documents)
        logger.info(f"Created {len(chunks)} text chunks")
        
        # Step 3: Initialize OpenAI Embeddings (matching Pinecone index: 1024 dimensions)
        logger.info("Initializing embeddings...")
        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large",
            dimensions=1024,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Step 4: Initialize Pinecone
        logger.info("Connecting to Pinecone...")
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        pinecone_index_name = os.getenv("PINECONE_INDEX_NAME")
        
        if not pinecone_api_key or not pinecone_index_name:
            error_msg = "Pinecone credentials not found in environment variables"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
        try:
            # Initialize Pinecone client
            pc = Pinecone(api_key=pinecone_api_key)
            
            # Get the host from environment or use the index name
            pinecone_host = os.getenv("PINECONE_HOST")
            if pinecone_host:
                index = pc.Index(name=pinecone_index_name, host=pinecone_host)
            else:
                index = pc.Index(pinecone_index_name)
            
            # Step 5: Process and upsert chunks
            logger.info("Generating embeddings and upserting to Pinecone...")
            vectors_to_upsert = []
            
            for i, chunk in enumerate(chunks):
                # Generate unique ID for each chunk
                chunk_id = f"{filename}_{i}"
                
                # Generate embedding for chunk text
                embedding = embeddings.embed_query(chunk.page_content)
                
                # Prepare metadata
                metadata = {
                    "source": filename,
                    "text": chunk.page_content,
                    "page": chunk.metadata.get("page", 0),
                    "chunk_index": i
                }
                
                # Add to batch
                vectors_to_upsert.append({
                    "id": chunk_id,
                    "values": embedding,
                    "metadata": metadata
                })
                
                # Upsert in batches of 100
                if len(vectors_to_upsert) >= 100:
                    index.upsert(vectors=vectors_to_upsert)
                    logger.info(f"Upserted batch of {len(vectors_to_upsert)} vectors")
                    vectors_to_upsert = []
            
            # Upsert remaining vectors
            if vectors_to_upsert:
                index.upsert(vectors=vectors_to_upsert)
                logger.info(f"Upserted final batch of {len(vectors_to_upsert)} vectors")
            
            success_msg = f"Successfully processed {len(chunks)} chunks from {filename}"
            logger.info(success_msg)
            
            return {
                "success": True,
                "message": success_msg,
                "chunks_processed": len(chunks),
                "filename": filename
            }
            
        except Exception as pinecone_error:
            # Log Pinecone errors but don't crash the server
            error_msg = f"Pinecone operation failed: {str(pinecone_error)}"
            logger.error(error_msg, exc_info=True)
            return {
                "success": False,
                "error": error_msg,
                "error_type": "pinecone_error"
            }
    
    except Exception as e:
        # Catch any other unexpected errors
        error_msg = f"PDF processing failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "error": error_msg,
            "error_type": "processing_error"
        }


def get_ingestion_stats() -> Dict[str, Any]:
    """
    Get statistics about documents in Pinecone index.
    
    Returns:
        Dictionary with index statistics
    """
    try:
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        pinecone_index_name = os.getenv("PINECONE_INDEX_NAME")
        
        if not pinecone_api_key or not pinecone_index_name:
            return {"error": "Pinecone credentials not configured"}
        
        pc = Pinecone(api_key=pinecone_api_key)
        index = pc.Index(pinecone_index_name)
        
        stats = index.describe_index_stats()
        
        return {
            "success": True,
            "total_vectors": stats.get("total_vector_count", 0),
            "dimension": stats.get("dimension", 0),
            "index_fullness": stats.get("index_fullness", 0)
        }
        
    except Exception as e:
        logger.error(f"Failed to get index stats: {str(e)}")
        return {"success": False, "error": str(e)}
