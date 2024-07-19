import copy
from typing import Dict

PREFIX = "embeddings_"
KEYS = frozenset(["skills", "markets", "industries", "specialisms", "test_index"])


class CollectionManager:
    def __init__(self, prefix: str = PREFIX, keys: list = KEYS):
        self.prefix = prefix
        self.keys = keys
        self.mapping = {key: f"{self.prefix}{key}" for key in self.keys}

    def get_all_collections(self) -> Dict[str, str]:
        return self.mapping

    def get_used_collections(self) -> Dict[str, str]:
        mapping_copy = copy.deepcopy(self.mapping)
        mapping_copy.pop("test_index", None)
        return mapping_copy
