from google import genai
import os
import logging
import json
import time
from datetime import datetime

# Configure logging
log_directory = os.getenv("LOG_DIR", "logs")
os.makedirs(log_directory, exist_ok=True)
log_file = os.path.join(log_directory, f"llm_calls_{datetime.now().strftime('%Y%m%d')}.log")

# Set up logger
logger = logging.getLogger("llm_logger")
logger.setLevel(logging.INFO)
logger.propagate = False  # Prevent propagation to root logger
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

# Built-in API key for fast analysis (Gemini 2.5 Flash-Lite Preview)
BUILT_IN_GEMINI_KEY = "AIzaSyBMRU4XUfWGs4TtxAXQOa7KoZoEwNC82W8"

def call_llm(prompt: str, max_retries: int = 3, retry_delay: int = 5, analysis_mode: str = "fast", user_api_key: str = None) -> str:
    """
    Call LLM with different modes:
    - fast: Uses built-in API key with Gemini 2.5 Flash-Lite Preview (limited to 5 files)
    - detailed: Uses user's API key with Gemini 2.5 Pro (unlimited files)
    """
    # Log the prompt
    logger.info(f"PROMPT ({analysis_mode} mode): {prompt}")
    
    # Determine API key and model based on analysis mode
    if analysis_mode == "fast":
        api_key = BUILT_IN_GEMINI_KEY
        model = "gemini-2.5-flash-lite-preview"
        logger.info("Using fast mode with Gemini 2.5 Flash-Lite Preview")
    else:  # detailed mode
        api_key = user_api_key or os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "your_gemini_api_key_here":
            return "Error: User API key required for detailed analysis. Please provide your Gemini API key."
        model = "gemini-2.5-pro-exp-03-25"
        logger.info(f"Using detailed mode with {model}")
    
    client = genai.Client(api_key=api_key)
    
    # Add retry logic for rate limits
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=[prompt]
            )
            response_text = response.text
            
            # Log the response
            logger.info(f"RESPONSE ({analysis_mode} mode): {response_text}")
            
            return response_text
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Attempt {attempt+1}/{max_retries} failed ({analysis_mode} mode): {error_msg}")
            
            # Check if it's a rate limit error
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                if attempt < max_retries - 1:  # Don't sleep on the last attempt
                    sleep_time = retry_delay * (attempt + 1)  # Exponential backoff
                    logger.info(f"Rate limit exceeded. Sleeping for {sleep_time} seconds...")
                    time.sleep(sleep_time)
                    continue
            
            # For non-rate-limit errors or if we've exhausted retries
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                return f"The request exceeded API rate limits. Please try again later with fewer chunks or a longer delay between requests."
            return f"Error calling LLM ({analysis_mode} mode): {error_msg}"

def get_analysis_limits(analysis_mode: str) -> dict:
    """Get limits for different analysis modes"""
    if analysis_mode == "fast":
        return {
            "max_files": 5,
            "max_file_size": 10000,  # 10KB per file
            "description": "Quick analysis with up to 5 files using fast AI model"
        }
    else:  # detailed
        return {
            "max_files": 100,
            "max_file_size": 50000,  # 50KB per file
            "description": "Comprehensive analysis with your API key"
        }

if __name__ == "__main__":
    test_prompt = "Hello, how are you?"
    
    # Test fast mode
    print("Testing fast mode...")
    response1 = call_llm(test_prompt, analysis_mode="fast")
    print(f"Fast mode response: {response1}")
    
    # Test detailed mode
    print("Testing detailed mode...")
    response2 = call_llm(test_prompt, analysis_mode="detailed")
    print(f"Detailed mode response: {response2}")

