import argparse
import os

from dotenv import load_dotenv
from langchain_azure_ai.chat_models import AzureAIChatCompletionsModel
from langchain_azure_ai.embeddings import AzureAIEmbeddingsModel
from langchain_core.messages import SystemMessage
from langchain_core.tools import tool
from langchain_core.vectorstores import InMemoryVectorStore
from langgraph.graph import MessagesState, StateGraph
from langgraph.graph import END
from langgraph.prebuilt import ToolNode, tools_condition


CHAT_MODEL = None
VECTOR_STORE = None


def get_chat_model():
    global CHAT_MODEL
    if CHAT_MODEL is None:
        CHAT_MODEL = AzureAIChatCompletionsModel(
            endpoint=os.environ["AZURE_CHAT_ENDPOINT"],
            credential=os.environ["AZURE_AI_CREDENTIAL"],
            model="gpt-4.1-mini",
        )
    return CHAT_MODEL


def get_vector_store() -> InMemoryVectorStore:
    global VECTOR_STORE
    if VECTOR_STORE is None:
        VECTOR_STORE = InMemoryVectorStore.load(
            ".vector.json",
            embedding=AzureAIEmbeddingsModel(
                endpoint=os.environ["AZURE_EMBEDDING_ENDPOINT"],
                credential=os.environ["AZURE_AI_CREDENTIAL"],
                model="text-embedding-3-large",
            ),
        )
    return VECTOR_STORE


@tool(response_format="content_and_artifact")
def retrieve(query: str):
    """Retrieve information related to a query."""
    retrieved_docs = get_vector_store().similarity_search(query)
    serialized = "\n\n".join(
        (f"Source: {doc.metadata}\nContent: {doc.page_content}")
        for doc in retrieved_docs
    )
    return serialized, retrieved_docs


def query_or_respond(state: MessagesState):
    """Generate tool call for retrieval or respond."""
    llm_with_tools = get_chat_model().bind_tools([retrieve])
    response = llm_with_tools.invoke(state["messages"])
    # MessagesState appends messages to state instead of overwriting
    return {"messages": [response]}


def generate(state: MessagesState):
    """Generate answer."""
    # Get generated ToolMessages
    recent_tool_messages = []
    for message in reversed(state["messages"]):
        if message.type == "tool":
            recent_tool_messages.append(message)
        else:
            break
    tool_messages = recent_tool_messages[::-1]

    # Format into prompt
    docs_content = "\n\n".join(doc.content for doc in tool_messages)
    system_message_content = (
        "You are an assistant for question-answering tasks. "
        "Use the following pieces of retrieved context to answer "
        "the question. If you don't know the answer, say that you "
        "don't know. Use three sentences maximum and keep the "
        "answer concise. If retrieved from the context, include the "
        "source in the format 'Source: {source}' on a newline at the end of the "
        "answer."
        "\n\n"
        f"{docs_content}"
    )
    conversation_messages = [
        message
        for message in state["messages"]
        if message.type in ("human", "system")
        or (message.type == "ai" and not message.tool_calls)
    ]
    prompt = [SystemMessage(system_message_content)] + conversation_messages

    # Run
    response = get_chat_model().invoke(prompt)
    return {"messages": [response]}


def generate_vector_store_if_not_exists():
    if not os.path.exists(".vector.json"):
        print("Vector store not found on disk. Loading and embedding documents...")
        from embed import load_and_embed_documents_from_container

        load_and_embed_documents_from_container()


def build_graph():
    graph_builder = StateGraph(MessagesState)
    graph_builder.add_node(query_or_respond)
    graph_builder.add_node("tools", ToolNode([retrieve]))
    graph_builder.add_node(generate)

    graph_builder.set_entry_point("query_or_respond")
    graph_builder.add_conditional_edges("query_or_respond", tools_condition)
    graph_builder.add_edge("tools", "generate")
    graph_builder.add_edge("generate", END)

    return graph_builder.compile()


def run(graph, input_message, verbose=False):
    for step in graph.stream(
        {"messages": [{"role": "user", "content": input_message}]},
        stream_mode="values",
    ):
        if verbose:
            step["messages"][-1].pretty_print()
    if not verbose:
        print(f"\n\033[1m\033[36m>>> {step['messages'][-1].content}\033[0m")


def get_argparser():
    parser = argparse.ArgumentParser(description="Run RAG agent to query vector store.")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Pretty print all steps performed by agent",
    )
    return parser


def main():
    parser = get_argparser()
    parsed_args = parser.parse_args()

    load_dotenv()
    generate_vector_store_if_not_exists()

    graph = build_graph()

    query = input("[Enter your query]> ")
    run(graph, query, verbose=parsed_args.verbose)


if __name__ == "__main__":
    main()
