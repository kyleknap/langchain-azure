from typing import Optional, Iterator

from azure.storage.blob import BlobClient, ContainerClient
from langchain_core.documents.base import Blob, Document
from langchain_core.document_loaders import BaseLoader, BaseBlobParser


def _get_client_kwargs(credential=None):
    return {"credential": credential, "connection_data_block_size": 256 * 1024}


def _lazy_load_documents_from_blob(
    blob_client: BlobClient, parser: Optional[BaseBlobParser] = None
) -> Iterator[Document]:
    blob_data = blob_client.download_blob(max_concurrency=10)
    blob = Blob.from_data(
        data=blob_data.readall(),
        mime_type=blob_data.properties.content_settings.content_type,
        metadata={
            "source": blob_client.url,
        },
    )
    if parser:
        yield from parser.lazy_parse(blob)
    else:
        yield Document(page_content=blob.as_string(), metadata=blob.metadata)


class AzureBlobStorageFileLoader(BaseLoader):
    def __init__(
        self, blob_url: str, credential=None, parser: Optional[BaseBlobParser] = None
    ):
        self._blob_url = blob_url
        self._credential = credential
        self._parser = parser

    def lazy_load(self) -> Iterator[Document]:
        blob_client = BlobClient.from_blob_url(
            self._blob_url, **_get_client_kwargs(self._credential)
        )
        yield from _lazy_load_documents_from_blob(blob_client, self._parser)


class AzureBlobStorageContainerLoader(BaseLoader):
    def __init__(
        self,
        container_url: str,
        prefix: str = None,
        credential=None,
        parser: Optional[BaseBlobParser] = None,
    ):
        self._container_url = container_url
        self._prefix = prefix
        self._credential = credential
        self._parser = parser

    def lazy_load(self) -> list[Document]:
        container_client = ContainerClient.from_container_url(
            self._container_url, **_get_client_kwargs(self._credential)
        )
        blobs = container_client.list_blob_names(name_starts_with=self._prefix)
        documents = []
        for blob_name in blobs:
            blob_client = container_client.get_blob_client(blob_name)
            yield from _lazy_load_documents_from_blob(blob_client, self._parser)
