from google import genai
from dotenv import load_dotenv
import os

class GeminiProvider:
    def __init__(self):
        load_dotenv()
        self.GEMINI_KEY = os.getenv("GEMINI_API_KEY")
        self.model_id = "gemini-2.5-flash-lite"
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
                            }
                        },
                        "required": ["title", "genre", "pitch"]
                    }
                }
            },
            "required": ["series_list"]
        }