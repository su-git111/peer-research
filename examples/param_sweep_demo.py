# 데모 워크로드: 합성 공간 데이터에서 클러스터 수 k를 스윕하며 silhouette를 계산.
# 실제 연구 스크립트 대신 야간 큐 실행을 시연하기 위한 자체 완결형 예시 (numpy만 사용).

import numpy as np

rng = np.random.default_rng(0)

n_true = 8
per = 90
spread = 0.55
centers = rng.uniform(-6, 6, size=(n_true, 2))
X = np.vstack([c + rng.normal(0, spread, size=(per, 2)) for c in centers])
rng.shuffle(X)


def kmeans(X, k, iters=50, restarts=5):
    best_labels, best_inertia = None, np.inf
    for r in range(restarts):
        idx = rng.choice(len(X), size=k, replace=False)
        C = X[idx].copy()
        for _ in range(iters):
            d = ((X[:, None, :] - C[None, :, :]) ** 2).sum(2)
            labels = d.argmin(1)
            newC = np.array([X[labels == j].mean(0) if np.any(labels == j) else C[j] for j in range(k)])
            if np.allclose(newC, C):
                C = newC
                break
            C = newC
        inertia = ((X - C[labels]) ** 2).sum()
        if inertia < best_inertia:
            best_labels, best_inertia = labels, inertia
    return best_labels


def silhouette(X, labels):
    D = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(2))
    uniq = np.unique(labels)
    s = np.zeros(len(X))
    for i in range(len(X)):
        same = labels == labels[i]
        same[i] = False
        a = D[i, same].mean() if same.any() else 0.0
        b = min(D[i, labels == c].mean() for c in uniq if c != labels[i])
        s[i] = (b - a) / max(a, b) if max(a, b) > 0 else 0.0
    return s.mean()

scores = {}
for k in range(2, 13):
    labels = kmeans(X, k)
    scores[k] = silhouette(X, labels)
    print(f"k={k:2d}  silhouette={scores[k]:.3f}")

best_k = max(scores, key=scores.get)
print(f"\nbest k = {best_k}  silhouette = {scores[best_k]:.3f}  (n={len(X)}, true clusters={n_true})")
