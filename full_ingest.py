#!/usr/bin/env python3
"""Full ingestion script for all documents."""

import json
import os
import requests
from dotenv import load_dotenv
import uuid
from openai import OpenAI
import time

# Load environment variables
load_dotenv()

api_key = os.getenv('QDRANT_API_KEY')
api_url = os.getenv('QDRANT_API_URL').rstrip('/')
collection_name = os.getenv('COLLECTION_NAME', 'garbrain2')
openai_api_key = os.getenv('OPENAI_API_KEY')

headers = {
    "api-key": api_key,
    "Content-Type": "application/json"
}

# Initialize OpenAI
openai_client = OpenAI(api_key=openai_api_key)

# Load data
print("Loading data...")
with open('garbicz_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print(f"Loaded {len(data)} documents")

# Process in batches
batch_size = 20
total_ingested = 0
failed_batches = []

print(f"\nIngesting documents in batches of {batch_size}...")

for i in range(0, len(data), batch_size):
    batch = data[i:i + batch_size]
    batch_num = i // batch_size + 1
    
    print(f"\nBatch {batch_num} ({i+1}-{min(i+batch_size, len(data))} of {len(data)})...")
    
    try:
        # Generate embeddings
        texts = [doc['text'] for doc in batch]
        response = openai_client.embeddings.create(
            input=texts,
            model="text-embedding-3-small"
        )
        embeddings = [item.embedding for item in response.data]
        
        # Prepare points
        points = []
        for doc, embedding in zip(batch, embeddings):
            points.append({
                "id": str(uuid.uuid4()),
                "vector": {
                    "garbrain-dence": embedding
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
            print(f"  ✗ Failed to upload batch: {response.status_code}")
            failed_batches.append(batch_num)
            
        # Small delay to avoid rate limiting
        time.sleep(0.5)
        
    except Exception as e:
        print(f"  ✗ Error in batch {batch_num}: {e}")
        failed_batches.append(batch_num)
        continue

# Final status
print("\n" + "="*50)
print("INGESTION COMPLETE")
print("="*50)

# Check final collection status
try:
    response = requests.get(f"{api_url}/collections/{collection_name}", headers=headers, timeout=10)
    if response.status_code == 200:
        info = response.json()['result']
        print(f"\nCollection '{collection_name}' status:")
        print(f"  Points count: {info['points_count']}")
        print(f"  Status: {info['status']}")
        print(f"  Indexed vectors: {info.get('indexed_vectors_count', 'N/A')}")
except Exception as e:
    print(f"Error getting collection info: {e}")

print(f"\nSummary:")
print(f"  Total documents: {len(data)}")
print(f"  Successfully ingested: {total_ingested}")
print(f"  Failed: {len(data) - total_ingested}")
if failed_batches:
    print(f"  Failed batches: {failed_batches}")

print("\nIngestion complete!")