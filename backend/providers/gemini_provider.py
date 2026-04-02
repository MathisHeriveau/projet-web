from google import genai
from dotenv import load_dotenv
import os

class GeminiProvider:
    def __init__(self):
        load_dotenv()
        self.GEMINI_KEY = os.getenv("GEMINI_API_KEY")
        self.model_id = "gemini-2.5-flash-lite"
        # self.model_id = "gemini-2.5-flash"
        self.client = genai.Client(api_key=self.GEMINI_KEY)
        self.series_recommendation_schema = {
            "type": "object",
            "properties": {
                "series_list": {
                    "type": "array",
                    "description": "A list of exactly 10 different TV series recommendations.",
                    "minItems": 10,
                    "maxItems": 10,
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "string",
                                "description": "The title of the series."
                            },
                            "genre": {
                                "type": "string",
                                "description": "The primary genre of the series."
                            },
                            "pitch": {
                                "type": "string",
                                "description": "A short, engaging 1-sentence pitch for why the user should watch it."
                            },
                            "explanation": {
                                "type": "string",
                                "description": "A concise explanation of why this series was recommended, based on the user's preferences and watch history."
                            }
                        },
                        "required": ["title", "genre", "pitch", "explanation"]
                    }
                }
            },
            "required": ["series_list"]
        }