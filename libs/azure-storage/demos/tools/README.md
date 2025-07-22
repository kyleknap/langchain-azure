# Azure Storage Container Agent Demo

An agent with Azure Storage-specific tools enabled for managing blobs in your container.

It currently supports:
* Reading blob content
* Writing content to a blob
* Listing blobs in a container
* Deleting a blob
* Uploading a local file
* Download a blob to a local file

For any operation that modifies state of your container or local filesystem, the agent will ask for confirmation
before proceeding.

## Quick Start

1. **Install dependencies:**
   ```bash
   python -m venv .venv
   ./.venv/Scripts/activate  # Windows only - Use `source .venv/bin/activate` on macOS/Linux
   python -m pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   ```bash
   dotenv set AZURE_STORAGE_CONTAINER_URL "https://langchainazstoragedemo.blob.core.windows.net/tools-sandbox"
   dotenv set AZURE_CHAT_ENDPOINT "https://saurse-ignite24-aiservice1.openai.azure.com/openai/deployments/gpt-4.1-mini"
   dotenv set AZURE_AI_CREDENTIAL "your-actual-api-key-here"
   ```

4. **Run the agent:**
    ```bash
    python app.py
    ```

   **Sample interaction:**
    ```text
    Operating on Azure Storage container: https://langchainazstoragedemo.blob.core.windows.net/tools-sandbox
    [Enter request]> Write the content "proof that I work" to the blob "check.txt"

    >>> Writing to blob: 'check.txt' with content: 'proof that I work'
    Approve this action? (Y/n): Y

    >>> The content "proof that I work" has been written to the blob "check.txt".
    [Enter request]> read the content back to me

    >>> The content of the blob "check.txt" is: "proof that I work".
    [Enter request]> download it as a file

    >>> Downloading blob 'check.txt' to file 'C:\Users\kyleknapp\GitHub\langchain-azure\libs\azure-storage\demos\tools\check.txt'
    Approve this action? (Y/n): Y

    >>> The blob "check.txt" has been downloaded as a file named "check.txt".
    [Enter request]> ls

    >>> The blobs in the storage container are:
    - check.txt
    - hello-1.txt
    - hello-10.txt
    - hello-2.txt
    - hello-3.txt
    - hello-4.txt
    ...
    [Enter request]> rm check.txt

    >>> Deleting blob: 'check.txt'
    Approve this action? (Y/n): Y

    >>> The blob "check.txt" has been deleted.
    ```
