# Mushroom Farm Management System

A comprehensive management system for mushroom farms with an integrated AI assistant.

## Features

- Farm management dashboard
- Order management
- Customer management
- Growing bed tracking
- Warehouse management
- Analytics
- AI Assistant powered by Google's Gemini

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your environment variables:
Create a `.env` file in the root directory with:
```
GEMINI_API_KEY=your_gemini_api_key_here
```

3. Run the application:
```bash
python UI/main.py
```

## AI Assistant

The system includes an AI assistant powered by Google's Gemini that can:
- Answer questions about mushroom farming
- Provide insights based on your farm data
- Help with troubleshooting
- Offer recommendations for farm management

To use the AI assistant:
1. Click the "💬 AI Assistant" button in the sidebar
2. Type your question in the chat interface
3. The AI will respond with relevant information based on your farm data and general mushroom farming knowledge

## Note

Make sure to keep your Gemini API key secure and never commit it to version control.
