# Azure RAG Agent Demo

A basic Retrieval-Augmented Generation (RAG) agent that answers queries by retrieving
documents originating from Azure Blob Storage stored in a vector store.

## Quick Start

1. **Install dependencies:**
   ```bash
   python -m venv .venv
   ./.venv/Scripts/activate  # Windows only - Use `source .venv/bin/activate` on macOS/Linux
   python -m pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   ```bash
   dotenv set AZURE_STORAGE_CONTAINER_URL "https://langchainazstoragedemo.blob.core.windows.net/documents"
   dotenv set AZURE_EMBEDDING_ENDPOINT "https://saurse-ignite24-aiservice1.openai.azure.com/openai/deployments/text-embedding-3-large"
   dotenv set AZURE_CHAT_ENDPOINT "https://saurse-ignite24-aiservice1.openai.azure.com/openai/deployments/gpt-4.1-mini"
   dotenv set AZURE_AI_CREDENTIAL "your-actual-api-key-here"
   ```

3. **Create vector store** (first time only):
   This step will load documents from Azure Blob Storage and create an embedding vector store
   that will be saved on disk at `.vector.json` for access as part of RAG agent.
   ```bash
   python embed.py
   ```

   **Sample output:**
   ```
   Added 50 documents, total added: 50
   Added 50 documents, total added: 100
   Added 32 documents, total added: 132
   Saving vector store to .vector.json
   ```

4. **Run the agent:**
    ```bash
    python app.py
    ```

   **Sample interaction:**
    ```text
    [Enter your query]> What is Azure Blob Storage?

    >>> Azure Blob Storage is a service for storing large amounts of unstructured data...
    Source: azure-guide/storage-overview.pdf
    ```
