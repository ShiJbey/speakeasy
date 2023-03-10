"""
speakeasy/actions.py

Characters take actions that are geared toward helping them keep their businesses
running properly.
"""
from __future__ import annotations

from typing import Generator, Optional
from abc import ABC, abstractmethod

from neighborly import GameObject


class Action(ABC):

    @abstractmethod
    def _check_preconditions(self, initiator: GameObject) -> bool:
        raise NotImplementedError()

    @abstractmethod
    def _bind_other(self, candidate: Optional[GameObject] = None) -> Generator[GameObject, None, None]:
        raise NotImplementedError()

    @abstractmethod
    def _bind_direct_object(self, candidate: Optional[GameObject] = None) -> Generator[GameObject, None, None]:
        raise NotImplementedError()

    @abstractmethod
    def _bind_location(self, candidate: Optional[GameObject] = None) -> Generator[GameObject, None, None]:
        raise NotImplementedError()

    def get_instances(self, initiator: GameObject) -> Generator[Action, None, None]:
        raise NotImplementedError()



if __name__ == "__main__":
    ...
