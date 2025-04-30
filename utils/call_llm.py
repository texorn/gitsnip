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


def call_llm(prompt: str, max_retries: int = 3, retry_delay: int = 5) -> str:
    # Log the prompt
    logger.info(f"PROMPT: {prompt}")
    
    client = genai.Client(
        api_key=os.getenv("GEMINI_API_KEY", "Your Gemini API Key"),
    )
    
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-pro-exp-03-25")
    
    # Add retry logic for rate limits
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model,
                contents=[prompt]
            )
            response_text = response.text
            
            # Log the response
            logger.info(f"RESPONSE: {response_text}")
            
            return response_text
            
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Attempt {attempt+1}/{max_retries} failed: {error_msg}")
            
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
            return f"Error calling LLM: {error_msg}"


if __name__ == "__main__":
    test_prompt = "Hello, how are you?"
    
    # First call - should hit the API
    print("Making call...")
    response1 = call_llm(test_prompt)
    print(f"Response: {response1}")
    
