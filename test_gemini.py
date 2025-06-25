#!/usr/bin/env python3
"""
Test script for the new Google Gemini API
"""
import os
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

def test_gemini_api():
    """Test the Gemini API with the new library"""
    try:
        # Get API key
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            # Use the provided API key
            api_key = "AIzaSyB0nWo8VcVoHoDsq54PYw_T82PL4DCg-Sg"
            print("⚠️ Using provided API key")
        else:
            print("✅ Using API key from .env")
        
        # Create client
        print("🔧 Creating Gemini client...")
        client = genai.Client(api_key=api_key)
        print("✅ Client created successfully")
        
        # Test simple generation
        print("🧪 Testing content generation...")
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents='Say "Hello World" in Hebrew'
        )
        
        print(f"✅ Response received: {response.text}")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Testing new Gemini API...")
    success = test_gemini_api()
    if success:
        print("🎉 All tests passed! The new API is working correctly.")
    else:
        print("💥 Tests failed. Please check the error above.") 