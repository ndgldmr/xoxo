"""GCP Cloud Scheduler client for reading and updating the daily send job."""
import json
from typing import Optional

from google.cloud import scheduler_v1
from google.protobuf.field_mask_pb2 import FieldMask


class GCPSchedulerError(Exception):
    """Raised when a Cloud Scheduler API call fails."""


class GCPSchedulerClient:
    """Wraps the Google Cloud Scheduler API for a single job."""

    def __init__(
        self,
        project_id: str,
        location: str,
        job_id: str,
        service_url: str,
        api_key: str,
    ) -> None:
        self._project_id = project_id
        self._location = location
        self._job_id = job_id
        self._service_url = service_url
        self._api_key = api_key
        self._client = scheduler_v1.CloudSchedulerClient()

    @property
    def _job_name(self) -> str:
        return (
            f"projects/{self._project_id}"
            f"/locations/{self._location}"
            f"/jobs/{self._job_id}"
        )

    def get_config(self) -> dict:
        """Fetch the job from GCP and return parsed config.

        Returns:
            dict with keys: theme, level, send_time (HH:MM), timezone

        Raises:
            GCPSchedulerError: if the API call fails or the job body is invalid.
        """
        try:
            job = self._client.get_job(name=self._job_name)
        except Exception as exc:
            raise GCPSchedulerError(f"Failed to get Cloud Scheduler job: {exc}") from exc

        try:
            body = json.loads(job.http_target.body.decode("utf-8"))
        except Exception as exc:
            raise GCPSchedulerError(f"Could not parse job body as JSON: {exc}") from exc

        # Parse cron "MM HH * * *" → "HH:MM"
        try:
            send_time = _cron_to_hhmm(job.schedule)
        except ValueError as exc:
            raise GCPSchedulerError(str(exc)) from exc

        return {
            "theme": body.get("theme", ""),
            "level": body.get("level", ""),
            "send_time": send_time,
            "timezone": job.time_zone,
        }

    def update_job(
        self,
        theme: str,
        level: str,
        send_time: str,
        timezone: str,
    ) -> None:
        """Update the Cloud Scheduler job with new config.

        Args:
            theme: topic string
            level: "beginner" | "intermediate" | "advanced"
            send_time: "HH:MM"
            timezone: IANA timezone string e.g. "America/Sao_Paulo"

        Raises:
            GCPSchedulerError: if the API call fails.
        """
        cron = _hhmm_to_cron(send_time)
        body_bytes = json.dumps({"theme": theme, "level": level}).encode("utf-8")

        job = scheduler_v1.Job(
            name=self._job_name,
            schedule=cron,
            time_zone=timezone,
            http_target=scheduler_v1.HttpTarget(
                uri=f"{self._service_url}/send-word-of-day",
                http_method=scheduler_v1.HttpMethod.POST,
                body=body_bytes,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Key": self._api_key,
                },
            ),
        )

        update_mask = FieldMask(
            paths=["schedule", "time_zone", "http_target.body", "http_target.headers"]
        )

        try:
            self._client.update_job(job=job, update_mask=update_mask)
        except Exception as exc:
            raise GCPSchedulerError(f"Failed to update Cloud Scheduler job: {exc}") from exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _cron_to_hhmm(cron: str) -> str:
    """Parse "MM HH * * *" → "HH:MM"."""
    parts = cron.strip().split()
    if len(parts) < 2:
        raise ValueError(f"Unexpected cron format: {cron!r}")
    mm, hh = parts[0], parts[1]
    return f"{int(hh):02d}:{int(mm):02d}"


def _hhmm_to_cron(send_time: str) -> str:
    """Convert "HH:MM" → "MM HH * * *"."""
    hh, mm = send_time.split(":")
    return f"{int(mm)} {int(hh)} * * *"
