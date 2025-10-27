# Introducing `langchain-azure-storage`: Azure Storage integrations for LangChain

We're excited to introduce [`langchain-azure-storage`][langchain-azure-storage-pypi], the first official
[Azure Storage][azure-storage-intro] integration package built by Microsoft for [LangChain][langchain-overview] 1.0.
As part of its launch, we've built a new [Azure Blob Storage document loader][langchain-azure-storage-loader-usage]
(currently in public preview) that improves upon prior [LangChain community][langchain-community-github] implementations.
This new loader unifies both blob and container level access, simplifying loader integration. More importantly, it
offers enhanced security through default OAuth 2.0 authentication, supports reliably loading millions to billions of
documents through efficient memory utilization, and allows pluggable parsing, so you can leverage other document
loaders to parse specific file formats.

## What are LangChain document loaders?

A typical [Retrieval‑Augmented Generation (RAG)][langchain-rag] pipeline follows these main steps:

1. Collect source content (PDFs, DOCX, Markdown, CSVs) — often stored in Azure Blob Storage.
2. Parse into text and associated metadata (i.e., represented as LangChain [`Document`][langchain-document-ref] objects).
3. Chunk + embed those documents and store in a vector store (e.g., Azure AI Search, Postgres pgvector, etc.).
4. At query time, retrieve the most relevant chunks and feed them to an LLM as grounded context.

[LangChain document loaders][langchain-document-loaders] make steps 1–2 turnkey and consistent so the rest of the stack
(splitters, vector stores, retrievers) “just works”. See this [LangChain RAG tutorial][langchain-rag] for a full example of
these steps when building a RAG application in LangChain.


## How can the Azure Blob Storage document loader help?

The `langchain-azure-storage` package offers the [`AzureBlobStorageLoader`][langchain-azure-storage-loader-ref], a document loader
that simplifies retrieving documents stored in Azure Blob Storage for use in a LangChain RAG application. Key benefits of
the `AzureBlobStorageLoader` include:

* Flexible loading of Azure Storage blobs to LangChain `Document` objects. You can load blobs as documents from an entire container,
  a specific prefix within a container, or by blob names. Each document loaded corresponds 1:1 to a blob in the container.
* Lazy loading support for improved memory efficiency when dealing with large document sets. Documents can now be loaded
  one-at-a-time as you iterate over them instead of all at once.
* Automatically uses [`DefaultAzureCredential`][azure-default-credential] to enable seamless OAuth 2.0 authentication across
  various environments, from local development to Azure-hosted services. You can also explicitly pass your own
  credential (e.g., [`ManagedIdentityCredential`][azure-managed-identity], [SAS][azure-sas-overview] token).
* Pluggable parsing. Easily customize how documents are parsed by providing your own LangChain document loader to parse
  downloaded blob content.


## Using the Azure Blob Storage document loader

### Installation

To install the `langchain-azure-storage` package, run:

```bash
pip install langchain-azure-storage
```

### Loading documents from a container
To load all blobs from an Azure Blob Storage container as LangChain [`Document`][langchain-document-ref] objects,
instantiate the [`AzureBlobStorageLoader`][langchain-azure-storage-loader-ref] with the Azure Storage account URL
and container name:


```python
from langchain_azure_storage.document_loaders import AzureBlobStorageLoader

loader = AzureBlobStorageLoader(
    "https://<your-storage-account>.blob.core.windows.net/",
    "<your-container-name>"
)

# lazy_load() yields one Document per blob for all blobs in the container
for doc in loader.lazy_load():
    print(doc.metadata["source"])  # The "source" metadata contains the full URL of the blob
    print(doc.page_content)  # The page_content contains the blob's content decoded as UTF-8 text
```

### Loading documents by blob names
To only load specific blobs as LangChain `Document` objects, you can additionally provide a list of blob names:

```python
from langchain_azure_storage.document_loaders import AzureBlobStorageLoader

loader = AzureBlobStorageLoader(
    "https://<your-storage-account>.blob.core.windows.net/",
    "<your-container-name>",
    ["<blob-name-1>", "<blob-name-2>"]
)

# lazy_load() yields one Document per blob for only the specified blobs
for doc in loader.lazy_load():
    print(doc.metadata["source"])  # The "source" metadata contains the full URL of the blob
    print(doc.page_content)  # The page_content contains the blob's content decoded as UTF-8 text
```

### Pluggable parsing

By default, loaded `Document` objects contain the blob's UTF-8 decoded content. To parse non-UTF-8 content (e.g., PDFs, DOCX, etc.)
or chunk blob content into smaller documents, provide a LangChain document loader via the `loader_factory` parameter.

When `loader_factory` is provided, the `AzureBlobStorageLoader` processes each blob with the following steps:

1. Downloads the blob to a new temporary file
2. Passes the temporary file path to the `loader_factory` callable to instantiate a document loader
3. Uses that loader to parse the file and yield [`Document`][langchain-document-ref] objects
4. Cleans up the temporary file

For example, below shows parsing PDF documents with the [`PyPDFLoader`][langchain-pypdf-loader] from the [`langchain-community`][langchain-community-github] package:

```python
from langchain_azure_storage.document_loaders import AzureBlobStorageLoader
from langchain_community.document_loaders import PyPDFLoader  # Requires langchain-community and pypdf packages

loader = AzureBlobStorageLoader(
    "https://<your-storage-account>.blob.core.windows.net/",
    "<your-container-name>",
    prefix="pdfs/",  # Only load blobs that start with "pdfs/"
    loader_factory=PyPDFLoader  # PyPDFLoader will parse each blob as a PDF
)

# Each blob is downloaded to a temporary file and parsed by PyPDFLoader instance
for doc in loader.lazy_load():
    print(doc.page_content)  # Content parsed by PyPDFLoader (yields one Document per page in the PDF)
```

This file path-based interface allows you to use any [LangChain document loader][langchain-document-loaders] that accepts
a local file path as input, giving you access to a wide range of parsers for different file formats.


## Migrating from community document loaders to `langchain-azure-storage`

If you're currently using [`AzureBlobStorageContainerLoader`][langchain-community-container-loader-ref] or
[`AzureBlobStorageFileLoader`][langchain-community-file-loader-ref] from the
[`langchain-community`][langchain-community-github] package, the new [`AzureBlobStorageLoader`][langchain-azure-storage-loader-ref]
provides an improved alternative. This section provides step-by-step guidance for migrating to the new loader.

### Steps to migrate

To migrate to the new Azure Storage document loader, make the following changes:

1. Depend on the `langchain-azure-storage` package
2. Update import statements from `langchain_community.document_loaders` to
   `langchain_azure_storage.document_loaders`.
3. Change class names from `AzureBlobStorageFileLoader` and `AzureBlobStorageContainerLoader`
   to `AzureBlobStorageLoader`.
4. Update document loader constructor calls to:
   1. Use an account URL instead of a connection string.
   2. Specify `UnstructuredLoader` as the `loader_factory` to continue to use
      [Unstructured][unstructured] for parsing documents.
5. Enable Microsoft Entra ID authentication in environment (e.g., run `az login` or configure managed identity)
   instead of using connection string authentication.

### Migration samples

Below shows code snippets of what usage patterns look like before and after migrating from
`langchain-community` to `langchain-azure-storage`:

**Before migration:**

```python
from langchain_community.document_loaders import AzureBlobStorageContainerLoader, AzureBlobStorageFileLoader

container_loader = AzureBlobStorageContainerLoader(
    "DefaultEndpointsProtocol=https;AccountName=<account>;AccountKey=<account-key>;EndpointSuffix=core.windows.net",
    "<container>",
)

file_loader = AzureBlobStorageFileLoader(
    "DefaultEndpointsProtocol=https;AccountName=<account>;AccountKey=<account-key>;EndpointSuffix=core.windows.net",
    "<container>",
    "<blob>"
)
```

**After migration:**

```python
from langchain_azure_storage.document_loaders import AzureBlobStorageLoader
from langchain_unstructured import UnstructuredLoader  # Requires langchain-unstructured and unstructured packages

container_loader = AzureBlobStorageLoader(
    "https://<account>.blob.core.windows.net",
    "<container>",
    loader_factory=UnstructuredLoader  # Only needed if continuing to use Unstructured for parsing
)

file_loader = AzureBlobStorageLoader(
    "https://<account>.blob.core.windows.net",
    "<container>",
    "<blob>",
    loader_factory=UnstructuredLoader  # Only needed if continuing to use Unstructured for parsing
)
```


## What's next?

We're excited for you to try the new Azure Blob Storage document loader and would love to hear your feedback! Here are some ways you can help shape the future of `langchain-azure-storage`:

* **Show support for interface stabilization** - The document loader is currently in public preview and the interface may change
in future versions based on feedback. If you'd like to see the current interface marked as stable,
[upvote the proposal PR][langchain-azure-storage-proposal] to show your support.
* **Report issues or suggest improvements** - Found a bug or have an idea to make the document loaders better?
[File an issue][langchain-azure-new-issue] on our GitHub repository.
* **Propose new LangChain integrations** - Interested in other ways to use Azure Storage with LangChain
(e.g., checkpointing for agents, persistent memory stores, retriever implementations)?
[Create a feature request][langchain-azure-new-issue] or [write to us][azure-storage-email] to let us know.

Your input is invaluable in making `langchain-azure-storage` better for the entire community!


## Resources
* [`langchain-azure` GitHub repository][langchain-azure-github]
* [`langchain-azure-storage` PyPI package][langchain-azure-storage-pypi]
* [`AzureBlobStorageLoader` usage guide][langchain-azure-storage-loader-usage]
* [`AzureBlobStorageLoader` documentation reference][langchain-azure-storage-loader-ref]


<!-- Reference Links -->
[azure-storage-intro]: https://learn.microsoft.com/en-us/azure/storage/common/storage-introduction
[azure-blob-storage-intro]: https://learn.microsoft.com/en-us/azure/storage/blobs/storage-blobs-overview
[azure-default-credential]: https://learn.microsoft.com/en-us/azure/developer/python/sdk/authentication/credential-chains?tabs=dac#defaultazurecredential-overview
[azure-managed-identity]: https://learn.microsoft.com/en-us/python/api/azure-identity/azure.identity.managedidentitycredential?view=azure-python
[azure-sas-overview]: https://learn.microsoft.com/en-us/azure/storage/common/storage-sas-overview
[azure-storage-email]: mailto:AzureStorageFeedback@microsoft.com

[langchain-overview]: https://docs.langchain.com/oss/python/langchain/overview
[langchain-community-github]: https://github.com/langchain-ai/langchain-community
[langchain-rag]: https://docs.langchain.com/oss/python/langchain/rag#build-a-rag-agent-with-langchain
[langchain-document-ref]: https://reference.langchain.com/python/langchain_core/documents/#langchain_core.documents.base.Document
[langchain-pypdf-loader]: https://docs.langchain.com/oss/python/integrations/document_loaders/pypdfloader
[langchain-document-loaders]: https://docs.langchain.com/oss/python/integrations/document_loaders
[langchain-community-container-loader-ref]: https://python.langchain.com/api_reference/community/document_loaders/langchain_community.document_loaders.azure_blob_storage_container.AzureBlobStorageContainerLoader.html
[langchain-community-file-loader-ref]: https://python.langchain.com/api_reference/community/document_loaders/langchain_community.document_loaders.azure_blob_storage_file.AzureBlobStorageFileLoader.html

[langchain-azure-github]: https://github.com/langchain-ai/langchain-azure
[langchain-azure-storage-pypi]: https://pypi.org/project/langchain-azure-storage/
[langchain-azure-storage-loader-usage]: https://docs.langchain.com/oss/python/integrations/document_loaders/azure_blob_storage
[langchain-azure-storage-loader-ref]: https://reference.langchain.com/python/integrations/langchain_azure/storage/
[langchain-azure-new-issue]: https://github.com/langchain-ai/langchain-azure/issues/new
[langchain-azure-storage-proposal]: https://github.com/langchain-ai/langchain-azure/pull/148

[unstructured]: https://pypi.org/project/unstructured/
