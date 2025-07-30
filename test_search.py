#!/usr/bin/env python3
"""Test search functionality."""

import os
import requests
from dotenv import load_dotenv
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

# Initialize OpenAI
openai_client = OpenAI(api_key=openai_api_key)

# Test queries
test_queries = [
    "What are the food options at the festival?",
    "When does the festival start?",
    "Where is the medical team located?",
    "Tell me about workshops",
    "What DJs are playing?"
]

print("Testing search functionality...\n")

for query in test_queries:
    print(f"\nQuery: '{query}'")
    print("-" * 50)
    
    try:
        # Generate query embedding
        response = openai_client.embeddings.create(
            input=[query],
            model="text-embedding-3-small"
        )
        query_embedding = response.data[0].embedding
        
        # Search
        search_payload = {
            "vector": {
                "name": "garbrain-dence",
                "vector": query_embedding
            },
            "limit": 3,
            "with_payload": True
        }
        
        response = requests.post(
            f"{api_url}/collections/{collection_name}/points/search",
            headers=headers,
            json=search_payload,
            timeout=10
        )
        
        if response.status_code == 200:
            results = response.json()['result']
            print(f"Found {len(results)} results:")
            
            for i, result in enumerate(results, 1):
                score = result['score']
                text = result['payload']['text'][:150] + "..."
                meta = result['payload'].get('meta', {})
                category = meta.get('category', 'N/A')
                
                print(f"\n{i}. Score: {score:.4f}")
                print(f"   Category: {category}")
                print(f"   Text: {text}")
        else:
            print(f"Search failed: {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

print("\n\nSearch tests complete!")