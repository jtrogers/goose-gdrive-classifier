from typing import List, Optional
from pydantic import BaseModel
from goose_mcp import MCPServer, register_function
import json
import os
from document_classifier import DocumentClassifier
from document_discovery import DocumentDiscovery
from document_processor import DocumentProcessor
from config_loader import ConfigLoader

class DiscoverRequest(BaseModel):
    folder_id: Optional[str] = None
    max_documents: Optional[int] = 100
    file_types: Optional[List[str]] = None

class ClassifyRequest(BaseModel):
    document_ids: List[str]
    batch_size: Optional[int] = None

class ReportRequest(BaseModel):
    output_format: Optional[str] = "markdown"
    include_details: Optional[bool] = True

class ValidateRequest(BaseModel):
    sample_size: Optional[int] = 100

class GDriveClassifierMCP(MCPServer):
    def __init__(self):
        super().__init__()
        self.config = ConfigLoader().load_config()
        self.classifier = DocumentClassifier(self.config)
        self.discovery = DocumentDiscovery(self.config)
        self.processor = DocumentProcessor(self.config)

    @register_function(
        "Discover documents in Google Drive that need classification",
        request_model=DiscoverRequest
    )
    async def discover_documents(self, request: DiscoverRequest):
        documents = self.discovery.discover_documents(
            folder_id=request.folder_id,
            max_documents=request.max_documents,
            file_types=request.file_types
        )
        return {"documents": documents}

    @register_function(
        "Classify discovered documents using LLM",
        request_model=ClassifyRequest
    )
    async def classify_documents(self, request: ClassifyRequest):
        batch_size = request.batch_size or self.config.processing.batch_size
        results = self.processor.process_documents(
            document_ids=request.document_ids,
            batch_size=batch_size
        )
        return {"classifications": results}

    @register_function(
        "Generate a classification report",
        request_model=ReportRequest
    )
    async def generate_report(self, request: ReportRequest):
        report = self.processor.generate_report(
            format=request.output_format,
            include_details=request.include_details
        )
        return {"report": report}

    @register_function(
        "Validate classification samples",
        request_model=ValidateRequest
    )
    async def validate_samples(self, request: ValidateRequest):
        validation_results = self.processor.validate_samples(
            sample_size=request.sample_size
        )
        return {"validation": validation_results}

if __name__ == "__main__":
    server = GDriveClassifierMCP()
    server.start()