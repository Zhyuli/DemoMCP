import re
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from http_client import jira_request
from adf import to_adf


def register(mcp: FastMCP) -> None:

    @mcp.tool
    def add_comment(
        issue_key: str,
        comment: str,
    ) -> dict:
        """
        Add a comment to a Jira issue.

        Args:
            issue_key: Issue key, e.g. 'DEV-1'.
            comment:   Comment text. Plain text only.

        Returns:
            Comment id, issue key and author.
        """
        if not issue_key or not issue_key.strip():
            raise ToolError("issue_key cannot be empty")

        if not comment or not comment.strip():
            raise ToolError("comment cannot be empty")

        cleaned_key = issue_key.strip().upper()
        if not re.match(r"^[A-Z]+-\d+$", cleaned_key):
            raise ToolError(
                f"Invalid issue key format: '{issue_key}'. Expected format like 'DEV-1'"
            )

        result = jira_request(
            "POST",
            f"/rest/api/3/issue/{cleaned_key}/comment",
            json={"body": to_adf(comment)},
        )

        author = result.get("author", {})

        return {
            "comment_id": result.get("id", "unknown"),
            "issue_key":  cleaned_key,
            "author":     author.get("displayName", "Unknown"),
            "created":    result.get("created", "—"),
        }