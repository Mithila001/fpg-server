from pprint import pprint

from app.algorithms.floor_plan_preprocessing import (
    prepare_generation_input,
)

from .builders import build_preprocessing_input


def main():
    input_data = build_preprocessing_input()

    result = prepare_generation_input(input_data)

    print("\n========== REPORT ==========\n")
    pprint(result.report)

    print("\n========== FLOOR ==========\n")
    pprint(result.generation_spec.floor)

    print("\n========== ROOMS ==========\n")
    for room in result.generation_spec.rooms:
        pprint(room)

    print("\n========== RELATIONS ==========\n")
    for relation in result.generation_spec.room_relations:
        pprint(relation)



if __name__ == "__main__":
    main()