import pytest


pytestmark = pytest.mark.skip(reason="Replaced by test_tools_unit.py and test_tools_integration.py")


# ─────────────────────────────────────────────────────────────────────────────
# HOW TO RUN
# ─────────────────────────────────────────────────────────────────────────────
# Run all tests:       pytest tests/ -v
# Run this file only:  pytest tests/test_example.py -v
# Run single test:     pytest tests/test_example.py::test_get_issue_valid -v
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURE
# Spins up the MCP server in-memory.
# Zero network overhead
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def mcp():
    server = FastMCP("JiraMCP-Test")
    get_issue.register(server)
    create_issue.register(server)
    update_issue.register(server)
    delete_issue.register(server)
    search_issues.register(server)
    return server


# ─────────────────────────────────────────────────────────────────────────────
# TYPE 1 — TOOL RESPONSE SHAPE
# Call one tool, assert the response fields and values are correct.
#
# Cover:
#   - get_issue returns key, summary, status, assignee, priority
#   - create_issue returns key and summary
#   - search_issues returns total and issues list
#   - add_comment returns comment_id, issue_key, author
#   - get_comments returns total and comments list
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_issue_valid(mcp):
    async with Client(mcp) as client:
        result = await client.call_tool_mcp("get_issue", {"issue_key": "DEV-1"})
        assert result.isError is False
        assert result.structuredContent is not None
        assert result.structuredContent["key"] == "DEV-1"
        assert "summary" in result.structuredContent
        assert "status" in result.structuredContent


# TYPE 2 — MULTI-STEP WORKFLOW
# Chain multiple tool calls, assert state after each step.
#
# Cover:
#   - create_issue → get_issue → assert summary matches
#   etc.

# @pytest.mark.asyncio
# async def test_create_then_get_issue(mcp):
#     async with Client(mcp) as client:
#         # Step 1 — create
#         # Step 2 — get and verify summary matches
#         # Step 3 — cleanup (delete)
#         pass

# TYPE 3 — VALIDATION / ERROR RESPONSE
# Call a tool with invalid input, assert isError=True and message is readable.
#
# Cover:
#   - empty issue_key → isError True
#   - invalid key format (no dash) → isError True
#   - empty summary → isError True
#   - invalid issue_type → isError True
#   - max_results out of range → isError True

# @pytest.mark.asyncio
# async def test_get_issue_invalid_key(mcp):
#     async with Client(mcp) as client:
#         # Call with invalid key, assert isError and message content
#         pass


# TYPE 4 — SCHEMA UNIT TEST
# Test Pydantic schemas directly — no MCP, no Jira, no network.
#
# Cover:
#   - IssueKeySchema: valid key, lowercase converted, empty raises, bad format raises
#   - CreateIssueSchema: valid input, empty summary raises, too long raises, bad type raises
#   - SearchIssuesSchema: valid jql, empty raises, max_results boundaries

# def test_issue_key_schema_empty_raises():
#     # No MCP needed — pure Pydantic validation
#     pass


# TYPE 5 — GOLDEN DATASET TEST
# Run the same assertion across a list of known inputs and expected outputs.
# Useful for catching regressions when tool behaviour changes.
#
# Cover:
#   - Multiple valid issue keys all return isError=False
#   - Multiple invalid inputs all return isError=True
#   - Multiple JQL queries all return non-empty results
#
# Recommended libraries for generating test data:
#
#   Hypothesis — from the course presentation
#   pip install hypothesis
#   Generates hundreds of edge cases automatically from type strategies.
#   Best for: boundary values, unexpected formats, stress testing schemas.
#
#   Faker — recommended addition
#   pip install faker
#   Generates realistic human-readable data.
#   Best for: believable Jira issue content in integration tests.
#   Example: fake.sentence(nb_words=5) → "Login fails on staging server"
# ─────────────────────────────────────────────────────────────────────────────

# VALID_ISSUE_KEYS = ["DEV-1", "DEV-2", "DEV-6"]
#
# @pytest.mark.parametrize("key", VALID_ISSUE_KEYS)
# @pytest.mark.asyncio
# async def test_get_issue_golden_dataset(mcp, key):
#     async with Client(mcp) as client:
#         # Assert each key returns isError=False and has expected fields
#         pass

# TYPE 6 — DEEPEVAL MCP EVALUATION
# Evaluate tool calls using DeepEval MCPUseMetric.
# Docs: https://deepeval.com/docs/getting-started-mcp
#
# pip install deepeval
#
# MCPUseMetric evaluates:
#   - Primitive usage: did the agent use the right MCP tool?
#   - Argument correctness: were the arguments correct?
#   - Final score = min(primitive_score, argument_score)
#
# Cover:
#   - Single-turn: one tool call, assert MCPUseMetric score >= 0.5
#   - Multi-turn: chain of tool calls, assert MultiTurnMCPUseMetric score >= 0.5
#   - Task completion: assert MCPTaskCompletionMetric score >= 0.5

# @pytest.mark.asyncio
# async def test_deepeval_get_issue(mcp):
#     from deepeval import evaluate
#     from deepeval.test_case import LLMTestCase, MCPServer, MCPToolCall
#     from deepeval.metrics import MCPUseMetric
#
#     async with Client(mcp) as client:
#         tools = await client.list_tools()
#         result = await client.call_tool_mcp("get_issue", {"issue_key": "DEV-1"})
#
#     test_case = LLMTestCase(
#         input="Get details for issue DEV-1",
#         actual_output=result.content[0].text,
#         mcp_servers=[MCPServer(name="JiraMCP", transport="stdio", available_tools=tools)],
#         mcp_tools_called=[MCPToolCall(name="get_issue", args={"issue_key": "DEV-1"}, result=result)],
#     )
#
#     metric = MCPUseMetric(model="gpt-4o")
#     evaluate([test_case], [metric])
#     assert metric.score >= 0.5