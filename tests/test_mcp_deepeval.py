import os

import pytest
from fastmcp import Client, FastMCP

from tests.test_tools_integration import mcp_with_fake_jira


def _require_deepeval() -> None:
    pytest.importorskip("deepeval")
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY is required to run DeepEval metrics")


@pytest.mark.asyncio
async def test_deepeval_get_issue_single_turn(mcp_with_fake_jira: FastMCP) -> None:
    _require_deepeval()

    from deepeval import evaluate
    from deepeval.metrics import MCPUseMetric
    from deepeval.test_case import LLMTestCase, MCPServer, MCPToolCall

    async with Client(mcp_with_fake_jira) as client:
        tools = await client.list_tools()
        result = await client.call_tool_mcp("get_issue", {"issue_key": "DEV-1"})

    test_case = LLMTestCase(
        input="Get issue DEV-1",
        actual_output=result.content[0].text if result.content else str(result.structuredContent),
        mcp_servers=[MCPServer(name="JiraMCP", transport="stdio", available_tools=tools)],
        mcp_tools_called=[MCPToolCall(name="get_issue", args={"issue_key": "DEV-1"}, result=result)],
    )

    metric = MCPUseMetric(model="gpt-4o", threshold=0.5)
    evaluate([test_case], [metric])
    assert metric.score >= 0.5


@pytest.mark.asyncio
async def test_deepeval_create_and_delete_issue(mcp_with_fake_jira: FastMCP) -> None:
    _require_deepeval()

    from deepeval import evaluate
    from deepeval.metrics import MCPUseMetric
    from deepeval.test_case import LLMTestCase, MCPServer, MCPToolCall

    async with Client(mcp_with_fake_jira) as client:
        tools = await client.list_tools()

        created = await client.call_tool_mcp(
            "create_issue",
            {"summary": "DeepEval create/delete", "description": "deepeval flow", "issue_type": "Task"},
        )
        key = created.structuredContent["key"]

        deleted = await client.call_tool_mcp("delete_issue", {"issue_key": key})

    test_case = LLMTestCase(
        input="Create issue and then delete it",
        actual_output=(deleted.content[0].text if deleted.content else str(deleted.structuredContent)),
        mcp_servers=[MCPServer(name="JiraMCP", transport="stdio", available_tools=tools)],
        mcp_tools_called=[
            MCPToolCall(
                name="create_issue",
                args={"summary": "DeepEval create/delete", "description": "deepeval flow", "issue_type": "Task"},
                result=created,
            ),
            MCPToolCall(name="delete_issue", args={"issue_key": key}, result=deleted),
        ],
    )

    metric = MCPUseMetric(model="gpt-4o", threshold=0.5)
    evaluate([test_case], [metric])
    assert metric.score >= 0.5
