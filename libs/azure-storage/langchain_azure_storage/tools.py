import os
from typing import Optional

from azure.storage.blob import ContainerClient
from langchain_core.tools import BaseTool, BaseToolkit
from langgraph.types import interrupt
from pydantic import BaseModel, Field


class AzureStorageBlobToolkit(BaseToolkit):
    """Toolkit for interacting with Azure Storage blobs."""

    def __init__(
        self,
        container_url: str,
        credential: Optional[str] = None,
        root_dir: str = os.getcwd(),
    ):
        super().__init__()
        self._container_url = container_url
        self._credential = credential
        self._root_dir = root_dir

    def get_tools(self):
        init_kwargs = {
            "container_url": self._container_url,
            "credential": self._credential,
        }
        return [
            ReadAzureStorageBlobTool(**init_kwargs),
            ListAzureStorageBlobsTool(**init_kwargs),
            WriteAzureStorageBlobTool(**init_kwargs),
            DeleteAzureStorageBlobTool(**init_kwargs),
            UploadAzureStorageBlobTool(**init_kwargs, root_dir=self._root_dir),
            DownloadAzureStorageBlobTool(**init_kwargs, root_dir=self._root_dir),
        ]


class ReadAzureStorageBlobInput(BaseModel):
    blob_name: str = Field(..., description="The name of the blob to read.")


class ReadAzureStorageBlobTool(BaseTool):
    """Tool for reading a blob from Azure Storage."""

    name: str = "read_azure_storage_blob"
    args_schema: type[BaseModel] = ReadAzureStorageBlobInput
    description: str = "Reads a blob from Azure Storage. Input should be the blob name. Output is the content of the blob."

    def __init__(self, container_url: str, credential: Optional[str] = None):
        super().__init__()
        self._container_client = ContainerClient.from_container_url(
            container_url=container_url, credential=credential
        )

    def _run(self, blob_name: str) -> str:
        return (
            self._container_client.get_blob_client(blob_name)
            .download_blob()
            .readall()
            .decode("utf-8")
        )


class ListAzureStorageBlobsTool(BaseTool):
    """Tool for listing blobs in an Azure Storage container."""

    name: str = "list_azure_storage_blobs"
    description: str = "Lists all blobs in the Azure Storage container. Output is a list of blob names."

    def __init__(self, container_url: str, credential: Optional[str] = None):
        super().__init__()
        self._container_client = ContainerClient.from_container_url(
            container_url=container_url, credential=credential
        )

    def _run(self) -> list[str]:
        return [blob for blob in self._container_client.list_blob_names()]


class WriteAzureStorageBlobInput(BaseModel):
    blob_name: str = Field(..., description="The name of the blob to write.")
    content: str = Field(..., description="The content to write to the blob.")


class WriteAzureStorageBlobTool(BaseTool):
    """Tool for writing a blob to Azure Storage."""

    name: str = "write_azure_storage_blob"
    args_schema: type[BaseModel] = WriteAzureStorageBlobInput
    description: str = "Writes content to a blob in Azure Storage. Input should be the blob name and content."

    def __init__(self, container_url: str, credential: Optional[str] = None):
        super().__init__()
        self._container_client = ContainerClient.from_container_url(
            container_url=container_url, credential=credential
        )

    def _run(self, blob_name: str, content: str) -> str:
        is_approved = interrupt(
            f"Writing to blob: {repr(blob_name)} with content: {repr(content)}"
        )
        if not is_approved:
            return "Write operation was not approved."
        blob_client = self._container_client.get_blob_client(blob_name)
        blob_client.upload_blob(content.encode("utf-8"), overwrite=True)
        return f"Blob '{blob_name}' written successfully."


class DeleteAzureStorageBlobInput(BaseModel):
    blob_name: str = Field(..., description="The name of the blob to delete.")


class DeleteAzureStorageBlobTool(BaseTool):
    """Tool for deleting a blob from Azure Storage."""

    name: str = "delete_azure_storage_blob"
    args_schema: type[BaseModel] = DeleteAzureStorageBlobInput
    description: str = (
        "Deletes a blob from Azure Storage. Input should be the blob name."
    )

    def __init__(self, container_url: str, credential: Optional[str] = None):
        super().__init__()
        self._container_client = ContainerClient.from_container_url(
            container_url=container_url, credential=credential
        )

    def _run(self, blob_name: str) -> str:
        is_approved = interrupt(f"Deleting blob: {repr(blob_name)}")
        if not is_approved:
            return "Delete operation was not approved."
        self._container_client.get_blob_client(blob_name).delete_blob()
        return f"Blob '{blob_name}' deleted successfully."


class UploadAzureStorageBlobInput(BaseModel):
    file_path: str = Field(..., description="The path to the file to upload.")
    blob_name: str = Field(
        ...,
        description="The name of the blob to upload. If not provided, match the file path value.",
    )


class UploadAzureStorageBlobTool(BaseTool):
    """Tool for uploading a file to Azure Storage as a blob."""

    name: str = "upload_azure_storage_blob"
    args_schema: type[BaseModel] = UploadAzureStorageBlobInput
    description: str = "Uploads a local file to Azure Storage as a blob"

    def __init__(
        self,
        container_url: str,
        credential: Optional[str] = None,
        root_dir: str = os.getcwd(),
    ):
        super().__init__()
        self._container_client = ContainerClient.from_container_url(
            container_url=container_url, credential=credential
        )
        self._root_dir = root_dir

    def _run(self, file_path: str, blob_name: str) -> str:
        full_file_path = os.path.join(self._root_dir, file_path)
        is_approved = interrupt(
            f"Uploading file '{full_file_path}' as blob '{blob_name}'"
        )
        if not is_approved:
            return "Upload operation was not approved."
        with open(file_path, "rb") as data:
            self._container_client.get_blob_client(blob_name).upload_blob(
                data, overwrite=True
            )
        return f"File '{file_path}' uploaded as blob '{blob_name}' successfully."


class DownloadAzureStorageBlobInput(BaseModel):
    blob_name: str = Field(..., description="The name of the blob to download.")
    file_path: str = Field(
        ...,
        description="The path to save the downloaded file. If not provided, defaults to the name of the blob.",
    )


class DownloadAzureStorageBlobTool(BaseTool):
    """Tool for downloading a blob from Azure Storage to a local file."""

    name: str = "download_azure_storage_blob"
    args_schema: type[BaseModel] = DownloadAzureStorageBlobInput
    description: str = "Downloads a blob from Azure Storage to a local file."

    def __init__(
        self,
        container_url: str,
        credential: Optional[str] = None,
        root_dir: str = os.getcwd(),
    ):
        super().__init__()
        self._container_client = ContainerClient.from_container_url(
            container_url=container_url, credential=credential
        )
        self._root_dir = root_dir

    def _run(self, blob_name: str, file_path: str) -> str:
        full_file_path = os.path.join(self._root_dir, file_path)
        is_approved = interrupt(
            f"Downloading blob '{blob_name}' to file '{full_file_path}'"
        )
        if not is_approved:
            return "Download operation was not approved."
        blob_client = self._container_client.get_blob_client(blob_name)
        downloader = blob_client.download_blob()
        os.makedirs(os.path.dirname(full_file_path), exist_ok=True)
        with open(full_file_path, "wb") as f:
            downloader.readinto(f)
        return f"Blob '{blob_name}' downloaded to '{file_path}' successfully."
