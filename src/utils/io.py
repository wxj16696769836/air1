import os
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt


def ensure_directory(path: str | Path) -> Path:
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


def save_figure(figure: plt.Figure, path: str | Path, dpi: int = 150) -> None:
    path_obj = Path(path)
    ensure_directory(path_obj.parent)
    figure.tight_layout()
    figure.savefig(path_obj, dpi=dpi)
    plt.close(figure)
