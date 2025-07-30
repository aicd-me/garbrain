#!/usr/bin/env python3
"""Test hybrid search functionality."""

import os
import requests
from dotenv import load_dotenv
from openai import OpenAI
import re
from collections import Counter

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
    words = re.findall(r'\b[a-z]+\b', text.lower())
    word_freq = Counter(words)
    
    sparse_indices = []
    sparse_values = []
    
    for word, freq in word_freq.items():
        if len(word) > 2:
            word_id = abs(hash(word)) % 100000
            sparse_indices.append(word_id)
            sparse_values.append(freq / len(words))
    
    return {
        "indices": sparse_indices,
        "values": sparse_values
    }

# Test queries
test_queries = [
    ("What are the food options at the festival?", "food dining eat restaurant gastronomy"),
    ("When does the festival start?", "start begin opening time date schedule"),
    ("Where is the medical team located?", "medical doctor health emergency first aid"),
    ("Tell me about workshops", "workshop class learn teach facilitator"),
    ("What DJs are playing?", "dj music techno house electronic artist")
]

print("Testing HYBRID search functionality...\n")
print("="*70)

for query, keywords in test_queries:
    print(f"\nQuery: '{query}'")
    print(f"Keywords: '{keywords}'")
    print("-" * 70)
    
    try:
        # Generate dense embedding for semantic search
        response = openai_client.embeddings.create(
            input=[query],
            model="text-embedding-3-small"
        )
        query_embedding = response.data[0].embedding
        
        # Create sparse vector for keyword search
        combined_text = query + " " + keywords
        sparse_vector = create_sparse_vector(combined_text)
        
        # Perform hybrid search
        search_payload = {
            "vector": {
                "name": "dense",
                "vector": query_embedding
            },
            "sparse_vector": {
                "name": "sparse",
                "vector": sparse_vector
            },
            "limit": 5,
            "with_payload": True,
            "fusion": "rrf"  # Reciprocal Rank Fusion for combining results
        }
        
        response = requests.post(
            f"{api_url}/collections/{collection_name}/points/search",
            headers=headers,
            json=search_payload,
            timeout=10
        )
        
        if response.status_code == 200:
            results = response.json()['result']
            print(f"\nFound {len(results)} results (HYBRID SEARCH):")
            
            for i, result in enumerate(results, 1):
                score = result['score']
                text = result['payload']['text'][:200] + "..."
                meta = result['payload'].get('meta', {})
                category = meta.get('category', 'N/A')
                topic = meta.get('topic', 'N/A')
                
                print(f"\n{i}. Score: {score:.4f}")
                print(f"   Category: {category}")
                print(f"   Topic: {topic}")
                print(f"   Text: {text}")
        else:
            print(f"Search failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

# Now test with filters
print("\n\n" + "="*70)
print("Testing HYBRID search with FILTERS...")
print("="*70)

# Search for workshops only
print("\nFiltered search: Workshops in the morning")
print("-" * 70)

try:
    # Generate embedding
    query = "morning activities"
    response = openai_client.embeddings.create(
        input=[query],
        model="text-embedding-3-small"
    )
    query_embedding = response.data[0].embedding
    
    # Create sparse vector
    sparse_vector = create_sparse_vector(query + " morning workshop activity")
    
    # Search with filter
    search_payload = {
        "vector": {
            "name": "dense",
            "vector": query_embedding
        },
        "sparse_vector": {
            "name": "sparse",
            "vector": sparse_vector
        },
        "filter": {
            "must": [
                {"key": "meta.category", "match": {"value": "Workshops"}}
            ]
        },
        "limit": 5,
        "with_payload": True,
        "fusion": "rrf"
    }
    
    response = requests.post(
        f"{api_url}/collections/{collection_name}/points/search",
        headers=headers,
        json=search_payload,
        timeout=10
    )
    
    if response.status_code == 200:
        results = response.json()['result']
        print(f"\nFound {len(results)} workshop results:")
        
        for i, result in enumerate(results, 1):
            score = result['score']
            meta = result['payload'].get('meta', {})
            event = meta.get('event', {})
            
            print(f"\n{i}. Score: {score:.4f}")
            print(f"   Workshop: {event.get('name', 'N/A')}")
            print(f"   Time: {event.get('time', 'N/A')}")
            print(f"   Day: {event.get('day', 'N/A')}")
            print(f"   Facilitator: {event.get('facilitator', 'N/A')}")
            
except Exception as e:
    print(f"Error in filtered search: {e}")

print("\n\nHybrid search tests complete!")