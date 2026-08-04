from typing import Any


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "BUSINESS_ERROR",
        status_code: int = 400,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


class NotFoundError(AppError):
    def __init__(self, message: str = "资源不存在", *, details: Any = None) -> None:
        super().__init__(
            message,
            code="NOT_FOUND",
            status_code=404,
            details=details,
        )


class AuthenticationError(AppError):
    def __init__(self, message: str = "认证失败") -> None:
        super().__init__(message, code="UNAUTHORIZED", status_code=401)


class AuthorizationError(AppError):
    def __init__(self, message: str = "没有操作权限") -> None:
        super().__init__(message, code="FORBIDDEN", status_code=403)


class ConflictError(AppError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="CONFLICT", status_code=409)
