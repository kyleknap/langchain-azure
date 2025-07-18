import os
import io
import itertools
from typing import Iterator

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from langchain_core.documents.base import Blob, Document
from langchain_core.document_loaders import BaseBlobParser
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_azure_ai.embeddings import AzureAIEmbeddingsModel
from langchain_azure_storage.document_loaders import AzureBlobStorageContainerLoader
from langchain_text_splitters import MarkdownTextSplitter
from markitdown import MarkItDown


class MarkItDownBlobParser(BaseBlobParser):
    def lazy_parse(self, blob: Blob) -> Iterator[Document]:
        md = MarkItDown()
        doc = Document(
            page_content=md.convert(io.BytesIO(blob.as_bytes())).markdown,
            metadata={
                "source": blob.metadata["source"],
            },
        )
        yield from MarkdownTextSplitter().split_documents([doc])


def load_and_embed_documents_from_container():
    embed_model = AzureAIEmbeddingsModel(
        endpoint=os.environ["AZURE_EMBEDDING_ENDPOINT"],
        credential=os.environ["AZURE_AI_CREDENTIAL"],
        model="text-embedding-3-large",
    )
    vector_store = InMemoryVectorStore(
        embedding=embed_model,
    )

    loader = AzureBlobStorageContainerLoader(
        container_url=os.environ.get("AZURE_STORAGE_CONTAINER_URL"),
        prefix="azure-guide/pdf/",
        credential=DefaultAzureCredential(),
        parser=MarkItDownBlobParser(),
    )

    total = 0
    for batch in itertools.batched(loader.lazy_load(), 50):
        vector_store.add_documents(batch)
        total += len(batch)
        print(f"Added {len(batch)} documents, total added: {total}")

    print(f"Saving vector store to .vector.json")
    vector_store.dump(".vector.json")


def main():
    load_dotenv()
    load_and_embed_documents_from_container()


if __name__ == "__main__":
    main()
