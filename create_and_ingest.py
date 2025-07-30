#!/usr/bin/env python3
"""Create collection and ingest data into Qdrant."""

import json
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid
from openai import OpenAI

# Load environment variables
load_dotenv()

# Initialize clients
api_key = os.getenv('QDRANT_API_KEY')
api_url = os.getenv('QDRANT_API_URL')
collection_name = os.getenv('COLLECTION_NAME', 'garbrain2')
openai_api_key = os.getenv('OPENAI_API_KEY')

print(f"Connecting to Qdrant at: {api_url}")
print(f"Collection name: {collection_name}")

# Initialize Qdrant client
client = QdrantClient(
    url=api_url,
    api_key=api_key,
    prefer_grpc=False,
    timeout=30.0,
    https=True
)

# Initialize OpenAI client
openai_client = OpenAI(api_key=openai_api_key)
embedding_model = "text-embedding-3-small"
vector_size = 1536
vector_name = "garbrain-dence"

# Step 1: Create collection
print("\nStep 1: Creating collection...")
try:
    # Check if collection exists
    collections = client.get_collections().collections
    if any(col.name == collection_name for col in collections):
        print(f"Collection '{collection_name}' already exists. Deleting it...")
        client.delete_collection(collection_name)
        print("Collection deleted.")
    
    # Create new collection
    client.create_collection(
        collection_name=collection_name,
        vectors_config={
            vector_name: VectorParams(
                size=vector_size,
                distance=Distance.COSINE
            )
        }
    )
    print(f"Created collection '{collection_name}'")
except Exception as e:
    print(f"Error creating collection: {e}")
    exit(1)

# Step 2: Load data
print("\nStep 2: Loading data...")
try:
    with open('garbicz_data.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"Loaded {len(data)} documents")
except Exception as e:
    print(f"Error loading data: {e}")
    exit(1)

# Step 3: Ingest data in small batches
print("\nStep 3: Ingesting data...")
batch_size = 10  # Smaller batch size for stability
total_ingested = 0

for i in range(0, len(data), batch_size):
    batch = data[i:i + batch_size]
    batch_num = i // batch_size + 1
    
    print(f"\nProcessing batch {batch_num} ({i+1}-{min(i+batch_size, len(data))} of {len(data)})...")
    
    try:
        # Generate embeddings
        texts = [doc['text'] for doc in batch]
        response = openai_client.embeddings.create(
            input=texts,
            model=embedding_model
        )
        embeddings = [item.embedding for item in response.data]
        
        # Prepare points
        points = []
        for doc, embedding in zip(batch, embeddings):
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector={vector_name: embedding},
                payload={
                    "text": doc['text'],
                    "meta": doc['meta']
                }
            )
            points.append(point)
        
        # Upload batch
        client.upsert(
            collection_name=collection_name,
            points=points
        )
        
        total_ingested += len(batch)
        print(f"  Successfully ingested {len(batch)} documents (Total: {total_ingested}/{len(data)})")
        
    except Exception as e:
        print(f"  Error in batch {batch_num}: {e}")
        continue

# Step 4: Verify collection
print("\nStep 4: Verifying collection...")
try:
    info = client.get_collection(collection_name)
    print(f"\nCollection Info:")
    print(f"  Name: {info.collection_name}")
    print(f"  Points count: {info.points_count}")
    print(f"  Status: {info.status}")
    print(f"\nSuccessfully created and populated collection '{collection_name}'!")
except Exception as e:
    print(f"Error getting collection info: {e}")