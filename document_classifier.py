from typing import Dict, List, Optional
import json
import os
from openai import OpenAI
from config_loader import Config

class DocumentClassifier:
    def __init__(self, config: Config):
        self.config = config
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.rubric = self._load_rubric()

    def _load_rubric(self) -> dict:
        """Load the classification rubric from the configured path."""
        with open(self.config.rubric_path, 'r') as f:
            return json.load(f)

    def classify_document(self, content: str, metadata: Optional[Dict] = None) -> Dict:
        """
        Classify a document using the LLM based on the rubric.
        
        Args:
            content: The document content to classify
            metadata: Optional document metadata
            
        Returns:
            Dictionary containing classification results
        """
        # Prepare the prompt
        prompt = self._build_classification_prompt(content, metadata)
        
        try:
            # Get classification from LLM
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            # Parse the response
            classification = self._parse_classification_response(response.choices[0].message.content)
            
            # Add confidence scores
            classification = self._add_confidence_levels(classification)
            
            return classification
            
        except Exception as e:
            print(f"Error during classification: {e}")
            return {
                "error": str(e),
                "categories": [],
                "confidence": 0
            }

    def _build_classification_prompt(self, content: str, metadata: Optional[Dict] = None) -> str:
        """Build the prompt for document classification."""
        prompt_parts = [
            "Please classify the following document according to the provided rubric.",
            "\nDocument content:",
            content[:4000]  # Limit content length
        ]
        
        if metadata:
            prompt_parts.extend([
                "\nDocument metadata:",
                json.dumps(metadata, indent=2)
            ])
            
        prompt_parts.extend([
            "\nClassification rubric:",
            json.dumps(self.rubric, indent=2),
            "\nPlease provide the classification in JSON format with the following structure:",
            """{
                "categories": [
                    {
                        "name": "category_name",
                        "confidence": 0-100,
                        "reasoning": "explanation"
                    }
                ],
                "overall_confidence": 0-100,
                "summary": "brief classification summary"
            }"""
        ])
        
        return "\n".join(prompt_parts)

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM."""
        return """You are a document classification expert. Your task is to:
1. Analyze document content and metadata
2. Match it against the provided classification rubric
3. Return structured classification results
4. Provide confidence scores and reasoning
Be precise and follow the rubric exactly."""

    def _parse_classification_response(self, response: str) -> Dict:
        """Parse the LLM's response into a structured format."""
        try:
            # Extract JSON from response (handle potential text before/after JSON)
            start = response.find('{')
            end = response.rfind('}') + 1
            json_str = response[start:end]
            
            # Parse the JSON
            classification = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['categories', 'overall_confidence', 'summary']
            for field in required_fields:
                if field not in classification:
                    raise ValueError(f"Missing required field: {field}")
            
            return classification
            
        except Exception as e:
            print(f"Error parsing classification response: {e}")
            return {
                "categories": [],
                "overall_confidence": 0,
                "summary": "Error parsing classification",
                "error": str(e)
            }

    def _add_confidence_levels(self, classification: Dict) -> Dict:
        """Add confidence level labels based on configured thresholds."""
        thresholds = self.config.confidence_thresholds
        
        def get_confidence_level(score: int) -> str:
            if score >= thresholds.high:
                return "HIGH"
            elif score >= thresholds.medium:
                return "MEDIUM"
            else:
                return "LOW"
        
        # Add confidence levels to categories
        for category in classification['categories']:
            category['confidence_level'] = get_confidence_level(category['confidence'])
        
        # Add overall confidence level
        classification['overall_confidence_level'] = get_confidence_level(
            classification['overall_confidence']
        )
        
        return classification