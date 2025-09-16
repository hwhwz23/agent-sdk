import os

from pydantic import SecretStr

from openhands.sdk import (
    LLM,
    Agent,
    Conversation,
    Event,
    EventWithMetrics,
    LLMConvertibleEvent,
    Message,
    TextContent,
    create_mcp_tools,
    get_logger,
)
from openhands.tools import BashTool, FileEditorTool


logger = get_logger(__name__)

# Configure LLM
# api_key = os.getenv("LITELLM_API_KEY")
# assert api_key is not None, "LITELLM_API_KEY environment variable is not set."
# llm = LLM(
#     model="litellm_proxy/anthropic/claude-sonnet-4-20250514",
#     base_url="https://llm-proxy.eval.all-hands.dev",
#     api_key=SecretStr(api_key),
# )

llm = LLM(
    # model="litellm_proxy/anthropic/claude-sonnet-4-20250514",
    model="ollama/devstral-64k",
    # base_url="https://llm-proxy.eval.all-hands.dev",
    base_url="http://localhost:11434",
    # api_key=SecretStr(api_key),
    api_key=SecretStr(""),
)

cwd = os.getcwd()
tools = [
    BashTool.create(working_dir=cwd),
    FileEditorTool.create(),
]

# Add MCP Tools
mcp_config = {"mcpServers": {"fetch": {"command": "uvx", "args": ["mcp-server-fetch"]}}}
mcp_tools = create_mcp_tools(mcp_config, timeout=30)
tools.extend(mcp_tools)
logger.info(f"Added {len(mcp_tools)} MCP tools")
for tool in mcp_tools:
    logger.info(f"  - {tool.name}: {tool.description}")


# Agent
agent = Agent(llm=llm, tools=tools)

llm_messages = []  # collect raw LLM messages


def conversation_callback(event: Event):
    if isinstance(event, LLMConvertibleEvent):
        llm_messages.append(event.to_llm_message())
    if isinstance(event, EventWithMetrics):
        if event.metrics is not None:
            logger.info(f"Metrics Snapshot: {event.metrics}")


# Conversation
conversation = Conversation(
    agent=agent,
    callbacks=[conversation_callback],
)

# Example message that can use MCP tools if available
message = Message(
    role="user",
    content=[
        TextContent(
            text="Read https://github.com/All-Hands-AI/OpenHands and "
            + "write 3 facts about the project into FACTS.txt."
        )
    ],
)

logger.info("Starting conversation with MCP integration...")
response = conversation.send_message(message)
conversation.run()

conversation.send_message(
    message=Message(
        role="user",
        content=[TextContent(text=("Great! Now delete that file."))],
    )
)
conversation.run()

print("=" * 100)
print("Conversation finished. Got the following LLM messages:")
for i, message in enumerate(llm_messages):
    print(f"Message {i}: {str(message)[:200]}")

assert llm.metrics is not None
print(
    f"Conversation finished. Final LLM metrics with details: {llm.metrics.model_dump()}"
)
