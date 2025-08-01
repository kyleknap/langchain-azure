import base64
import datetime
import json
from typing import Iterable, Union

from azure.storage.blob import ContainerClient, BlobClient
from langgraph.store.base import (
    BaseStore,
    Op,
    Result,
    GetOp,
    PutOp,
    SearchOp,
    ListNamespacesOp,
    Item,
)

from langchain_azure_storage.index import AzureAISearchClient


class AzureBlobStore(BaseStore):
    def __init__(self, container_url: str, credential=None, search_index=None):
        self._container_url = container_url
        self._credential = credential
        self._container_client = ContainerClient.from_container_url(
            container_url=self._container_url, credential=self._credential
        )
        self._search_index = search_index
        self._search_client = AzureAISearchClient(**search_index)
        self._search_client.initialize_index_from_container(container_url)

    def batch(self, ops: Iterable[Op]) -> list[Result]:
        results = []
        for op in ops:
            if isinstance(op, GetOp):
                results.append(self._do_get_op(op))
            elif isinstance(op, PutOp):
                results.append(self._do_put_op(op))
            elif isinstance(op, SearchOp):
                results.append(self._do_search_op(op))
            elif isinstance(op, ListNamespacesOp):
                raise NotImplementedError("ListNamespacesOp")
            else:
                raise ValueError(f"Unsupported operation: {op}")
        return results

    async def abatch(self, ops: Iterable[Op]) -> list[Result]:
        raise NotImplementedError("abatch")

    def _do_get_op(self, op: GetOp) -> Item:
        blob_client = self._get_blob_client(op)
        downloader = blob_client.download_blob()
        value = json.loads(downloader.readall().decode("utf-8"))
        return Item(
            namespace=op.namespace,
            key=op.key,
            value=value,
            created_at=downloader.properties.creation_time,
            updated_at=downloader.properties.last_modified,
        )

    def _do_put_op(self, op: PutOp) -> None:
        blob_client = self._get_blob_client(op)
        if op.value is None:
            blob_client.delete_blob()
        else:
            blob_client.upload_blob(
                data=json.dumps(op.value).encode("utf-8"), overwrite=True
            )
        self._search_client.run_indexer()
        return None

    def _do_search_op(self, op: SearchOp) -> list[Item]:
        if op.query:
            return self._do_search_with_query(op)
        return self._do_search_no_query(op)

    def _do_search_with_query(self, op: SearchOp) -> list[Item]:
        results = []
        for result in self._search_client.search(query=op.query, limit=op.limit):
            blob_name = self._get_blob_name_from_full_path(
                self._b64decode(result["metadata_storage_path"])
            )
            print(blob_name)
            namespace, key = self._get_namespace_key(blob_name)
            results.append(
                Item(
                    namespace=namespace,
                    key=key,
                    value={"content": result["content"]},
                    created_at=datetime.datetime.now(),
                    updated_at=datetime.datetime.now(),
                )
            )
        return results

    def _do_search_no_query(self, op: SearchOp) -> list[Item]:
        blob_prefix = self._to_prefix(op.namespace_prefix)
        blobs = self._container_client.list_blob_names(name_starts_with=blob_prefix)
        items = []
        for blob_name in blobs:
            blob_client = self._container_client.get_blob_client(blob=blob_name)
            downloader = blob_client.download_blob()
            value = json.loads(downloader.readall().decode("utf-8"))
            namespace, key = self._get_namespace_key(blob_name)
            items.append(
                Item(
                    namespace=namespace,
                    key=key,
                    value=value,
                    created_at=downloader.properties.creation_time,
                    updated_at=downloader.properties.last_modified,
                )
            )
        return items

    def _get_blob_client(self, op: Union[GetOp, PutOp]) -> BlobClient:
        blob_name = self._to_blob_name(op.namespace, op.key)
        return self._container_client.get_blob_client(blob=blob_name)

    def _to_prefix(self, namespace: tuple[str, ...]) -> str:
        return "/".join(namespace) + "/" if namespace else ""

    def _to_blob_name(self, namespace: tuple[str, ...], key: str) -> str:
        prefix = self._to_prefix(namespace)
        return f"{prefix}{key}"

    def _get_namespace_key(self, blob_name: str) -> tuple[tuple[str, ...], str]:
        parts = blob_name.split("/")
        if len(parts) < 2:
            return (), parts[0]
        return (tuple(parts[:-1]), parts[-1])

    def _get_blob_name_from_full_path(self, full_path: str) -> str:
        container_url = self._container_url.rstrip("/")
        blob_name = full_path[len(container_url) + 1 :]
        return blob_name

    def _b64decode(self, value: str) -> str:
        missing_padding = len(value) % 4
        if missing_padding:
            value += "=" * (4 - missing_padding)
        return base64.b64decode(value).decode("utf-8")
