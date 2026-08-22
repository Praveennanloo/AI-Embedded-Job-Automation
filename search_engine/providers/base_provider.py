from abc import ABC, abstractmethod
import re
from typing import List

from models.job import Job


class BaseProvider(ABC):

    QUERY_LEVEL_TERMS = {
        "junior",
        "trainee",
        "graduate",
        "intern",
        "entry-level",
        "fresher",
        "associate",
    }

    REMOTE_LOCATION_INDICATORS = (
        "remote",
        "home based",
        "home-based",
        "worldwide",
        "global",
    )

    QUERY_INTENT_TERMS = {
        "embedded",
        "firmware",
        "linux",
        "kernel",
        "driver",
        "drivers",
        "rtos",
        "freertos",
        "iot",
        "mcu",
        "microcontroller",
        "microcontrollers",
        "arm",
        "bsp",
        "yocto",
        "uboot",
        "u-boot",
    }

    @classmethod
    def _query_terms(cls, query: str) -> List[str]:
        return [
            term
            for term in re.findall(r"[a-z0-9][a-z0-9+-]*", (query or "").lower())
            if len(term) > 2
        ]

    @classmethod
    def _query_text(cls, job: Job) -> str:
        return " ".join([
            job.title or "",
            getattr(job, "description", "") or "",
            " ".join(job.skills or []),
        ]).lower()

    @classmethod
    def query_match_details(cls, job: Job, query: str) -> dict:
        terms = cls._query_terms(query)
        if not terms:
            return {
                "matched": True,
                "strength": "no_query",
                "matched_terms": [],
                "reason": "No query terms supplied",
            }

        text = cls._query_text(job)
        matched_terms = [term for term in terms if term in text]
        intent_matches = [
            term for term in matched_terms if term in cls.QUERY_INTENT_TERMS
        ]
        level_terms = [term for term in terms if term in cls.QUERY_LEVEL_TERMS]
        missing_level_terms = [term for term in level_terms if term not in matched_terms]

        if missing_level_terms:
            return {
                "matched": False,
                "strength": "missing_level_intent",
                "matched_terms": matched_terms,
                "missing_level_terms": missing_level_terms,
                "reason": (
                    "Explicit query level intent was not found in candidate job text"
                ),
            }

        if len(matched_terms) == len(terms):
            return {
                "matched": True,
                "strength": "exact",
                "matched_terms": matched_terms,
                "reason": "All query terms matched provider job text",
            }

        if len(terms) == 1 and matched_terms:
            return {
                "matched": True,
                "strength": "single_term",
                "matched_terms": matched_terms,
                "reason": "Single query term matched provider job text",
            }

        if len(matched_terms) >= 2 and intent_matches:
            return {
                "matched": True,
                "strength": "partial_intent",
                "matched_terms": matched_terms,
                "reason": (
                    "At least two query terms matched, including an embedded/"
                    "firmware/Linux intent term"
                ),
            }

        return {
            "matched": False,
            "strength": "insufficient",
            "matched_terms": matched_terms,
            "reason": (
                "Fewer than two query terms matched, or no embedded/firmware/"
                "Linux intent term matched"
            ),
        }

    @classmethod
    def location_matches(cls, job: Job, requested_location: str) -> bool:
        """Apply the provider-level location gate using the final filter's semantics."""
        location_term = (requested_location or "").strip().lower()
        if not location_term:
            return True

        location = (job.location or "").strip().lower()
        if getattr(job, "remote", False) or any(
            indicator in location for indicator in cls.REMOTE_LOCATION_INDICATORS
        ):
            return True

        return location_term in location

    @abstractmethod
    def search(self, query: str = "", location: str = "", limit: int | None = None) -> List[Job]:
        """
        Returns a list of Job objects.
        """
        pass
