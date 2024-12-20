from abc import ABC, abstractmethod

class LayoutManager(ABC):
    @abstractmethod
    def apply(self, diagram, verbose=False):
        pass
