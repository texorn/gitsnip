import os
import yaml
import numpy as np  # Add numpy for embedding operations
from pocketflow import Node, BatchNode
from utils.crawl_github_files import crawl_github_files
from utils.call_llm import call_llm
from utils.crawl_local_files import crawl_local_files
from utils.get_embedding import get_embedding, cluster_embeddings
import pickle
import hashlib
import time

# Helper to get content for specific file indices
def get_content_for_indices(files_data, indices):
    content_map = {}
    for i in indices:
        if 0 <= i < len(files_data):
            path, content = files_data[i]
            content_map[f"{i} # {path}"] = content 
    return content_map


# Users can adjust this value based on their LLM of choice
MAX_CONTEXT_SIZE = 8000000  

class FetchRepo(Node):
    def __init__(self, max_retries=1, wait=0):
        super().__init__(max_retries=max_retries, wait=wait)
        self.callbacks = []
    
    def add_callback(self, callback):
        """Add a callback function that will be executed after this node runs"""
        self.callbacks.append(callback)

    def prep(self, shared):
        repo_url = shared.get("repo_url")
        local_dir = shared.get("local_dir")
        project_name = shared.get("project_name")

        if not project_name:
            # Basic name derivation from URL or directory
            if repo_url:
                project_name = repo_url.split('/')[-1].replace('.git', '')
            else:
                project_name = os.path.basename(os.path.abspath(local_dir))
            shared["project_name"] = project_name

        # Get file patterns directly from shared
        include_patterns = shared["include_patterns"]
        exclude_patterns = shared["exclude_patterns"]
        max_file_size = shared["max_file_size"]

        return {
            "repo_url": repo_url,
            "local_dir": local_dir,
            "token": shared.get("github_token"),
            "include_patterns": include_patterns,
            "exclude_patterns": exclude_patterns,
            "max_file_size": max_file_size,
            "use_relative_paths": True
        }

    def exec(self, prep_res):
        if prep_res["repo_url"]:
            print(f"Crawling repository: {prep_res['repo_url']}...")
            result = crawl_github_files(
                repo_url=prep_res["repo_url"],
                token=prep_res["token"],
                include_patterns=prep_res["include_patterns"],
                exclude_patterns=prep_res["exclude_patterns"],
                max_file_size=prep_res["max_file_size"],
                use_relative_paths=prep_res["use_relative_paths"]
            )
        else:
            print(f"Crawling directory: {prep_res['local_dir']}...")
            result = crawl_local_files(
                directory=prep_res["local_dir"],
                include_patterns=prep_res["include_patterns"],
                exclude_patterns=prep_res["exclude_patterns"],
                max_file_size=prep_res["max_file_size"],
                use_relative_paths=prep_res["use_relative_paths"]
            )

        files_list = list(result.get("files", {}).items())
        if len(files_list) == 0:
            raise(ValueError("Failed to fetch files"))
        print(f"Fetched {len(files_list)} files.")
        return files_list

    def post(self, shared, prep_res, exec_res):
        shared["files"] = exec_res 
        
        # Execute any registered callbacks
        for callback in self.callbacks:
            callback(shared)
            
        return "default"

class IdentifyAbstractions(Node):
    def prep(self, shared):
        files_data = shared["files"]
        project_name = shared["project_name"]
        language = shared.get("language", "english")
        output_dir = shared.get("output_dir", "./output")

        print(f"Preparing to identify abstractions from {len(files_data)} files...")
        
        # Calculate initial content size for informational purposes only
        initial_content_size = sum(len(content) for _, content in files_data)
        print(f"Initial codebase size: {initial_content_size/1000000:.2f}MB ({initial_content_size} chars)")
        
        # Filter out non-code and extremely large files in any case
        INDIVIDUAL_FILE_SIZE_LIMIT = 1000000  # Skip individual files larger than 1MB
        filtered_files = []
        skipped_count = {"virtual_env": 0, "node_modules": 0, "size": 0, "other": 0}
        
        for path, content in files_data:
            # Skip virtual environment files and node modules
            if "venv/" in path:
                skipped_count["virtual_env"] += 1
                continue
            elif "node_modules/" in path:
                skipped_count["node_modules"] += 1
                continue
            # Skip very large files
            elif len(content) > INDIVIDUAL_FILE_SIZE_LIMIT:
                skipped_count["size"] += 1
                continue
                
            # Add to filtered list
            filtered_files.append((path, content))
        
        # Calculate the filtered content size 
        filtered_content_size = sum(len(content) for _, content in filtered_files)
        
        total_skipped = sum(skipped_count.values())
        print(f"Using {len(filtered_files)} files after filtering ({total_skipped} files skipped)")
        print(f"  - Virtual env files skipped: {skipped_count['virtual_env']}")
        print(f"  - Node modules skipped: {skipped_count['node_modules']}")
        print(f"  - Large files skipped: {skipped_count['size']}")
        print(f"Filtered codebase size: {filtered_content_size/1000000:.2f}MB ({filtered_content_size} chars)")
        
        # Choose approach based on FILTERED content size
        if filtered_content_size <= MAX_CONTEXT_SIZE and len(filtered_files) <= 100:
            print(f"Filtered codebase is small enough to process directly with LLM context window")
            return self._direct_llm_approach(filtered_files, project_name, language)
        else:
            print(f"Filtered codebase exceeds context limit, using embedding-based clustering approach")
            return self._embedding_approach(filtered_files, files_data, project_name, language)

    def _direct_llm_approach(self, filtered_files, project_name, language):
        """Process smaller codebases by sending content directly to the LLM"""
        # Create context from all filtered files
        context = ""
        file_info = []  
        
        for i, (path, content) in enumerate(filtered_files):
            # Truncate very large files
            if len(content) > 20000:
                content = content[:20000] + "\n... (content truncated for brevity) ...\n"
                
                entry = f"--- File Index {i}: {path} ---\n{content}\n\n"
                context += entry
                file_info.append((i, path))

        # Format file info for the prompt
        file_listing_for_prompt = "\n".join([f"- {idx} # {path}" for idx, path in file_info])
        
        # Include metadata about files
        context_prefix = f"""
ANALYSIS CONTEXT:
- Project Name: {project_name}
- Total Files Analyzed: {len(filtered_files)}
- Context Size: {len(context)/1000:.1f}KB

"""
        context = context_prefix + context
        
        # Add language instruction for non-English responses if needed
        language_instruction = ""
        name_lang_hint = ""
        desc_lang_hint = ""
        if language.lower() != "english":
            language_instruction = f"IMPORTANT: Generate the `name` and `description` for each abstraction in **{language.capitalize()}** language. Do NOT use English for these fields.\n\n"
            name_lang_hint = f" (value in {language.capitalize()})"
            desc_lang_hint = f" (value in {language.capitalize()})"

        # Create prompt for LLM
        prompt = f"""
For the project `{project_name}`:

{language_instruction}Analyze the following codebase context to identify the core abstractions.
Identify the top 5-10 most important abstractions that would help a new developer understand this codebase.

For each abstraction, provide:
1. A concise `name`{name_lang_hint} that clearly identifies the component.
2. A beginner-friendly `description` explaining what it does with a simple analogy if possible, in around 100 words{desc_lang_hint}.
3. A list of relevant `file_indices` from the codebase that implement this abstraction.

Codebase Context:
{context}

List of file indices and paths present in the context:
{file_listing_for_prompt}

Your response MUST be in the following YAML format and nothing else:

```yaml
- name: |
    Query Processing{name_lang_hint}
  description: |
    Explains what the abstraction does.
    It's like a central dispatcher routing requests.{desc_lang_hint}
  file_indices:
    - 0 # path/to/file1.py
    - 3 # path/to/related.py
- name: |
    Query Optimization{name_lang_hint}
  description: |
    Another core concept, similar to a blueprint for objects.{desc_lang_hint}
  file_indices:
    - 5 # path/to/another.js
# ... up to 10 abstractions
```"""

        print("Identifying abstractions using direct LLM approach...")
        response = call_llm(prompt)

        # Parse YAML response
        try:
            # Try different YAML formats
            yaml_str = ""
            if "```yaml" in response:
                yaml_str = response.split("```yaml")[1].split("```")[0].strip()
            elif "```" in response:
                yaml_blocks = response.split("```")
                if len(yaml_blocks) >= 3:
                    yaml_str = yaml_blocks[1].strip()
            else:
                yaml_str = response.strip()
                
            abstractions = yaml.safe_load(yaml_str)

            # Handle case where YAML parsed but not as expected list
            if not isinstance(abstractions, list):
                print("WARNING: YAML parsed but not as a list. Attempting to wrap it...")
                abstractions = [abstractions]
                
        except Exception as e:
            print(f"Error parsing YAML: {e}")
            print("Could not parse response. Creating default abstractions...")
            return self._create_default_abstractions(filtered_files, 1)
        
        # Validate and convert the abstractions
        validated_abstractions = []
        for item in abstractions:
            # Skip invalid items
            if not isinstance(item, dict):
                continue
                
            # Ensure required fields
            if "name" not in item or "description" not in item:
                continue
                
            # Extract file indices
            file_indices = []
            if "file_indices" in item and isinstance(item["file_indices"], list):
                for idx_entry in item["file_indices"]:
                    try:
                        if isinstance(idx_entry, int):
                            idx = idx_entry
                        elif isinstance(idx_entry, str) and '#' in idx_entry:
                            idx = int(idx_entry.split('#')[0].strip())
                        else:
                            idx = int(str(idx_entry).strip())

                        if 0 <= idx < len(filtered_files):
                            # Map to global file index
                            for global_idx, (global_path, _) in enumerate(files_data):
                                if filtered_files[idx][0] == global_path:
                                    file_indices.append(global_idx)
                                    break
                    except (ValueError, TypeError):
                        continue

            # Add validated abstraction
            validated_abstractions.append({
                "name": item["name"],
                "description": item["description"],
                "files": sorted(list(set(file_indices)))
            })
            
        # Ensure we have at least some abstractions
        if not validated_abstractions:
            print("No valid abstractions found. Creating defaults...")
            return self._create_default_abstractions(filtered_files, 1)
            
        print(f"Identified {len(validated_abstractions)} abstractions using direct LLM approach")
        return validated_abstractions

    def _embedding_approach(self, filtered_files, original_files, project_name, language):
        """Process larger codebases using embeddings and clustering with improved chunking"""
        from utils.get_embedding import get_embedding, cluster_embeddings
        
        print(f"Generating embeddings for {len(filtered_files)} files...")
        
        file_paths = [path for path, _ in filtered_files]
        file_contents = [content for _, content in filtered_files]
        

        embeddings = []
        CHUNK_SIZE = 8000  # Typical embedding model token limit (approx chars)
        OVERLAP = 1000  # Overlap between chunks to maintain context
        
        for i, content in enumerate(file_contents):
            if i % 100 == 0 and i > 0:
                print(f"Generated {i}/{len(file_contents)} embeddings...")
            
            # Enhanced chunking for large files
            if len(content) <= CHUNK_SIZE:
                # For small files, use the entire content
                embedding = get_embedding(content)
                embeddings.append(embedding)
            else:
                # For large files, chunk and average embeddings
                chunks = []
                for j in range(0, len(content), CHUNK_SIZE - OVERLAP):
                    chunk = content[j:j + CHUNK_SIZE]
                    if len(chunk) > 200:  # Skip tiny chunks
                        chunks.append(chunk)
                
                # Get embedding for each chunk
                chunk_embeddings = []
                for chunk in chunks:
                    chunk_embedding = get_embedding(chunk)
                    chunk_embeddings.append(chunk_embedding)
                
                # Average the embeddings to get a representative embedding for the file
                if chunk_embeddings:
                    file_embedding = np.mean(chunk_embeddings, axis=0).tolist()
                    embeddings.append(file_embedding)
                else:
                    # Fallback if chunking failed
                    embedding = get_embedding(content[:CHUNK_SIZE])
                    embeddings.append(embedding)
        
        # Determine optimal number of clusters
        file_count = len(file_paths)
        if file_count < 20:
            n_clusters = min(5, max(2, file_count // 2))
        else:
            n_clusters = min(10, max(5, file_count // 500 + 5))
            
        print(f"Clustering {len(embeddings)} files into {n_clusters} groups...")
        
        # Cluster the embeddings
        clusters = cluster_embeddings(embeddings, n_clusters=n_clusters)
        
        # Group files by cluster
        cluster_groups = {}
        for i, cluster_id in enumerate(clusters):
            if cluster_id not in cluster_groups:
                cluster_groups[cluster_id] = []
            cluster_groups[cluster_id].append(i)
        
        # Calculate index mapping for all files
        index_mapping = {}
        for i, (path, _) in enumerate(filtered_files):
            # Find matching path in original files
            for global_idx, (global_path, _) in enumerate(original_files):
                if path == global_path:
                    index_mapping[i] = global_idx
                    break
                    
        # Process each cluster with improved LLM analysis
        abstractions = []
        MAX_FILES_PER_BATCH = 10
        
        for cluster_id, file_indices in sorted(cluster_groups.items()):
            # Derive cluster name from common directory or file patterns (as before)
            dirs = {}
            extensions = {}
            
            for i in file_indices:
                path = file_paths[i]
                directory = os.path.dirname(path)
                if directory not in dirs:
                    dirs[directory] = 0
                dirs[directory] += 1
                
                ext = os.path.splitext(path)[1]
                if ext and ext not in extensions:
                    extensions[ext] = 0
                if ext:
                    extensions[ext] += 1
            
            most_common_dir = max(dirs.items(), key=lambda x: x[1])[0] if dirs else ""
            most_common_ext = max(extensions.items(), key=lambda x: x[1])[0] if extensions else ""
            
            # Create initial abstraction name
            if most_common_dir:
                dir_name = os.path.basename(most_common_dir.rstrip('/'))
                abstraction_name = dir_name.replace('_', ' ').replace('-', ' ').title()
                if not abstraction_name:
                    abstraction_name = "Core Module"
            else:
                abstraction_name = "Component"
                
            if most_common_ext:
                ext_type = most_common_ext.strip('.').upper()
                if ext_type in ['PY', 'JS', 'TS', 'GO', 'JAVA', 'CPP', 'CS']:
                    abstraction_name += f" ({ext_type})"
            
            # Process all files in batches
            batch_analyses = []
            for j in range(0, len(file_indices), MAX_FILES_PER_BATCH):
                batch_file_indices = file_indices[j:j + MAX_FILES_PER_BATCH]
                print(f"Analyzing batch {j//MAX_FILES_PER_BATCH + 1} of cluster {cluster_id} ({len(batch_file_indices)} files)...")
                
                batch_analysis = self._analyze_file_batch(
                    file_paths, 
                    file_contents, 
                    batch_file_indices, 
                    cluster_id, 
                    batch_num=j//MAX_FILES_PER_BATCH
                )
                batch_analyses.append(batch_analysis)
            
            if len(batch_analyses) == 1:
                name, description = batch_analyses[0]
            else:
                print(f"Synthesizing analyses from {len(batch_analyses)} batches for cluster {cluster_id}...")
                synthesis_prompt = f"""
Synthesize these {len(batch_analyses)} analyses of related code files into:
1. A concise name for this group of files (5 words max)
2. A brief description of what functionality these files implement (2-3 sentences)

The analyses:
{chr(10).join([f"BATCH {i+1}:\nNAME: {analysis[0]}\nDESCRIPTION: {analysis[1]}" for i, analysis in enumerate(batch_analyses)])}

Format as:
NAME: [Your suggested name]
DESCRIPTION: [Your description]
"""
                response = call_llm(synthesis_prompt)
                
                # Parse name and description
                try:
                    if "NAME:" in response and "DESCRIPTION:" in response:
                        name = response.split("NAME:")[1].split("DESCRIPTION:")[0].strip()
                        description = response.split("DESCRIPTION:")[1].strip()
                    else:
                        # Fallback to first batch
                        name, description = batch_analyses[0]
                except Exception as e:
                    print(f"Error synthesizing batch analyses: {e}")
                    name, description = batch_analyses[0]
            
            # Map sample indices to global indices
            global_indices = [index_mapping[i] for i in file_indices if i in index_mapping]
            
            # Add to abstractions list
            abstractions.append({
                "name": name,
                "description": description,
                "files": global_indices
            })
        
        # Rank abstractions by importance
        print("Ranking abstractions by importance...")
        ranked_abstractions = self._rank_abstractions_importance(abstractions, project_name)
        
        # --- Add uniqueness check for abstraction names ---
        final_abstractions = []
        seen_names = {}
        for abstr in ranked_abstractions:
            name = abstr["name"]
            original_name = name
            count = 1
            # Append a number if the name is already seen
            while name in seen_names:
                count += 1
                name = f"{original_name} ({count})"
            
            seen_names[name] = True # Mark this name as seen
            abstr["name"] = name # Update the abstraction name if modified
            final_abstractions.append(abstr)
        # --- End uniqueness check ---
        
        print(f"Identified {len(final_abstractions)} unique abstractions through improved clustering.")
        # Return the list with unique names
        return final_abstractions

    def _analyze_file_batch(self, file_paths, file_contents, batch_indices, cluster_id, batch_num=0):
        """Analyze a batch of files using LLM with distributed sampling"""
        MAX_SAMPLE_CHARS = 5000
        
        sample_contents = []
        
        for i in batch_indices:
            content = file_contents[i]
            path = file_paths[i]
            
            # If file is small enough, use entire content
            if len(content) <= MAX_SAMPLE_CHARS:
                sample = content
            else:
                # For large files, create a distributed sample
                file_length = len(content)
                
                # Take samples from beginning, middle and end
                beginning = content[:MAX_SAMPLE_CHARS // 3]
                
                middle_start = (file_length // 2) - (MAX_SAMPLE_CHARS // 6)
                middle = content[middle_start:middle_start + (MAX_SAMPLE_CHARS // 3)]
                
                end_start = file_length - (MAX_SAMPLE_CHARS // 3)
                end = content[end_start:]
                
                # Combine with markers
                sample = (beginning + 
                         "\n\n... (omitted content) ...\n\n" + 
                         middle + 
                         "\n\n... (omitted content) ...\n\n" + 
                         end)
                
                # Send to LLM to identify important parts
                selection_prompt = f"""
I'm showing you samples from beginning, middle, and end of a large code file: {path}
Based on these samples, identify the 3-4 most important code sections that best represent this file's functionality.

File samples:
```
{sample}
```

Return ONLY the selected important code sections in this format:
IMPORTANT SECTIONS:
```
[First important section code]
```

```
[Second important section code]
```

... and so on. Do not include any other commentary.
"""
                # Call LLM to identify important sections
                important_sections = call_llm(selection_prompt)
                
                # Extract the identified important sections
                if "IMPORTANT SECTIONS:" in important_sections:
                    sections_text = important_sections.split("IMPORTANT SECTIONS:")[1].strip()
                    # Create final sample with LLM-selected important parts
                    sample = "--- BEGINNING OF FILE ---\n" + beginning[:1000] + "\n\n"
                    sample += "--- LLM-SELECTED IMPORTANT SECTIONS ---\n" + sections_text
                # Use original sample as fallback if parsing fails
            
            sample_contents.append(f"--- {path} ---\n{sample}")
        
        # Combine all samples
        full_sample = "\n\n".join(sample_contents)
        
        # Regular analysis prompt
        prompt = f"""
Analyze these related code files which were automatically grouped together (Cluster {cluster_id}, Batch {batch_num}):

{full_sample}

Please provide:
1. A concise, accurate name for this group of files (5 words max)
2. A brief description of what functionality these files likely implement (2-3 sentences)

Format the response as:
NAME: [Your suggested name]
DESCRIPTION: [Your description]
"""
        
        response = call_llm(prompt)
        
        # Parse name and description
        name = f"Cluster {cluster_id} Files"
        description = f"A component containing {len(batch_indices)} files."
        
        try:
            if "NAME:" in response and "DESCRIPTION:" in response:
                name_part = response.split("NAME:")[1].split("DESCRIPTION:")[0].strip()
                if name_part and len(name_part) < 100:
                    name = name_part
                    
                desc_part = response.split("DESCRIPTION:")[1].strip()
                if desc_part and len(desc_part) < 500:
                    description = desc_part
        except Exception as e:
            print(f"Error parsing LLM response: {e}")
        
        return name, description

    def _rank_abstractions_importance(self, abstractions, project_name):
        """Rank abstractions by importance to core functionality"""
        # Create prompt for LLM
        abstraction_list = "\n".join([f"- {i}: {a['name']}\n  {a['description']}" 
                                     for i, a in enumerate(abstractions)])
        
        prompt = f"""
For the project {project_name}, rank these code abstractions by their importance 
to the core functionality (most important first):

{abstraction_list}

Return ONLY a comma-separated list of abstraction indices in descending order of importance.
For example: 2,0,3,1,4
"""
        
        response = call_llm(prompt)
        try:
            # Parse comma-separated indices
            importance_order = [int(idx.strip()) for idx in response.split(',')]
            
            # Validate indices
            valid_indices = [i for i in importance_order if 0 <= i < len(abstractions)]
            
            # Add any missing indices at the end
            all_indices = set(range(len(abstractions)))
            missing_indices = all_indices - set(valid_indices)
            complete_order = valid_indices + list(missing_indices)
            
            # Reorder abstractions by importance
            ranked_abstractions = [abstractions[i] for i in complete_order]
            return ranked_abstractions
        except Exception as e:
            print(f"Error ranking abstractions: {e}. Using original order.")
            return abstractions
    
    def _create_default_abstractions(self, files, method):
        """Create default fallback abstractions when other methods fail"""
        print(f"Creating default abstractions using method {method}")
        
        # Method 1: Simple file-based defaults
        if method == 1:
            if not files:
                return [{
                    "name": "Main Component",
                    "description": "The core functionality of the project",
                    "files": [0]
                }]
                
            # Group by directories
            dir_files = {}
            for i, (path, _) in enumerate(files):
                directory = os.path.dirname(path)
                if not directory:
                    directory = "Root"
                if directory not in dir_files:
                    dir_files[directory] = []
                dir_files[directory].append(i)
                
            # Create abstractions for top directories
            abstractions = []
            for dir_name, indices in sorted(dir_files.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
                basename = os.path.basename(dir_name) if dir_name != "Root" else "Core"
                name = basename.replace("_", " ").replace("-", " ").title() + " Module"
                description = f"Files located in the {basename} directory, likely handling related functionality."
                
                abstractions.append({
                    "name": name,
                    "description": description,
                    "files": indices[:10]  # Limit to 10 files per abstraction
                })
                
            return abstractions
            
        # Method 2: Extension-based defaults
        else:
            if not files:
                return [{
                    "name": "Main Component",
                    "description": "The core functionality of the project",
                    "files": [0]
                }]
                
            # Group by extension
            ext_files = {}
            for i, (path, _) in enumerate(files):
                ext = os.path.splitext(path)[1]
                if not ext:
                    ext = "No Extension"
                if ext not in ext_files:
                    ext_files[ext] = []
                ext_files[ext].append(i)
                
            # Create abstractions for top extensions
            abstractions = []
            for ext, indices in sorted(ext_files.items(), key=lambda x: len(x[1]), reverse=True)[:5]:
                if ext == "No Extension":
                    name = "Configuration Files"
                elif ext.lower() in [".py", ".js", ".ts", ".go", ".java", ".c", ".cpp"]:
                    name = f"{ext.strip('.').upper()} Codebase"
                else:
                    name = f"{ext.strip('.').upper()} Files"
                    
                description = f"Files with {ext} extension, likely handling related functionality."
                
                abstractions.append({
                    "name": name,
                    "description": description,
                    "files": indices[:10]  # Limit to 10 files per abstraction
                })
                
            return abstractions

    def post(self, shared, prep_res, exec_res):
        shared["abstractions"] = prep_res  # In this case, the work is done in prep
        return "default"

class AnalyzeRelationships(Node):
    def prep(self, shared):
        abstractions = shared["abstractions"] # Now contains 'files' list of indices, name/description potentially translated
        files_data = shared["files"]
        project_name = shared["project_name"]  # Get project name
        language = shared.get("language", "english") # Get language

        # Create context with abstraction names, indices, descriptions, and relevant file snippets
        context = "Identified Abstractions:\n"
        all_relevant_indices = set()
        abstraction_info_for_prompt = []
        for i, abstr in enumerate(abstractions):
            # Use 'files' which contains indices directly
            file_indices_str = ", ".join(map(str, abstr['files']))
            # Abstraction name and description might be translated already
            info_line = f"- Index {i}: {abstr['name']} (Relevant file indices: [{file_indices_str}])\n  Description: {abstr['description']}"
            context += info_line + "\n"
            abstraction_info_for_prompt.append(f"{i} # {abstr['name']}") # Use potentially translated name here too
            all_relevant_indices.update(abstr['files'])

        context += "\nRelevant File Snippets (Referenced by Index and Path):\n"
        
        # Get content for relevant files using helper
        relevant_files_content_map = get_content_for_indices(
            files_data,
            sorted(list(all_relevant_indices))
        )
        
        # For large codebases, trim the file content to avoid excessive context
        MAX_CHARS_PER_FILE = 3000  # Maximum chars per file
        MAX_TOTAL_CHARS = 30000  # Maximum total characters for all files
        
        # Format file content for context with limits
        trimmed_content_map = {}
        total_chars = 0
        
        for idx_path, content in relevant_files_content_map.items():
            # Trim content if too large
            if len(content) > MAX_CHARS_PER_FILE:
                trimmed = content[:MAX_CHARS_PER_FILE] + "\n... (content truncated) ...\n"
            else:
                trimmed = content
                
            if total_chars + len(trimmed) > MAX_TOTAL_CHARS:
                if trimmed_content_map:
                    trimmed = "... (additional files truncated to stay within size limits) ..."
                    trimmed_content_map[idx_path] = trimmed
                    break
                else:
                    available_chars = MAX_TOTAL_CHARS - total_chars
                    if available_chars > 1000: 
                        trimmed = content[:available_chars] + "\n... (severely truncated) ...\n"
                    else:
                        trimmed = "... (file too large to include) ..."
            
            trimmed_content_map[idx_path] = trimmed
            total_chars += len(trimmed)
            
            # Break if we've hit the total character limit
            if total_chars >= MAX_TOTAL_CHARS:
                break
                
        # Format file content for context
        file_context_str = "\n\n".join(
            f"--- File: {idx_path} ---\n{content}"
            for idx_path, content in trimmed_content_map.items()
        )
        
        # Add note about sampling
        if len(trimmed_content_map) < len(relevant_files_content_map):
            file_context_str += f"\n\n--- NOTE: Only showing {len(trimmed_content_map)} of {len(relevant_files_content_map)} relevant files due to size constraints ---"
            
        context += file_context_str

        return context, "\n".join(abstraction_info_for_prompt), project_name, language # Return language

    def exec(self, prep_res):
        context, abstraction_listing, project_name, language = prep_res  # Unpack project name and language
        print(f"Analyzing relationships using LLM...")

        # Add language instruction and hints only if not English
        language_instruction = ""
        lang_hint = ""
        list_lang_note = ""
        if language.lower() != "english":
            language_instruction = f"IMPORTANT: Generate the `summary` and relationship `label` fields in **{language.capitalize()}** language. Do NOT use English for these fields.\n\n"
            lang_hint = f" (in {language.capitalize()})"
            list_lang_note = f" (Names might be in {language.capitalize()})" # Note for the input list

        prompt = f"""
Based on the following abstractions and relevant code snippets from the project `{project_name}`:

List of Abstraction Indices and Names{list_lang_note}:
{abstraction_listing}

Context (Abstractions, Descriptions, Code):
{context}

{language_instruction}Please provide:
1. A high-level `summary` of the project's main purpose and functionality in a few beginner-friendly sentences{lang_hint}. Use markdown formatting with **bold** and *italic* text to highlight important concepts.
2. A list (`relationships`) describing the key interactions between these abstractions. For each relationship, specify:
    - `from_abstraction`: Index of the source abstraction (e.g., `0 # AbstractionName1`)
    - `to_abstraction`: Index of the target abstraction (e.g., `1 # AbstractionName2`)
    - `label`: A brief label for the interaction **in just a few words**{lang_hint} (e.g., "Manages", "Inherits", "Uses").
    Ideally the relationship should be backed by one abstraction calling or passing parameters to another.
    Simplify the relationship and exclude those non-important ones.

IMPORTANT: Make sure EVERY abstraction is involved in at least ONE relationship (either as source or target). Each abstraction index must appear at least once across all relationships.

Format the output as YAML:

```yaml
summary: |
  A brief, simple explanation of the project{lang_hint}.
  Can span multiple lines with **bold** and *italic* for emphasis.
relationships:
  - from_abstraction: 0 # AbstractionName1
    to_abstraction: 1 # AbstractionName2
    label: "Manages"{lang_hint}
  - from_abstraction: 2 # AbstractionName3
    to_abstraction: 0 # AbstractionName1
    label: "Provides config"{lang_hint}
  # ... other relationships
```

Now, provide the YAML output:
"""
        response = call_llm(prompt)

        # --- Validation ---
        try:
            # First try to extract yaml with markers
            if "```yaml" in response:
                yaml_str = response.strip().split("```yaml")[1].split("```")[0].strip()
            elif "```" in response:
                yaml_blocks = response.split("```")
                if len(yaml_blocks) >= 3:
                    yaml_str = yaml_blocks[1].strip()
            else:
                yaml_str = response.strip()
                
            relationships_data = yaml.safe_load(yaml_str)

            if not isinstance(relationships_data, dict):
                raise ValueError("Parsed YAML is not a dictionary")
        except Exception as e:
            print(f"Error parsing YAML: {e}")
            print("Creating a default relationships structure")
            
            # Create a minimally viable structure
            relationships_data = {
                "summary": f"This project appears to be a codebase for {project_name}.",
                "relationships": []
            }
            
            # Generate basic relationships to connect all abstractions
            num_abstractions = len(abstraction_listing.split('\n'))
            
            # Connect abstractions in sequence for simplicity
            for i in range(num_abstractions - 1):
                relationships_data["relationships"].append({
                    "from_abstraction": i,
                    "to_abstraction": i + 1,
                    "label": "Works with"
                })
            
            # Add one more to complete the circle
            if num_abstractions > 1:
                relationships_data["relationships"].append({
                    "from_abstraction": num_abstractions - 1,
                    "to_abstraction": 0,
                    "label": "Provides data to"
                })

        # Validate required keys
        if not all(k in relationships_data for k in ["summary", "relationships"]):
            missing_keys = set(["summary", "relationships"]) - set(relationships_data.keys())
            print(f"Missing keys in relationships data: {missing_keys}")
            
            # Add missing keys with defaults
            if "summary" not in relationships_data:
                relationships_data["summary"] = f"This project appears to be a codebase for {project_name}."
            if "relationships" not in relationships_data:
                relationships_data["relationships"] = []

        # Ensure types are correct
        if not isinstance(relationships_data["summary"], str):
            print("WARNING: Summary is not a string. Converting to string.")
            relationships_data["summary"] = str(relationships_data["summary"])
            
        if not isinstance(relationships_data["relationships"], list):
            print("WARNING: Relationships is not a list. Converting to empty list.")
            relationships_data["relationships"] = []

        # Validate relationships structure
        validated_relationships = []
        num_abstractions = len(abstraction_listing.split('\n'))
        
        # Track which abstractions are covered
        abstraction_coverage = set()
        
        for rel in relationships_data["relationships"]:
            try:
                # Check for required keys
                if not isinstance(rel, dict):
                    print(f"WARNING: Relationship item is not a dict: {rel}. Skipping.")
                    continue
                    
                if not all(k in rel for k in ["from_abstraction", "to_abstraction"]):
                    print(f"WARNING: Missing keys in relationship: {rel}. Skipping.")
                    continue
                    
                # Add label if missing
                if "label" not in rel or not isinstance(rel["label"], str):
                    rel["label"] = "Interacts with"
                
                # Parse indices
                try:
                    if isinstance(rel["from_abstraction"], int):
                        from_idx = rel["from_abstraction"]
                    elif isinstance(rel["from_abstraction"], str) and '#' in rel["from_abstraction"]:
                        from_idx = int(rel["from_abstraction"].split('#')[0].strip())
                    else:
                        from_idx = int(str(rel["from_abstraction"]).strip())
                        
                    if isinstance(rel["to_abstraction"], int):
                        to_idx = rel["to_abstraction"]
                    elif isinstance(rel["to_abstraction"], str) and '#' in rel["to_abstraction"]:
                        to_idx = int(rel["to_abstraction"].split('#')[0].strip())
                    else:
                        to_idx = int(str(rel["to_abstraction"]).strip())
                except (ValueError, TypeError):
                    print(f"WARNING: Could not parse indices from relationship: {rel}. Skipping.")
                    continue
                
                # Validate indices
                if not (0 <= from_idx < num_abstractions and 0 <= to_idx < num_abstractions):
                    print(f"WARNING: Invalid index in relationship: from={from_idx}, to={to_idx}. Max index is {num_abstractions-1}. Skipping.")
                    continue
                    
                # Track covered abstractions
                abstraction_coverage.add(from_idx)
                abstraction_coverage.add(to_idx)
                
                validated_relationships.append({
                    "from": from_idx,
                    "to": to_idx,
                    "label": rel["label"] 
                })
            except Exception as e:
                print(f"WARNING: Error processing relationship: {e}")
                continue
                
        # Check if all abstractions are covered in relationships
        if len(abstraction_coverage) < num_abstractions:
            print(f"WARNING: Not all abstractions are covered in relationships. Covered: {len(abstraction_coverage)}/{num_abstractions}")
            
            # Add relationships for uncovered abstractions
            uncovered = set(range(num_abstractions)) - abstraction_coverage
            
            for idx in uncovered:
                # Find a target abstraction
                if abstraction_coverage:
                    # Connect to an existing abstraction
                    target = min(abstraction_coverage)
                else:
                    # If nothing is covered yet, connect to the next one
                    target = (idx + 1) % num_abstractions
                    
                validated_relationships.append({
                    "from": idx,
                    "to": target,
                    "label": "Connects to"
                })
                
                # Update coverage
                abstraction_coverage.add(idx)
                abstraction_coverage.add(target)

        print("Generated project summary and relationship details.")
        return {
            "summary": relationships_data["summary"], 
            "details": validated_relationships 
        }

    def post(self, shared, prep_res, exec_res):
        shared["relationships"] = exec_res

class OrderChapters(Node):
    def prep(self, shared):
        abstractions = shared["abstractions"] 
        relationships = shared["relationships"] 
        project_name = shared["project_name"]  
        language = shared.get("language", "english") 

        # Prepare context for the LLM
        abstraction_info_for_prompt = []
        for i, a in enumerate(abstractions):
            abstraction_info_for_prompt.append(f"- {i} # {a['name']}") 
        abstraction_listing = "\n".join(abstraction_info_for_prompt)

        summary_note = ""
        if language.lower() != "english":
             summary_note = f" (Note: Project Summary might be in {language.capitalize()})"

        context = f"Project Summary{summary_note}:\n{relationships['summary']}\n\n"
        context += "Relationships (Indices refer to abstractions above):\n"
        
        # Add safety check for relationship indices
        num_abstractions = len(abstractions)
        for rel in relationships['details']:
            from_idx = rel['from']
            to_idx = rel['to']
            
            # Validate that indices are within bounds
            if 0 <= from_idx < num_abstractions and 0 <= to_idx < num_abstractions:
                from_name = abstractions[from_idx]['name']
                to_name = abstractions[to_idx]['name']

                context += f"- From {from_idx} ({from_name}) to {to_idx} ({to_name}): {rel['label']}\n" # Label might be translated
            else:
                # Use a placeholder for invalid indices
                if 0 <= from_idx < num_abstractions:
                    from_name = abstractions[from_idx]['name']
                    context += f"- From {from_idx} ({from_name}) to {to_idx} (Invalid Index): {rel['label']}\n"
                elif 0 <= to_idx < num_abstractions:
                    to_name = abstractions[to_idx]['name']
                    context += f"- From {from_idx} (Invalid Index) to {to_idx} ({to_name}): {rel['label']}\n"
                else:
                    context += f"- From {from_idx} (Invalid Index) to {to_idx} (Invalid Index): {rel['label']}\n"

        list_lang_note = ""
        if language.lower() != "english":
             list_lang_note = f" (Names might be in {language.capitalize()})"

        return abstraction_listing, context, len(abstractions), project_name, list_lang_note

    def exec(self, prep_res):
        abstraction_listing, context, num_abstractions, project_name, list_lang_note = prep_res
        print("Determining chapter order using LLM...")
        prompt = f"""
Given the following project abstractions and their relationships for the project ```` {project_name} ````:

Abstractions (Index # Name){list_lang_note}:
{abstraction_listing}

Context about relationships and project summary:
{context}

If you are going to make a tutorial for ```` {project_name} ````, what is the best order to explain these abstractions, from first to last?
Ideally, first explain those that are the most important or foundational, perhaps user-facing concepts or entry points. Then move to more detailed, lower-level implementation details or supporting concepts.

Output the ordered list of abstraction indices, including the name in a comment for clarity. Use the format `idx # AbstractionName`.

```yaml
- 2 # FoundationalConcept
- 0 # CoreClassA
- 1 # CoreClassB (uses CoreClassA)
- ...
```

Now, provide the YAML output:
"""
        response = call_llm(prompt)

        # --- Validation ---
        yaml_str = response.strip().split("```yaml")[1].split("```")[0].strip()
        ordered_indices_raw = yaml.safe_load(yaml_str)

        if not isinstance(ordered_indices_raw, list):
            raise ValueError("LLM output is not a list")

        ordered_indices = []
        seen_indices = set()
        for entry in ordered_indices_raw:
            try:
                 if isinstance(entry, int):
                     idx = entry
                 elif isinstance(entry, str) and '#' in entry:
                      idx = int(entry.split('#')[0].strip())
                 else:
                      idx = int(str(entry).strip())

                 if not (0 <= idx < num_abstractions):
                      raise ValueError(f"Invalid index {idx} in ordered list. Max index is {num_abstractions-1}.")
                 if idx in seen_indices:
                     raise ValueError(f"Duplicate index {idx} found in ordered list.")
                 ordered_indices.append(idx)
                 seen_indices.add(idx)

            except (ValueError, TypeError):
                 raise ValueError(f"Could not parse index from ordered list entry: {entry}")

        # Check if all abstractions are included
        if len(ordered_indices) != num_abstractions:
             raise ValueError(f"Ordered list length ({len(ordered_indices)}) does not match number of abstractions ({num_abstractions}). Missing indices: {set(range(num_abstractions)) - seen_indices}")

        print(f"Determined chapter order (indices): {ordered_indices}")
        return ordered_indices # Return the list of indices

    def post(self, shared, prep_res, exec_res):
        shared["chapter_order"] = exec_res # List of indices

class WriteChapters(BatchNode):
    def prep(self, shared):
        abstractions = shared["abstractions"]
        relationships = shared["relationships"]
        chapter_order = shared["chapter_order"]
        files_data = shared["files"]
        project_name = shared["project_name"]
        language = shared.get("language", "english")
        
        # Store files_data in the instance for later use
        self.files_data = files_data
        
        # Map chapter indices to ordered positions
        self.chapter_position_map = {}
        for position, idx in enumerate(chapter_order):
            self.chapter_position_map[idx] = position + 1  # 1-based position
        
        # Store chapter order and abstractions for navigation links
        self.chapter_order = chapter_order
        self.abstractions = abstractions
        
        # Number of abstractions for validation
        num_abstractions = len(abstractions)
        
        # Prepare a batch item for each chapter
        batch_items = []
        for chapter_idx in chapter_order:
            # Get abstraction for this chapter
            abstraction = abstractions[chapter_idx]
            
            # Get file indices for this abstraction
            file_indices = abstraction["files"]
            
            # Get relationship details for visualization if applicable
            related_abstractions = []
            for rel in relationships.get("details", []):
                # Only add valid relationships
                if rel["from"] == chapter_idx and 0 <= rel["to"] < num_abstractions:
                    related_abstractions.append({
                        "to": rel["to"],
                        "label": rel["label"],
                        "abstraction": abstractions[rel["to"]]
                    })
                elif rel["to"] == chapter_idx and 0 <= rel["from"] < num_abstractions:
                    related_abstractions.append({
                        "to": rel["from"],
                        "label": rel["label"],
                        "abstraction": abstractions[rel["from"]]
                    })
            
            # Prepare a batch item for this chapter
            batch_items.append({
                "chapter_idx": chapter_idx,
                "abstraction": abstraction,
                "file_indices": file_indices,
                "related_abstractions": related_abstractions,
                "project_name": project_name,
                "language": language
            })
        
        return batch_items

    def exec(self, item):
        # This runs for each item prepared above
        chapter_idx = item["chapter_idx"]
        abstraction = item["abstraction"]
        file_indices = item["file_indices"]
        related_abstractions = item["related_abstractions"]
        project_name = item["project_name"]
        language = item["language"]
        
        print(f"Generating chapter for abstraction: {abstraction['name']}...")
        
        # Use the instance variable for file access
        files_for_chapter = get_content_for_indices(self.files_data, file_indices)
        
        # Get total size of files to determine if chunking is needed
        total_size = sum(len(content) for content in files_for_chapter.values())
        
        # Determine if we need to use chunking based on total size
        using_chunking = total_size > 100000  # Use chunking if > 100KB
        
        # Create language hint for prompt if needed
        language_prompt = f"in {language}" if language.lower() != "english" else ""
        
        # Generate diagram markup if we have relationships
        mermaid_diagram = ""
        if related_abstractions:
            # Start mermaid diagram with proper formatting
            mermaid_lines = [
                "```mermaid",
                "flowchart TD"
            ]
            
            # Add central node (current abstraction)
            central_node_label = abstraction["name"].replace('"', '').replace('\n', ' ').strip()
            mermaid_lines.append(f'    C["{central_node_label}"]')
            
            # Add related nodes and connections
            for i, rel in enumerate(related_abstractions):
                to_idx = rel["to"]
                label = rel["label"].replace('"', '').replace('\n', ' ').strip()
                to_name = rel["abstraction"]["name"].replace('"', '').replace('\n', ' ').strip()
                
                # Create a unique ID for each related node
                node_id = f'N{i}'
                
                # Add node for related abstraction
                mermaid_lines.append(f'    {node_id}["{to_name}"]')
                
                # Add edge with clean label - ensure proper spacing
                if len(label) > 20:
                    label = label[:17] + "..."
                mermaid_lines.append(f'    C --->|"{label}"| {node_id}')
            
            # Close mermaid diagram
            mermaid_lines.append("```")
            mermaid_diagram = "\n".join(mermaid_lines)
            
        # Add instructions for better markdown formatting
        formatting_guidance = """
- Use informative section headings (## and ###) to organize the content
- Use **bold** and *italic* for emphasis
- Use bullet points and numbered lists when appropriate
- Include helpful code examples with ```python, ```typescript, etc. syntax highlighting
- Add tables where it makes sense to compare items
- For any diagrams, ensure they follow proper mermaid syntax with correct spacing and indentation
"""

        # Add mermaid syntax instructions
        mermaid_syntax_guide = """
FOR MERMAID DIAGRAMS:
1. ALWAYS use triple arrows (--->) in flowcharts: `A ---> B` not `A --> B`
2. Use proper indentation for all elements in subgraphs
3. Add a space between the arrow and any labels: `A ---> |"Label"| B`
4. For complex diagrams with many nodes, use clear hierarchical structure
5. Include this example syntax exactly as shown:

```mermaid
flowchart TD
    A[Node A] ---> |"Uses"| B[Node B]
    B ---> |"Calls"| C[Node C]
    
    subgraph GroupX
        D[Node D]
        E[Node E]
    end
    
    C ---> D
    C ---> E
```
"""

        # Generate content with or without chunking
        files_content = ""
        chapter_content = ""
        
        if not using_chunking:
            # For smaller content, process directly
            files_content = "\n\n".join([f"FILE: {file_key}\n```\n{content}\n```" for file_key, content in files_for_chapter.items()])
            
            prompt = f"""
Write a detailed tutorial chapter {language_prompt} titled "{abstraction['name']}" about the following code.

CHAPTER FOCUS:
{abstraction['description']}

PROJECT:
{project_name}

CODE CONTEXT:
{files_content}

{'RELATIONSHIPS WITH OTHER COMPONENTS:\n' + mermaid_diagram if mermaid_diagram else ''}

Use mermaid diagrams to illustrate complex concepts (```mermaid``` format).

FORMATTING GUIDANCE:
{formatting_guidance}



IMPORTANT INSTRUCTIONS:
1. Start with a clean, professional chapter format with heading "# Chapter {self.chapter_position_map[chapter_idx]}: {abstraction['name']}"
2. DO NOT prefix the chapter with phrases like "Here is a tutorial chapter" or "Okay, let me write"
3. DO NOT include any introductory text about what you're going to do
4. DO NOT include any meta-commentary or explanations about your process
5. Jump directly into the tutorial content after the main heading


Your chapter should be comprehensive but focused on the specific topic.
Include code examples, explanations, and how components work together.
Format the response in Markdown with proper headings, code blocks, and explanations.
"""
            
            chapter_content = call_llm(prompt)
            
        else:
            # For larger content, use a map-reduce approach with chunking
            # Chunk the files
            chunks = []
            chunk_size = 50000  # 50K chars per chunk
            current_chunk = {}
            current_size = 0
            
            for file_key, content in files_for_chapter.items():
                # If this file would exceed chunk size, finalize current chunk
                if current_size + len(content) > chunk_size and current_chunk:
                    chunks.append(dict(current_chunk))
                    current_chunk = {}
                    current_size = 0
                
                # Add file to current chunk
                current_chunk[file_key] = content
                current_size += len(content)
            
            # Add final chunk if not empty
            if current_chunk:
                chunks.append(dict(current_chunk))
            
            # Process each chunk
            chunk_analyses = []
            for i, chunk_files in enumerate(chunks):
                # Format files for this chunk
                chunk_files_content = "\n\n".join([f"FILE: {file_key}\n```\n{content}\n```" for file_key, content in chunk_files.items()])
                
                chunk_prompt = f"""
Analyze this subset of code for a tutorial chapter {language_prompt} titled "{abstraction['name']}".

CHAPTER FOCUS:
{abstraction['description']}

PROJECT:
{project_name}

CODE CONTEXT (Part {i+1}/{len(chunks)}):
{chunk_files_content}

Provide insights about the code related to the chapter focus.
Focus on describing the key functionalities, patterns, and implementations in this code subset.
Do not write a full chapter yet, just analyze this specific piece of the codebase.
"""
                
                chunk_analysis = call_llm(chunk_prompt)
                chunk_analyses.append(chunk_analysis)
            
            # Combine analyses into a final chapter
            combine_prompt = f"""
Write a detailed tutorial chapter {language_prompt} titled "{abstraction['name']}" based on the following code analyses.

CHAPTER FOCUS:
{abstraction['description']}

PROJECT:
{project_name}

{'RELATIONSHIPS WITH OTHER COMPONENTS:\n' + mermaid_diagram if mermaid_diagram else ''}

FORMATTING GUIDANCE:
{formatting_guidance}

{mermaid_syntax_guide}

IMPORTANT INSTRUCTIONS:
1. Start with a clean, professional chapter format with heading "# Chapter {self.chapter_position_map[chapter_idx]}: {abstraction['name']}"
2. DO NOT prefix the chapter with phrases like "Here is a tutorial chapter" or "Okay, let me write"
3. DO NOT include any introductory text about what you're going to do
4. DO NOT include any meta-commentary or explanations about your process
5. Jump directly into the tutorial content after the main heading
6. For ANY mermaid diagrams in your response, ensure ALL arrows use the triple-arrow syntax: `--->`

CODE ANALYSES:
{'====' * 20}
{chr(10).join([f"ANALYSIS PART {i+1}/{len(chunk_analyses)}:\n{analysis}" for i, analysis in enumerate(chunk_analyses)])}
{'====' * 20}

Your chapter should be comprehensive but focused on the specific topic.
Include code examples, explanations, and how components work together.
Format the response in Markdown with proper headings, code blocks, and explanations.
"""
            
            chapter_content = call_llm(combine_prompt)
            
        # Clean up the chapter content - remove any introductory text that might have been added
        lines = chapter_content.split('\n')
        clean_lines = []
        found_heading = False
        skip_intro = True
        
        for line in lines:
            if line.startswith('# Chapter'):
                found_heading = True
                skip_intro = False
                clean_lines.append(line)
            elif found_heading:
                clean_lines.append(line)
            elif not skip_intro:
                clean_lines.append(line)
                
        if not found_heading:
            clean_lines = [f"# Chapter {self.chapter_position_map[chapter_idx]}: {abstraction['name']}"] + lines
        
        chapter_content = '\n'.join(clean_lines)
        
        return {
            "chapter_idx": chapter_idx,
            "title": abstraction["name"],
            "content": chapter_content
        }

    def post(self, shared, prep_res, exec_res_list):
        output_dir = shared.get("output_dir", "./output")
        project_name = shared["project_name"]
        
        os.makedirs(output_dir, exist_ok=True)
        project_dir = os.path.join(output_dir, project_name.replace(" ", "_"))
        os.makedirs(project_dir, exist_ok=True)
        
        # Get all chapter data and prepare filename mapping
        # Sort by their order in chapter_order
        chapters = []
        for result in exec_res_list:
            chapter_idx = result["chapter_idx"]
            position = self.chapter_position_map[chapter_idx]
            
            # Create clean title and filename
            title = result["title"]
            safe_title = title.replace("&", "and").replace("/", "-")
            
            # Add chapter number to filename
            filename = f"{position:02d}_{safe_title.replace(' ', '_').lower()}.md"
            filename = filename.strip().replace("\n", "").replace("\r", "")
            
            chapters.append({
                "chapter_idx": chapter_idx,
                "position": position,
                "title": title,
                "content": result["content"],
                "filename": filename
            })
        
        # Sort chapters by position
        chapters.sort(key=lambda x: x["position"])
        
        # Pre-process to build navigation links
        for i, chapter in enumerate(chapters):
            # Previous chapter
            prev_chapter = chapters[i-1] if i > 0 else None
            # Next chapter
            next_chapter = chapters[i+1] if i < len(chapters)-1 else None
            
            # Add navigation footer
            nav_links = []
            
            # Add table of contents link
            nav_links.append("[📚 Table of Contents](README.md)")
            
            # Add previous chapter link if exists
            if prev_chapter:
                nav_links.append(f"[⬅️ Previous: {prev_chapter['title']}]({prev_chapter['filename']})")
                
            # Add next chapter link if exists
            if next_chapter:
                nav_links.append(f"[➡️ Next: {next_chapter['title']}]({next_chapter['filename']})")
            
            # Combine navigation links
            nav_footer = "\n\n---\n\n" + " | ".join(nav_links)
            
            # Check if content already starts with a chapter heading
            content = chapter["content"]
            expected_heading = f"# Chapter {chapter['position']}: {chapter['title']}"
            
            # Only add the heading if it's not already present
            if not content.startswith(expected_heading):
                final_content = f"{expected_heading}\n\n{content}{nav_footer}"
            else:
                final_content = f"{content}{nav_footer}"
                
            # Final content with navigation
            chapter["final_content"] = final_content
            
        # Now write all chapters with navigation
        for chapter in chapters:
            filepath = os.path.join(project_dir, chapter["filename"])
            
            # Write content
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(chapter["final_content"])
                
            print(f"Chapter saved: {filepath}")
            
            # Store information for README generation
            if "generated_chapters" not in shared:
                shared["generated_chapters"] = []
                
            shared["generated_chapters"].append({
                "position": chapter["position"],
                "title": chapter["title"],
                "filename": chapter["filename"],
                "path": filepath
            })
        
        # Store the tutorial directory path for main.py
        shared["tutorial_dir"] = project_dir
        
        return "default"  # Go to the next node

class CombineTutorial(Node):
    def prep(self, shared):
        project_name = shared["project_name"]
        output_dir = shared.get("output_dir", "./output")
        generated_chapters = shared.get("generated_chapters", [])
        relationships = shared.get("relationships", {"summary": "", "details": []})
        abstractions = shared.get("abstractions", [])
        chapter_order = shared.get("chapter_order", [])
        
        # Create README with links to all chapters
        readme_content = f"# {project_name} Tutorial\n\n"
        
        # Add project summary if available
        if relationships and "summary" in relationships:
            # Clean any line breaks in the summary
            summary = relationships["summary"].replace("\n", " ").strip()
            readme_content += f"{summary}\n\n"

        # Add mermaid diagram for relationships if available
        if "details" in relationships and abstractions:
            readme_content += "## Project Structure\n\n"
            
            # Start mermaid diagram with proper formatting
            mermaid_lines = [
                "```mermaid",
                "flowchart TD"
            ]
            
            # Add nodes with clean labels
            for i, abstraction in enumerate(abstractions):
                node_id = f"A{i}"
                # Clean node label: replace quotes, remove line breaks
                node_label = abstraction["name"].replace('"', '').replace('\n', ' ').strip()
                mermaid_lines.append(f'    {node_id}["{node_label}"]')
            
            # Add edges for relationships using potentially translated labels
            for rel in relationships["details"]:
                from_node_id = f"A{rel['from']}"
                to_node_id = f"A{rel['to']}"
                edge_label = rel['label'].replace('"', '').replace('\n', ' ')
                max_label_len = 30
                if len(edge_label) > max_label_len:
                    edge_label = edge_label[:max_label_len-3] + "..."
                mermaid_lines.append(f'    {from_node_id} -->|"{edge_label}"| {to_node_id}') # Edge label uses potentially translated label
            
            # Close mermaid diagram
            mermaid_lines.append("```")
            
            # Join lines with proper line breaks
            readme_content += "\n".join(mermaid_lines) + "\n\n"
        
        # Add table of contents
        readme_content += "## Table of Contents\n\n"
        
        # Sort chapters by position
        sorted_chapters = sorted(generated_chapters, key=lambda x: x.get("position", 0))
        
        # Add formatted chapter links to README
        for chapter in sorted_chapters:
            position = chapter.get("position", 0)
            # Clean up title
            clean_title = chapter["title"].strip().replace('\n', ' ').replace('\r', ' ')
            # Clean up filename
            clean_filename = chapter["filename"].strip().replace('\n', '').replace('\r', '')
            # Add the nicely formatted link with chapter number
            readme_content += f"{position}. [{clean_title}]({clean_filename})\n"
        
        # Add getting started section
        readme_content += f"""
## Getting Started

This tutorial is organized in a sequential manner to help you understand the {project_name} codebase.
Each chapter builds upon concepts from previous chapters, so it's recommended to read them in order.

To get the most out of this tutorial:

1. Start with chapter 1 to get an overview of the project
2. Pay attention to the relationships between components
3. Refer to the original codebase alongside the tutorial
4. Use the navigation links at the bottom of each chapter to move between chapters

## How to Use This Tutorial

Each chapter focuses on a specific aspect of the codebase and includes:

- **Overview**: A high-level explanation of the component
- **Code Examples**: Important snippets that illustrate key concepts
- **Relationships**: How this component interacts with others 
- **Implementation Details**: Explanations of the internal workings

The chapters include navigation links at the bottom to help you move between chapters easily.
"""
        
        readme_content += f"\n\n---\n\nGenerated by [AI Codebase Knowledge Builder](https://github.com/The-Pocket/Tutorial-Codebase-Knowledge)"

        return {
            "readme_content": readme_content,
            "tutorial_dir": shared.get("tutorial_dir", "")
        }

    def exec(self, prep_res):
        readme_content = prep_res["readme_content"]
        tutorial_dir = prep_res["tutorial_dir"]
        
        if not tutorial_dir:
            raise ValueError("Tutorial directory not found in shared data")
            
        # Write README
        readme_path = os.path.join(tutorial_dir, "README.md")
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
            
        print(f"README created: {readme_path}")
        
        return tutorial_dir

    def post(self, shared, prep_res, exec_res):
        # Store the final output directory
        shared["final_output_dir"] = exec_res
        print(f"\nTutorial generation complete! Files are in: {exec_res}")
        return "default"
