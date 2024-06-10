from abc import ABC, abstractmethod


class BaseManager(ABC):
    @abstractmethod
    def start():
        pass

    @abstractmethod
    def stop():
        pass
