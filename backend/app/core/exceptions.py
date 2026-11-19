from __future__ import annotations

from typing import Any


class AppError(Exception):
    """业务异常基类。

    统一由 main.py 中的异常处理器转换为 {code, message, detail} 结构，
    便于前端做统一的错误提示。
    """

    status_code: int = 400
    code: str = "bad_request"

    def __init__(
        self,
        message: str = "请求错误",
        *,
        code: str | None = None,
        status_code: int | None = None,
        detail: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        self.detail = detail


class AuthError(AppError):
    status_code = 401
    code = "unauthorized"

    def __init__(self, message: str = "未认证或登录已过期", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class PermissionDenied(AppError):
    status_code = 403
    code = "forbidden"

    def __init__(self, message: str = "没有访问该资源的权限", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"

    def __init__(self, message: str = "资源不存在", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class ConflictError(AppError):
    status_code = 409
    code = "conflict"

    def __init__(self, message: str = "资源冲突", **kwargs: Any) -> None:
        super().__init__(message, **kwargs)


class BadRequestError(AppError):
    status_code = 400
    code = "bad_request"
