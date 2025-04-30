#!/usr/bin/env python3
"""
Validate and fix Mermaid diagrams in markdown files
"""

import os
import re
import sys
import glob
import subprocess
import tempfile
import json
from bs4 import BeautifulSoup
import importlib.util
import importlib.machinery
from pathlib import Path

def load_call_llm():
    """Load the call_llm function from utils/call_llm.py"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        utils_dir = os.path.join(script_dir, "utils")
        
        if not os.path.exists(utils_dir):
            utils_dir = os.path.join(os.path.dirname(script_dir), "utils")
        
        call_llm_path = os.path.join(utils_dir, "call_llm.py")
        
        if not os.path.exists(call_llm_path):
            print(f"Warning: call_llm.py not found at {call_llm_path}")
            return None
            
        # Load the module
        loader = importlib.machinery.SourceFileLoader("call_llm_module", call_llm_path)
        spec = importlib.util.spec_from_loader("call_llm_module", loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        
        return module.call_llm
    except Exception as e:
        print(f"Error loading call_llm: {e}")
        return None

def extract_mermaid_blocks(markdown_file):
    """Extract mermaid code blocks from markdown file."""
    with open(markdown_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all mermaid blocks
    pattern = r'```mermaid\s+(.*?)\s+```'
    blocks = re.findall(pattern, content, re.DOTALL)
    return blocks

def fix_common_issues(mermaid_code):
    """Fix common mermaid syntax issues."""
    # Fix 1: Incorrect arrow syntax with quotes
    # From: A --- "label" ---> B
    # To:   A -->|"label"| B
    mermaid_code = re.sub(r'(\w+)\s+---\s+"([^"]+)"\s+--->\s+(\w+)', 
                         r'\1 -->|"\2"| \3', 
                         mermaid_code)
    
    # Fix 2: Extra dash in arrow syntax
    # From: A ---> |"label"| B
    # To:   A --> |"label"| B
    mermaid_code = re.sub(r'(--+)>\s+\|', 
                         r'-->\|', 
                         mermaid_code)
    
    # Fix 3: Remove spaces between arrow and pipe
    # From: --> |"label"|
    # To:   -->|"label"|
    mermaid_code = re.sub(r'-->\s+\|', r'-->|', mermaid_code)
    
    # Fix 4: Convert 'graph' to 'flowchart'
    mermaid_code = re.sub(r'^graph\s+(TD|LR|RL|BT)', r'flowchart \1', mermaid_code, flags=re.MULTILINE)
    
    # Fix 5: Fix arrows with triple dashes to standard format
    # From: A ---> B
    # To:   A --> B
    mermaid_code = re.sub(r'(-->+)', r'-->', mermaid_code)
    
    # Fix 6: Fix backslash-escaped pipe in arrows
    # From: -->\|"label"|
    # To:   -->|"label"|
    mermaid_code = re.sub(r'-->\\\|', r'-->|', mermaid_code)
    
    # Fix 7: Fix reverse arrow direction with label
    # From: A <-- |"label"| B
    # To:   B -->|"label"| A
    lines = mermaid_code.split('\n')
    for i, line in enumerate(lines):
        # Match the reverse arrow pattern
        match = re.search(r'(\w+)\s+<--\s+\|"([^"]+)"\|\s+(\w+)', line)
        if match:
            # Reverse the direction (node1 and node2 swap positions)
            node1, label, node2 = match.groups()
            lines[i] = re.sub(r'(\w+)\s+<--\s+\|"([^"]+)"\|\s+(\w+)', 
                              f"{node2} -->|\"\\2\"| {node1}", line)
            
        # Match simple reverse arrow without label
        match = re.search(r'(\w+)\s+<--\s+(\w+)', line)
        if match:
            node1, node2 = match.groups()
            lines[i] = re.sub(r'(\w+)\s+<--\s+(\w+)', f"{node2} --> {node1}", line)
            
        # Match reverse arrow with label but no quotes
        match = re.search(r'(\w+)\s+<--\s+\|([^|]+)\|\s+(\w+)', line)
        if match:
            node1, label, node2 = match.groups()
            lines[i] = re.sub(r'(\w+)\s+<--\s+\|([^|]+)\|\s+(\w+)', 
                              f"{node2} -->|\\2| {node1}", line)
    
    mermaid_code = '\n'.join(lines)
    
    # Add quotes to node labels if missing
    mermaid_code = re.sub(r'(\w+)\[([^"\]\[]+)\]', 
                         lambda m: f'{m.group(1)}["{m.group(2)}"]', 
                         mermaid_code)
    
    # Fix nodes with empty brackets
    mermaid_code = re.sub(r'(\w+)\[\s*\]', 
                         lambda m: f'{m.group(1)}["{m.group(1)}"]', 
                         mermaid_code)
    
    # Wrap unquoted subgraph titles in quotes
    mermaid_code = re.sub(
        r'^(\s*subgraph\s+)(?!\")(.*)$',
        r'\1"\2"',
        mermaid_code,
        flags=re.MULTILINE,
    )

    # Convert nodes with parentheses in curly braces to square brackets labels
    mermaid_code = re.sub(
        r'(\w+)\{([^\}]*\([^)]*\)[^\}]*)\}',
        r'\1["\2"]',
        mermaid_code
    )
    
    # Fix backward edges written as `<|---`: reverse direction to forward `-->`
    # e.g., BI <|--- MI becomes MI --> BI
    mermaid_code = re.sub(
        r"(\w+)\s*<\|---\s*(\w+)",
        r"\2 --> \1",
        mermaid_code
    )
    
    return mermaid_code

def call_llm_to_fix(mermaid_code, error_msg=""):
    """Use LLM to fix a mermaid diagram that couldn't be fixed with regex patterns."""
    call_llm = load_call_llm()
    if call_llm is None:
        print("Warning: call_llm utility not available, skipping LLM fix")
        return mermaid_code
    
    try:
        prompt = f"""Fix this Mermaid diagram to make it valid.

{f'The error is: {error_msg}' if error_msg else 'Check for syntax errors.'}

Here are common Mermaid issues to fix:
1. Use 'flowchart TD' instead of 'graph TD'
2. Ensure arrows use the correct syntax (e.g., -->)
3. Make sure subgraphs are properly defined with quotes: subgraph "Name" ... end
4. Fix nodes with empty brackets []
5. Fix nodes with incomplete closing brackets like [name)]
6. Any node referencing a file should be properly quoted and brackets closed
7. Make sure there's only one 'end' statement per subgraph, not multiple

The most common issue currently is multiple 'end' statements following a subgraph. Each subgraph should have exactly one 'end'.

Diagram:
```mermaid
{mermaid_code}
```

Respond with ONLY the fixed diagram code. No explanations, no markdown code blocks, just the raw diagram code starting with "flowchart".
"""
        
        # Call the LLM using the utility function
        response_text = call_llm(prompt, use_cache=True)
        
        # Clean the response
        fixed_diagram = response_text.strip()
        fixed_diagram = re.sub(r'^```mermaid\s*', '', fixed_diagram)
        fixed_diagram = re.sub(r'\s*```$', '', fixed_diagram)
        
        # Basic validation of LLM output - make sure it's actually a flowchart
        if not fixed_diagram.startswith("flowchart") and not fixed_diagram.startswith("graph"):
            print("LLM returned invalid response, keeping original")
            return mermaid_code
            
        return fixed_diagram
        
    except Exception as e:
        print(f"Error calling LLM: {e}")
        return mermaid_code

def validate_mermaid(mermaid_code):
    """Validate mermaid syntax using mmdc CLI if available."""
    try:
        with tempfile.NamedTemporaryFile(suffix='.mmd', mode='w', delete=False) as tmp:
            tmp.write(mermaid_code)
            tmp_path = tmp.name
        
        # Create a temporary output file for mmdc (it requires a valid output file)
        out_tmp_path = tmp_path + '.svg'
        
        try:
            print("Validating Mermaid diagram using mmdc...", file=sys.stderr)
            result = subprocess.run(
                ['mmdc', '-i', tmp_path, '-o', out_tmp_path],
                capture_output=True,
                text=True
            )
            valid = result.returncode == 0
            error_msg = result.stderr if not valid else ""
            if os.path.exists(out_tmp_path):
                os.unlink(out_tmp_path)
        except FileNotFoundError:
            print("Error: Mermaid CLI 'mmdc' not found. Please install @mermaid-js/mermaid-cli", file=sys.stderr)
            sys.exit(1)
        
        os.unlink(tmp_path)
        return valid, error_msg
        
    except Exception as e:
        return False, str(e)

def fix_markdown_file(markdown_file, use_llm=False):
    """Fix mermaid diagrams in a markdown file."""
    with open(markdown_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocks = extract_mermaid_blocks(markdown_file)
    fixed_content = content
    blocks_fixed = 0
    blocks_removed = 0 # Track removed blocks
    
    for block in blocks:
        original_block_string = f"```mermaid\n{block}\n```"
        replacement_string = original_block_string 
        block_changed = False
        block_removed_flag = False 
        fixed_block = fix_common_issues(block)
        valid, error_msg = validate_mermaid(fixed_block)
        
        if valid:
            if fixed_block != block: # Regex fixed it
                replacement_string = f"```mermaid\n{fixed_block}\n```"
                block_changed = True
                blocks_fixed += 1
            # If valid and regex didn't change anything, leave original (block_changed=False)
        else:
            # Regex fix didn't work or wasn't enough
            if use_llm:
                print(f"Regex fix insufficient, trying LLM-based fix for invalid diagram...")
                llm_fixed_block = call_llm_to_fix(fixed_block, error_msg)
                
                # Validate the LLM-fixed diagram
                llm_valid, _ = validate_mermaid(llm_fixed_block)
                if llm_valid:
                    print("LLM successfully fixed the diagram.")
                    replacement_string = f"```mermaid\n{llm_fixed_block}\n```"
                    block_changed = True
                    blocks_fixed += 1
                else:
                    print("LLM fix was not successful. Removing block.")
                    replacement_string = "" 
                    block_changed = True 
                    block_removed_flag = True
                    blocks_removed += 1
            else:
                # Invalid, no LLM fix attempted, keep original broken block for now
                # Or optionally remove here too? Let's keep it for now unless LLM fails.
                print(f"⚠️ Mermaid diagram remains invalid (LLM fix not enabled) in {markdown_file}", file=sys.stderr)

        # Only replace in the content if something actually changed (fixed or removed)
        if block_changed:
            fixed_content = fixed_content.replace(original_block_string, replacement_string)
    
    # Write back if changes were made
    if fixed_content != content:
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(fixed_content)
        print(f"✅ Processed {markdown_file}: {blocks_fixed} blocks fixed, {blocks_removed} blocks removed.")
        return True, blocks_fixed + blocks_removed # Return count of fixed + removed
    else:
        print(f"✓ No syntax issues needed fixing in {markdown_file}")
        return False, 0

def process_directory(directory_path, fix_mode=False, use_llm=False, recursive=False):
    """Process all markdown files in a directory."""
    # Get list of markdown files
    if recursive:
        pattern = os.path.join(directory_path, "**", "*.md")
        md_files = glob.glob(pattern, recursive=True)
    else:
        pattern = os.path.join(directory_path, "*.md")
        md_files = glob.glob(pattern)
    
    if not md_files:
        print(f"No markdown files found in {directory_path}")
        return 0, 0, 0
    
    print(f"Found {len(md_files)} markdown files in {directory_path}")
    
    # Process each file
    total_files = len(md_files)
    files_with_diagrams = 0
    fixed_files = 0
    total_blocks_fixed = 0
    
    for file_path in md_files:
        print(f"\n===== Processing {os.path.basename(file_path)} =====")
        blocks = extract_mermaid_blocks(file_path)
        
        if blocks:
            files_with_diagrams += 1
            if fix_mode:
                # Attempt to fix mermaid blocks (regex + optional LLM)
                fixed, blocks_fixed = fix_markdown_file(file_path, use_llm)
                if fixed:
                    fixed_files += 1
                    total_blocks_fixed += blocks_fixed
            else:
                for i, block in enumerate(blocks):
                    print(f"\nValidating block {i+1}:")
                    fixed_block = fix_common_issues(block)
                    needs_fixing = fixed_block != block
                    valid, error_msg = validate_mermaid(fixed_block)

                    if valid:
                        print(f"✓ Block {i+1} is valid")
                        if needs_fixing:
                            print("  (Would fix syntax issues with regex patterns)")
                    else:
                        print(f"✗ Block {i+1} has errors:")
                        print(error_msg)
    
    print(f"\n===== Summary =====")
    print(f"Total files: {total_files}")
    print(f"Files with mermaid diagrams: {files_with_diagrams}")
    if fix_mode:
        print(f"Files fixed: {fixed_files}")
        print(f"Total blocks fixed: {total_blocks_fixed}")
    
    return total_files, files_with_diagrams, fixed_files

def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_mermaid.py <file_or_directory> [--fix] [--llm] [--recursive]")
        sys.exit(1)
    
    path = sys.argv[1]
    fix_mode = "--fix" in sys.argv
    use_llm = "--llm" in sys.argv or fix_mode
    recursive = "--recursive" in sys.argv or "-r" in sys.argv
    
    if not os.path.exists(path):
        print(f"Error: Path {path} not found")
        sys.exit(1)
    
    if os.path.isdir(path):
        # Process all files in directory
        print(f"Processing directory: {path}")
        total_files, files_with_diagrams, fixed_files = process_directory(
            path, fix_mode, use_llm, recursive
        )
        
        if files_with_diagrams == 0:
            print("No files with mermaid diagrams found")
            sys.exit(0)
            
        if fix_mode and fixed_files == 0:
            print("No files needed fixing")
            sys.exit(0)
    else:
        # Process single file
        blocks = extract_mermaid_blocks(path)
        if not blocks:
            print(f"No mermaid blocks found in {path}")
            sys.exit(0)
        
        print(f"Found {len(blocks)} mermaid blocks in {path}")
        
        all_valid = True
        
        for i, block in enumerate(blocks):
            print(f"\nValidating block {i+1}:")
            
            # Check if fixing is needed with regex
            fixed_block = fix_common_issues(block)
            needs_fixing = fixed_block != block
            
            # Validate the fixed or original block
            valid, error_msg = validate_mermaid(fixed_block)
            
            if valid:
                print(f"✓ Block {i+1} is valid")
                if needs_fixing:
                    print("  (Fixed syntax issues with regex patterns)")
            else:
                print(f"✗ Block {i+1} has errors:")
                print(error_msg)
                all_valid = False
                
                if fix_mode:
                    if use_llm:
                        print("  Will attempt LLM-based repair")
                    else:
                        print("  Will attempt regex-based repair")
                        print("  (Use --llm flag to try advanced AI repair for complex issues)")
                else:
                    print("  Run with --fix to attempt automatic repairs")
                    if not use_llm:
                        print("  Add --llm flag for advanced AI repair of complex issues")
        
        if fix_mode and not all_valid:
            fix_markdown_file(path, use_llm)
    
    sys.exit(0)

if __name__ == "__main__":
    main() 