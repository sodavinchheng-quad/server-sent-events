from typing import Dict
from entities import Store

STORES: Dict[int, Store] = {
    i: Store(i, f"Store {i}") for i in range(1, 601)
}
