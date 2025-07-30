#!/usr/bin/env python3
"""
Test queries for Garbicz Festival Qdrant search system.
Tests various query types to evaluate search effectiveness.
"""

import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from openai import OpenAI
from typing import List, Dict, Any
import json


class QueryTester:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        self.api_key = os.getenv('QDRANT_API_KEY', 'NObiSurpKZgDVbsXnzEp3BuuTyo1BvLp')
        self.api_url = os.getenv('QDRANT_API_URL', 'https://garbrain.aicd.me/')
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        self.collection_name = os.getenv('COLLECTION_NAME', 'garbrain')
        self.vector_name = "garbrain-dence"
        
        # Initialize clients
        self.client = QdrantClient(
            url=self.api_url,
            api_key=self.api_key,
            prefer_grpc=False,
            timeout=30.0
        )
        
        if self.openai_api_key and self.openai_api_key != "your_openai_api_key_here":
            self.openai_client = OpenAI(api_key=self.openai_api_key)
            self.embedding_model = "text-embedding-3-small"
        else:
            print("WARNING: OpenAI API key not found. Using mock embeddings for testing.")
            self.openai_client = None
            
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if self.openai_client:
            response = self.openai_client.embeddings.create(
                input=[text],
                model=self.embedding_model
            )
            return response.data[0].embedding
        else:
            # Mock embedding for testing without OpenAI API
            import random
            return [random.random() for _ in range(1536)]
            
    def search(self, query: str, limit: int = 5, filter_dict: Dict[str, Any] = None) -> List[Any]:
        """Perform a search with optional filtering."""
        query_embedding = self.generate_embedding(query)
        
        search_params = {
            "collection_name": self.collection_name,
            "query_vector": (self.vector_name, query_embedding),
            "limit": limit,
            "with_payload": True
        }
        
        if filter_dict:
            search_params["query_filter"] = filter_dict
            
        return self.client.search(**search_params)
        
    def test_query(self, query: str, expected_topics: List[str] = None, 
                   filter_dict: Dict[str, Any] = None, limit: int = 5):
        """Test a single query and display results."""
        print(f"\n{'='*80}")
        print(f"QUERY: {query}")
        if filter_dict:
            print(f"FILTER: {json.dumps(filter_dict, indent=2)}")
        print(f"{'='*80}\n")
        
        results = self.search(query, limit=limit, filter_dict=filter_dict)
        
        if not results:
            print("No results found.")
            return
            
        for i, result in enumerate(results, 1):
            print(f"Result {i} (Score: {result.score:.4f}):")
            
            # Display payload information
            payload = result.payload
            if 'text' in payload:
                text_preview = payload['text'][:200] + "..." if len(payload['text']) > 200 else payload['text']
                print(f"  Text: {text_preview}")
                
            if 'meta' in payload:
                meta = payload['meta']
                print(f"  Category: {meta.get('category', 'N/A')}")
                print(f"  Topic: {meta.get('topic', 'N/A')}")
                print(f"  Type: {meta.get('type', 'N/A')}")
                
                if 'location' in meta and meta['location']:
                    print(f"  Location: {meta['location'].get('name', 'N/A')}")
                    
                if 'event' in meta and meta['event']:
                    event = meta['event']
                    print(f"  Event: {event.get('name', 'N/A')}")
                    if 'day' in event:
                        print(f"  Day: {event['day']}")
                    if 'time' in event:
                        print(f"  Time: {event['time']}")
                        
            print()
            
        # Check if expected topics were found
        if expected_topics:
            found_topics = []
            for result in results:
                if 'meta' in result.payload and 'topic' in result.payload['meta']:
                    found_topics.append(result.payload['meta']['topic'])
                    
            print(f"\nExpected topics: {expected_topics}")
            print(f"Found topics: {found_topics[:len(expected_topics)]}")
            matches = sum(1 for topic in expected_topics if any(topic.lower() in found.lower() for found in found_topics))
            print(f"Match rate: {matches}/{len(expected_topics)} ({matches/len(expected_topics)*100:.0f}%)")


def main():
    tester = QueryTester()
    
    # Check collection status
    try:
        info = tester.client.get_collection(tester.collection_name)
        print(f"Collection '{tester.collection_name}' status:")
        print(f"  Points count: {info.points_count}")
        print(f"  Vectors count: {info.indexed_vectors_count}")
        print(f"  Status: {info.status}")
    except Exception as e:
        print(f"Error accessing collection: {e}")
        return
        
    # Test queries covering different use cases
    test_cases = [
        # General information queries
        {
            "query": "What are the highlights for Friday?",
            "expected_topics": ["Friday", "Timetable", "Events"]
        },
        
        # Location-based queries
        {
            "query": "Who is playing at the Seebühne at 10pm?",
            "filter": {
                "must": [
                    {"key": "meta.location.name", "match": {"value": "Seebühne"}}
                ]
            }
        },
        
        # Food and dining queries
        {
            "query": "Tell me about the food options",
            "expected_topics": ["Food", "Gastronomy", "Dining"]
        },
        
        # Safety and services
        {
            "query": "Where can I find the Medical Team?",
            "expected_topics": ["Medical Team", "Safety", "Services"]
        },
        
        # Workshop queries
        {
            "query": "What workshops are available?",
            "filter": {
                "must": [
                    {"key": "meta.category", "match": {"value": "Workshops"}}
                ]
            }
        },
        
        # Time-specific queries
        {
            "query": "What's happening on Thursday afternoon?",
            "filter": {
                "must": [
                    {"key": "meta.event.day", "match": {"value": "Thursday"}}
                ]
            }
        },
        
        # Artist queries
        {
            "query": "When does Captain of None perform?",
            "expected_topics": ["Captain of None"]
        },
        
        # Camping queries
        {
            "query": "Tell me about silent camping options",
            "expected_topics": ["Silent Camping", "Camping", "Accommodation"]
        },
        
        # Sustainability queries
        {
            "query": "What are the sustainability initiatives at the festival?",
            "expected_topics": ["Sustainability", "Eco", "Environment"]
        },
        
        # FAQ queries
        {
            "query": "How do I get tickets?",
            "filter": {
                "must": [
                    {"key": "meta.category", "match": {"value": "FAQ"}}
                ]
            }
        }
    ]
    
    # Run test queries
    for test_case in test_cases:
        query = test_case["query"]
        expected_topics = test_case.get("expected_topics", None)
        filter_dict = test_case.get("filter", None)
        
        tester.test_query(query, expected_topics, filter_dict)
        
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Total test queries: {len(test_cases)}")
    print("\nRecommendations:")
    print("1. Ensure all markdown files are properly processed")
    print("2. Verify embeddings are being generated correctly")
    print("3. Check that metadata fields are properly indexed")
    print("4. Consider adding more specific keywords to improve search relevance")


if __name__ == "__main__":
    main()