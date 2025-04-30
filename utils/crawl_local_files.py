import os
import fnmatch

def chunk_text(text, chunk_size=4000, overlap=200):
    """
    Split text into chunks of specified size with overlap.
    
    Args:
        text (str): Text to chunk
        chunk_size (int): Maximum size of each chunk
        overlap (int): Overlap between chunks
        
    Returns:
        list: List of text chunks
    """
    if not text:
        return []
        
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = min(start + chunk_size, text_len)
        
        # If not at the end and not at a newline, try to find a good break point
        if end < text_len and text[end] != '\n':
            # Try to find a newline or period to break at
            newline_pos = text.rfind('\n', start, end)
            period_pos = text.rfind('. ', start, end)
            space_pos = text.rfind(' ', start, end)
            
            # Use the latest good break point
            if newline_pos > start + chunk_size // 2:
                end = newline_pos + 1
            elif period_pos > start + chunk_size // 2:
                end = period_pos + 2
            elif space_pos > start + chunk_size // 2:
                end = space_pos + 1
        
        chunks.append(text[start:end])
        
        # Move start position for next chunk, including overlap
        start = max(start, end - overlap) if end < text_len else text_len
        
        # Avoid getting stuck in an infinite loop
        if start >= end:
            break
            
    return chunks

def crawl_local_files(directory, include_patterns=None, exclude_patterns=None, max_file_size=None, 
                      use_relative_paths=True, chunk_size=4000, chunk_overlap=200, enable_chunking=False):
    """
    Crawl files in a local directory with similar interface as crawl_github_files.
    
    Args:
        directory (str): Path to local directory
        include_patterns (set): File patterns to include (e.g. {"*.py", "*.js"})
        exclude_patterns (set): File patterns to exclude (e.g. {"tests/*"})
        max_file_size (int): Maximum file size in bytes
        use_relative_paths (bool): Whether to use paths relative to directory
        chunk_size (int): Maximum size of each chunk if enable_chunking is True
        chunk_overlap (int): Overlap between chunks if enable_chunking is True
        enable_chunking (bool): Whether to chunk large files
        
    Returns:
        dict: {"files": {filepath: content}} or 
              {"files": {filepath_chunk_N: content}} if chunking is enabled
    """
    if not os.path.isdir(directory):
        raise ValueError(f"Directory does not exist: {directory}")
        
    files_dict = {}
    
    for root, _, files in os.walk(directory):
        for filename in files:
            filepath = os.path.join(root, filename)
            
            # Get path relative to directory if requested
            if use_relative_paths:
                relpath = os.path.relpath(filepath, directory)
            else:
                relpath = filepath
                
            # Check if file matches any include pattern
            included = False
            if include_patterns:
                for pattern in include_patterns:
                    if fnmatch.fnmatch(relpath, pattern):
                        included = True
                        break
            else:
                included = True
                
            # Check if file matches any exclude pattern
            excluded = False
            if exclude_patterns:
                for pattern in exclude_patterns:
                    if fnmatch.fnmatch(relpath, pattern):
                        excluded = True
                        break
                        
            if not included or excluded:
                continue
                
            # Check file size
            if max_file_size and os.path.getsize(filepath) > max_file_size:
                continue
                
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if enable_chunking:
                    chunks = chunk_text(content, chunk_size, chunk_overlap)
                    if chunks:
                        for i, chunk in enumerate(chunks):
                            chunk_key = f"{relpath}#chunk_{i+1}"
                            files_dict[chunk_key] = chunk
                    else:
                        # If no chunks (empty file), still include it
                        files_dict[relpath] = content
                else:
                    files_dict[relpath] = content
            except Exception as e:
                print(f"Warning: Could not read file {filepath}: {e}")
                
    return {"files": files_dict}

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Crawl local files with chunking support")
    parser.add_argument("--dir", default="..", help="Directory to crawl")
    parser.add_argument("--chunk", action="store_true", help="Enable chunking")
    parser.add_argument("--chunk-size", type=int, default=4000, help="Chunk size")
    parser.add_argument("--overlap", type=int, default=200, help="Chunk overlap")
    args = parser.parse_args()
    
    print(f"--- Crawling directory '{args.dir}' {'with chunking' if args.chunk else 'without chunking'} ---")
    files_data = crawl_local_files(
        args.dir, 
        exclude_patterns={"*.pyc", "__pycache__/*", ".git/*", "output/*", "*.jpg", "*.png", "*.pdf"},
        enable_chunking=args.chunk,
        chunk_size=args.chunk_size,
        chunk_overlap=args.overlap
    )
    print(f"Found {len(files_data['files'])} {'chunks' if args.chunk else 'files'}:")
    for i, path in enumerate(list(files_data["files"].keys())[:10]):
        print(f"  {path}")
    if len(files_data["files"]) > 10:
        print(f"  ... and {len(files_data['files']) - 10} more")