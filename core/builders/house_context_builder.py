from typing import Dict
from core.repositories.house_repository import HouseRepository

class HouseContextBuilder:
    def __init__(self, house_repo: HouseRepository):
        self._house_repo = house_repo

    def build(self) -> Dict:
        """Builds context related to house long-term config."""
        return self._house_repo.get_house_context()
