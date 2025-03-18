from typing import List, Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import json
from datetime import datetime, timedelta
from config_loader import Config

class DocumentDiscovery:
    def __init__(self, config: Config):
        self.config = config
        self.credentials = self._load_credentials()
        self.service = build('drive', 'v3', credentials=self.credentials)

    def _load_credentials(self) -> Credentials:
        # Load credentials from the OAuth token file
        token_path = os.getenv('GOOGLE_TOKEN_PATH', 'token.json')
        if not os.path.exists(token_path):
            raise FileNotFoundError(f"Google OAuth token not found at {token_path}")
        
        with open(token_path, 'r') as token:
            token_data = json.load(token)
            return Credentials.from_authorized_user_info(token_data)

    def discover_documents(
        self,
        folder_id: Optional[str] = None,
        max_documents: int = 100,
        file_types: Optional[List[str]] = None
    ) -> List[dict]:
        """
        Discover documents in Google Drive that need classification.
        
        Args:
            folder_id: Optional folder ID to limit search scope
            max_documents: Maximum number of documents to return
            file_types: List of file MIME types to include
            
        Returns:
            List of document metadata dictionaries
        """
        try:
            # Build the search query
            query_parts = []
            
            # Filter by folder if specified
            if folder_id:
                query_parts.append(f"'{folder_id}' in parents")
            
            # Filter by file types
            if file_types:
                mime_types = [f"mimeType = '{mime}'" for mime in file_types]
                query_parts.append(f"({' or '.join(mime_types)})")
            
            # Exclude already processed files (using a custom property)
            query_parts.append("not properties has { key='classified' and value='true' }")
            
            # Combine all query parts
            query = " and ".join(query_parts) if query_parts else None
            
            # Execute the search
            results = []
            page_token = None
            
            while True:
                response = self.service.files().list(
                    q=query,
                    spaces='drive',
                    fields='nextPageToken, files(id, name, mimeType, createdTime, modifiedTime, owners, size)',
                    pageToken=page_token,
                    pageSize=min(100, max_documents - len(results))
                ).execute()
                
                results.extend(response.get('files', []))
                
                if len(results) >= max_documents:
                    results = results[:max_documents]
                    break
                    
                page_token = response.get('nextPageToken')
                if not page_token:
                    break
            
            return results
            
        except HttpError as error:
            print(f'An error occurred: {error}')
            return []

    def mark_document_processed(self, document_id: str, classification_result: dict):
        """
        Mark a document as processed with its classification result.
        """
        try:
            # Update the file's properties
            self.service.files().update(
                fileId=document_id,
                body={
                    'properties': {
                        'classified': 'true',
                        'classification_date': datetime.now().isoformat(),
                        'classification_result': json.dumps(classification_result)
                    }
                }
            ).execute()
        except HttpError as error:
            print(f'Error marking document as processed: {error}')