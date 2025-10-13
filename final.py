import json
import os
import re
from typing import List, Dict, Any
import requests 

# --- Langchain Imports ---
# These imports are used for text splitting (chunking)
try:
    from langchain_core.documents import Document
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    # Minimal mock classes for execution safety if not installed
    class Document:
        def __init__(self, page_content: str, metadata: Dict[str, Any] = None):
            self.page_content = page_content
            self.metadata = metadata if metadata is not None else {}
        def dict(self):
            return {"page_content": self.page_content, "metadata": self.metadata}
    
    class RecursiveCharacterTextSplitter:
        def __init__(self, chunk_size, chunk_overlap): pass
        def split_documents(self, documents): return documents

# --- Local Model Imports ---
try:
    # Requires: pip install llama-cpp-python
    from llama_cpp import Llama
    LOCAL_MODEL_LOADED = True
except ImportError:
    LOCAL_MODEL_LOADED = False


# --- Configuration ---
MAX_BATCH_CHARS = 8000 * 4   # Proxy for 8K tokens
PHI4_MODEL_PATH = "/home/anand/Downloads/phi4.gguf" # !!! IMPORTANT: Ensure this path is correct for your local model


# ==============================================================================
# HELPER FUNCTIONS (Refactored from your pipeline)
# ==============================================================================

def estimate_char_length(chunk_data: Dict[str, Any]) -> int:
    """Estimates the character length of a chunk's content."""
    return len(chunk_data.get('page_content', ''))


def process_and_chunk_reddit_data(input_file_path: str, chunk_size: int = 2000, chunk_overlap: int = 200):
    """Loads raw Reddit JSON data, chunks the text, and saves chunks to the 'chunks' directory."""
    if not os.path.exists(input_file_path):
        print(f"Error: Input file {input_file_path} not found.")
        return 0

    with open(input_file_path, 'r', encoding='utf-8') as f:
        all_posts_data = json.load(f)

    documents: List[Document] = []
    for post in all_posts_data:
        # Combine post title and body for the document content
        content = (
            f"Title: {post.get('title', 'N/A')}\n"
            f"URL: {post.get('url', 'N/A')}\n"
            f"Post Body:\n{post.get('selftext', 'N/A')}"
        )
        url = post.get('url', '')
        subreddit = 'N/A'
        if '/r/' in url:
            try:
                if '/r/' in url:
                    subreddit_segment = url.split('/r/', 1)[1]
                    subreddit = subreddit_segment.split('/')[0]
            except IndexError:
                subreddit = 'N/A'

        metadata = {
            "source_url": post.get('url', 'N/A'),
            "post_title": post.get('title', 'N/A'),
            "subreddit": subreddit,
            "score": post.get('score')
        }
        documents.append(Document(page_content=content, metadata=metadata))

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    chunked_documents = text_splitter.split_documents(documents)
    
    chunk_dir = "chunks"
    os.makedirs(chunk_dir, exist_ok=True)
    
    # Clean old chunks
    for f in os.listdir(chunk_dir):
        if f.endswith('.json'):
            os.remove(os.path.join(chunk_dir, f))

    for i, chunk in enumerate(chunked_documents):
        # Use model_dump or dict based on Pydantic version
        try:
            chunk_data = chunk.model_dump() 
        except AttributeError:
            chunk_data = chunk.dict()
            
        chunk_filename = os.path.join(chunk_dir, f"chunk_{i+1:04d}.json")
        with open(chunk_filename, 'w', encoding='utf-8') as f:
            json.dump(chunk_data, f, indent=2, ensure_ascii=False)
            
    return len(chunked_documents)


def create_batches(chunks_dir_path: str = "chunks", max_batch_chars: int = MAX_BATCH_CHARS) -> int:
    """Merges individual chunks into batches and returns the batch count."""
    try:
        chunk_files = [f for f in os.listdir(chunks_dir_path) if f.endswith('.json')]
        chunk_files.sort()
    except FileNotFoundError:
        return 0

    batch_dir = "batches"
    os.makedirs(batch_dir, exist_ok=True)
    
    # Clean old batches
    for f in os.listdir(batch_dir):
        if f.endswith('.json'):
            os.remove(os.path.join(batch_dir, f))

    current_batch_content: List[Dict[str, Any]] = []
    current_batch_size_chars = 0
    batch_count = 1
    
    def save_batch():
        nonlocal batch_count, current_batch_content, current_batch_size_chars
        batch_filename = os.path.join(batch_dir, f"batch_{batch_count:02d}.json")
        with open(batch_filename, 'w', encoding='utf-8') as f:
            json.dump(current_batch_content, f, indent=2, ensure_ascii=False)
        batch_count += 1
        current_batch_content = []
        current_batch_size_chars = 0

    for filename in chunk_files:
        file_path = os.path.join(chunks_dir_path, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                chunk_data = json.load(f)
        except Exception:
            continue
            
        chunk_size_chars = estimate_char_length(chunk_data)
        
        if current_batch_size_chars + chunk_size_chars > max_batch_chars and current_batch_content:
            save_batch()
            current_batch_content = [chunk_data]
            current_batch_size_chars = chunk_size_chars
            
        else:
            current_batch_content.append(chunk_data)
            current_batch_size_chars += chunk_size_chars

    if current_batch_content:
        save_batch()
        
    return batch_count - 1 # Return number of batches created


def call_local_analysis(batch_content: str) -> List[Dict[str, Any]] | None:
    """Calls the local Phi4 GGUF model for multi-claim analysis."""
    if not LOCAL_MODEL_LOADED:
        print("Error: 'llama-cpp-python' is not installed. Cannot run local analysis.")
        return None
        
    try:
        # Initialize Llama model
        llm = Llama(
            model_path=PHI4_MODEL_PATH,
            n_ctx=18000, 
            n_gpu_layers=-1, # Use GPU if available
            verbose=False
        )
    except Exception as e:
        print(f"Error loading local model at {PHI4_MODEL_PATH}: {e}")
        return None
    
    # System prompt to define the model's role
    system_prompt = (
        "You are an expert fact-checker and journalist specializing in analyzing online discussions "
        "for misinformation. Your task is to review the provided Reddit content batch and identify the "
        "top 3 most significant, distinct factual claims being discussed across different posts/comments. "
        "Classify the veracity of each claim using your internal knowledge. "
        "Output the result strictly as a JSON array of objects."
    )
    
    # User query to enforce the task and the JSON structure
    user_query = f"""
    Analyze the following batch of Reddit posts and comments and extract the top 3 most significant factual claims.
    
    You must output a single JSON array containing exactly three objects. Each object must adhere exactly to the following structure:
    [
      {{
        "claim": "The specific factual statement or claim identified.",
        "classification": "The veracity: 'True', 'False', 'Misleading', or 'Unverifiable'.",
        "reason": "A concise explanation for the classification, referencing the content and supporting evidence.",
        "source": "Local Model Analysis (No real-time web search available)"
      }},
      // ... two more objects following the exact same structure
    ]

    CONTENT BATCH:
    ---
    {batch_content}
    ---
    
    Please output ONLY the JSON array.
    """
    
    try:
        stream_response = llm.create_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            temperature=0.3,
            max_tokens=3072,
            stream=False 
        )

        generated_text = stream_response['choices'][0]['message']['content']
        
        # Clean up JSON code fences if the model added them
        if generated_text.startswith("```"):
            generated_text = re.sub(r'^(```json|```)\s*', '', generated_text, flags=re.IGNORECASE)
            if generated_text.endswith("```"):
                generated_text = generated_text[:-3]

        return json.loads(generated_text)

    except Exception as e:
        print(f"Error during local model inference or JSON parsing: {e}")
        return None


def analyze_batches() -> List[Dict[str, Any]]:
    """Loads all batches, analyzes them, and returns a flat list of all claims."""
    batches_dir_path = "batches"
    
    try:
        batch_files = [f for f in os.listdir(batches_dir_path) if f.endswith('.json')]
        batch_files.sort()
    except FileNotFoundError:
        return []

    analysis_dir = "analysis_results"
    os.makedirs(analysis_dir, exist_ok=True)
    
    all_analysis_results = []
    
    for filename in batch_files:
        file_path = os.path.join(batches_dir_path, filename)
        batch_id = filename.split('.')[0]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                batch_data = json.load(f)
        except Exception:
            continue

        # Combine all chunks into one string for the LLM prompt
        full_batch_content = "\n\n--- NEXT CHUNK ---\n\n".join(
            item.get('page_content', '') for item in batch_data
        )

        analysis_result_list = call_local_analysis(full_batch_content)

        if analysis_result_list and isinstance(analysis_result_list, list):
            # Add metadata to each claim object
            for claim_data in analysis_result_list:
                claim_data['batch_id'] = batch_id
                claim_data['chunk_count'] = len(batch_data)
                
            all_analysis_results.extend(analysis_result_list)

    # Save the combined report (flat list of all claims)
    combined_filename = os.path.join(analysis_dir, "combined_analysis_report.json")
    if all_analysis_results:
        with open(combined_filename, 'w', encoding='utf-8') as f:
            json.dump(all_analysis_results, f, indent=2, ensure_ascii=False)
            
    return all_analysis_results


# ==============================================================================
# MAIN ORCHESTRATOR FUNCTION (The one imported by Streamlit)
# ==============================================================================

def run_full_analysis_pipeline(input_file: str = "reddit_search_output.json") -> List[Dict[str, Any]]:
    """Runs the entire pipeline from chunking to analysis and returns the results."""
    
    # 1. CHUNKING
    print("\n--- Starting Chunking ---")
    chunk_count = process_and_chunk_reddit_data(input_file)
    if chunk_count == 0:
        return []
    print(f"Chunking complete. Created {chunk_count} chunks.")

    # 2. BATCHING
    print("\n--- Starting Batching ---")
    batch_count = create_batches()
    if batch_count == 0:
        return []
    print(f"Batching complete. Created {batch_count} batches.")

    # 3. ANALYSIS
    print("\n--- Starting Analysis (Local LLM) ---")
    results = analyze_batches()
    print(f"Analysis pipeline finished. Total claims: {len(results)}")
    return results

if __name__ == '__main__':
    # This block is for testing the analysis flow independently
    if os.path.exists("reddit_search_output.json"):
        print("Running full analysis pipeline test...")
        results = run_full_analysis_pipeline()
        print(f"Total claims analyzed: {len(results)}")
    else:
        print("Test requires 'reddit_search_output.json' to exist.")

