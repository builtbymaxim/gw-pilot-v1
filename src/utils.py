import regex as re
import random
import numpy as np


def normalize_year_tokens(text: str) -> str:
    """Join split year tokens like "20 30" or "2-0-3-0" into "2030".

    Accepts any value convertible to ``str`` and ensures years split with
    non-digit separators are normalized to a continuous four-digit year.
    """
    if not isinstance(text, str):
        text = "" if text is None else str(text)
    return re.sub(r'(?i)(?<!\d)2\W*0\W*([0-9])\W*([0-9])(?!\d)', r'20\1\2', text)


def set_all_seeds(seed: int) -> None:
    """Seed Python, NumPy, and PyTorch for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    try:  # torch is optional
        import torch

        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)
    except Exception:
        pass
