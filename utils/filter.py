from pprint import pprint
from typing import TypedDict

Filtered = TypedDict("Filtered", {"data": list[dict], "counts": int})

FILTERS10U = {
    "Email": ("#N/A", ""),
    "Status": ("New", "Waiting"),
    "English": ("#N/A", "", 0),
}
FILTERS09D = {
    "Email": ("#N/A", ""),
    "Status": ("New", "Waiting"),
}


def filter_unwanted(records: list[dict]) -> Filtered:

    filtered_records = filter(
        lambda record: record["Year"] not in ("#N/A", ""), records
    )

    for FILTER in FILTERS10U:
        filtered_records = list(
            # filter(
            #     lambda record: record[FILTER] not in FILTERS10U[FILTER]
            #     if record["Year"] >= 10
            #     else record[FILTER] not in FILTERS09D[FILTER]
            #     if FILTER not in FILTERS09D
            #     else None,
            #     filtered_records,
            # )
            filter(
                lambda record: record.get(FILTER, "something")
                not in FILTERS10U.get(FILTER, FILTERS09D.get(FILTER, None)),
                filtered_records,
            ),
        )

    counts = len(filtered_records)

    return {"data": filtered_records, "counts": counts}
