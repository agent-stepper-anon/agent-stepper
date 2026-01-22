from git import Repo
from agentstepper.api.common import Change, ChangeType
from typing import List, Dict, Any
import os
import openai

def read_file_content(file_path: str) -> str:
    """Read the content of a file.

    Args:
        file_path (str): Path to the file.

    Returns:
        str: File content or error message if reading fails.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            return file.read()
    except Exception as error:
        return f"Error reading file: {str(error)}"


def collect_new_files(repo: Repo) -> List[Dict[str, str]]:
    """Collect untracked files and their contents.

    Args:
        repo (Repo): Git repository object.

    Returns:
        List[Dict[str, str]]: List of dictionaries with file path and content.
    """
    return [{"path": path, "content": read_file_content(os.path.join(repo.working_tree_dir, path))} for path in repo.untracked_files]


def get_unstaged_diff(repo: Repo, diff_item: Any) -> str:
    """Get the diff for an unstaged file change.

    Args:
        repo (Repo): Git repository object.
        diff_item: Diff item from repo.index.diff.

    Returns:
        str: Diff string or fallback message.
    """
    return repo.git.diff(os.path.join(repo.working_tree_dir, diff_item.a_path)) or "No diff available"


def collect_unstaged_diffs(repo: Repo) -> List[Dict[str, str]]:
    """Collect diffs for unstaged changes.

    Args:
        repo (Repo): Git repository object.

    Returns:
        List[Dict[str, str]]: List of dictionaries with file path and diff.
    """
    return [
        {"path": diff.a_path or diff.b_path, "diff": get_unstaged_diff(repo, diff)}
        for diff in repo.index.diff(None)
        if (diff.a_path or diff.b_path) and not diff.deleted_file
    ]
    
    
def get_deleted_file_content(repo: Repo, file_path: str) -> str:
    """Retrieve the first 20 lines of a deleted file's content from HEAD.

    Args:
        repo (Repo): Git repository object.
        file_path (str): Path to the deleted file.

    Returns:
        str: First 20 lines of file content or error message if retrieval fails.
    """
    try:
        content = repo.git.show(f"HEAD:{file_path}")
        return "\n".join(content.splitlines()[:20])
    except Exception as error:
        return f"Error retrieving content: {str(error)}"


def collect_removed_files(repo: Repo) -> List[Dict[str, str]]:
    """Collect paths and content of deleted files, both staged and unstaged.

    Args:
        repo (Repo): Git repository object.

    Returns:
        List[Dict[str, str]]: List of dictionaries with file path and first 20 lines of content.
    """
    staged_deletions = [
        {"path": diff.a_path, "content": get_deleted_file_content(repo, diff.a_path)}
        for diff in repo.index.diff("HEAD") if diff.deleted_file
    ]
    unstaged_deletions = [
        {"path": diff.a_path, "content": get_deleted_file_content(repo, diff.a_path)}
        for diff in repo.index.diff(None) if diff.deleted_file
    ]
    return list({d["path"]: d for d in staged_deletions + unstaged_deletions}.values())


def format_section(title: str, items: List[Any], item_formatter=lambda x: str(x)) -> List[str]:
    """Format a section of the diff summary.

    Args:
        title (str): Section title.
        items (List[Any]): List of items to format.
        item_formatter (callable): Function to format each item.

    Returns:
        List[str]: Formatted section lines.
    """
    lines = [title]
    if not items:
        lines.append("   (None)")
    else:
        lines.extend(item_formatter(item) for item in items)
    return lines


def format_new_file(item: Dict[str, str]) -> str:
    """Format a new file entry.

    Args:
        item (Dict[str, str]): Dictionary with file path and content.

    Returns:
        str: Formatted string for the new file.
    """
    return f"   {item['path']}:\n   ```\n{item['content']}\n   ```"


def format_changed_file(item: Dict[str, str]) -> str:
    """Format a changed file entry.

    Args:
        item (Dict[str, str]): Dictionary with file path and diff.

    Returns:
        str: Formatted string for the changed file.
    """
    return f"   {item['path']}:\n   ```diff\n{item['diff']}\n   ```"

def format_removed_file(item: Dict[str, str]) -> str:
    """Format a removed file entry with its content.

    Args:
        item (Dict[str, str]): Dictionary with file path and content.

    Returns:
        str: Formatted string for the removed file.
    """
    return f"   {item['path']} (first 20 lines):\n   ```\n{item['content']}\n   ```"


def format_diff_summary(summary: Dict[str, List[Any]]) -> str:
    """Format the complete diff summary.

    Args:
        summary (Dict[str, List[Any]]): Dictionary with new, changed, and removed files.

    Returns:
        str: Formatted diff summary string.
    """
    sections = [
        format_section("1. New files:", summary["new_files"], format_new_file),
        format_section("\n2. Changes to existing files:", summary["changed_files"], format_changed_file),
        format_section("\n3. Removed files:", summary["removed_files"], format_removed_file),
    ]
    return "\n".join(line for section in sections for line in section)


def get_system_prompt(formatted_summary: str) -> str:
    """Generate the system prompt for LLM commit message generation.

    Args:
        formatted_summary (str): Formatted diff summary.

    Returns:
        str: System prompt string.
    """
    return f"""
You are an expert Git user tasked with generating a commit message based on a diff summary. Follow Git style guidelines:
- The commit title is a single, concise sentence (up to 50 characters) summarizing the changes.
- Use imperative mood (e.g., "Add feature", "Fix bug").
- The description provides context, explaining what changed and why, wrapped at 72 characters.
- Base the message solely on the provided diff summary, ensuring accuracy.

**Diff Summary:**
{formatted_summary}

**Output Format:**
```
<Title>

<Description>
```
"""


def get_changes(repo: Repo) -> List[Change]:
    """
    Collect changes in the repository including new, changed, and removed files.

    :param Repo repo: Git repository object
    :return: List of Change objects representing new, changed, and removed files
    :rtype: List[Change]
    """
    changes = []

    # Collect new files (untracked files)
    for new_file in collect_new_files(repo):
        changes.append(Change(
            path=new_file["path"],
            change_type=ChangeType.NEW_FILE,
            diff="",  # No diff for new files
            content=new_file["content"],
            previous_content=""
        ))

    # Collect changed files (unstaged diffs)
    for changed_file in collect_unstaged_diffs(repo):
        try:
            previous_content = repo.git.show(f"HEAD:{changed_file['path']}")
        except Exception:
            previous_content = ""  # Handle case where file is new or HEAD is empty
        changes.append(Change(
            path=changed_file["path"],
            change_type=ChangeType.CHANGE,
            diff=changed_file["diff"],
            content=read_file_content(os.path.join(repo.working_tree_dir, changed_file["path"])),
            previous_content=previous_content
        ))

    # Collect removed files
    for removed_file in collect_removed_files(repo):
        changes.append(Change(
            path=removed_file["path"],
            change_type=ChangeType.DELETED_FILE,
            diff="",  # No diff for deleted files
            content="",
            previous_content=removed_file["content"]
        ))

    return changes


def get_summary_of_changes(changes: List[Change]) -> str:
    """
    Generate formatted diff summary string from a list of Change objects.

    :param List[Change] changes: List of Change objects representing repository changes
    :return: Formatted diff summary string
    :rtype: str
    """
    summary = {
        "new_files": [
            {"path": change.path, "content": change.content}
            for change in changes if change.change_type == ChangeType.NEW_FILE
        ],
        "changed_files": [
            {"path": change.path, "diff": change.diff}
            for change in changes if change.change_type == ChangeType.CHANGE
        ],
        "removed_files": [
            {"path": change.path, "content": change.previous_content}
            for change in changes if change.change_type == ChangeType.DELETED_FILE
        ]
    }
    return format_diff_summary(summary)


def generate_commit_message(summary_of_changes: str, llm: Any = None) -> str:
    '''
    Generates a commit message for the given code changes.
    
    :param str summary_of_changes: Textual list of changes in the codebase.
    :param OpenAI llm: OpenAI LLm object if using openai api >= `1.0.0`. Otherwise uses calls from older api versions.
    '''
    def extract_text(text: str):
        start = text.find("```")
        if start == -1:
            return text.strip()
        end = text.find("```", start + 3)
        if end == -1:
            return text.strip()
        return text[start + 3:end].strip()
    
    try:
        if llm:
            return extract_text(llm.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": get_system_prompt(summary_of_changes)
                    }
                ]
            ).choices[0].message.content)
        else:
            return extract_text(openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": get_system_prompt(summary_of_changes)
                    }
                ]
            ).choices[0].message.content)
    except Exception as e:
        print('Failed to summarize commit with OpenAI API...')
        return 'Commit agent changes'