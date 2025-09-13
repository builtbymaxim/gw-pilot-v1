import numpy as np
from sklearn.metrics import (
    auc,
    confusion_matrix,
    precision_recall_curve,
    roc_curve,
)

def cohen_kappa(y1, y2):
    y1, y2 = np.asarray(y1), np.asarray(y2)
    assert y1.shape == y2.shape
    n = len(y1)
    po = (y1 == y2).sum()/n
    p1 = np.mean(y1); p0 = 1 - p1
    q1 = np.mean(y2); q0 = 1 - q1
    pe = p1*q1 + p0*q0
    return (po - pe) / (1 - pe + 1e-12)

def calibrate_tau(entail_probs, labels):
    fpr, tpr, thr = roc_curve(labels, entail_probs)
    youden = tpr - fpr
    j_idx = int(np.argmax(youden))

    precision, recall, _ = precision_recall_curve(labels, entail_probs)
    pr_curve = [
        {"precision": float(p), "recall": float(r)} for p, r in zip(precision, recall)
    ]

    return {
        "auc": float(auc(fpr, tpr)),
        "pr_auc": float(auc(recall, precision)),
        "tau": float(thr[j_idx]),
        "tpr": float(tpr[j_idx]),
        "fpr": float(fpr[j_idx]),
        "pr_curve": pr_curve,
    }

def confusion_at_tau(entail_probs, labels, tau):
    import numpy as np
    from sklearn.metrics import confusion_matrix
    yhat = (np.asarray(entail_probs) >= tau).astype(int)
    tn, fp, fn, tp = confusion_matrix(labels, yhat).ravel()
    return {"tp":int(tp),"fp":int(fp),"tn":int(tn),"fn":int(fn)}
