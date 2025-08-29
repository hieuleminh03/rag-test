import asyncio
from rag_service import RAGService
import logging
import json
import dotenv

dotenv.load_dotenv()

# Configure logging to show informational messages
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    """
    Main asynchronous function to initialize and run the RAG service test client.
    """
    print("Initializing RAG Service...")
    rag_service = RAGService()

    # Initialize the service. This sets up the Weaviate client, LLM, and vector store.
    if not rag_service.initialize():
        print("Failed to initialize RAG Service. Please check logs for errors. Exiting.")
        return

    print("RAG Service Initialized Successfully.")

    # Check the status of the RAG service, specifically if documents are embedded.
    status = rag_service.get_status()
    if not status.get('embedded'):
        print("Warning: No documents appear to be embedded. The RAG model may not have context.")
        print("Consider running the embedding process if you haven't already.")
        # You can optionally trigger embedding here if needed:
        # print("Starting embedding process...")
        # result = rag_service.embed_documents()
        # if not result.get('success'):
        #     print(f"Embedding failed: {result.get('error')}")
        #     rag_service.close()
        #     return
        # print("Embedding complete.")

    print("\nReady to generate test cases.")
    print("Enter your API documentation or query below.")
    print("Submit your query by pressing Enter on an empty line. Type 'exit' and press Enter to quit.")

    while True:
        print("\n---------------------------------")
        print("Enter your query:")
        
        # Read multi-line input from the user
        lines = []
        try:
            while True:
                line = input()
                if line == "":
                    break
                lines.append(line)
        except EOFError:
            # Handle Ctrl+D to exit gracefully
            break
            
        query = "\n".join(lines)

        if query.lower().strip() == 'exit':
            break
        
        if not query.strip():
            print("Query cannot be empty. Please try again.")
            continue

        print("\nGenerating test cases, please wait...")
        
        # Call the generation service with the user's query
        result = rag_service.generate_test_cases(api_documentation=query)

        if result.get("success"):
            print("\n--- Generated Test Cases ---")
            generated_cases = result.get("generated_cases", [])
            if generated_cases:
                # Pretty-print the JSON output
                print(json.dumps(generated_cases, indent=2))
            else:
                print("No test cases were successfully parsed from the response.")
                print("\n--- Raw LLM Response ---")
                print(result.get("raw_response", "No raw response available."))
        else:
            print(f"\n--- An Error Occurred ---")
            print(result.get("error", "An unknown error occurred during test case generation."))

    print("\nClosing RAG Service and cleaning up.")
    rag_service.close()
    print("Test script finished.")

if __name__ == "__main__":
    try:
        # Run the main async function
        asyncio.run(main())
    except KeyboardInterrupt:
        # Handle Ctrl+C to exit gracefully
        print("\nInterrupted by user. Exiting.")
