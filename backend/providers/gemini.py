import os

class GeminiProvider:
    def __init__(self):
        try:
            from dotenv import load_dotenv
        except ImportError:
            self.import_error = ImportError("python-dotenv is not installed")
            self.gemini_key = None
            self.model_id = "gemini-2.5-flash-lite"
            self.client = None
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
            return

        load_dotenv()
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.model_id = "gemini-2.5-flash-lite"
        self.client = None
        self.import_error = None
        try:
            from google import genai
        except ImportError as error:
            self.import_error = error
        else:
            if self.gemini_key:
                self.client = genai.Client(api_key=self.gemini_key)
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

    def get_unavailable_reason(self):
        if self.import_error is not None:
            return "Gemini dependencies are not installed"
        if not self.gemini_key:
            return "GEMINI_API_KEY is missing"
        if self.client is None:
            return "Gemini client could not be initialized"
        return None
