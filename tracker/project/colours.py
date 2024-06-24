from itertools import cycle
from django.apps import apps


def hex_to_rbga(colour):
    print(colour)
    return [f'#{colour}', f"rgba{tuple(int(colour[i:i+2], 16) for i in (0, 2, 4)) + (0.3,)}"]


def get_model_colour_map():
    hex_colours = cycle(
        map(
            hex_to_rbga,
            [
                "002051",
                "0a326a",
                "2b446e",
                "4d566d",
                "696970",
                "7f7c75",
                "948f78",
                "ada476",
                "caba6a",
                "ead156",
                "fdea45",
                "1f77b4",
                "ff7f0e",
                "2ca02c",
                "d62728",
                "9467bd",
                "8c564b",
                "e377c2",
                "7f7f7f",
                "bcbd22",
                "17becf",
            ],
        )
    )
    return {
        model: next(hex_colours)
        for model in apps.get_models()
        if model._meta.app_label == "project"
    }
