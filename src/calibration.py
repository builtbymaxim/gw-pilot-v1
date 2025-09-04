import numpy as np
from sklearn.metrics import roc_curve, auc, confusion_matrix

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
    return {
        "auc": float(auc(fpr, tpr)),
        "tau": float(thr[j_idx]),
        "tpr": float(tpr[j_idx]),
        "fpr": float(fpr[j_idx]),
        "thresholds": [float(x) for x in thr]
    }

def confusion_at_tau(entail_probs, labels, tau):
    import numpy as np
    from sklearn.metrics import confusion_matrix
    yhat = (np.asarray(entail_probs) >= tau).astype(int)
    tn, fp, fn, tp = confusion_matrix(labels, yhat).ravel()
    return {"tp":int(tp),"fp":int(fp),"tn":int(tn),"fn":int(fn)}
