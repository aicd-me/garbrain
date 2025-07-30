# Briefing for a Technical Assistant (Roo)

## Objective:

To create a robust and efficient search system for the Garbicz Festival knowledge base using Qdrant's hybrid search capabilities. This system will be able to understand and answer a wide range of user queries, from specific keyword searches to more abstract, semantic questions.

## Background and Context:

The Garbicz Festival knowledge base is currently stored in a collection of markdown files. An initial analysis of these files has revealed several inconsistencies in naming conventions and a lack of a standardized data structure. This makes it difficult to search the knowledge base effectively.

To address this, we have decided to use Qdrant, a vector database that is well-suited for a variety of search tasks. We will use Qdrant's hybrid search capabilities, which combine the strengths of both keyword and vector search, to create a powerful and intelligent search system.

## Key Resources:

*   **Qdrant Credentials:**
    *   `QDRANT_API_KEY`: NObiSurpKZgDVbsXnzEp3BuuTyo1BvLp
    *   `QDRANT_API_URL`: https://garbrain.aicd.me/
*   **Markdown Files to Process:**
    *   `garbicz_faq_chunked(en).md`
    *   `garbicz_gastro_highlights.md`
    *   `garbicz_timetable_chunked(en).md`
    *   `garbicz_workshops.md`
    *   `garbicz-general.md`
    *   `garbicz-overview.md`
    *   `locations.md`
*   **Proposed Qdrant JSON Schema:**

    ```json
    {
      "text": "The main content of the document.",
      "meta": {
        "category": "The main category of the document.",
        "topic": "The specific topic of the document.",
        "type": "The type of content.",
        "location": {
          "name": "The name of the location.",
          "alternative_names": ["Alternative Name 1", "Alternative Name 2"],
          "coordinates": {
            "lat": 52.306927,
            "lon": 14.999499
          }
        },
        "event": {
          "name": "The name of the event.",
          "day": "The day of the event.",
          "time": "The time of the event.",
          "facilitator": "The name of the workshop facilitator."
        },
        "keywords": ["keyword1", "keyword2", "keyword3"]
      }
    }
    ```

## Detailed Plan of Action:

**Part 1: Data Preparation and Standardization (`data_processor.py`)**

1.  **Create the script:** Create a new Python script named `data_processor.py`.
2.  **Read the markdown files:** Implement a function that reads all the markdown files listed in the "Key Resources" section.
3.  **Parse the data:** Implement parsing functions for each type of markdown file to extract the data and transform it into the proposed JSON schema.
4.  **Standardize the data:** As you parse the data, make sure to standardize it as follows:
    *   **Categories:** Standardize all category names to English (e.g., "Gastronomy", "Sustainability", "Travel", "Safety").
    *   **Locations:** Standardize all location names and add their coordinates by cross-referencing with the `locations.md` file. For any new locations not in `locations.md`, add them to the file with their coordinates.
    *   **Type:** Add a `type` field to each entry to classify the content (e.g., "general info", "dining", "DJ", "workshop").
5.  **Generate JSON output:** The script should output a single JSON file named `garbicz_data.json` containing a list of all the processed documents.

**Part 2: Qdrant Collection Setup and Data Ingestion (`qdrant_manager.py`)**

1.  **Create the script:** Create a new Python script named `qdrant_manager.py`.
2.  **Connect to Qdrant:** Use the `qdrant-client` library and the credentials from the `.env` file to connect to your Qdrant instance.
3.  **Create the collection:** Create a new collection named `garbicz_festival` with the following parameters:
    *   **Vectors:** Use a vector size of `768` (for a sentence-transformer model like `all-MiniLM-L6-v2`) and a distance metric of `Cosine`.
    *   **Metadata Indexing:** Enable keyword and vector indexing on all the fields in the `meta` part of the JSON schema.
4.  **Ingest the data:** Read the `garbicz_data.json` file and upload the documents to the `garbicz_festival` collection in batches of 100.

**Part 3: Testing and Evaluation (`test_queries.py`)**

1.  **Create the script:** Create a new Python script named `test_queries.py`.
2.  **Implement test queries:** Implement a set of test queries that cover the typical use cases, such as:
    *   "What are the highlights for Friday?"
    *   "Who is playing at the Seebühne at 10pm?"
    *   "Tell me about the food options."
    *   "Where can I find the Medical Team?"
3.  **Evaluate the results:** For each query, print the top 5 results and evaluate their relevance and accuracy. This will help us to fine-tune the search parameters if necessary.

## Success Criteria:

The project will be considered a success when:

*   All the data from the markdown files has been successfully processed, standardized, and ingested into the Qdrant collection.
*   The search system is able to provide accurate and relevant results for a wide range of queries, including both keyword and semantic searches.
*   The test queries in the `test_queries.py` script return the expected results.