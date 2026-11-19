from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, DBDep, require_permissions
from app.core.exceptions import AppError
from app.schemas.ai import (
    AIModelConfigCreate,
    AIModelConfigRead,
    AIModelConfigUpdate,
    AIUsageSummary,
    ChatRequest,
    ChatResponse,
    ProviderOption,
)
from app.schemas.common import MessageResponse
from app.services.ai import AIService

router = APIRouter(prefix="/ai", tags=["AI 模型网关"])

# 模型配置涉及 API Key，只让有系统配置权限的人管；对话权限走 ai:chat
ManageAI = Annotated[CurrentUser, Depends(require_permissions("system:config"))]
ChatAI = Annotated[CurrentUser, Depends(require_permissions("ai:chat"))]


@router.get("/providers", response_model=list[ProviderOption], summary="内置模型厂商")
async def list_providers(current: ChatAI) -> list[ProviderOption]:
    """前端下拉用：厂商、默认端点、默认模型、是否需要 Key。"""
    return AIService.providers()


@router.get("/models", response_model=list[AIModelConfigRead], summary="模型配置列表")
async def list_model_configs(current: ManageAI, db: DBDep) -> list[AIModelConfigRead]:
    return await AIService(db).list_configs(current.organization_id)


@router.post(
    "/models",
    response_model=AIModelConfigRead,
    status_code=status.HTTP_201_CREATED,
    summary="新增模型配置",
)
async def create_model_config(
    payload: AIModelConfigCreate, current: ManageAI, db: DBDep
) -> AIModelConfigRead:
    return await AIService(db).create_config(current.organization_id, payload)


@router.get(
    "/models/{config_id}", response_model=AIModelConfigRead, summary="模型配置详情"
)
async def get_model_config(
    config_id: int, current: ManageAI, db: DBDep
) -> AIModelConfigRead:
    return await AIService(db).get_config(current.organization_id, config_id)


@router.put(
    "/models/{config_id}", response_model=AIModelConfigRead, summary="修改模型配置"
)
async def update_model_config(
    config_id: int, payload: AIModelConfigUpdate, current: ManageAI, db: DBDep
) -> AIModelConfigRead:
    return await AIService(db).update_config(
        current.organization_id, config_id, payload
    )


@router.delete(
    "/models/{config_id}", response_model=MessageResponse, summary="删除模型配置"
)
async def delete_model_config(
    config_id: int, current: ManageAI, db: DBDep
) -> MessageResponse:
    await AIService(db).delete_config(current.organization_id, config_id)
    return MessageResponse(message="模型配置已删除")


@router.post("/chat", response_model=ChatResponse, summary="对话（非流式）")
async def chat(
    payload: ChatRequest, current: ChatAI, db: DBDep
) -> ChatResponse:
    return await AIService(db).chat(current.organization_id, current.id, payload)


@router.post("/chat/stream", summary="对话（流式 SSE）")
async def chat_stream(payload: ChatRequest, current: ChatAI, db: DBDep):
    service = AIService(db)
    # 检索在流开始前完成，先把引用推给前端，再逐字输出
    token_stream, citations = await service.stream_chat(
        current.organization_id, current.id, payload
    )

    async def event_source():
        try:
            if citations:
                payload_json = json.dumps(
                    {"citations": [item.model_dump() for item in citations]},
                    ensure_ascii=False,
                )
                yield f"data: {payload_json}\n\n"
            async for text in token_stream:
                yield f"data: {json.dumps({'delta': text}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        except AppError as exc:
            # 响应头已发出，不能再走全局异常处理器，只能以事件形式回传
            yield f"data: {json.dumps({'error': exc.message, 'code': exc.code}, ensure_ascii=False)}\n\n"
        except Exception as exc:  # noqa: BLE001
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/usage", response_model=AIUsageSummary, summary="AI 用量统计")
async def usage_summary(
    current: ManageAI,
    db: DBDep,
    days: int = Query(default=7, ge=1, le=90, description="统计最近多少天"),
) -> AIUsageSummary:
    return await AIService(db).usage_summary(current.organization_id, days)
