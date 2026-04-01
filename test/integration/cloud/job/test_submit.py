import pytest

from test.integration.cloud.job._helpers import make_job


def test_submit_raises_runtime_error() -> None:
    """It raises RuntimeError because jobs are submitted via backend.run()."""
    job = make_job()

    with pytest.raises(RuntimeError, match=r"Job is already submitted via backend.run\(\)"):
        job.submit()
