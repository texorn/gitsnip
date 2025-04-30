import os
import sys
import json
from utils.crawl_local_files import crawl_local_files

def prepare_codebase_chunks(directory, chunk_size=4000, chunk_overlap=200, include_patterns=None, exclude_patterns=None):
    """
    Prepares a codebase by chunking files for LLM processing.
    
    Args:
        directory (str): Path to codebase directory
        chunk_size (int): Maximum size of each chunk
        chunk_overlap (int): Overlap between chunks
        include_patterns (set): File patterns to include (e.g. {"*.py", "*.js"})
        exclude_patterns (set): File patterns to exclude (e.g. {"tests/*"})
        
    Returns:
        dict: {"chunks": [{filepath, content, chunk_number, total_chunks}]}
    """
    if exclude_patterns is None:
        exclude_patterns = {"*.pyc", "__pycache__/*", ".git/*", "node_modules/*", "*.jpg", "*.png", "*.gif", "*.pdf"}
    
    # Check if we should use large chunk mode (combine multiple files into chunks)
    use_large_chunk_mode = chunk_size > 100000
    
    if use_large_chunk_mode:
        print(f"Using large chunk mode: combining multiple files into chunks of ~{chunk_size} characters")
        # First, get all files without chunking
        from utils.crawl_local_files import crawl_local_files as get_files
        files_data = get_files(
            directory,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            enable_chunking=False
        )
        
        # Sort files by size (smallest first)
        sorted_files = sorted(files_data["files"].items(), key=lambda x: len(x[1]))
        
        # Build chunks by combining files until we reach chunk_size
        chunks_list = []
        current_chunk_files = []
        current_chunk_size = 0
        
        for filepath, content in sorted_files:
            # If adding this file would exceed chunk_size, create a chunk
            if current_chunk_size > 0 and current_chunk_size + len(content) > chunk_size:
                # Create a chunk from accumulated files
                chunks_list.append({
                    "filepath": ", ".join(current_chunk_files),
                    "content": "\n\n".join([f"FILE: {f}\n```\n{files_data['files'][f]}\n```" for f in current_chunk_files]),
                    "chunk_number": len(chunks_list) + 1,
                    "total_chunks": -1  # Will update later
                })
                # Reset for next chunk
                current_chunk_files = []
                current_chunk_size = 0
            
            # Add file to current chunk
            current_chunk_files.append(filepath)
            current_chunk_size += len(content)
            
        # Add any remaining files as a final chunk
        if current_chunk_files:
            chunks_list.append({
                "filepath": ", ".join(current_chunk_files),
                "content": "\n\n".join([f"FILE: {f}\n```\n{files_data['files'][f]}\n```" for f in current_chunk_files]),
                "chunk_number": len(chunks_list) + 1,
                "total_chunks": -1
            })
        
        # Update total_chunks
        total_chunks = len(chunks_list)
        for chunk in chunks_list:
            chunk["total_chunks"] = total_chunks
            
        return {"chunks": chunks_list}
    else:
        # Crawl files with chunking enabled
        result = crawl_local_files(
            directory,
            include_patterns=include_patterns,
            exclude_patterns=exclude_patterns,
            enable_chunking=True,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        # Convert to a format more suitable for LLM consumption
        chunks_list = []
        
        # Group chunks by original file
        file_chunks = {}
        for chunk_key, content in result["files"].items():
            if "#chunk_" in chunk_key:
                filepath, chunk_info = chunk_key.split("#chunk_")
                chunk_number = int(chunk_info)
                
                if filepath not in file_chunks:
                    file_chunks[filepath] = []
                    
                file_chunks[filepath].append((chunk_number, content))
            else:
                # Single chunk file
                file_chunks[chunk_key] = [(1, content)]
        
        # Sort chunks by number and create entries
        for filepath, chunks in file_chunks.items():
            # Sort by chunk number
            chunks.sort(key=lambda x: x[0])
            total_chunks = len(chunks)
            
            for chunk_number, content in chunks:
                chunks_list.append({
                    "filepath": filepath,
                    "content": content,
                    "chunk_number": chunk_number,
                    "total_chunks": total_chunks
                })
        
        return {"chunks": chunks_list}

def format_codebase_context(chunks, max_chunks=5):
    """
    Format chunks into a context string suitable for LLM prompts.
    
    Args:
        chunks (list): List of chunk dictionaries
        max_chunks (int): Maximum number of chunks to include
        
    Returns:
        str: Formatted context string
    """
    context = []
    
    # Limit the number of chunks to avoid context window limits
    for i, chunk in enumerate(chunks[:max_chunks]):
        context.append(f"FILE: {chunk['filepath']} (Chunk {chunk['chunk_number']}/{chunk['total_chunks']})")
        context.append("```")
        context.append(chunk["content"])
        context.append("```")
        context.append("")
    
    if len(chunks) > max_chunks:
        context.append(f"... and {len(chunks) - max_chunks} more chunks not shown")
    
    return "\n".join(context)

def example_llm_prompt(chunks, query):
    """
    Create an example prompt that could be sent to an LLM.
    
    Args:
        chunks (list): List of chunk dictionaries
        query (str): User query about the codebase
        
    Returns:
        str: Formatted prompt
    """
    prompt = f"""
You are an AI assistant helping with code understanding.

USER QUERY: {query}

CODE CONTEXT:
{format_codebase_context(chunks)}

Based on the code context provided above, please answer the user's query.
"""
    return prompt

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Prepare codebase for LLM analysis with chunking")
    parser.add_argument("--dir", default=".", help="Directory to analyze")
    parser.add_argument("--query", default="Explain what this code does", help="Query to answer about the code")
    parser.add_argument("--chunk-size", type=int, default=4000, help="Chunk size")
    parser.add_argument("--overlap", type=int, default=200, help="Chunk overlap")
    parser.add_argument("--output", help="Output file for chunks (JSON)")
    args = parser.parse_args()
    
    # Prepare the codebase chunks
    result = prepare_codebase_chunks(
        args.dir,
        chunk_size=args.chunk_size,
        chunk_overlap=args.overlap
    )
    
    # Print statistics
    print(f"Found {len(result['chunks'])} chunks across {len(set(c['filepath'] for c in result['chunks']))} files")
    
    # Save to output file if specified
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)
        print(f"Chunks saved to {args.output}")
    
    # Show example prompt with first few chunks
    print("\nEXAMPLE LLM PROMPT:")
    print("-" * 80)
    print(example_llm_prompt(result["chunks"], args.query))
    print("-" * 80)
    
    