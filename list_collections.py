#!/usr/bin/env python3
"""List all collections in Qdrant database."""

import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient

# Load environment variables
load_dotenv()

# Get credentials from .env
api_key = os.getenv('QDRANT_API_KEY')
api_url = os.getenv('QDRANT_API_URL')

print(f"Connecting to Qdrant at: {api_url}")

try:
    # Initialize Qdrant client
    client = QdrantClient(
        url=api_url,
        api_key=api_key,
        prefer_grpc=False,
        timeout=10.0,
        https=True
    )
    
    # Get all collections
    print("Fetching collections...")
    collections = client.get_collections()
    
    print(f"\nFound {len(collections.collections)} collections:\n")
    
    for collection in collections.collections:
        print(f"Collection: {collection.name}")
        try:
            # Get detailed info for each collection
            info = client.get_collection(collection.name)
            print(f"  Points count: {info.points_count}")
            print(f"  Vectors count: {info.vectors_count}")
            print(f"  Status: {info.status}")
            if hasattr(info.config.params, 'vectors'):
                print(f"  Vector configs: {info.config.params.vectors}")
        except Exception as e:
            print(f"  Error getting details: {e}")
        print()
        
except Exception as e:
    print(f"Error connecting to Qdrant: {e}")