from google import genai

# Test the API key
api_key = "AIzaSyB0nWo8VcVoHoDsq54PYw_T82PL4DCg-Sg"

try:
    print("🔧 Creating client...")
    client = genai.Client(api_key=api_key)
    print("✅ Client created successfully")
    
    print("🧪 Testing content generation...")
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents='Say "Hello World" in Hebrew'
    )
    
    print(f"✅ Response: {response.text}")
    print("🎉 API is working correctly!")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    print("💥 API test failed") 