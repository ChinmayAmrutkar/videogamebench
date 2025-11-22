import os
from google import genai                    # FIX 1: Change import
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

try:
    # Get the API key from the environment variables
    api_key = os.getenv("GEMINI_API_KEY")
    
    # Create the Gemini client instance and pass the API key (New way)
    # The client often automatically picks up the key if you export GEMINI_API_KEY
    client = genai.Client(api_key=api_key)  # FIX 2: Create a Client object

    # Create a GenerativeModel instance using the client
    # We use 'gemini-pro' for this text-based test
    model_name = 'gemini-pro'
    print(f"Sending a test prompt to the Gemini API using {model_name}...")
    
    # FIX 3: Use the client to call the model method
    response = client.models.generate_content(
        model=model_name,
        contents="What is the speed of light in a vacuum?"
    )

    # Print the model's response
    print("\nSuccess! Gemini API responded:\n")
    print(response.text)

except Exception as e:
    # The new SDK raises different exceptions, but a general catch works for this test
    print(f"\nAn error occurred: {e}")
    print("\nPlease check if your GEMINI_API_KEY is set correctly in the .env file.")
