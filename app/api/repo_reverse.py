"""
Repository Reverse Engineering REST API endpoints.
"""

from __future__ import annotations

import os
import base64
import logging
import asyncio
import re
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
import httpx

from app.core.auth import get_current_user
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repo-reverse", tags=["RepoReverse"])

API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


class TreeRequest(BaseModel):
    owner: str
    repo: str


class AnalyzeRequest(BaseModel):
    owner: str
    repo: str
    model: str = "gemini-2.5-pro"
    apiKey: Optional[str] = None
    style: str = "detailed-architectural"
    manualFiles: List[str] = Field(default_factory=list)


class AdaptRequest(BaseModel):
    originalPrompt: str
    newAppDescription: Optional[str] = None
    techStackChanges: Optional[str] = None
    model: str = "gemini-2.5-pro"
    apiKey: Optional[str] = None


class RefineRequest(BaseModel):
    originalPrompt: str
    rating: int
    feedbackTags: List[str] = Field(default_factory=list)
    feedbackText: str = ""
    model: str = "gemini-2.5-pro"
    apiKey: Optional[str] = None


async def generate_gemini_content(
    prompt: str,
    model: str,
    api_key: str,
    system_instruction: Optional[str] = None,
) -> str:
    """Helper method to call Gemini generateContent endpoint directly."""
    payload: Dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {},
    }
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    url = f"{API_BASE}/{model}:generateContent?key={api_key}"
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

    candidates = data.get("candidates", [])
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        return ""
    return parts[0].get("text", "").strip()


def get_github_headers() -> Dict[str, str]:
    """Helper to return Github authentication headers."""
    headers = {
        "User-Agent": "Repo-Reverse-Engineer",
        "Accept": "application/vnd.github.v3+json",
    }
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    return headers


@router.post("/tree")
async def get_tree(
    body: TreeRequest, user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Retrieves metadata and recursive file tree of a GitHub repository."""
    owner = body.owner
    repo = body.repo

    if not owner or not repo:
        raise HTTPException(status_code=400, detail="Owner and repo are required.")

    headers = get_github_headers()

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Fetch metadata
        repo_url = f"https://api.github.com/repos/{owner}/{repo}"
        repo_res = await client.get(repo_url, headers=headers)
        if repo_res.status_code != 200:
            err_msg = (
                "Repository not found."
                if repo_res.status_code == 404
                else "Failed to fetch repository metadata."
            )
            raise HTTPException(status_code=repo_res.status_code, detail=err_msg)

        repo_data = repo_res.json()
        default_branch = repo_data.get("default_branch", "main")
        description = repo_data.get("description", "")
        language = repo_data.get("language", "Unknown")

        # 2. Fetch recursive tree
        tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
        tree_res = await client.get(tree_url, headers=headers)
        all_files = []
        if tree_res.status_code == 200:
            tree_data = tree_res.json()
            if "tree" in tree_data:
                all_files = [
                    item["path"]
                    for item in tree_data["tree"]
                    if item.get("type") == "blob"
                ]
        else:
            raise HTTPException(
                status_code=tree_res.status_code,
                detail="Failed to retrieve repository files structure.",
            )

    return {
        "owner": owner,
        "repo": repo,
        "defaultBranch": default_branch,
        "files": all_files,
        "description": description,
        "language": language,
    }


@router.post("/analyze")
async def analyze_repo(
    body: AnalyzeRequest, user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Analyzes a GitHub repository files & commit metrics, sending prompt generation instruction to Gemini."""
    owner = body.owner
    repo = body.repo

    if not owner or not repo:
        raise HTTPException(status_code=400, detail="Owner and repo are required.")

    gemini_key = body.apiKey or settings.gemini_api_key
    if gemini_key:
        gemini_key = gemini_key.strip().strip("\"'")
    if not gemini_key or gemini_key == "MY_GEMINI_API_KEY":
        raise HTTPException(
            status_code=400,
            detail="Gemini API Key is invalid or missing. Please configure it.",
        )

    headers = get_github_headers()

    async with httpx.AsyncClient(timeout=30.0) as client:
        # 1. Fetch metadata
        repo_url = f"https://api.github.com/repos/{owner}/{repo}"
        repo_res = await client.get(repo_url, headers=headers)
        if repo_res.status_code != 200:
            err_msg = (
                "Repository not found."
                if repo_res.status_code == 404
                else "Failed to fetch repository metadata. Rate limit might be exceeded."
            )
            raise HTTPException(status_code=repo_res.status_code, detail=err_msg)
        repo_data = repo_res.json()
        default_branch = repo_data.get("default_branch", "main")

        # 2. Fetch README
        readme_text = ""
        readme_url = f"https://api.github.com/repos/{owner}/{repo}/readme"
        readme_res = await client.get(readme_url, headers=headers)
        if readme_res.status_code == 200:
            readme_data = readme_res.json()
            if "content" in readme_data:
                try:
                    readme_text = base64.b64decode(readme_data["content"]).decode(
                        "utf-8"
                    )
                except Exception:
                    pass

        # 3. Fetch File Tree
        tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{default_branch}?recursive=1"
        tree_res = await client.get(tree_url, headers=headers)
        file_tree = ""
        all_files = []
        if tree_res.status_code == 200:
            tree_data = tree_res.json()
            if "tree" in tree_data:
                all_files = [
                    item["path"]
                    for item in tree_data["tree"]
                    if item.get("type") == "blob"
                ]
                file_tree = "\n".join(all_files[:500])

        # 4. Fetch Commit History to track file frequency changes
        frequently_edited_files = []
        try:
            commits_url = (
                f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=15"
            )
            commits_res = await client.get(commits_url, headers=headers)
            if commits_res.status_code == 200:
                commits = commits_res.json()
                if isinstance(commits, list):
                    commit_shas = [c["sha"] for c in commits[:8] if c.get("sha")]

                    async def get_commit_files(sha: str) -> List[str]:
                        try:
                            url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
                            res = await client.get(url, headers=headers)
                            if res.status_code == 200:
                                c_detail = res.json()
                                return [
                                    f["filename"]
                                    for f in c_detail.get("files", [])
                                    if f.get("filename")
                                ]
                        except Exception as e:
                            logger.error(
                                f"Error fetching commit details for {sha}: {e}"
                            )
                        return []

                    files_modified_lists = await asyncio.gather(
                        *(get_commit_files(sha) for sha in commit_shas)
                    )
                    file_frequency: Dict[str, int] = {}
                    for lst in files_modified_lists:
                        for f in lst:
                            if f:
                                file_frequency[f] = file_frequency.get(f, 0) + 1

                    trivial_pattern = re.compile(
                        r"node_modules|package-lock\.json|yarn\.lock|pnpm-lock\.yaml|Cargo\.lock|\.(png|jpe?g|gif|svg|ico|webp|woff2?|ttf|eot|pdf|zip|gz)$",
                        re.IGNORECASE,
                    )
                    sorted_freq_files = sorted(
                        [
                            f
                            for f in file_frequency.keys()
                            if not trivial_pattern.search(f)
                        ],
                        key=lambda x: file_frequency[x],
                        reverse=True,
                    )
                    frequently_edited_files = sorted_freq_files
        except Exception as e:
            logger.error(f"Failed to scan frequently edited files: {e}")

        # 5. Extract significant files in the root folder
        root_pattern = re.compile(
            r"^\.(gitignore|eslint|prettier|env|npmrc|babelrc|github|vscode|dockerignore)|license|lock|yaml|yml|md$",
            re.IGNORECASE,
        )
        root_files = [
            f for f in all_files if "/" not in f and not root_pattern.search(f)
        ]

        # 6. Merge candidates
        candidates_set = set()
        for f in frequently_edited_files[:6]:
            candidates_set.add(f)

        for f in root_files:
            if len(candidates_set) >= 10:
                break
            candidates_set.add(f)

        interesting_patterns = [
            re.compile(r"^package\.json$"),
            re.compile(r"^requirements\.txt$"),
            re.compile(r"^Cargo\.toml$"),
            re.compile(r"^tsconfig\.json$"),
            re.compile(r"^tailwind\.config\.(js|ts)$"),
            re.compile(r"^next\.config\.(js|ts|mjs)$"),
            re.compile(r"^(src/|app/)?(layout|page|App|main|index)\.(tsx|ts|jsx|js)$"),
            re.compile(r"^docker-compose\.yml$"),
        ]

        important_configs = [
            f for f in all_files if any(pat.search(f) for pat in interesting_patterns)
        ]
        for f in important_configs:
            if len(candidates_set) >= 12:
                break
            candidates_set.add(f)

        selected_files = list(candidates_set)[:10]

        # 7. Fetch file content for candidates (up to 3000 chars)
        file_contents_context = ""
        for file_path in selected_files:
            try:
                url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}?ref={default_branch}"
                res = await client.get(url, headers=headers)
                if res.status_code == 200:
                    c_data = res.json()
                    if "content" in c_data:
                        text = base64.b64decode(c_data["content"]).decode(
                            "utf-8", errors="replace"
                        )
                        file_contents_context += (
                            f"\n--- {file_path} ---\n{text[:3000]}\n"
                        )
            except Exception as e:
                logger.error(f"Failed to fetch content for {file_path}: {e}")

        # 8. Fetch file content for manualFiles (up to 4000 chars)
        manual_contents_context = ""
        if body.manualFiles:
            for file_path in body.manualFiles[:10]:
                try:
                    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}?ref={default_branch}"
                    res = await client.get(url, headers=headers)
                    if res.status_code == 200:
                        c_data = res.json()
                        if "content" in c_data:
                            text = base64.b64decode(c_data["content"]).decode(
                                "utf-8", errors="replace"
                            )
                            manual_contents_context += f"\n--- [MANUALLY HIGHLIGHTED] {file_path} ---\n{text[:4000]}\n"
                except Exception as e:
                    logger.error(
                        f"Failed to fetch content for manual file {file_path}: {e}"
                    )

    # 9. Prompt constraints mapping
    style = body.style
    if style == "minimalist":
        style_instruction = (
            "STYLE REQUIREMENT: MINIMALIST\n"
            "Ensure the generated prompt is concise, brief, and highly direct. Avoid long files lists, "
            "excessive architectural design sections, or general boilerplate instructions. Focus exclusively "
            "on the primary purpose, key functional expectations, clean core mechanics, and baseline layout. "
            "It should feel lightweight yet complete."
        )
    elif style == "developer-focus":
        style_instruction = (
            "STYLE REQUIREMENT: DEVELOPER-FOCUS\n"
            "Ensure the generated prompt is highly technical and developer-focused. Focus on exact architectural structures, "
            "file layout mappings, library configurations, specific dependencies, database rules/schemas (if applicable), "
            "raw API specs/endpoints, strict type safety, clean coding directives, and low-level specifications useful for "
            "junior/mid-level engineers. Avoid high-level conceptual summaries."
        )
    else:
        style_instruction = (
            "STYLE REQUIREMENT: DETAILED/ARCHITECTURAL\n"
            "Ensure the generated prompt is in a detailed, blueprint-grade architectural style. Systematically cover "
            "high-level system architecture patterns (e.g., modular monolith, clean architecture), folder mapping rules, "
            "comprehensive functional requirements, data workflows, security boundaries, and step-by-step implementation milestones. "
            "Explain both standard features and the architectural design reasoning."
        )

    prompt_text = (
        'I need you to "reverse engineer" a GitHub repository and generate a synthetic prompt that someone '
        "could use to create this exact repository using an AI coding assistant.\n\n"
        f"Here is the context about the repository:\n"
        f"Repository: {owner}/{repo}\n"
        f"Description: {repo_data.get('description') or 'No description'}\n"
        f"Primary Language: {repo_data.get('language') or 'Unknown'}\n\n"
        f"File Tree (Top 500 files):\n{file_tree if file_tree else 'Could not fetch file tree.'}\n\n"
    )

    if manual_contents_context:
        prompt_text += (
            "### HIGH PRIORITY - Specific Files Manually Selected By User For Analysis:\n"
            "The user explicitly requested that the following file contents be included and thoroughly "
            "integrated in the generated system prompt. Focus on extracting exact types, schemas, state logic, and APIs from them:\n"
            f"{manual_contents_context}\n\n"
        )

    prompt_text += (
        f"Key Representative Files (Top Frequently Edited & Root Configurations):\n"
        f"{file_contents_context if file_contents_context else 'No key file contents could be fetched.'}\n\n"
        f"README Content:\n{readme_text if readme_text else 'No README found.'}\n\n"
        f"Task Constraints Based on Style Selection:\n{style_instruction}\n\n"
        "Task:\nWrite a comprehensive natural language prompt based on the style constraints detailed above that someone "
        "would feed into an AI coding assistant to create a similar project from scratch. The prompt should specify "
        "the tech stack, the main features, file structure requirements, and any specific styling choices inferred from the README "
        "or file tree. Format the output clearly. Output *only* the synthetic prompt itself, do not include introductory text like "
        '"Here is the prompt:".'
    )

    try:
        response_text = await generate_gemini_content(
            prompt=prompt_text,
            model=body.model,
            api_key=gemini_key,
            system_instruction="You are an expert software architect and prompt engineer.",
        )
    except Exception as e:
        logger.exception("Failed to query Gemini in analyze")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to generate prompt due to an API error: {str(e)}",
        )

    return {
        "prompt": response_text or "Failed to generate prompt.",
        "metadata": {
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
            "ownerAvatar": repo_data.get("owner", {}).get("avatar_url", ""),
            "language": repo_data.get("language", "Unknown"),
            "license": (
                repo_data.get("license", {}).get("spdx_id")
                if repo_data.get("license")
                else "No License"
            ),
            "owner": repo_data.get("owner", {}).get("login", owner),
            "repo": repo_data.get("name", repo),
        },
    }


@router.post("/adapt")
async def adapt_prompt(
    body: AdaptRequest, user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Modifies a reverse-engineered system prompt to adapt to a new tech stack or description."""
    gemini_key = body.apiKey or settings.gemini_api_key
    if gemini_key:
        gemini_key = gemini_key.strip().strip("\"'")
    if not gemini_key or gemini_key == "MY_GEMINI_API_KEY":
        raise HTTPException(
            status_code=400, detail="Gemini API Key is invalid or missing."
        )

    prompt_text = (
        "You are an expert software architect. Below is a system prompt that was reverse-engineered "
        "from an existing GitHub repository.\n\n"
        f"Original Repo Prompt:\n{body.originalPrompt}\n\n"
        "The user wants to build a NEW application based on this architecture, but with the following changes:\n"
        f"New App Description: {body.newAppDescription or 'Keep the same core domain but update the tech stack as requested.'}\n"
        f"Technology Changes: {body.techStackChanges or 'None specified.'}\n\n"
        'Task:\nRewrite the "Original Repo Prompt" so that it now instructs an AI coding assistant to build this new '
        "application using the changed technologies. Maintain the same level of detail, file structure requirements "
        "(adapted for the new tech stack), and professional tone.\n"
        "Output *only* the new synthetic prompt itself, do not include introductory text."
    )

    try:
        response_text = await generate_gemini_content(
            prompt=prompt_text,
            model=body.model,
            api_key=gemini_key,
            system_instruction="You are an expert software architect and prompt engineer.",
        )
    except Exception as e:
        logger.exception("Failed to query Gemini in adapt")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to generate adapted prompt due to an API error: {str(e)}",
        )

    return {"prompt": response_text or "Failed to generate prompt."}


@router.post("/refine")
async def refine_prompt(
    body: RefineRequest, user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    """Refines a system prompt based on developer feedback and rating scores."""
    if not body.originalPrompt:
        raise HTTPException(status_code=400, detail="Original prompt is required.")

    gemini_key = body.apiKey or settings.gemini_api_key
    if gemini_key:
        gemini_key = gemini_key.strip().strip("\"'")
    if not gemini_key or gemini_key == "MY_GEMINI_API_KEY":
        raise HTTPException(
            status_code=400, detail="Gemini API Key is invalid or missing."
        )

    tag_bullet_list = (
        "Selected Feedback Tags:\n" + "\n".join(f"- {tag}" for tag in body.feedbackTags)
        if body.feedbackTags
        else "No tags selected."
    )
    written_comment = (
        f'User Custom Feedback:\n"{body.feedbackText.strip()}"'
        if body.feedbackText.strip()
        else "No separate custom comments."
    )

    prompt_text = (
        "You are a software architect and system prompt engineer.\n"
        "Below is a reverse-engineered system prompt generated from a repository.\n"
        f"The user rated the accuracy of this prompt: {body.rating}/5.\n\n"
        f"{tag_bullet_list}\n\n"
        f"{written_comment}\n\n"
        f"Original Reverse-Engineered Prompt:\n"
        "---\n"
        f"{body.originalPrompt}\n"
        "---\n\n"
        "Task:\nPlease slightly adjust and rewrite the Original Reverse-Engineered Prompt to address the user's feedback, issues, and ratings.\n"
        '- If the feedback highlights that it is "too simple", explain file layouts, configurations, and core features in additional detail.\n'
        '- If it says "missed key technologies", evaluate what technology details might be missing and describe them thoroughly (add instructions for configs, styling library defaults, or data flow).\n'
        '- If it says "overly complex", refine and streamline unnecessary blocks.\n'
        "- Otherwise, incorporate any written instructions cleanly without replacing correct and valid instructions in the original.\n\n"
        "Maintain the professional system prompt style, clear hierarchy, and technical clarity.\n"
        "Output *only* the final updated synthetic prompt. No conversational headers, explanations, or meta-introductions of any kind. Just the prompt itself."
    )

    try:
        response_text = await generate_gemini_content(
            prompt=prompt_text,
            model=body.model,
            api_key=gemini_key,
            system_instruction="You are an expert software architect and prompt engineer specialized in refinement workflows.",
        )
    except Exception as e:
        logger.exception("Failed to query Gemini in refine")
        raise HTTPException(
            status_code=400,
            detail=f"Failed to refine prompt due to an API error: {str(e)}",
        )

    return {"prompt": response_text or "Failed to refine prompt."}
