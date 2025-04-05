from watchdog_ai.data_utils.procurement_data_config import METHODS_DATA


all_items = []
for method, data in METHODS_DATA.items():
    item_keys = data['items'].keys()
    all_items.extend(item_keys)

print(all_items) # to verify
