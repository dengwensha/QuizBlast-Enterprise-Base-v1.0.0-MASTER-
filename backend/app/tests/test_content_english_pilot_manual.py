"""CONTENT-01A: validate both English education pilot sets without publishing."""
from copy import deepcopy

from app.services.content_english_pilot import (
    load_english_pilot,
    validate_english_pilot,
)


def expect_invalid(data):
    try:
        validate_english_pilot(data)
    except ValueError:
        return
    raise AssertionError("Invalid English pilot content was accepted")


def run():
    data = load_english_pilot()
    assert validate_english_pilot(data) == {"set_count": 2, "question_count": 20}

    invalid = deepcopy(data)
    invalid["sets"][0]["questions"][0]["correct"] = 9
    expect_invalid(invalid)

    invalid = deepcopy(data)
    invalid["sets"][0]["questions"][0]["explanation"] = ""
    expect_invalid(invalid)

    invalid = deepcopy(data)
    invalid["sets"][1]["questions"][0]["options"][1] = (
        invalid["sets"][1]["questions"][0]["options"][0]
    )
    expect_invalid(invalid)

    invalid = deepcopy(data)
    invalid["sets"][0]["grade"] = 8
    expect_invalid(invalid)

    invalid = deepcopy(data)
    invalid["sets"][1]["questions"][0]["time"] = 0
    expect_invalid(invalid)


if __name__ == "__main__":
    run()
    print("PASS — English pilot: 2 sets / 20 questions; negative cases rejected")
