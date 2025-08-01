import argparse
import os

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.core.credentials import AzureKeyCredential
from langchain_azure_ai.chat_models import AzureAIChatCompletionsModel
from langchain_azure_storage.store import AzureBlobStore


from langgraph.checkpoint.memory import InMemorySaver
from langgraph.prebuilt import create_react_agent
from langmem import (
    create_manage_memory_tool,
    create_search_memory_tool,
)


CHAT_MODEL = None
STORE = None


def get_chat_model():
    global CHAT_MODEL
    if CHAT_MODEL is None:
        CHAT_MODEL = AzureAIChatCompletionsModel(
            endpoint=os.environ["AZURE_CHAT_ENDPOINT"],
            credential=os.environ["AZURE_AI_CREDENTIAL"],
            model="gpt-4.1-mini",
        )
    return CHAT_MODEL


def get_store():
    global STORE
    if STORE is None:
        STORE = AzureBlobStore(
            container_url=os.environ["AZURE_STORAGE_CONTAINER_URL"],
            credential=DefaultAzureCredential(),
            search_index={
                "index_name": os.environ["AZURE_SEARCH_INDEX_NAME"],
                "endpoint": os.environ["AZURE_SEARCH_ENDPOINT"],
                "credential": AzureKeyCredential(os.environ["AZURE_SEARCH_API_KEY"]),
                "container_connection_string": os.environ[
                    "AZURE_STORAGE_CONNECTION_STRING"
                ],
                "embedding": {
                    "resource_url": os.environ["AZURE_AI_EMBEDDING_URL"],
                    "model": os.environ["AZURE_AI_EMBEDDING_MODEL"],
                    "deployment_name": os.environ["AZURE_AI_EMBEDDING_DEPLOYMENT_NAME"],
                    "api_key": os.environ["AZURE_AI_CREDENTIAL"],
                    "dimensions": 1536,
                },
            },
        )
    return STORE


def build_graph(container_url: str):
    return create_react_agent(
        model=get_chat_model(),
        prompt=("You are a helpful assistant that answers general knowledge questions"),
        tools=[
            create_search_memory_tool(("memories",)),
            create_manage_memory_tool(("memories",)),
        ],
        # checkpointer=InMemorySaver(),
        store=get_store(),
    )


def run(graph, input_message, verbose=False):
    steps = stream_graph(
        graph, {"messages": [{"role": "user", "content": input_message}]}
    )
    process_steps(graph, steps, verbose=verbose)


def stream_graph(graph, input_message):
    return graph.stream(
        input_message,
        {"configurable": {"thread_id": "1"}},
    )


def process_steps(graph, steps, verbose=False):
    for step in steps:
        if verbose:
            step_name = "agent"
            if "tools" in step:
                step_name = "tools"
            step[step_name]["messages"][-1].pretty_print()
    if not verbose:
        print_ai_message(step["agent"]["messages"][-1].content)


def ask_for_approval():
    answer = input("Approve this action? (Y/n): ")
    return answer.strip().lower() in ["yes", "y"]


def print_ai_message(message):
    print(f"\n\033[1m\033[36m>>> {message}\033[0m")


def get_argparser():
    parser = argparse.ArgumentParser(
        description="Run agent that manages memories in Azure Storage"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Pretty print all steps performed by agent",
    )
    parser.add_argument(
        "-c",
        "--container-url",
        type=str,
        default=os.environ.get("AZURE_STORAGE_CONTAINER_URL"),
        help="Azure Storage container URL (default from environment variable AZURE_STORAGE_CONTAINER_URL)",
    )
    return parser


def main():
    load_dotenv()
    parser = get_argparser()
    parsed_args = parser.parse_args()

    graph = build_graph(container_url=parsed_args.container_url)

    print("Operating on Azure Storage container:", parsed_args.container_url)
    while query := input("[Enter request]> "):
        run(graph, query, verbose=parsed_args.verbose)


if __name__ == "__main__":
    main()
