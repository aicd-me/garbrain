#!/usr/bin/env python3
"""Quick script to create collection and test ingestion."""

import json
import os
import requests
from dotenv import load_dotenv
import uuid
from openai import OpenAI

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

print(f"API URL: {api_url}")
print(f"Collection: {collection_name}")

# Step 1: Delete collection if exists
print("\nStep 1: Checking if collection exists...")
try:
    response = requests.delete(f"{api_url}/collections/{collection_name}", headers=headers, timeout=10)
    if response.status_code == 200:
        print(f"Deleted existing collection '{collection_name}'")
    else:
        print(f"Collection doesn't exist or couldn't delete (status: {response.status_code})")
except Exception as e:
    print(f"Error checking collection: {e}")

# Step 2: Create collection
print("\nStep 2: Creating collection...")
create_payload = {
    "vectors": {
        "garbrain-dence": {
            "size": 1536,
            "distance": "Cosine"
        }
    }
}

try:
    response = requests.put(
        f"{api_url}/collections/{collection_name}",
        headers=headers,
        json=create_payload,
        timeout=30
    )
    if response.status_code == 200:
        print(f"Successfully created collection '{collection_name}'")
    else:
        print(f"Failed to create collection: {response.status_code} - {response.text}")
        exit(1)
except Exception as e:
    print(f"Error creating collection: {e}")
    exit(1)

# Step 3: Load data and prepare first batch
print("\nStep 3: Loading data...")
with open('garbicz_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
print(f"Loaded {len(data)} documents")

# Initialize OpenAI
openai_client = OpenAI(api_key=openai_api_key)

# Step 4: Test with just one document first
print("\nStep 4: Testing with one document...")
test_doc = data[0]

try:
    # Generate embedding
    response = openai_client.embeddings.create(
        input=[test_doc['text']],
        model="text-embedding-3-small"
    )
    embedding = response.data[0].embedding
    
    # Prepare point
    point_id = str(uuid.uuid4())
    points_payload = {
        "points": [{
            "id": point_id,
            "vector": {
                "garbrain-dence": embedding
            },
            "payload": {
                "text": test_doc['text'],
                "meta": test_doc['meta']
            }
        }]
    }
    
    # Upload point
    response = requests.put(
        f"{api_url}/collections/{collection_name}/points",
        headers=headers,
        json=points_payload,
        timeout=30
    )
    
    if response.status_code == 200:
        print("Successfully uploaded test document!")
        
        # Check collection status
        response = requests.get(f"{api_url}/collections/{collection_name}", headers=headers, timeout=10)
        if response.status_code == 200:
            info = response.json()['result']
            print(f"\nCollection status:")
            print(f"  Points count: {info['points_count']}")
            print(f"  Status: {info['status']}")
    else:
        print(f"Failed to upload: {response.status_code} - {response.text}")
        
except Exception as e:
    print(f"Error in test upload: {e}")

print("\nTest complete! Run full ingestion with qdrant_manager.py when ready.")