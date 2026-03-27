from datetime import datetime
from typing import Any

from aqt_connector.models.arnica.resources import ResourceStatus, ResourceType
from aqt_connector.models.arnica.response_bodies.resources import ResourceDetails, WorkspaceResource
from aqt_connector.models.arnica.response_bodies.workspaces import Workspace
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

app = FastAPI()
_requests = []


def _record_request(request: Request) -> None:
    _requests.append(
        {
            "method": request.method,
            "path": request.url.path,
            "headers": dict(request.headers),
            "query": dict(request.query_params),
            "client": request.client.host if request.client else None,
        }
    )


@app.get("/health")
async def health() -> Any:
    return {"status": "ok"}


@app.get("/v1/workspaces")
async def workspaces(request: Request) -> Any:
    _record_request(request)
    return JSONResponse(
        content=jsonable_encoder(
            [
                Workspace(
                    id="w1",
                    accepting_job_submissions=True,
                    jobs_being_processed=True,
                    resources=[
                        WorkspaceResource(id="r1", name="R1", type=ResourceType.DEVICE),
                        WorkspaceResource(id="r2", name="R2", type=ResourceType.DEVICE),
                    ],
                ),
                Workspace(
                    id="w2",
                    accepting_job_submissions=True,
                    jobs_being_processed=True,
                    resources=[
                        WorkspaceResource(id="r1", name="R1", type=ResourceType.DEVICE),
                    ],
                ),
            ]
        )
    )


@app.get("/v1/resources/{resource_id}")
async def resource_details(resource_id: str, request: Request) -> Any:
    _record_request(request)
    if resource_id == "r1":
        return JSONResponse(
            content=jsonable_encoder(
                ResourceDetails(
                    id="r1",
                    name="R1",
                    type=ResourceType.DEVICE,
                    status=ResourceStatus.ONLINE,
                    available_qubits=10,
                    status_updated_at=datetime(2026, 3, 27, 0, 0, 0),
                )
            )
        )
    if resource_id == "r2":
        return JSONResponse(
            content=jsonable_encoder(
                ResourceDetails(
                    id="r2",
                    name="R2",
                    type=ResourceType.DEVICE,
                    status=ResourceStatus.ONLINE,
                    available_qubits=20,
                    status_updated_at=datetime(2026, 3, 27, 0, 0, 0),
                )
            )
        )

    return JSONResponse(status_code=404, content={"error": f"Resource with ID '{resource_id}' not found."})


@app.get("/__requests")
async def get_requests() -> Any:
    return JSONResponse(_requests)


@app.post("/__clear")
async def clear_requests() -> Any:
    _requests.clear()
    return JSONResponse({"ok": True})
