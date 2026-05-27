import asyncio
from typing import Any, Optional
from uuid import uuid4

from fastapi import Body, FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from qiskit_aqt_provider.api_client.models_direct import JobResultError, JobResultFinished

app = FastAPI()
_requests: list[dict[str, Any]] = []


def _default_direct_access_state() -> dict[str, Any]:
    return {
        "name": "direct-device",
        "num_ions": 4,
        "result_delay_seconds": 0.0,
        "submit_error_status": None,
        "queued_results": [],
    }


_direct_access_state = _default_direct_access_state()


def _record_request(request: Request, body: Optional[Any] = None) -> None:
    _requests.append(
        {
            "method": request.method,
            "path": request.url.path,
            "headers": dict(request.headers),
            "query": dict(request.query_params),
            "client": request.client.host if request.client else None,
            "body": jsonable_encoder(body) if body is not None else None,
        }
    )


@app.get("/health")
async def health() -> Any:
    return {"status": "ok"}


@app.get("/status/ions")
async def direct_status_ions(request: Request) -> Any:
    _record_request(request)
    return JSONResponse(content={"num_ions": _direct_access_state["num_ions"]})


@app.get("/system/name")
async def direct_system_name(request: Request) -> Any:
    _record_request(request)
    return JSONResponse(content=_direct_access_state["name"])


@app.put("/circuit")
async def direct_submit_circuit(request: Request, body: dict[str, Any] = Body(...)) -> Any:
    _record_request(request, body)

    submit_error_status = _direct_access_state["submit_error_status"]
    if submit_error_status is not None:
        return JSONResponse(status_code=submit_error_status, content={"detail": "submit failed"})

    return JSONResponse(content=str(uuid4()))


@app.get("/circuit/result/{job_id}")
async def direct_circuit_result(job_id: str, request: Request) -> Any:
    _record_request(request)

    result_delay_seconds = float(_direct_access_state["result_delay_seconds"])
    if result_delay_seconds > 0.0:
        await asyncio.sleep(result_delay_seconds)

    queued_results: list[JobResultError | JobResultFinished] = _direct_access_state["queued_results"]
    if queued_results:
        payload = queued_results.pop(0).model_dump()
    else:
        return JSONResponse(status_code=404, content={"detail": "job not found"})

    return JSONResponse(
        content={
            "job_id": job_id,
            "payload": payload,
        }
    )


@app.get("/__requests")
async def get_requests() -> Any:
    return JSONResponse(_requests)


@app.post("/__clear")
async def clear_requests() -> Any:
    _requests.clear()
    return JSONResponse({"ok": True})


@app.post("/__direct/reset")
async def direct_reset(request: Request) -> Any:
    _record_request(request)
    _direct_access_state.clear()
    _direct_access_state.update(_default_direct_access_state())
    return JSONResponse({"ok": True})


@app.post("/__direct/config")
async def direct_config(request: Request, body: dict[str, Any]) -> Any:
    _record_request(request, body)

    if "name" in body:
        _direct_access_state["name"] = str(body["name"])
    if "num_ions" in body:
        _direct_access_state["num_ions"] = int(body["num_ions"])
    if "result_delay_seconds" in body:
        _direct_access_state["result_delay_seconds"] = float(body["result_delay_seconds"])
    if "submit_error_status" in body:
        _direct_access_state["submit_error_status"] = body["submit_error_status"]
    if "queued_results" in body:
        for result in list(body["queued_results"]):
            if result.get("status") == "finished":
                _direct_access_state["queued_results"].append(JobResultFinished.model_validate(result))
            else:
                _direct_access_state["queued_results"].append(JobResultError())

    return JSONResponse({"ok": True})
