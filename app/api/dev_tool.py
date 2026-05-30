"""
Dev AI toolbox REST API — AI completions and user persistence.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, NoReturn, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import delete, select

from app.core.auth import get_current_user
from app.database.sqlalchemy import AsyncSessionLocal
from app.models.dev_tool import (
    DevToolIconHistoryModel,
    DevToolMemoryModel,
    DevToolRegexHistoryModel,
)
from app.services.dev_tool.gemini_client import DevToolGeminiClient
from app.services.dev_tool.html_fetch import (
    parse_page_assets,
)
from app.services.storage_service import get_storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dev-tool", tags=["DevTool"])

_gemini = DevToolGeminiClient()


def _owner_id(user: dict) -> str:
    oid = user.get("sub") or user.get("id")
    if not oid:
        raise HTTPException(status_code=401, detail="Invalid user")
    return str(oid)


def _raise_gemini_error(e: Exception) -> NoReturn:
    if isinstance(e, ValueError):
        raise HTTPException(status_code=400, detail=str(e)) from e
    logger.exception("Dev tool Gemini error")
    raise HTTPException(status_code=500, detail=str(e)) from e


class TextBody(BaseModel):
    text: str = ""


class MinifyBody(BaseModel):
    code: str
    language: str = "JavaScript"


class CheatsheetBody(BaseModel):
    topic: str


class RegexGenerateBody(BaseModel):
    description: str


class RegexExplainBody(BaseModel):
    regex: str


class JsonToTypeBody(BaseModel):
    json_string: str = Field(alias="jsonString")
    type_system: str = Field(default="TypeScript", alias="typeSystem")
    root_type_name: str = Field(default="RootType", alias="rootTypeName")

    model_config = {"populate_by_name": True}


class RefactorBody(BaseModel):
    code: str
    language: str = "JavaScript"
    instructions: str = ""


class PromptBody(BaseModel):
    prompt: str


class CetoBody(BaseModel):
    topic: str


class WebsiteAnalyzeBody(BaseModel):
    html: str
    url: Optional[str] = None


class MemoryTitleBody(BaseModel):
    content: str
    type: str = "text"


class MemoryCreateBody(BaseModel):
    type: str  # text | url | file
    content: str
    title: Optional[str] = None


class RegexHistoryCreateBody(BaseModel):
    mode: str
    input: str
    regex: Optional[str] = None
    explanation: str


class IconHistoryCreateBody(BaseModel):
    source_storage_path: str = Field(alias="sourceStoragePath")
    source_image_url: Optional[str] = Field(default=None, alias="sourceImageUrl")

    model_config = {"populate_by_name": True}


@router.post("/minify")
async def dev_tool_minify(
    body: MinifyBody, user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    try:
        text = await _gemini.minify_code(body.code, body.language)
        return {"text": text}
    except Exception as e:
        _raise_gemini_error(e)


@router.post("/cheatsheet")
async def dev_tool_cheatsheet(
    body: CheatsheetBody, user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    try:
        text = await _gemini.generate_cheatsheet(body.topic)
        return {"text": text}
    except Exception as e:
        _raise_gemini_error(e)


@router.post("/regex/generate")
async def dev_tool_regex_generate(
    body: RegexGenerateBody, user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    try:
        result = await _gemini.generate_and_explain_regex(body.description)
        return result
    except Exception as e:
        _raise_gemini_error(e)


@router.post("/regex/explain")
async def dev_tool_regex_explain(
    body: RegexExplainBody, user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    try:
        text = await _gemini.explain_regex(body.regex)
        return {"text": text}
    except Exception as e:
        _raise_gemini_error(e)


@router.post("/json-to-type")
async def dev_tool_json_to_type(
    body: JsonToTypeBody, user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    try:
        text = await _gemini.generate_types(
            body.json_string, body.type_system, body.root_type_name
        )
        return {"text": text}
    except Exception as e:
        _raise_gemini_error(e)


@router.post("/refactor")
async def dev_tool_refactor(
    body: RefactorBody, user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    try:
        text = await _gemini.refactor_code(body.code, body.language, body.instructions)
        return {"text": text}
    except Exception as e:
        _raise_gemini_error(e)


@router.post("/prompt/enhance")
async def dev_tool_prompt_enhance(
    body: PromptBody, user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    try:
        text = await _gemini.enhance_prompt(body.prompt)
        return {"text": text}
    except Exception as e:
        _raise_gemini_error(e)


@router.post("/prompt/ceto")
async def dev_tool_prompt_ceto(
    body: CetoBody, user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    try:
        text = await _gemini.generate_ceto_prompts(body.topic)
        return {"text": text}
    except Exception as e:
        _raise_gemini_error(e)


@router.post("/website/analyze")
async def dev_tool_website_analyze(
    body: WebsiteAnalyzeBody, user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    try:
        generated = await _gemini.generate_code_from_html(body.html)
        parsed = parse_page_assets(body.html, body.url or "https://example.com")
        return {
            "generatedCode": generated,
            "assets": parsed.get("assets", {}),
            "pageInfo": parsed.get("pageInfo", {}),
        }
    except Exception as e:
        _raise_gemini_error(e)


@router.post("/memory/title")
async def dev_tool_memory_title(
    body: MemoryTitleBody, user: dict = Depends(get_current_user)
) -> Dict[str, str]:
    try:
        title = await _gemini.generate_memory_title(body.content, body.type)
        return {"title": title}
    except Exception as e:
        _raise_gemini_error(e)


# --- Memories CRUD ---


@router.get("/memories")
async def list_memories(user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    owner = _owner_id(user)
    async with AsyncSessionLocal() as session:
        stmt = (
            select(DevToolMemoryModel)
            .where(DevToolMemoryModel.owner_id == owner)
            .order_by(DevToolMemoryModel.created_at.desc())
        )
        rows = (await session.execute(stmt)).scalars().all()
    return {"items": [r.to_dict() for r in rows]}


@router.post("/memories")
async def create_memory(
    body: MemoryCreateBody, user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    owner = _owner_id(user)
    title = body.title
    if not title:
        try:
            title = await _gemini.generate_memory_title(body.content, body.type)
        except Exception:
            title = "Untitled Memory"
    row = DevToolMemoryModel(
        id=str(uuid.uuid4()),
        owner_id=owner,
        type=body.type,
        title=title or "Untitled Memory",
        content=body.content,
    )
    async with AsyncSessionLocal() as session:
        session.add(row)
        await session.commit()
        await session.refresh(row)
    return row.to_dict()


@router.delete("/memories/{memory_id}")
async def delete_memory(
    memory_id: str, user: dict = Depends(get_current_user)
) -> Dict[str, bool]:
    owner = _owner_id(user)
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(DevToolMemoryModel).where(
                DevToolMemoryModel.id == memory_id,
                DevToolMemoryModel.owner_id == owner,
            )
        )
        await session.commit()
    return {"success": True}


# --- Regex history CRUD ---


@router.get("/regex-history")
async def list_regex_history(
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    owner = _owner_id(user)
    async with AsyncSessionLocal() as session:
        stmt = (
            select(DevToolRegexHistoryModel)
            .where(DevToolRegexHistoryModel.owner_id == owner)
            .order_by(DevToolRegexHistoryModel.created_at.desc())
            .limit(20)
        )
        rows = (await session.execute(stmt)).scalars().all()
    return {"items": [r.to_dict() for r in rows]}


@router.post("/regex-history")
async def create_regex_history(
    body: RegexHistoryCreateBody, user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    owner = _owner_id(user)
    row = DevToolRegexHistoryModel(
        id=str(uuid.uuid4()),
        owner_id=owner,
        mode=body.mode,
        input=body.input,
        regex=body.regex,
        explanation=body.explanation,
    )
    async with AsyncSessionLocal() as session:
        session.add(row)
        await session.commit()
        await session.refresh(row)
    return row.to_dict()


@router.delete("/regex-history/{item_id}")
async def delete_regex_history(
    item_id: str, user: dict = Depends(get_current_user)
) -> Dict[str, bool]:
    owner = _owner_id(user)
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(DevToolRegexHistoryModel).where(
                DevToolRegexHistoryModel.id == item_id,
                DevToolRegexHistoryModel.owner_id == owner,
            )
        )
        await session.commit()
    return {"success": True}


# --- Icon history CRUD ---


@router.get("/icon-history")
async def list_icon_history(
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    owner = _owner_id(user)
    async with AsyncSessionLocal() as session:
        stmt = (
            select(DevToolIconHistoryModel)
            .where(DevToolIconHistoryModel.owner_id == owner)
            .order_by(DevToolIconHistoryModel.created_at.desc())
        )
        rows = (await session.execute(stmt)).scalars().all()
    return {"items": [r.to_dict() for r in rows]}


@router.post("/icon-history")
async def create_icon_history(
    body: IconHistoryCreateBody, user: dict = Depends(get_current_user)
) -> Dict[str, Any]:
    owner = _owner_id(user)
    row = DevToolIconHistoryModel(
        id=str(uuid.uuid4()),
        owner_id=owner,
        source_storage_path=body.source_storage_path,
        source_image_url=body.source_image_url,
    )
    async with AsyncSessionLocal() as session:
        session.add(row)
        await session.commit()
        await session.refresh(row)
    return row.to_dict()


@router.delete("/icon-history/{item_id}")
async def delete_icon_history(
    item_id: str, user: dict = Depends(get_current_user)
) -> Dict[str, bool]:
    owner = _owner_id(user)
    async with AsyncSessionLocal() as session:
        await session.execute(
            delete(DevToolIconHistoryModel).where(
                DevToolIconHistoryModel.id == item_id,
                DevToolIconHistoryModel.owner_id == owner,
            )
        )
        await session.commit()
    return {"success": True}


@router.post("/upload")
async def dev_tool_upload(
    file: UploadFile = File(...),
    subpath: str = Form(default="icons"),
    user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Upload a file to user storage under dev-tool/{subpath}/."""
    owner = _owner_id(user)
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large (max 5MB)")
    safe_name = (file.filename or "upload.bin").replace("..", "").replace("/", "_")
    rel = f"dev-tool/{subpath}/{uuid.uuid4().hex}_{safe_name}"
    file_path = f"{owner}/{rel}"
    storage = get_storage_service(use_admin=False)
    content_type = file.content_type or "application/octet-stream"
    result = storage.upload_file(
        bucket_type="uploads",
        file_path=file_path,
        file_data=data,
        content_type=content_type,
    )
    if not result:
        raise HTTPException(status_code=500, detail="Upload failed")
    signed = storage.create_signed_url("uploads", result, expires_in=3600)
    public = storage.get_public_url("uploads", result)
    return {
        "path": result,
        "signed_url": signed,
        "public_url": public,
    }
