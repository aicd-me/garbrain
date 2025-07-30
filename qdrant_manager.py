#!/usr/bin/env python3
"""
Qdrant manager for Garbicz Festival knowledge base.
Creates collection, configures indexing, and ingests processed data.
"""

import json
import os
from typing import List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, 
    VectorParams, 
    PointStruct,
    PayloadSchemaType
)
import uuid
from tqdm import tqdm
from openai import OpenAI


class QdrantManager:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        self.api_key = os.getenv('QDRANT_API_KEY', 'NObiSurpKZgDVbsXnzEp3BuuTyo1BvLp')
        self.api_url = os.getenv('QDRANT_API_URL', 'https://garbrain.aicd.me/')
        self.collection_name = os.getenv('COLLECTION_NAME', 'garbrain3')
        
        # Initialize Qdrant client
        self.client = QdrantClient(
            url=self.api_url,
            api_key=self.api_key,
            prefer_grpc=False,
            timeout=120.0,
            https=True
        )
        
        # Initialize OpenAI client for embeddings
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        
        self.openai_client = OpenAI(api_key=self.openai_api_key)
        self.embedding_model = "text-embedding-3-small"  # 1536 dimensions
        self.vector_size = 1536  # text-embedding-3-small produces 1536-dimensional vectors
        self.vector_name = "garbrain-dence"  # Match the existing vector name
        
    def create_collection(self):
        """Create Qdrant collection with proper configuration."""
        try:
            # Check if collection exists
            collections = self.client.get_collections().collections
            if any(col.name == self.collection_name for col in collections):
                print(f"Collection '{self.collection_name}' already exists. Using existing collection.")
                # Clear existing data if needed
                # self.client.delete(
                #     collection_name=self.collection_name,
                #     points_selector={"filter": {}}
                # )
            else:
                # Create collection with vector configuration
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config={
                        self.vector_name: VectorParams(
                            size=self.vector_size,
                            distance=Distance.COSINE
                        )
                    }
                )
                
                print(f"Created collection '{self.collection_name}' with vector size {self.vector_size}")
            
            # Create payload indexes for better search performance
            self._create_payload_indexes()
            
        except Exception as e:
            print(f"Error creating collection: {e}")
            raise
            
    def _create_payload_indexes(self):
        """Create indexes on payload fields for efficient filtering."""
        index_fields = [
            ("meta.category", PayloadSchemaType.KEYWORD),
            ("meta.topic", PayloadSchemaType.TEXT),
            ("meta.type", PayloadSchemaType.KEYWORD),
            ("meta.location.name", PayloadSchemaType.TEXT),
            ("meta.event.name", PayloadSchemaType.TEXT),
            ("meta.event.day", PayloadSchemaType.KEYWORD),
            ("meta.event.time", PayloadSchemaType.KEYWORD),
            ("meta.keywords", PayloadSchemaType.KEYWORD),
            ("text", PayloadSchemaType.TEXT)
        ]
        
        for field_name, field_type in index_fields:
            try:
                # Create index on the field
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=field_type
                )
                print(f"Created {field_type} index on '{field_name}'")
            except Exception as e:
                print(f"Warning: Could not create index on '{field_name}': {e}")
                
    def load_data(self, json_file: str = "garbicz_data.json") -> List[Dict[str, Any]]:
        """Load processed data from JSON file."""
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"Loaded {len(data)} documents from {json_file}")
        return data
        
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts using OpenAI."""
        try:
            response = self.openai_client.embeddings.create(
                input=texts,
                model=self.embedding_model
            )
            embeddings = [item.embedding for item in response.data]
            return embeddings
        except Exception as e:
            print(f"Error generating embeddings: {e}")
            raise
        
    def ingest_data(self, data: List[Dict[str, Any]], batch_size: int = 100):
        """Ingest data into Qdrant collection in batches."""
        total_docs = len(data)
        print(f"Starting ingestion of {total_docs} documents...")
        
        for i in tqdm(range(0, total_docs, batch_size), desc="Ingesting batches"):
            batch = data[i:i + batch_size]
            
            # Prepare texts for embedding
            texts = [doc['text'] for doc in batch]
            
            # Generate embeddings
            embeddings = self.generate_embeddings(texts)
            
            # Prepare points for upload
            points = []
            for j, (doc, embedding) in enumerate(zip(batch, embeddings)):
                # Generate unique ID
                point_id = str(uuid.uuid4())
                
                # Create point with named vector
                point = PointStruct(
                    id=point_id,
                    vector={self.vector_name: embedding},
                    payload={
                        "text": doc['text'],
                        "meta": doc['meta']
                    }
                )
                points.append(point)
                
            # Upload batch to Qdrant
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
            except Exception as e:
                print(f"Error uploading batch {i//batch_size + 1}: {e}")
                
        print(f"Successfully ingested {total_docs} documents into Qdrant")
        
    def get_collection_info(self):
        """Get information about the collection."""
        try:
            info = self.client.get_collection(self.collection_name)
            print(f"\nCollection Info:")
            print(f"  Name: {info.collection_name}")
            print(f"  Vectors count: {info.vectors_count}")
            print(f"  Points count: {info.points_count}")
            print(f"  Status: {info.status}")
            return info
        except Exception as e:
            print(f"Error getting collection info: {e}")
            return None
            
    def test_search(self, query: str, limit: int = 5):
        """Test search functionality with a sample query."""
        print(f"\nTesting search with query: '{query}'")
        
        # Generate query embedding using OpenAI
        query_embeddings = self.generate_embeddings([query])
        query_embedding = query_embeddings[0]
        
        # Perform search with named vector
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=(self.vector_name, query_embedding),
            limit=limit,
            with_payload=True
        )
        
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Score: {result.score:.4f}")
            print(f"   Text: {result.payload['text'][:200]}...")
            if 'meta' in result.payload:
                print(f"   Category: {result.payload['meta'].get('category', 'N/A')}")
                print(f"   Topic: {result.payload['meta'].get('topic', 'N/A')}")
                
        return results


def main():
    # Initialize manager
    manager = QdrantManager()
    
    # Create collection
    print("Creating Qdrant collection...")
    manager.create_collection()
    
    # Load data
    print("\nLoading processed data...")
    data = manager.load_data()
    
    # Ingest data
    print("\nIngesting data into Qdrant...")
    manager.ingest_data(data)
    
    # Get collection info
    manager.get_collection_info()
    
    # Test with a sample query
    print("\n" + "="*50)
    print("Testing search functionality...")
    print("="*50)
    
    test_queries = [
        "What are the food options?",
        "When does the festival start?",
        "Where is the medical team?"
    ]
    
    for query in test_queries:
        manager.test_search(query, limit=3)
        print("\n" + "-"*50)


if __name__ == "__main__":
    main()