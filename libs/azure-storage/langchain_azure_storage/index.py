import azure.core.exceptions
from azure.storage.blob import ContainerClient
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchProfile,
    HnswAlgorithmConfiguration,
    HnswParameters,
    AzureOpenAIVectorizer,
    AzureOpenAIVectorizerParameters,
    SearchIndexerDataContainer,
    SearchIndexerDataSourceConnection,
    SearchIndexer,
    IndexingParameters,
    IndexingParametersConfiguration,
    SearchIndexerSkillset,
    AzureOpenAIEmbeddingSkill,
    InputFieldMappingEntry,
    OutputFieldMappingEntry,
    FieldMapping,
    FieldMappingFunction,
)
from azure.search.documents.models import VectorizableTextQuery


class AzureAISearchClient:
    def __init__(
        self,
        endpoint: str,
        index_name: str,
        credential=None,
        container_connection_string=None,
        embedding=None,
    ):
        self._search_index_client = SearchIndexClient(
            endpoint=endpoint, credential=credential
        )
        self._search_indexer_client = SearchIndexerClient(
            endpoint=endpoint, credential=credential
        )
        self._index_name = index_name
        self._search_client = SearchClient(
            endpoint=endpoint, index_name=index_name, credential=credential
        )
        self._container_connection_string = container_connection_string
        self._embedding = embedding

    def initialize_index_from_container(self, container_url: str):
        self._get_or_create_document_source(container_url)
        self._get_or_create_index()
        self._get_or_create_skillset()
        self._get_or_create_indexer()

    def search(self, query: str, limit: int = 10):
        return self._search_client.search(
            vector_queries=[
                VectorizableTextQuery(
                    text=query,
                    fields="content_vector_",
                )
            ],
            top=limit,
        )

    def run_indexer(self):
        self._search_indexer_client.run_indexer(f"{self._index_name}-indexer")

    def _get_or_create_skillset(self):
        try:
            self._search_indexer_client.get_skillset(f"{self._index_name}-skillset")
        except azure.core.exceptions.ResourceNotFoundError:
            self._create_skillset()

    def _create_skillset(self):
        self._search_indexer_client.create_skillset(
            SearchIndexerSkillset(
                name=f"{self._index_name}-skillset",
                skills=[
                    AzureOpenAIEmbeddingSkill(
                        name=f"{self._index_name}-embedding-skill",
                        api_key=self._embedding["api_key"],
                        resource_url=self._embedding["resource_url"],
                        model_name=self._embedding["model"],
                        deployment_name=self._embedding["deployment_name"],
                        dimensions=self._embedding["dimensions"],
                        inputs=[
                            InputFieldMappingEntry(
                                name="text", source="/document/content"
                            )
                        ],
                        outputs=[
                            OutputFieldMappingEntry(
                                name="embedding", target_name="content_vector_"
                            )
                        ],
                    )
                ],
            )
        )

    def _get_or_create_indexer(self):
        try:
            self._search_indexer_client.get_indexer(f"{self._index_name}-indexer")
        except azure.core.exceptions.ResourceNotFoundError:
            self._create_indexer()

    def _create_indexer(self):
        self._search_indexer_client.create_indexer(
            SearchIndexer(
                name=f"{self._index_name}-indexer",
                data_source_name=f"{self._index_name}-blob-data-source",
                target_index_name=self._index_name,
                parameters=IndexingParameters(
                    configuration=IndexingParametersConfiguration(
                        data_to_extract="contentAndMetadata",
                        parsing_mode="json",
                        query_timeout=None,
                    )
                ),
                skillset_name=f"{self._index_name}-skillset",
                field_mappings=[
                    FieldMapping(
                        source_field_name="metadata_storage_path",
                        target_field_name="metadata_storage_path",
                        mapping_function=FieldMappingFunction(
                            name="base64Encode",
                            parameters={"useHttpServerUtilityUrlTokenEncode": False},
                        ),
                    )
                ],
                output_field_mappings=[
                    FieldMapping(
                        source_field_name="/document/content_vector_/*",
                        target_field_name="content_vector_",
                    ),
                ],
            )
        )

    def _get_or_create_document_source(self, container_url: str):
        try:
            self._search_indexer_client.get_data_source_connection(
                f"{self._index_name}-blob-data-source"
            )
        except azure.core.exceptions.ResourceNotFoundError:
            self._create_document_source(container_url)

    def _create_document_source(self, container_url: str):
        self._search_indexer_client.create_data_source_connection(
            SearchIndexerDataSourceConnection(
                name=f"{self._index_name}-blob-data-source",
                type="azureblob",
                connection_string=self._container_connection_string,
                container=SearchIndexerDataContainer(
                    name=ContainerClient.from_container_url(
                        container_url
                    ).container_name
                ),
            )
        )

    def _get_or_create_index(self):
        try:
            self._search_index_client.get_index(self._index_name)
        except azure.core.exceptions.ResourceNotFoundError:
            self._create_index()

    def _create_index(self):
        self._search_index_client.create_index(
            SearchIndex(
                name=self._index_name,
                fields=[
                    SearchField(
                        name="metadata_storage_path",
                        type=SearchFieldDataType.String,
                        key=True,
                    ),
                    SearchField(name="content", type=SearchFieldDataType.String),
                    SearchField(
                        name="content_vector_",
                        type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                        searchable=True,
                        hidden=True,
                        stored=False,
                        vector_search_dimensions=1536,
                        vector_search_profile_name=f"{self._index_name}-vector-profile",
                    ),
                ],
                vector_search=VectorSearch(
                    profiles=[
                        VectorSearchProfile(
                            name=f"{self._index_name}-vector-profile",
                            vectorizer_name=f"{self._index_name}-vectorizer",
                            algorithm_configuration_name=f"{self._index_name}-algorithm-configuration",
                        )
                    ],
                    vectorizers=[
                        AzureOpenAIVectorizer(
                            vectorizer_name=f"{self._index_name}-vectorizer",
                            parameters=AzureOpenAIVectorizerParameters(
                                resource_url=self._embedding["resource_url"],
                                model_name=self._embedding["model"],
                                deployment_name=self._embedding["deployment_name"],
                                api_key=self._embedding["api_key"],
                            ),
                        ),
                    ],
                    algorithms=[
                        HnswAlgorithmConfiguration(
                            name=f"{self._index_name}-algorithm-configuration",
                            parameters=HnswParameters(
                                m=4, ef_construction=400, ef_search=500, metric="cosine"
                            ),
                        )
                    ],
                ),
            )
        )
