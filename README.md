# Goose Google Drive Classifier Extension

This extension provides automated classification of Google Drive documents using LLMs. It helps identify and categorize documents based on their content and metadata using a configurable classification rubric.

## Features

- Automated document discovery in Google Drive
- LLM-based content classification
- Configurable classification rubrics
- Confidence scoring
- Batch processing with caching
- Classification reports generation

## Installation

1. Install the extension using Goose:
   ```bash
   goose extension install gdrive-classifier
   ```

2. Configure the extension:
   ```yaml
   rubric_path: /path/to/rubric.json
   confidence_thresholds:
     high: 90
     medium: 70
     low: 0
   batch_size: 100
   cache_duration_days: 7
   ```

## Usage

The extension provides several tools for document classification:

1. `discover_documents` - Find documents in Google Drive
2. `classify_documents` - Classify discovered documents
3. `generate_report` - Create classification reports
4. `validate_samples` - Validate classification accuracy

## Configuration

### Rubric Format

The classification rubric should be a JSON file with the following structure:

```json
{
  "categories": [
    {
      "name": "category_name",
      "description": "category_description",
      "patterns": ["pattern1", "pattern2"],
      "keywords": ["keyword1", "keyword2"]
    }
  ]
}
```

### Authentication

The extension uses Google OAuth2 for authentication. You'll need to set up credentials in your Google Cloud Project.

## License

MIT