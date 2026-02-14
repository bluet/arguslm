"""ArgusLM Python SDK client."""

from __future__ import annotations

import os
from types import TracebackType
from typing import Any
from uuid import UUID

import httpx

from arguslm.exceptions import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
)
from arguslm.schemas.alert import (
    AlertListResponse,
    AlertResponse,
    AlertRuleCreate,
    AlertRuleResponse,
    AlertRuleUpdate,
)
from arguslm.schemas.benchmark import (
    BenchmarkCreate,
    BenchmarkDetailResponse,
    BenchmarkListResponse,
    BenchmarkResultListResponse,
    BenchmarkStartResponse,
)
from arguslm.schemas.model import (
    ModelCreate,
    ModelListResponse,
    ModelResponse,
    ModelUpdate,
)
from arguslm.schemas.monitoring import (
    MonitoringConfigResponse,
    MonitoringConfigUpdate,
    MonitoringRunResponse,
    PromptPackResponse,
    UptimeHistoryResponse,
)
from arguslm.schemas.provider import (
    ProviderCatalogResponse,
    ProviderCreate,
    ProviderListResponse,
    ProviderRefreshResponse,
    ProviderResponse,
    ProviderTestResponse,
    ProviderUpdate,
)

DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = httpx.Timeout(timeout=30.0, connect=5.0)
DEFAULT_MAX_RETRIES = 2

_RETRY_STATUS_CODES = frozenset({408, 409, 429, 500, 502, 503, 504})


class ArgusLMClient:
    """Synchronous client for the ArgusLM REST API.

    Usage::

        client = ArgusLMClient(base_url="http://localhost:8000")
        uptime = client.get_uptime_history(limit=10)
        client.close()

    Or as a context manager::

        with ArgusLMClient() as client:
            uptime = client.get_uptime_history()
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout: float | httpx.Timeout | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: httpx.Client | None = None,
    ) -> None:
        if base_url is None:
            base_url = os.environ.get("ARGUSLM_BASE_URL", DEFAULT_BASE_URL)

        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries

        if http_client is not None:
            self._client = http_client
            self._owns_client = False
        else:
            self._client = httpx.Client(
                base_url=self._base_url,
                timeout=timeout if timeout is not None else DEFAULT_TIMEOUT,
            )
            self._owns_client = True

    def close(self) -> None:
        if self._owns_client and hasattr(self, "_client"):
            self._client.close()

    def __enter__(self) -> ArgusLMClient:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Internal request handling
    # ------------------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        request = self._client.build_request(method, path, json=json, params=_clean_params(params))

        last_exc: Exception | None = None
        for attempt in range(1 + self._max_retries):
            try:
                response = self._client.send(request)
            except httpx.TimeoutException:
                last_exc = APITimeoutError(request)
                continue
            except httpx.ConnectError as exc:
                last_exc = APIConnectionError(message=str(exc), request=request)
                continue

            if response.status_code >= 400:
                if response.status_code in _RETRY_STATUS_CODES and attempt < self._max_retries:
                    continue
                raise APIStatusError.from_response(response)

            return response

        raise last_exc  # type: ignore[misc]

    def _get(self, path: str, **kwargs: Any) -> httpx.Response:
        return self._request("GET", path, **kwargs)

    def _post(self, path: str, **kwargs: Any) -> httpx.Response:
        return self._request("POST", path, **kwargs)

    def _patch(self, path: str, **kwargs: Any) -> httpx.Response:
        return self._request("PATCH", path, **kwargs)

    def _delete(self, path: str, **kwargs: Any) -> httpx.Response:
        return self._request("DELETE", path, **kwargs)

    # ------------------------------------------------------------------
    # Monitoring
    # ------------------------------------------------------------------

    def get_monitoring_config(self) -> MonitoringConfigResponse:
        resp = self._get("/api/v1/monitoring/config")
        return MonitoringConfigResponse.model_validate(resp.json())

    def update_monitoring_config(self, config: MonitoringConfigUpdate) -> MonitoringConfigResponse:
        resp = self._patch(
            "/api/v1/monitoring/config",
            json=config.model_dump(exclude_none=True),
        )
        return MonitoringConfigResponse.model_validate(resp.json())

    def run_monitoring(self) -> MonitoringRunResponse:
        resp = self._post("/api/v1/monitoring/run")
        return MonitoringRunResponse.model_validate(resp.json())

    def get_uptime_history(
        self,
        *,
        model_id: UUID | str | None = None,
        status: str | None = None,
        since: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> UptimeHistoryResponse:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if model_id is not None:
            params["model_id"] = str(model_id)
        if status is not None:
            params["status"] = status
        if since is not None:
            params["since"] = since

        resp = self._get("/api/v1/monitoring/uptime", params=params)
        return UptimeHistoryResponse.model_validate(resp.json())

    def list_prompt_packs(self) -> list[PromptPackResponse]:
        resp = self._get("/api/v1/monitoring/prompt-packs")
        return [PromptPackResponse.model_validate(p) for p in resp.json()]

    # ------------------------------------------------------------------
    # Benchmarks
    # ------------------------------------------------------------------

    def start_benchmark(self, benchmark: BenchmarkCreate) -> BenchmarkStartResponse:
        resp = self._post(
            "/api/v1/benchmarks",
            json=benchmark.model_dump(mode="json"),
        )
        return BenchmarkStartResponse.model_validate(resp.json())

    def list_benchmarks(self, *, page: int = 1, per_page: int = 20) -> BenchmarkListResponse:
        resp = self._get(
            "/api/v1/benchmarks",
            params={"page": page, "per_page": per_page},
        )
        return BenchmarkListResponse.model_validate(resp.json())

    def get_benchmark(self, run_id: UUID | str) -> BenchmarkDetailResponse:
        resp = self._get(f"/api/v1/benchmarks/{run_id}")
        return BenchmarkDetailResponse.model_validate(resp.json())

    def get_benchmark_results(self, run_id: UUID | str) -> BenchmarkResultListResponse:
        resp = self._get(f"/api/v1/benchmarks/{run_id}/results")
        return BenchmarkResultListResponse.model_validate(resp.json())

    # ------------------------------------------------------------------
    # Providers
    # ------------------------------------------------------------------

    def list_providers(self) -> ProviderListResponse:
        resp = self._get("/api/v1/providers")
        return ProviderListResponse.model_validate(resp.json())

    def create_provider(self, provider: ProviderCreate) -> ProviderResponse:
        resp = self._post(
            "/api/v1/providers",
            json=provider.model_dump(mode="json"),
        )
        return ProviderResponse.model_validate(resp.json())

    def get_provider(self, provider_id: UUID | str) -> ProviderResponse:
        resp = self._get(f"/api/v1/providers/{provider_id}")
        return ProviderResponse.model_validate(resp.json())

    def update_provider(
        self,
        provider_id: UUID | str,
        update: ProviderUpdate,
    ) -> ProviderResponse:
        resp = self._patch(
            f"/api/v1/providers/{provider_id}",
            json=update.model_dump(exclude_none=True),
        )
        return ProviderResponse.model_validate(resp.json())

    def delete_provider(self, provider_id: UUID | str) -> None:
        self._delete(f"/api/v1/providers/{provider_id}")

    def test_provider_connection(self, provider: ProviderCreate) -> ProviderTestResponse:
        resp = self._post(
            "/api/v1/providers/test-connection",
            json=provider.model_dump(mode="json"),
        )
        return ProviderTestResponse.model_validate(resp.json())

    def test_existing_provider(self, provider_id: UUID | str) -> ProviderTestResponse:
        resp = self._post(f"/api/v1/providers/{provider_id}/test")
        return ProviderTestResponse.model_validate(resp.json())

    def refresh_provider_models(self, provider_id: UUID | str) -> ProviderRefreshResponse:
        resp = self._post(f"/api/v1/providers/{provider_id}/refresh-models")
        return ProviderRefreshResponse.model_validate(resp.json())

    def get_provider_catalog(self) -> ProviderCatalogResponse:
        resp = self._get("/api/v1/providers/catalog")
        return ProviderCatalogResponse.model_validate(resp.json())

    # ------------------------------------------------------------------
    # Models
    # ------------------------------------------------------------------

    def list_models(
        self,
        *,
        provider_id: UUID | str | None = None,
        enabled_for_monitoring: bool | None = None,
        enabled_for_benchmark: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ModelListResponse:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if provider_id is not None:
            params["provider_account_id"] = str(provider_id)
        if enabled_for_monitoring is not None:
            params["enabled_for_monitoring"] = enabled_for_monitoring
        if enabled_for_benchmark is not None:
            params["enabled_for_benchmark"] = enabled_for_benchmark

        resp = self._get("/api/v1/models", params=params)
        return ModelListResponse.model_validate(resp.json())

    def create_model(self, model: ModelCreate) -> ModelResponse:
        resp = self._post(
            "/api/v1/models",
            json=model.model_dump(mode="json"),
        )
        return ModelResponse.model_validate(resp.json())

    def update_model(
        self,
        model_id: UUID | str,
        update: ModelUpdate,
    ) -> ModelResponse:
        resp = self._patch(
            f"/api/v1/models/{model_id}",
            json=update.model_dump(exclude_none=True),
        )
        return ModelResponse.model_validate(resp.json())

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------

    def list_alert_rules(self) -> list[AlertRuleResponse]:
        resp = self._get("/api/v1/alerts/rules")
        return [AlertRuleResponse.model_validate(r) for r in resp.json()]

    def create_alert_rule(self, rule: AlertRuleCreate) -> AlertRuleResponse:
        resp = self._post(
            "/api/v1/alerts/rules",
            json=rule.model_dump(mode="json"),
        )
        return AlertRuleResponse.model_validate(resp.json())

    def update_alert_rule(
        self,
        rule_id: UUID | str,
        update: AlertRuleUpdate,
    ) -> AlertRuleResponse:
        resp = self._patch(
            f"/api/v1/alerts/rules/{rule_id}",
            json=update.model_dump(exclude_none=True),
        )
        return AlertRuleResponse.model_validate(resp.json())

    def delete_alert_rule(self, rule_id: UUID | str) -> None:
        self._delete(f"/api/v1/alerts/rules/{rule_id}")

    def list_alerts(
        self,
        *,
        acknowledged: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AlertListResponse:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if acknowledged is not None:
            params["acknowledged"] = acknowledged

        resp = self._get("/api/v1/alerts", params=params)
        return AlertListResponse.model_validate(resp.json())

    def acknowledge_alert(self, alert_id: UUID | str) -> AlertResponse:
        resp = self._patch(f"/api/v1/alerts/{alert_id}/acknowledge")
        return AlertResponse.model_validate(resp.json())


class AsyncArgusLMClient:
    """Asynchronous client for the ArgusLM REST API.

    Usage::

        async with AsyncArgusLMClient() as client:
            uptime = await client.get_uptime_history()
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        timeout: float | httpx.Timeout | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if base_url is None:
            base_url = os.environ.get("ARGUSLM_BASE_URL", DEFAULT_BASE_URL)

        self._base_url = base_url.rstrip("/")
        self._max_retries = max_retries

        if http_client is not None:
            self._client = http_client
            self._owns_client = False
        else:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=timeout if timeout is not None else DEFAULT_TIMEOUT,
            )
            self._owns_client = True

    async def close(self) -> None:
        if self._owns_client and hasattr(self, "_client"):
            await self._client.aclose()

    async def __aenter__(self) -> AsyncArgusLMClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Internal request handling
    # ------------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        request = self._client.build_request(method, path, json=json, params=_clean_params(params))

        last_exc: Exception | None = None
        for attempt in range(1 + self._max_retries):
            try:
                response = await self._client.send(request)
            except httpx.TimeoutException:
                last_exc = APITimeoutError(request)
                continue
            except httpx.ConnectError as exc:
                last_exc = APIConnectionError(message=str(exc), request=request)
                continue

            if response.status_code >= 400:
                if response.status_code in _RETRY_STATUS_CODES and attempt < self._max_retries:
                    continue
                raise APIStatusError.from_response(response)

            return response

        raise last_exc  # type: ignore[misc]

    async def _get(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self._request("GET", path, **kwargs)

    async def _post(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self._request("POST", path, **kwargs)

    async def _patch(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self._request("PATCH", path, **kwargs)

    async def _delete(self, path: str, **kwargs: Any) -> httpx.Response:
        return await self._request("DELETE", path, **kwargs)

    # ------------------------------------------------------------------
    # Monitoring
    # ------------------------------------------------------------------

    async def get_monitoring_config(self) -> MonitoringConfigResponse:
        resp = await self._get("/api/v1/monitoring/config")
        return MonitoringConfigResponse.model_validate(resp.json())

    async def update_monitoring_config(
        self, config: MonitoringConfigUpdate
    ) -> MonitoringConfigResponse:
        resp = await self._patch(
            "/api/v1/monitoring/config",
            json=config.model_dump(exclude_none=True),
        )
        return MonitoringConfigResponse.model_validate(resp.json())

    async def run_monitoring(self) -> MonitoringRunResponse:
        resp = await self._post("/api/v1/monitoring/run")
        return MonitoringRunResponse.model_validate(resp.json())

    async def get_uptime_history(
        self,
        *,
        model_id: UUID | str | None = None,
        status: str | None = None,
        since: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> UptimeHistoryResponse:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if model_id is not None:
            params["model_id"] = str(model_id)
        if status is not None:
            params["status"] = status
        if since is not None:
            params["since"] = since

        resp = await self._get("/api/v1/monitoring/uptime", params=params)
        return UptimeHistoryResponse.model_validate(resp.json())

    async def list_prompt_packs(self) -> list[PromptPackResponse]:
        resp = await self._get("/api/v1/monitoring/prompt-packs")
        return [PromptPackResponse.model_validate(p) for p in resp.json()]

    # ------------------------------------------------------------------
    # Benchmarks
    # ------------------------------------------------------------------

    async def start_benchmark(self, benchmark: BenchmarkCreate) -> BenchmarkStartResponse:
        resp = await self._post(
            "/api/v1/benchmarks",
            json=benchmark.model_dump(mode="json"),
        )
        return BenchmarkStartResponse.model_validate(resp.json())

    async def list_benchmarks(self, *, page: int = 1, per_page: int = 20) -> BenchmarkListResponse:
        resp = await self._get(
            "/api/v1/benchmarks",
            params={"page": page, "per_page": per_page},
        )
        return BenchmarkListResponse.model_validate(resp.json())

    async def get_benchmark(self, run_id: UUID | str) -> BenchmarkDetailResponse:
        resp = await self._get(f"/api/v1/benchmarks/{run_id}")
        return BenchmarkDetailResponse.model_validate(resp.json())

    async def get_benchmark_results(self, run_id: UUID | str) -> BenchmarkResultListResponse:
        resp = await self._get(f"/api/v1/benchmarks/{run_id}/results")
        return BenchmarkResultListResponse.model_validate(resp.json())

    # ------------------------------------------------------------------
    # Providers
    # ------------------------------------------------------------------

    async def list_providers(self) -> ProviderListResponse:
        resp = await self._get("/api/v1/providers")
        return ProviderListResponse.model_validate(resp.json())

    async def create_provider(self, provider: ProviderCreate) -> ProviderResponse:
        resp = await self._post(
            "/api/v1/providers",
            json=provider.model_dump(mode="json"),
        )
        return ProviderResponse.model_validate(resp.json())

    async def get_provider(self, provider_id: UUID | str) -> ProviderResponse:
        resp = await self._get(f"/api/v1/providers/{provider_id}")
        return ProviderResponse.model_validate(resp.json())

    async def update_provider(
        self,
        provider_id: UUID | str,
        update: ProviderUpdate,
    ) -> ProviderResponse:
        resp = await self._patch(
            f"/api/v1/providers/{provider_id}",
            json=update.model_dump(exclude_none=True),
        )
        return ProviderResponse.model_validate(resp.json())

    async def delete_provider(self, provider_id: UUID | str) -> None:
        await self._delete(f"/api/v1/providers/{provider_id}")

    async def test_provider_connection(self, provider: ProviderCreate) -> ProviderTestResponse:
        resp = await self._post(
            "/api/v1/providers/test-connection",
            json=provider.model_dump(mode="json"),
        )
        return ProviderTestResponse.model_validate(resp.json())

    async def test_existing_provider(self, provider_id: UUID | str) -> ProviderTestResponse:
        resp = await self._post(f"/api/v1/providers/{provider_id}/test")
        return ProviderTestResponse.model_validate(resp.json())

    async def refresh_provider_models(self, provider_id: UUID | str) -> ProviderRefreshResponse:
        resp = await self._post(f"/api/v1/providers/{provider_id}/refresh-models")
        return ProviderRefreshResponse.model_validate(resp.json())

    async def get_provider_catalog(self) -> ProviderCatalogResponse:
        resp = await self._get("/api/v1/providers/catalog")
        return ProviderCatalogResponse.model_validate(resp.json())

    # ------------------------------------------------------------------
    # Models
    # ------------------------------------------------------------------

    async def list_models(
        self,
        *,
        provider_id: UUID | str | None = None,
        enabled_for_monitoring: bool | None = None,
        enabled_for_benchmark: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> ModelListResponse:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if provider_id is not None:
            params["provider_account_id"] = str(provider_id)
        if enabled_for_monitoring is not None:
            params["enabled_for_monitoring"] = enabled_for_monitoring
        if enabled_for_benchmark is not None:
            params["enabled_for_benchmark"] = enabled_for_benchmark

        resp = await self._get("/api/v1/models", params=params)
        return ModelListResponse.model_validate(resp.json())

    async def create_model(self, model: ModelCreate) -> ModelResponse:
        resp = await self._post(
            "/api/v1/models",
            json=model.model_dump(mode="json"),
        )
        return ModelResponse.model_validate(resp.json())

    async def update_model(
        self,
        model_id: UUID | str,
        update: ModelUpdate,
    ) -> ModelResponse:
        resp = await self._patch(
            f"/api/v1/models/{model_id}",
            json=update.model_dump(exclude_none=True),
        )
        return ModelResponse.model_validate(resp.json())

    # ------------------------------------------------------------------
    # Alerts
    # ------------------------------------------------------------------

    async def list_alert_rules(self) -> list[AlertRuleResponse]:
        resp = await self._get("/api/v1/alerts/rules")
        return [AlertRuleResponse.model_validate(r) for r in resp.json()]

    async def create_alert_rule(self, rule: AlertRuleCreate) -> AlertRuleResponse:
        resp = await self._post(
            "/api/v1/alerts/rules",
            json=rule.model_dump(mode="json"),
        )
        return AlertRuleResponse.model_validate(resp.json())

    async def update_alert_rule(
        self,
        rule_id: UUID | str,
        update: AlertRuleUpdate,
    ) -> AlertRuleResponse:
        resp = await self._patch(
            f"/api/v1/alerts/rules/{rule_id}",
            json=update.model_dump(exclude_none=True),
        )
        return AlertRuleResponse.model_validate(resp.json())

    async def delete_alert_rule(self, rule_id: UUID | str) -> None:
        await self._delete(f"/api/v1/alerts/rules/{rule_id}")

    async def list_alerts(
        self,
        *,
        acknowledged: bool | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> AlertListResponse:
        params: dict[str, Any] = {"limit": limit, "offset": offset}
        if acknowledged is not None:
            params["acknowledged"] = acknowledged

        resp = await self._get("/api/v1/alerts", params=params)
        return AlertListResponse.model_validate(resp.json())

    async def acknowledge_alert(self, alert_id: UUID | str) -> AlertResponse:
        resp = await self._patch(f"/api/v1/alerts/{alert_id}/acknowledge")
        return AlertResponse.model_validate(resp.json())


def _clean_params(
    params: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if params is None:
        return None
    return {k: v for k, v in params.items() if v is not None}
