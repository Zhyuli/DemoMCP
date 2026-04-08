import re
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from http_client import jira_request


def register(mcp: FastMCP) -> None:

    @mcp.tool(
        annotations={"readOnlyHint": True}
    )
    def get_comments(
        issue_key: str,
    ) -> dict:
        """
        Get all comments for a Jira issue.

        Args:
            issue_key: Issue key, e.g. 'DEV-1'.

        Returns:
            List of comments with id, author and text.
        """
        if not issue_key:
            raise ToolError("issue_key cannot be empty")
        
        cleaned_key = issue_key.strip().upper()
        if not re.match(r"^[A-Z]+-\d+$", cleaned_key):
            raise ToolError(
                f"Invalid issue key format: '{issue_key}'. Expected format like 'DEV-1'"
            )

        result = jira_request(
            "GET",
            f"/rest/api/3/issue/{cleaned_key}/comment",
        )

        comments = result.get("comments", [])
        total    = result.get("total", 0)

        items = []
        for c in comments:
            author = c.get("author", {})

            texts = []
            body  = c.get("body", {})
            for block in body.get("content", []):
                for inline in block.get("content", []):
                    if inline.get("type") == "text":
                        texts.append(inline.get("text", ""))

            items.append({
                "comment_id": c.get("id", "—"),
                "author":     author.get("displayName", "Unknown"),
                "created":    c.get("created", "—"),
                "text":       " ".join(texts).strip() or "—",
            })

        return {
            "total":    total,
            "comments": items,
        }