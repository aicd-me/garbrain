# Qdrant Hybrid Search Setup for n8n

This guide explains how to configure the Qdrant agent tool in n8n to use hybrid search with the Garbicz Festival knowledge base.

## Overview

The Garbicz knowledge base uses **hybrid search** combining:
- **Dense vectors**: Semantic search using OpenAI embeddings (1536 dimensions)
- **Sparse vectors**: Keyword-based search for exact matches
- **RRF fusion**: Reciprocal Rank Fusion to combine both search methods

## Collection Details

- **Collection Name**: `garbrain3`
- **Qdrant URL**: `https://garbrain.aicd.me/`
- **API Key**: `NObiSurpKZgDVbsXnzEp3BuuTyo1BvLp`
- **Dense Vector Name**: `dense`
- **Sparse Vector Name**: `sparse`
- **Vector Size**: 1536 (OpenAI text-embedding-3-small)

## n8n Qdrant Node Configuration

### 1. Basic Connection Setup

In your n8n Qdrant node:

```json
{
  "authentication": {
    "type": "apiKey",
    "apiKey": "NObiSurpKZgDVbsXnzEp3BuuTyo1BvLp"
  },
  "url": "https://garbrain.aicd.me",
  "collection": "garbrain3"
}
```

### 2. Hybrid Search Query Structure

For hybrid search, you need to provide both dense and sparse vectors:

```json
{
  "operation": "search",
  "collection": "garbrain3",
  "vector": {
    "name": "dense",
    "vector": [/* 1536-dimensional array from OpenAI */]
  },
  "sparse_vector": {
    "name": "sparse",
    "vector": {
      "indices": [/* array of word IDs */],
      "values": [/* array of TF-IDF scores */]
    }
  },
  "limit": 5,
  "with_payload": true,
  "fusion": "rrf"
}
```

### 3. n8n Workflow Example

Here's a complete n8n workflow setup:

#### Step 1: OpenAI Embeddings Node
```json
{
  "name": "Generate Embeddings",
  "type": "n8n-nodes-base.openAi",
  "operation": "embedding",
  "model": "text-embedding-3-small",
  "text": "={{$json.query}}"
}
```

#### Step 2: Code Node (Generate Sparse Vector)
```javascript
// Function to create sparse vector from text
function createSparseVector(text) {
  const words = text.toLowerCase().match(/\b[a-z]+\b/g) || [];
  const wordFreq = {};
  
  // Count frequencies
  words.forEach(word => {
    if (word.length > 2) {
      wordFreq[word] = (wordFreq[word] || 0) + 1;
    }
  });
  
  const indices = [];
  const values = [];
  
  // Convert to sparse vector format
  Object.entries(wordFreq).forEach(([word, freq]) => {
    const wordId = Math.abs(hashCode(word)) % 100000;
    indices.push(wordId);
    values.push(freq / words.length);
  });
  
  return { indices, values };
}

// Simple hash function
function hashCode(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return hash;
}

// Process the query
const query = $input.item.json.query;
const keywords = $input.item.json.keywords || "";
const combinedText = query + " " + keywords;

return {
  sparseVector: createSparseVector(combinedText)
};
```

#### Step 3: Qdrant Search Node
```json
{
  "name": "Hybrid Search",
  "type": "n8n-nodes-base.qdrant",
  "operation": "search",
  "requestOptions": {
    "body": {
      "vector": {
        "name": "dense",
        "vector": "={{$node['Generate Embeddings'].json.embedding}}"
      },
      "sparse_vector": {
        "name": "sparse", 
        "vector": "={{$node['Code'].json.sparseVector}}"
      },
      "limit": 5,
      "with_payload": true,
      "fusion": "rrf"
    }
  }
}
```

### 4. Filtered Search

To search within specific categories:

```json
{
  "filter": {
    "must": [
      {
        "key": "meta.category",
        "match": {
          "value": "Workshops"
        }
      }
    ]
  }
}
```

Available filter fields:
- `meta.category`: FAQ, Gastronomy, Timetable, Workshops, General
- `meta.type`: general info, dining, DJ, workshop, performance
- `meta.location.name`: Venue names
- `meta.event.name`: Event/Artist names
- `meta.event.day`: Day of the week
- `meta.keywords`: Keyword array

### 5. Complete n8n HTTP Request Node Example

If using the HTTP Request node instead:

```json
{
  "method": "POST",
  "url": "https://garbrain.aicd.me/collections/garbrain3/points/search",
  "authentication": {
    "type": "genericHeaderAuth",
    "headerName": "api-key",
    "headerValue": "NObiSurpKZgDVbsXnzEp3BuuTyo1BvLp"
  },
  "headers": {
    "Content-Type": "application/json"
  },
  "body": {
    "vector": {
      "name": "dense",
      "vector": "={{$json.embedding}}"
    },
    "sparse_vector": {
      "name": "sparse",
      "vector": {
        "indices": "={{$json.sparseIndices}}",
        "values": "={{$json.sparseValues}}"
      }
    },
    "limit": 5,
    "with_payload": true,
    "fusion": "rrf",
    "filter": {
      "must": [
        {
          "key": "meta.category",
          "match": {
            "value": "={{$json.filterCategory}}"
          }
        }
      ]
    }
  }
}
```

## Example Queries and Expected Results

### 1. Food Information
**Query**: "What food options are available?"
**Keywords**: "food dining restaurant gastronomy eat"
**Expected**: Returns information about Food Forest, dining options, gastronomy highlights

### 2. Workshop Search
**Query**: "morning yoga classes"
**Keywords**: "yoga workshop morning class exercise"
**Filter**: `meta.category = "Workshops"`
**Expected**: Returns morning yoga workshops with facilitator info

### 3. DJ Lineup
**Query**: "techno DJs playing Saturday"
**Keywords**: "dj techno house electronic music saturday"
**Filter**: `meta.event.day = "Saturday"`
**Expected**: Returns DJ performances on Saturday

## Response Format

Each search result includes:
```json
{
  "id": "uuid",
  "score": 0.85,
  "payload": {
    "text": "Full content text...",
    "meta": {
      "category": "Workshops",
      "topic": "Electric Yoga",
      "type": "workshop",
      "location": {
        "name": "Amphitheater",
        "coordinates": {"lat": 52.306927, "lon": 14.999499}
      },
      "event": {
        "name": "Electric Yoga",
        "day": "Friday",
        "time": "10:00",
        "facilitator": "Steph Yaksch"
      },
      "keywords": ["yoga", "morning", "wellness"]
    }
  }
}
```

## Tips for Better Results

1. **Combine semantic and keyword queries**: Use natural language in the query and add relevant keywords
2. **Use filters**: Narrow down results by category, location, or event type
3. **Adjust fusion method**: RRF works well for most cases, but you can experiment with other fusion methods
4. **Set appropriate limits**: Start with 5-10 results and adjust based on needs
5. **Include context**: Add temporal context (morning, evening) or spatial context (stage names) to queries

## Troubleshooting

1. **No results**: Check if both vector types are being sent correctly
2. **Poor relevance**: Adjust the keyword list or try different query phrasings
3. **Timeout issues**: Reduce the limit or add request timeout settings
4. **Authentication errors**: Verify the API key is correctly set in headers

## Advanced Usage

### Custom Scoring
You can adjust how dense and sparse results are combined:
```json
{
  "fusion": {
    "type": "rrf",
    "k": 60  // Adjust ranking constant (default: 60)
  }
}
```

### Batch Search
For multiple queries:
```json
{
  "searches": [
    {
      "vector": {"name": "dense", "vector": [...]},
      "sparse_vector": {"name": "sparse", "vector": {...}},
      "filter": {...}
    },
    // More searches...
  ]
}
```

This setup enables powerful hybrid search capabilities combining the semantic understanding of dense vectors with the precision of keyword matching through sparse vectors.