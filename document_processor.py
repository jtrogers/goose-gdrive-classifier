from typing import List, Dict, Optional
import json
import os
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from config_loader import Config
from document_classifier import DocumentClassifier
import random

class DocumentProcessor:
    def __init__(self, config: Config):
        self.config = config
        self.classifier = DocumentClassifier(config)
        self.credentials = self._load_credentials()
        self.service = build('drive', 'v3', credentials=self.credentials)

    def _load_credentials(self) -> Credentials:
        token_path = os.getenv('GOOGLE_TOKEN_PATH', 'token.json')
        if not os.path.exists(token_path):
            raise FileNotFoundError(f"Google OAuth token not found at {token_path}")
        
        with open(token_path, 'r') as token:
            token_data = json.load(token)
            return Credentials.from_authorized_user_info(token_data)

    def process_documents(
        self,
        document_ids: List[str],
        batch_size: Optional[int] = None
    ) -> List[Dict]:
        """
        Process a list of documents for classification.
        
        Args:
            document_ids: List of Google Drive document IDs
            batch_size: Optional batch size for processing
            
        Returns:
            List of classification results
        """
        batch_size = batch_size or self.config.processing.batch_size
        results = []
        
        # Process documents in batches
        for i in range(0, len(document_ids), batch_size):
            batch = document_ids[i:i + batch_size]
            batch_results = self._process_batch(batch)
            results.extend(batch_results)
            
        return results

    def _process_batch(self, document_ids: List[str]) -> List[Dict]:
        """Process a batch of documents."""
        results = []
        
        for doc_id in document_ids:
            try:
                # Get document content and metadata
                content, metadata = self._get_document_content(doc_id)
                
                # Classify the document
                classification = self.classifier.classify_document(content, metadata)
                
                # Store the results
                result = {
                    'document_id': doc_id,
                    'classification': classification,
                    'processed_at': datetime.now().isoformat(),
                    'success': True
                }
                
                # Update document properties with classification
                self._update_document_properties(doc_id, classification)
                
            except Exception as e:
                result = {
                    'document_id': doc_id,
                    'error': str(e),
                    'processed_at': datetime.now().isoformat(),
                    'success': False
                }
            
            results.append(result)
            
        return results

    def _get_document_content(self, doc_id: str) -> tuple:
        """Get document content and metadata from Google Drive."""
        # Get metadata
        file = self.service.files().get(
            fileId=doc_id,
            fields='id, name, mimeType, createdTime, modifiedTime, owners'
        ).execute()
        
        # Get content based on mime type
        if file['mimeType'] == 'application/vnd.google-apps.document':
            content = self._get_docs_content(doc_id)
        else:
            content = self._get_file_content(doc_id)
            
        return content, file

    def _get_docs_content(self, doc_id: str) -> str:
        """Get content from a Google Doc."""
        docs_service = build('docs', 'v1', credentials=self.credentials)
        document = docs_service.documents().get(documentId=doc_id).execute()
        
        # Extract text content
        content = []
        for elem in document.get('body', {}).get('content', []):
            if 'paragraph' in elem:
                for para_elem in elem['paragraph']['elements']:
                    if 'textRun' in para_elem:
                        content.append(para_elem['textRun']['content'])
                        
        return '\n'.join(content)

    def _get_file_content(self, file_id: str) -> str:
        """Get content from a regular file."""
        request = self.service.files().get_media(fileId=file_id)
        return request.execute().decode('utf-8')

    def _update_document_properties(self, doc_id: str, classification: Dict):
        """Update document properties with classification results."""
        properties = {
            'classified': 'true',
            'classification_date': datetime.now().isoformat(),
            'classification_summary': classification['summary'],
            'overall_confidence': str(classification['overall_confidence']),
            'categories': ','.join([c['name'] for c in classification['categories']])
        }
        
        self.service.files().update(
            fileId=doc_id,
            body={'properties': properties}
        ).execute()

    def generate_report(
        self,
        format: str = "markdown",
        include_details: bool = True
    ) -> str:
        """Generate a classification report."""
        # Get all classified documents
        results = self.service.files().list(
            q="properties has { key='classified' and value='true' }",
            fields='files(id, name, properties)'
        ).execute()
        
        files = results.get('files', [])
        
        if format == "markdown":
            return self._generate_markdown_report(files, include_details)
        else:
            return json.dumps(files, indent=2)

    def _generate_markdown_report(self, files: List[Dict], include_details: bool) -> str:
        """Generate a markdown format report."""
        report_parts = [
            "# Document Classification Report",
            f"\nGenerated: {datetime.now().isoformat()}",
            f"\nTotal Documents: {len(files)}",
            "\n## Summary",
        ]
        
        # Aggregate statistics
        categories = {}
        confidence_levels = {'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
        
        for file in files:
            props = file.get('properties', {})
            for cat in props.get('categories', '').split(','):
                if cat:
                    categories[cat] = categories.get(cat, 0) + 1
            
            confidence = int(props.get('overall_confidence', 0))
            if confidence >= self.config.confidence_thresholds.high:
                confidence_levels['HIGH'] += 1
            elif confidence >= self.config.confidence_thresholds.medium:
                confidence_levels['MEDIUM'] += 1
            else:
                confidence_levels['LOW'] += 1
        
        # Add statistics to report
        report_parts.extend([
            "\n### Categories",
            *[f"- {cat}: {count}" for cat, count in categories.items()],
            "\n### Confidence Levels",
            *[f"- {level}: {count}" for level, count in confidence_levels.items()]
        ])
        
        if include_details:
            report_parts.extend([
                "\n## Detailed Results",
                *[self._format_file_details(f) for f in files]
            ])
        
        return "\n".join(report_parts)

    def _format_file_details(self, file: Dict) -> str:
        """Format file details for markdown report."""
        props = file.get('properties', {})
        return f"""
### {file['name']}
- ID: {file['id']}
- Classification Date: {props.get('classification_date')}
- Categories: {props.get('categories')}
- Confidence: {props.get('overall_confidence')}%
- Summary: {props.get('classification_summary')}
"""

    def validate_samples(self, sample_size: int = 100) -> Dict:
        """
        Validate classification results using random sampling.
        
        Args:
            sample_size: Number of documents to sample
            
        Returns:
            Validation results and statistics
        """
        # Get all classified documents
        results = self.service.files().list(
            q="properties has { key='classified' and value='true' }",
            fields='files(id, name, properties)'
        ).execute()
        
        files = results.get('files', [])
        
        # Take a random sample
        sample = random.sample(files, min(sample_size, len(files)))
        
        # Analyze the sample
        validation_results = {
            'sample_size': len(sample),
            'total_documents': len(files),
            'confidence_distribution': {
                'high': 0,
                'medium': 0,
                'low': 0
            },
            'category_distribution': {},
            'samples': []
        }
        
        for file in sample:
            props = file.get('properties', {})
            confidence = int(props.get('overall_confidence', 0))
            
            # Count confidence levels
            if confidence >= self.config.confidence_thresholds.high:
                validation_results['confidence_distribution']['high'] += 1
            elif confidence >= self.config.confidence_thresholds.medium:
                validation_results['confidence_distribution']['medium'] += 1
            else:
                validation_results['confidence_distribution']['low'] += 1
            
            # Count categories
            for category in props.get('categories', '').split(','):
                if category:
                    validation_results['category_distribution'][category] = \
                        validation_results['category_distribution'].get(category, 0) + 1
            
            # Add sample details
            validation_results['samples'].append({
                'id': file['id'],
                'name': file['name'],
                'confidence': confidence,
                'categories': props.get('categories', '').split(','),
                'summary': props.get('classification_summary')
            })
        
        return validation_results