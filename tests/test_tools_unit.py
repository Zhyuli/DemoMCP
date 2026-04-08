import pytest
from pydantic import ValidationError

from schemas import CreateIssueSchema, IssueKeySchema, SearchIssuesSchema


def test_valid_key() -> None:
    data = IssueKeySchema(issue_key=" scrum-42 ")
    assert data.issue_key == "SCRUM-42"


def test_lowercase_converted() -> None:
    data = IssueKeySchema(issue_key="scrum-7")
    assert data.issue_key == "SCRUM-7"


def test_empty_key_raises() -> None:
    with pytest.raises(ValidationError):
        IssueKeySchema(issue_key="")


def test_invalid_format_raises() -> None:
    with pytest.raises(ValidationError):
        IssueKeySchema(issue_key="INVALID")


def test_create_issue_schema_valid_input() -> None:
    data = CreateIssueSchema(summary="  test summary  ", issue_type="Task")
    assert data.summary == "test summary"
    assert data.issue_type == "Task"


def test_empty_summary_raises() -> None:
    with pytest.raises(ValidationError):
        CreateIssueSchema(summary="", issue_type="Task")


def test_whitespace_summary_raises() -> None:
    with pytest.raises(ValidationError):
        CreateIssueSchema(summary="   ", issue_type="Task")


def test_summary_too_long_raises() -> None:
    with pytest.raises(ValidationError):
        CreateIssueSchema(summary="A" * 256, issue_type="Task")


def test_invalid_issue_type_raises() -> None:
    with pytest.raises(ValidationError):
        CreateIssueSchema(summary="Valid summary", issue_type="invalidType")


def test_search_issues_schema_valid_input() -> None:
    data = SearchIssuesSchema(jql="project=SCRUM ORDER BY created DESC", max_results=20)
    assert data.jql == "project=SCRUM ORDER BY created DESC"
    assert data.max_results == 20


def test_search_issues_schema_empty_jql_raises() -> None:
    with pytest.raises(ValidationError):
        SearchIssuesSchema(jql="")


def test_search_issues_schema_max_results_boundaries() -> None:
    assert SearchIssuesSchema(jql="project=SCRUM", max_results=1).max_results == 1
    assert SearchIssuesSchema(jql="project=SCRUM", max_results=50).max_results == 50


def test_max_results_out_of_range_raises() -> None:
    with pytest.raises(ValidationError):
        SearchIssuesSchema(jql="project=SCRUM", max_results=0)

    with pytest.raises(ValidationError):
        SearchIssuesSchema(jql="project=SCRUM", max_results=51)
