"""Tests for services/scheduler.py (Task 6.4).

Verifies that start_scheduler() registers all three expected jobs.
"""

import pytest


@pytest.mark.asyncio
async def test_scheduler_has_three_jobs():
    """After start_scheduler(), the scheduler must have jobs: stock_scan, fx_scan, nav_snapshot."""
    from services.scheduler import start_scheduler, stop_scheduler, scheduler

    # Ensure scheduler is stopped before we begin (in case of prior test leakage)
    stop_scheduler()

    try:
        start_scheduler()

        job_ids = {job.id for job in scheduler.get_jobs()}

        assert "stock_scan" in job_ids, f"stock_scan missing; found: {job_ids}"
        assert "fx_scan" in job_ids, f"fx_scan missing; found: {job_ids}"
        assert "nav_snapshot" in job_ids, f"nav_snapshot missing; found: {job_ids}"
        assert len(job_ids) == 3, f"Expected 3 jobs, got {len(job_ids)}: {job_ids}"

    finally:
        stop_scheduler()
