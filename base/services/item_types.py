from base.constants import ITEM_TYPE_NAMES, TYPE_A_ITEM_PREFIXES, ItemType


def check_item_type(item_cat: str) -> str:
    if item_cat.startswith(TYPE_A_ITEM_PREFIXES):
        return ItemType.A
    return ItemType.B


def get_item_type_name(item_cat: str) -> str | None:
    for prefix, item_type_name in ITEM_TYPE_NAMES:
        if item_cat.startswith(prefix):
            return item_type_name
    return None
