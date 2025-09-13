# Auto-seeding via sitecustomize: wird bei jedem Python-Start importiert
import os, random
SEED = int(os.environ.get("PILOT_SEED", "42"))
random.seed(SEED)
try:
    import numpy as np; np.random.seed(SEED)
except Exception:
    pass
try:
    import torch
    torch.manual_seed(SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(SEED)
except Exception:
    pass
