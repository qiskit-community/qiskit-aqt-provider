from typing import TypedDict


class ResourceRunOptions(TypedDict, total=False):
    """Options for running a job on an AQT resource."""

    shots: int
    """Number of shots to use for the execution."""
    seed_simulator: int
    """Seed for the simulator."""
    memory: bool
    """Whether to return memory results."""
