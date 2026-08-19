from abc import ABC, abstractmethod
from typing import List

from models.job import Job


class BaseProvider(ABC):

    @abstractmethod
    def search(self) -> List[Job]:
        """
        Returns a list of Job objects.
        """
        pass
