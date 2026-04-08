import copy

import pytest
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError

from config import PROJECT_KEY
from tools import add_comment, create_issue, delete_issue, get_comments, get_issue, search_issues, update_issue


@pytest.fixture
def mcp_with_fake_jira(monkeypatch: pytest.MonkeyPatch) -> FastMCP:
    store = {
        "next_issue_num": 2,
        "next_comment_id": 1000,
        "issues": {
            "SCRUM-1": {
                "fields": {
                    "summary": "Seed issue",
                    "status": {"name": "To Do"},
                    "assignee": {"displayName": "Unassigned"},
                    "priority": {"name": "Medium"},
                    "issuetype": {"name": "Task"},
                    "description": {
                        "type": "doc",
                        "version": 1,
                        "content": [
                            {
                                "type": "paragraph",
                                "content": [{"type": "text", "text": "Seed description"}],
                            }
                        ],
                    },
                }
            }
        },
        "comments": {"SCRUM-1": []},
    }

    def fake_jira_request(method: str, path: str, **kwargs):
        if method == "GET" and path.startswith("/rest/api/3/issue/") and path.endswith("/comment"):
            key = path.split("/")[-2]
            if key not in store["issues"]:
                raise ToolError("Jira API error 404: issue not found")
            comments = store["comments"].get(key, [])
            return {"total": len(comments), "comments": copy.deepcopy(comments)}

        if method == "POST" and path.startswith("/rest/api/3/issue/") and path.endswith("/comment"):
            key = path.split("/")[-2]
            if key not in store["issues"]:
                raise ToolError("Jira API error 404: issue not found")
            payload = kwargs.get("json", {})
            cid = str(store["next_comment_id"])
            store["next_comment_id"] += 1
            comment = {
                "id": cid,
                "author": {
                    "displayName": "Test User",
                    "accountId": "acc-123",
                },
                "created": "2026-04-06T12:42:35.417+0300",
                "body": payload.get("body", {}),
            }
            store["comments"].setdefault(key, []).append(comment)
            return copy.deepcopy(comment)

        if method == "POST" and path == "/rest/api/3/issue":
            payload = kwargs.get("json", {})
            fields = payload.get("fields", {})
            key = f"{PROJECT_KEY}-{store['next_issue_num']}"
            store["next_issue_num"] += 1
            store["issues"][key] = {
                "fields": {
                    "summary": fields.get("summary", "—"),
                    "status": {"name": "To Do"},
                    "assignee": None,
                    "priority": {"name": "Medium"},
                    "issuetype": {"name": fields.get("issuetype", {}).get("name", "Task")},
                    "description": fields.get("description"),
                }
            }
            store["comments"].setdefault(key, [])
            return {"key": key}

        if method == "GET" and path.startswith("/rest/api/3/issue/"):
            key = path.split("/")[-1]
            issue = store["issues"].get(key)
            if not issue:
                raise ToolError("Jira API error 404: issue not found")
            return {"key": key, "fields": copy.deepcopy(issue["fields"])}

        if method == "PUT" and path.startswith("/rest/api/3/issue/"):
            key = path.split("/")[-1]
            if key not in store["issues"]:
                raise ToolError("Jira API error 404: issue not found")
            fields = kwargs.get("json", {}).get("fields", {})
            store["issues"][key]["fields"].update(fields)
            return {}

        if method == "DELETE" and path.startswith("/rest/api/3/issue/"):
            key = path.split("/")[-1]
            if key not in store["issues"]:
                raise ToolError("Jira API error 404: issue not found")
            del store["issues"][key]
            store["comments"].pop(key, None)
            return {}

        if method == "POST" and path == "/rest/api/3/search/jql":
            payload = kwargs.get("json", {})
            max_results = payload.get("maxResults", 20)
            issues = []
            for key, issue in sorted(store["issues"].items()):
                issues.append({"key": key, "fields": copy.deepcopy(issue["fields"])})
            return {"total": len(issues), "issues": issues[:max_results]}

        raise ToolError(f"Unhandled fake Jira request: {method} {path}")

    monkeypatch.setattr(get_issue, "jira_request", fake_jira_request)
    monkeypatch.setattr(create_issue, "jira_request", fake_jira_request)
    monkeypatch.setattr(update_issue, "jira_request", fake_jira_request)
    monkeypatch.setattr(delete_issue, "jira_request", fake_jira_request)
    monkeypatch.setattr(search_issues, "jira_request", fake_jira_request)
    monkeypatch.setattr(add_comment, "jira_request", fake_jira_request)
    monkeypatch.setattr(get_comments, "jira_request", fake_jira_request)

    mcp = FastMCP("JiraMCP-Test")
    get_issue.register(mcp)
    create_issue.register(mcp)
    update_issue.register(mcp)
    delete_issue.register(mcp)
    search_issues.register(mcp)
    add_comment.register(mcp)
    get_comments.register(mcp)
    return mcp


@pytest.mark.asyncio
async def test_get_issue_valid(mcp_with_fake_jira: FastMCP) -> None:
    async with Client(mcp_with_fake_jira) as client:
        result = await client.call_tool_mcp("get_issue", {"issue_key": "scrum-1"})

    assert result.isError is False
    data = result.structuredContent
    assert data["key"] == "SCRUM-1"
    assert "summary" in data
    assert "status" in data
    assert "assignee" in data
    assert "priority" in data
    assert "description" in data


@pytest.mark.asyncio
async def test_get_issue_invalid_format(mcp_with_fake_jira: FastMCP) -> None:
    async with Client(mcp_with_fake_jira) as client:
        result = await client.call_tool_mcp("get_issue", {"issue_key": "invalid"})

    assert result.isError is True
    assert result.content
    assert "invalid issue key format" in result.content[0].text.lower()


@pytest.mark.asyncio
async def test_create_issue_empty_summary(mcp_with_fake_jira: FastMCP) -> None:
    async with Client(mcp_with_fake_jira) as client:
        result = await client.call_tool_mcp(
            "create_issue",
            {"summary": "", "description": "", "issue_type": "Task"},
        )

    assert result.isError is True
    assert result.content
    assert "summary" in result.content[0].text.lower()


@pytest.mark.asyncio
async def test_create_get_delete_workflow(mcp_with_fake_jira: FastMCP) -> None:
    async with Client(mcp_with_fake_jira) as client:
        created = await client.call_tool_mcp(
            "create_issue",
            {"summary": "Workflow ticket", "description": "Created in integration test", "issue_type": "Task"},
        )
        assert created.isError is False
        key = created.structuredContent["key"]

        fetched = await client.call_tool_mcp("get_issue", {"issue_key": key})
        assert fetched.isError is False
        assert fetched.structuredContent["summary"] == "Workflow ticket"

        deleted = await client.call_tool_mcp("delete_issue", {"issue_key": key})
        assert deleted.isError is False
        assert deleted.structuredContent["deleted"] is True

        not_found = await client.call_tool_mcp("get_issue", {"issue_key": key})
        assert not_found.isError is True


@pytest.mark.asyncio
async def test_add_comment_response_fields_are_correct(mcp_with_fake_jira: FastMCP) -> None:
    async with Client(mcp_with_fake_jira) as client:
        added = await client.call_tool_mcp(
            "add_comment",
            {"issue_key": "SCRUM-1", "comment": "comment id verification"},
        )
        assert added.isError is False
        added_data = added.structuredContent

        comments = await client.call_tool_mcp("get_comments", {"issue_key": "SCRUM-1"})
        assert comments.isError is False
        last_comment = comments.structuredContent["comments"][-1]

    assert added_data["comment_id"] == last_comment["comment_id"]
    assert added_data["author"] == last_comment["author"]
    assert added_data["issue_key"] == "SCRUM-1"


# BUG: before the fix get_comments rejected keys with trailing whitespace.
@pytest.mark.asyncio
async def test_get_comments_trailing_space(mcp_with_fake_jira: FastMCP) -> None:
    async with Client(mcp_with_fake_jira) as client:
        result = await client.call_tool_mcp("get_comments", {"issue_key": "SCRUM-1\t"})

    assert result.isError is False
    assert "comments" in result.structuredContent


# BUG: before the fix get_comments rejected keys with leading whitespace.
@pytest.mark.asyncio
async def test_get_comments_leading_space(mcp_with_fake_jira: FastMCP) -> None:
    async with Client(mcp_with_fake_jira) as client:
        result = await client.call_tool_mcp("get_comments", {"issue_key": "\tSCRUM-1"})

    assert result.isError is False
    assert "comments" in result.structuredContent


@pytest.mark.asyncio
async def test_search_issues_response_shape(mcp_with_fake_jira: FastMCP) -> None:
    async with Client(mcp_with_fake_jira) as client:
        result = await client.call_tool_mcp(
            "search_issues",
            {"jql": "project=SCRUM ORDER BY created DESC", "max_results": 10},
        )

    assert result.isError is False
    data = result.structuredContent
    assert "total" in data
    assert "count" in data
    assert isinstance(data["issues"], list)
