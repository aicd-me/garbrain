# Garbicz Festival Qdrant Search System

A robust search system for the Garbicz Festival knowledge base using Qdrant's hybrid search capabilities with OpenAI embeddings.

## Overview

This system processes markdown files containing festival information and creates a searchable vector database using Qdrant. It supports both semantic and keyword-based searches for festival-related queries.

## Components

### 1. Data Processor (`data_processor.py`)
- Reads and parses markdown files
- Standardizes data into a consistent JSON schema
- Extracts metadata including categories, locations, events, and keywords
- Outputs processed data to `garbicz_data.json`

### 2. Qdrant Manager (`qdrant_manager.py`)
- Connects to Qdrant vector database
- Creates/manages the 'garbrain2' collection (defined in .env) with proper indexing
- Generates embeddings using OpenAI's text-embedding-3-small model
- Ingests processed data in batches
- Provides search functionality

### 3. Test Queries (`test_queries.py`)
- Tests various query patterns
- Validates search accuracy
- Supports filtered searches by category, location, event details
- Provides performance metrics

## Setup

### Prerequisites
- Python 3.8+
- Qdrant instance (provided)
- OpenAI API key

### Installation

1. Install required packages:
```bash
pip install qdrant-client openai python-dotenv tqdm
```

2. Create `.env` file with credentials:
```env
QDRANT_API_KEY=NObiSurpKZgDVbsXnzEp3BuuTyo1BvLp
QDRANT_API_URL=https://garbrain.aicd.me/
OPENAI_API_KEY=your_openai_api_key_here
QDRANT_COLLECTION_NAME=garbrain2
```

## Usage

### 1. Process Markdown Files
```bash
python data_processor.py
```

This will:
- Read all markdown files in the current directory
- Parse and standardize the data
- Generate `garbicz_data.json` with structured documents

### 2. Ingest Data into Qdrant
```bash
python qdrant_manager.py
```

This will:
- Connect to the Qdrant instance
- Create/update the 'garbrain2' collection with proper indexes
- Generate OpenAI embeddings for all documents
- Upload documents in batches

### 3. Test Search Functionality
```bash
python test_queries.py
```

This will run various test queries to validate the search system.

## Data Schema

Each document in the collection follows this structure:

```json
{
  "text": "The main content of the document",
  "meta": {
    "category": "FAQ|Gastronomy|Timetable|Workshops|General|etc",
    "topic": "Specific topic or title",
    "type": "general info|dining|DJ|workshop|performance",
    "location": {
      "name": "Location name",
      "coordinates": {"lat": 52.306927, "lon": 14.999499}
    },
    "event": {
      "name": "Event/Artist name",
      "day": "Day of the week",
      "time": "Time of event",
      "facilitator": "Workshop facilitator (if applicable)"
    },
    "keywords": ["keyword1", "keyword2", "keyword3"]
  }
}
```

## Search Examples

### Basic Semantic Search
```python
results = tester.search("What are the food options?")
```

### Filtered Search by Category
```python
results = tester.search(
    "workshops available", 
    filter_dict={
        "must": [
            {"key": "meta.category", "match": {"value": "Workshops"}}
        ]
    }
)
```

### Location-based Search
```python
results = tester.search(
    "events at Seebühne",
    filter_dict={
        "must": [
            {"key": "meta.location.name", "match": {"value": "Seebühne"}}
        ]
    }
)
```

## Files Processed

- `garbicz_faq_chunked(en).md` - Frequently asked questions
- `garbicz_gastro_highlights.md` - Food and dining options
- `garbicz_timetable_chunked(en).md` - Event schedule and performances
- `garbicz_workshops.md` - Workshop listings
- `garbicz-general.md` - General festival information
- `garbicz-overview.md` - Festival overview and guidelines
- `locations.md` - Venue locations with coordinates

## Performance

- Vector dimensions: 1536 (OpenAI text-embedding-3-small)
- Distance metric: Cosine similarity
- Indexed fields: category, topic, type, location.name, event details, keywords
- Batch processing: 100 documents per batch

## Troubleshooting

### Connection Issues
- Verify Qdrant URL is accessible
- Check API key is correct
- Ensure network connectivity

### Embedding Errors
- Verify OpenAI API key is valid
- Check rate limits aren't exceeded
- Monitor token usage

### Search Quality
- Ensure all documents are properly indexed
- Verify metadata extraction is working
- Check embedding model consistency

## Future Improvements

1. Add support for multilingual content
2. Implement query expansion for better recall
3. Add relevance feedback mechanism
4. Create API endpoints for integration
5. Implement caching for frequently asked queries
6. Add monitoring and analytics