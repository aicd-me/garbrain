#!/usr/bin/env python3
"""Create collection with hybrid search and ingest data with both dense and sparse vectors."""

import json
import os
import requests
from dotenv import load_dotenv
import uuid
from openai import OpenAI
import time
from collections import Counter
import re

# Load environment variables
load_dotenv()

api_key = os.getenv('QDRANT_API_KEY')
api_url = os.getenv('QDRANT_API_URL').rstrip('/')
collection_name = os.getenv('COLLECTION_NAME', 'garbrain3')
openai_api_key = os.getenv('OPENAI_API_KEY')

headers = {
    "api-key": api_key,
    "Content-Type": "application/json"
}

# Initialize OpenAI
openai_client = OpenAI(api_key=openai_api_key)

def create_sparse_vector(text):
    """Create a simple sparse vector from text using TF-IDF-like approach."""
    # Tokenize and clean text
    words = re.findall(r'\b[a-z]+\b', text.lower())
    
    # Count word frequencies
    word_freq = Counter(words)
    
    # Create sparse vector (word_id: frequency)
    sparse_indices = []
    sparse_values = []
    
    # Use a simple hash function to convert words to IDs
    for word, freq in word_freq.items():
        if len(word) > 2:  # Skip very short words
            word_id = abs(hash(word)) % 100000  # Limit to 100k vocabulary
            sparse_indices.append(word_id)
            # TF-IDF-like scoring (simplified)
            sparse_values.append(freq / len(words))
    
    return {
        "indices": sparse_indices,
        "values": sparse_values
    }

# Step 1: Delete and create collection with hybrid configuration
print(f"\nStep 1: Creating hybrid collection '{collection_name}'...")
try:
    # Delete if exists
    response = requests.delete(f"{api_url}/collections/{collection_name}", headers=headers, timeout=10)
    if response.status_code == 200:
        print(f"Deleted existing collection '{collection_name}'")
    
    # Create collection with both dense and sparse vectors
    create_payload = {
        "vectors": {
            "dense": {
                "size": 1536,
                "distance": "Cosine"
            }
        },
        "sparse_vectors": {
            "sparse": {
                "index": {
                    "on_disk": False
                }
            }
        }
    }
    
    response = requests.put(
        f"{api_url}/collections/{collection_name}",
        headers=headers,
        json=create_payload,
        timeout=30
    )
    
    if response.status_code == 200:
        print(f"Successfully created hybrid collection '{collection_name}'")
    else:
        print(f"Failed to create collection: {response.status_code} - {response.text}")
        exit(1)
except Exception as e:
    print(f"Error creating collection: {e}")
    exit(1)

# Step 2: Create payload indexes for filtering
print("\nStep 2: Creating payload indexes...")
index_fields = [
    ("meta.category", "keyword"),
    ("meta.topic", "text"), 
    ("meta.type", "keyword"),
    ("meta.location.name", "text"),
    ("meta.event.name", "text"),
    ("meta.keywords", "keyword"),
    ("text", "text")
]

for field_name, field_type in index_fields:
    try:
        payload = {
            "field_name": field_name,
            "field_type": field_type
        }
        response = requests.put(
            f"{api_url}/collections/{collection_name}/index",
            headers=headers,
            json=payload,
            timeout=10
        )
        if response.status_code == 200:
            print(f"  ✓ Created {field_type} index on '{field_name}'")
        else:
            print(f"  ✗ Failed to create index on '{field_name}': {response.status_code}")
    except Exception as e:
        print(f"  ✗ Error creating index on '{field_name}': {e}")

# Step 3: Load data
print("\nStep 3: Loading data...")
with open('garbicz_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print(f"Loaded {len(data)} documents")

# Step 4: Ingest data with both dense and sparse vectors
print("\nStep 4: Ingesting data with hybrid vectors...")
batch_size = 20
total_ingested = 0
failed_batches = []

for i in range(0, len(data), batch_size):
    batch = data[i:i + batch_size]
    batch_num = i // batch_size + 1
    
    print(f"\nBatch {batch_num} ({i+1}-{min(i+batch_size, len(data))} of {len(data)})...")
    
    try:
        # Generate dense embeddings
        texts = [doc['text'] for doc in batch]
        response = openai_client.embeddings.create(
            input=texts,
            model="text-embedding-3-small"
        )
        embeddings = [item.embedding for item in response.data]
        
        # Prepare points with both dense and sparse vectors
        points = []
        for doc, embedding in zip(batch, embeddings):
            # Create sparse vector from text
            sparse_vector = create_sparse_vector(doc['text'])
            
            points.append({
                "id": str(uuid.uuid4()),
                "vector": {
                    "dense": embedding
                },
                "sparse_vector": {
                    "sparse": sparse_vector
                },
                "payload": {
                    "text": doc['text'],
                    "meta": doc['meta']
                }
            })
        
        # Upload batch
        points_payload = {"points": points}
        response = requests.put(
            f"{api_url}/collections/{collection_name}/points",
            headers=headers,
            json=points_payload,
            timeout=30
        )
        
        if response.status_code == 200:
            total_ingested += len(batch)
            print(f"  ✓ Successfully ingested {len(batch)} documents (Total: {total_ingested}/{len(data)})")
        else:
            print(f"  ✗ Failed to upload batch: {response.status_code} - {response.text}")
            failed_batches.append(batch_num)
            
        # Small delay to avoid rate limiting
        time.sleep(0.5)
        
    except Exception as e:
        print(f"  ✗ Error in batch {batch_num}: {e}")
        failed_batches.append(batch_num)
        continue

# Final status
print("\n" + "="*50)
print("HYBRID INGESTION COMPLETE")
print("="*50)

# Check final collection status
try:
    response = requests.get(f"{api_url}/collections/{collection_name}", headers=headers, timeout=10)
    if response.status_code == 200:
        info = response.json()['result']
        print(f"\nCollection '{collection_name}' status:")
        print(f"  Points count: {info['points_count']}")
        print(f"  Status: {info['status']}")
        print(f"  Dense vectors: {info['config']['params']['vectors']}")
        print(f"  Sparse vectors: {info['config']['params']['sparse_vectors']}")
except Exception as e:
    print(f"Error getting collection info: {e}")

print(f"\nSummary:")
print(f"  Total documents: {len(data)}")
print(f"  Successfully ingested: {total_ingested}")
print(f"  Failed: {len(data) - total_ingested}")
if failed_batches:
    print(f"  Failed batches: {failed_batches}")

print("\nHybrid ingestion complete!")