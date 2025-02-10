import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
import re
from tools import read_url_content, web_scrape_for_llm, get_search_links
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain_community.vectorstores import FAISS
from urllib.parse import urljoin
import time
from googleapiclient.discovery import build

load_dotenv()
llm = ChatGoogleGenerativeAI(
    api_key=os.getenv("API_KEY"),
    model="gemini-2.0-flash",
    temperature=0.7,
    top_p=0.9,
    top_k=40,
    max_output_tokens=2048,
)

# Initialize embeddings model
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def should_use_rag(query: str) -> bool:
    """Let the model decide if the query needs RAG."""
    # Modified to almost always return True to prefer online searching
    return True  # Simplified to always use RAG by default

def get_search_links(query: str) -> list:
    """Get scientific research-focused search results."""
    try:
        # Create search service
        api_key = os.getenv("GOOGLE_API_KEY")
        cse_id = os.getenv("GOOGLE_CSE_ID")
        
        if not api_key or not cse_id:
            print("Missing Google API credentials")
            return []
            
        service = build("customsearch", "v1", developerKey=api_key)
        
        # Add scientific focus to the query
        scientific_query = f"{query} (site:.edu OR site:.gov OR site:nature.com OR site:science.org OR site:sciencedirect.com OR site:ncbi.nlm.nih.gov)"
        
        try:
            # Execute search
            result = service.cse().list(
                q=scientific_query,
                cx=cse_id,
                num=10  # Request more results
            ).execute()
            
            # Extract URLs
            links = []
            if "items" in result:
                for item in result["items"]:
                    url = item.get("link", "")
                    # Prioritize scientific domains
                    if any(domain in url.lower() for domain in [
                        '.edu', '.gov', 'nature.com', 'science.org', 
                        'sciencedirect.com', 'ncbi.nlm.nih.gov'
                    ]):
                        links.append(url)
            
            # Take top 5 unique links
            unique_links = list(dict.fromkeys(links))[:5]
            
            print(f"Found {len(unique_links)} scientific sources")
            if not unique_links:
                print("No scientific sources found, trying general search...")
                # Fallback to general search if no scientific sources found
                result = service.cse().list(
                    q=query,
                    cx=cse_id,
                    num=5
                ).execute()
                
                if "items" in result:
                    unique_links = [item.get("link", "") for item in result["items"]]
                    print(f"Found {len(unique_links)} general sources")
            
            return unique_links
            
        except Exception as e:
            print(f"Search API error: {str(e)}")
            return []
            
    except Exception as e:
        print(f"Search setup error: {str(e)}")
        return []

def web_scrape_for_llm(url: str, retries=1, delay=3, timeout=20):
    """Read content from a webpage."""
    try:
        # Use the read_url_content tool
        content = read_url_content(url)
        if not content:
            return f"Error: No content found for {url}"
            
        # Clean and format the content
        if isinstance(content, str):
            # Remove extra whitespace and normalize
            content = re.sub(r'\s+', ' ', content).strip()
            # Truncate if too long (to avoid token limits)
            if len(content) > 10000:
                content = content[:10000] + "..."
            return content
        return f"Error: Invalid content type for {url}"
    except Exception as e:
        return f"Error: Failed to read {url}: {str(e)}"

def create_vector_store(texts: list[str], sources: list[str]) -> FAISS:
    """Create a vector store from the given texts."""
    # Split texts into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    
    # Create documents with metadata
    documents = []
    for text, source in zip(texts, sources):
        chunks = text_splitter.create_documents([text], metadatas=[{"source": source}])
        documents.extend(chunks)
    
    # Create and return vector store
    vector_store = FAISS.from_documents(
        documents=documents,
        embedding=embeddings,
    )
    
    return vector_store

def setup_rag_chain(vector_store: FAISS) -> RetrievalQA:
    """Set up the RAG chain with the vector store."""
    prompt_template = """You are a specialized scientific research assistant. Use the following pieces of context to answer the question at the end.
    
    Guidelines for your response:
        1. Focus ONLY on scientific and research-related queries
    2. Break down complex scientific concepts into simpler explanations
    3. Include relevant technical details while making them accessible
    4. Cite specific studies or papers when available
    5. Explain scientific methodologies and their significance
    6. For technical terms, provide brief definitions in parentheses
    7. If relevant, mention practical applications of the research
    8. Acknowledge any limitations or uncertainties in the research
    9. For non-scientific queries, politely explain that you focus on scientific research topics
    
    1. Structure your response using proper markdown formatting:
       - Use # for main headings
       - Use ## for subheadings
       - Use bullet points (•) for lists
       - Use numbered lists for steps or sequences
       - Create tables using markdown syntax for comparing data
       - Use **bold** for emphasis on key terms
       - Use *italics* for scientific names
       - Use `code blocks` for technical specifications or data
       - Use > for important quotes or findings
       - Use --- for separating sections
    
    2. Your response should typically include:
       # Main Topic or Finding
       Brief introduction paragraph
       
       ## Key Concepts
       • Definition and explanation of important terms
       • Fundamental principles involved
       
       ## Technical Details
       • Detailed scientific explanation
       • Methodology or processes involved
       • Relevant equations or formulas in `code blocks`
       
       ## Research Context 
       • Current state of research
       • Notable studies or papers
       • Recent developments
       
       ## Practical Applications (if needed)
       • Real-world uses
       • Industry relevance
       • Future implications
       
       ## Summary 
       Concluding paragraph with key takeaways
       
       ---
       
       If data comparison is needed, use tables:
       | Parameter | Value | Significance |
       |-----------|--------|-------------|
       | Data 1    | Value 1| Impact 1    |
       
    3. Additional formatting rules:
       • Break down complex concepts step by step
       • Use clear section breaks between topics
       • Include source citations in a dedicated section
       • Format technical terms consistently
       • Use tables for comparing data when relevant
    
    Context: {context}
    
    Question: {question}
    
    Scientific Response: """

    PROMPT = PromptTemplate(
        template=prompt_template, input_variables=["context", "question"]
    )

    chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vector_store.as_retriever(search_kwargs={"k": 5}),
        return_source_documents=True,
        chain_type_kwargs={"prompt": PROMPT}
    )
    
    return chain

class ResearchSession:
    def __init__(self):
        self.conversation_history = []
        self.current_sources = []
        self.vector_store = None
    
    def add_to_history(self, role: str, content: str):
        """Add a message to conversation history."""
        self.conversation_history.append({"role": role, "content": content})
    
    def get_context_window(self, window_size: int = 5) -> str:
        """Get the recent conversation context."""
        recent_history = self.conversation_history[-window_size:] if len(self.conversation_history) > window_size else self.conversation_history
        return "\n\n".join([f"{msg['role']}: {msg['content']}" for msg in recent_history])

def process_url(url: str) -> tuple[str, list[str]]:
    """Process a URL and return its content and sources."""
    try:
        content = web_scrape_for_llm(url)
        if content.startswith("Error"):
            return content, []
        return content, [url]
    except Exception as e:
        return f"Error processing URL: {str(e)}", []

def get_dual_response(query: str, context: str = "") -> dict:
    """Get both general and technical responses for scientific queries."""
    general_prompt = f"""As a scientific research assistant, provide a clear, simple explanation that anyone can understand. 
    Focus on the main concepts and practical implications.
    
    Previous conversation context:
    {context}
    
    Current query: {query}
    
    Guidelines:
    • Use simple, everyday language
    • Explain concepts with analogies where possible
    • Focus on the "what" and "why" rather than technical details
    • Keep the explanation concise and engaging
    
    Response:"""

    technical_prompt = f"""As a scientific research assistant, provide a detailed technical analysis with academic depth.
    
    Previous conversation context:
    {context}
    
    Current query: {query}
    
    Structure your response using:
    
    # Technical Analysis
    Brief technical overview
    
    ## Core Concepts
    • Detailed technical definitions
    • Underlying principles
    • Mathematical formulations if applicable
    
    ## Methodology & Implementation
    • Technical processes
    • Research methods
    • Relevant equations or algorithms
    
    ## Research Context
    • Current state of research
    • Key studies and findings
    • Technical challenges and solutions
    
    ## Advanced Applications
    • Specialized use cases
    • Technical requirements
    • Implementation considerations
    
    Response:"""

    general_response = llm.invoke(general_prompt)
    technical_response = llm.invoke(technical_prompt)
    
    return {
        "general": general_response.content,
        "technical": technical_response.content
    }

def research_with_rag(query: str, session: ResearchSession = None, url: str = None) -> dict:
    """Main function to perform research using RAG."""
    if session is None:
        session = ResearchSession()
    
    session.add_to_history("user", query)
    
    # Check if it's a URL submission
    if url:
        print(f"Processing URL: {url}")
        content, sources = process_url(url)
        if not content.startswith("Error"):
            texts = [content]
            session.current_sources = sources
            session.vector_store = create_vector_store(texts, sources)
            response = {
                "content": "I've read and processed the content from the URL. You can now ask questions about it.",
                "sources": sources
            }
            session.add_to_history("assistant", response["content"])
            return response
        else:
            error_msg = f"Failed to process URL: {content}"
            session.add_to_history("assistant", error_msg)
            return {"content": error_msg, "sources": []}

    # Always try to get online information first
    print("Using RAG for current information...")
    
    # Get search links from Google
    links = get_search_links(query)
    if not links:
        print("No search results found, falling back to direct answer...")
        response = get_dual_response(query, session.get_context_window())
        session.add_to_history("assistant", response["general"])  # Store only general response in history
        return {
            "content": response,  # Now contains both general and technical responses
            "sources": []
        }
    
    print(f"Found {len(links)} potential sources")
    
    # Scrape content from all links
    texts = []
    valid_sources = []
    for link in links:
        try:
            print(f"Reading content from: {link}")
            content = web_scrape_for_llm(link)
            if content and not content.startswith("Error"):
                texts.append(content)
                valid_sources.append(link)
                print(f"Successfully read: {link}")
            else:
                print(f"Failed to read: {link}")
        except Exception as e:
            print(f"Error reading {link}: {str(e)}")
            continue
    
    if not texts:
        print("No valid sources found, falling back to direct answer...")
        response = get_dual_response(query, session.get_context_window())
        session.add_to_history("assistant", response["general"])  # Store only general response in history
        return {
            "content": response,  # Now contains both general and technical responses
            "sources": []
        }
    
    print(f"Processing {len(texts)} valid sources...")
    vector_store = create_vector_store(texts, valid_sources)
    
    # Setup RAG chain with conversation context
    chain = setup_rag_chain(vector_store)
    
    # Get the response with source documents
    context = session.get_context_window()
    augmented_query = f"""Previous conversation:\n{context}\n\nCurrent query: {query}"""
    
    result = chain({"query": augmented_query})
    
    # Process the RAG response to generate both views
    rag_response = result["result"]
    source_docs = result["source_documents"]
    
    # Generate dual response using the RAG results as additional context
    dual_response = get_dual_response(query, f"{context}\n\nResearch findings:\n{rag_response}")
    
    # Extract all unique sources while preserving order
    seen_sources = set()
    ordered_sources = []
    
    # First add sources from the source documents (most relevant)
    for doc in source_docs:
        if "source" in doc.metadata:
            source = doc.metadata["source"]
            if source not in seen_sources:
                ordered_sources.append(source)
                seen_sources.add(source)
    
    # Then add any remaining valid sources that weren't in source_docs
    for source in valid_sources:
        if source not in seen_sources:
            ordered_sources.append(source)
            seen_sources.add(source)
    
    session.add_to_history("assistant", dual_response["general"])
    return {
        "content": dual_response,
        "sources": ordered_sources
    }

# Example usage
if __name__ == "__main__":
    query = "Elon Musk"
    answer = research_with_rag(query)
    print(f"\nAnswer: {answer}")
