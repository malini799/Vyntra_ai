import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("ERROR: Gemini API key was not found in .env")
else:
    try:
        client = genai.Client(api_key=api_key)

        print("Testing Gemini AI...")

        response = client.models.generate_content(
            model="gemini-3.8-flash",
            contents=(
                "You are being tested for the Vyntra AI project. "
                "Reply with: Gemini AI is working successfully!"
            ),
        )

        print("\nSUCCESS!")
        print("Gemini's response:")
        print(response.text)

    except Exception as error:
        print("\nGEMINI TEST FAILED")
        print("Error type:", type(error).__name__)
        print("Error details:", error)