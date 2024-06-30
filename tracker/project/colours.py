from itertools import cycle
from django.apps import apps


def hex_to_rbga(colour):
    return [
        f"#{colour}",
        f"rgba{tuple(int(colour[i:i+2], 16) for i in (0, 2, 4)) + (0.3,)}",
    ]


def get_model_colour_map():
    hex_colours = cycle(
        map(
            hex_to_rbga,
            [
                "4e79a7",
                "f28e2c",
                "e15759",
                "76b7b2",
                "59a14f",
                "edc949",
                "af7aa1",
                "ff9da7",
                "9c755f",
                "bab0ab",
            ],
        )
    )
    return {
        model: next(hex_colours)
        for model in apps.get_models()
        if model._meta.app_label == "project"
    }
