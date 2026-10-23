import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

def ingest_pdfs():
    print("Ingesting PDFs into Pinecone Enterprise Vector Store...")
    
    pdf_dir = "reports"
    if not os.path.exists(pdf_dir):
        print(f"Directory {pdf_dir} not found. Run generate_pdfs.py first.")
        return

    documents = []
    for file in os.listdir(pdf_dir):
        if file.endswith(".pdf"):
            loader = PyPDFLoader(os.path.join(pdf_dir, file))
            docs = loader.load()
            documents.extend(docs)
            print(f"Loaded {file}")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(documents)
    
    print(f"Split into {len(splits)} chunks.")
    
    # Enterprise Configuration
    api_key = os.getenv("OPENAI_API_KEY")
    pinecone_key = os.getenv("PINECONE_API_KEY")
    index_name = os.getenv("PINECONE_INDEX_NAME", "datascout")
    
    if not api_key or api_key.startswith("sk-placeholder"):
        print("❌ CRITICAL: OpenAI API Key missing. Cannot generate embeddings.")
        return

    # Using text-embedding-3-small with 512 dimensions as requested
    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        dimensions=512
    )

    print(f"Targeting Pinecone Index: {index_name}")
    
    # Create/Update Vector Store
    # Note: We assume the index already exists as per user provided details
    vectorstore = PineconeVectorStore.from_documents(
        documents=splits,
        embedding=embeddings,
        index_name=index_name
    )
    print("✅ Ingestion complete. Enterprise Knowledge Base updated.")

if __name__ == "__main__":
    # Load env vars if running directly
    from dotenv import load_dotenv
    load_dotenv()
    ingest_pdfs()
