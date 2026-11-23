"""Physics-aware ML pieces: dimensionless features, physics targets, the hybrid model M4,
deep ensembles (M6), and a physical-consistency check that works for any model."""
import numpy as np
import torch
import torch.nn as nn

from .nets import SimpleMLP
from .physics import NU, U, drag_m0, wetted_area_and_volume

FEATURE_NAMES = ['d/L', 'a/L', 'c/L', 'n', 'tan(theta)', 'd/(2c)', 'Cp', 'log10(Re)']


def physics_features(X):
    """Turn raw hull numbers (a, b, c, d in mm; n; theta in degrees) into dimensionless groups.
    Dimensionless inputs mean the model learns shape *proportions*, not absolute sizes."""
    a, b, c, d, n, th = X.T
    L = a + b + c
    S_V = np.array([wetted_area_and_volume(*row) for row in X])           # m², m³
    V = S_V[:, 1]
    A_front = np.pi / 4 * (d / 1000) ** 2
    Cp = V / (A_front * L / 1000)                                          # prismatic coefficient: how "full" the hull is
    Re = U * (L / 1000) / NU
    return np.column_stack([d / L, a / L, c / L, n, np.tan(np.radians(th)), d / (2 * c), Cp, np.log10(Re)])


def m0_drag(X):
    """Physics baseline drag (N) for many hulls."""
    return np.array([drag_m0(*row) for row in X])


class Standardise:
    """Remember mean/std of the training data and apply the same scaling later."""

    def fit(self, A):
        self.mu, self.sd = A.mean(0), A.std(0) + 1e-12
        return self

    def __call__(self, A):
        return (A - self.mu) / self.sd


def train_mlp(xs, ys, xv, yv, width=64, depth=3, lr=1e-3, weight_decay=1e-4, batch=64, epochs=1500,
              patience=150, seed=0, penalty_fn=None, penalty_weight=0.0):
    """Train a SimpleMLP on scaled inputs/targets (numpy), keeping the best validation weights.
    penalty_fn(model) -> scalar tensor adds a physics penalty to every step (used by M4)."""
    torch.manual_seed(seed)
    T = lambda a: torch.tensor(a, dtype=torch.float32)
    xt, yt, xvt, yvt = T(xs), T(ys[:, None]), T(xv), T(yv[:, None])
    model = SimpleMLP(xs.shape[1], width, depth)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    best, best_state, since = float('inf'), None, 0
    for _ in range(epochs):
        model.train()
        for i in torch.randperm(len(xt)).split(batch):
            opt.zero_grad()
            loss = nn.functional.mse_loss(model(xt[i]), yt[i])
            if penalty_fn is not None and penalty_weight > 0:
                loss = loss + penalty_weight * penalty_fn(model)
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            v = nn.functional.mse_loss(model(xvt), yvt).item()
        if v < best:
            best, best_state, since = v, {k: t.clone() for k, t in model.state_dict().items()}, 0
        else:
            since += 1
            if since >= patience:
                break
    model.load_state_dict(best_state)
    return model


def mlp_predict(model, xs):
    with torch.no_grad():
        return model(torch.tensor(xs, dtype=torch.float32)).numpy().ravel()


class Variant:
    """One cell of the ablation: inputs 'raw' or 'physics' × target 'drag' or 'correction' (drag / M0 drag).
    All targets are learned in log space, so errors are relative."""

    def __init__(self, inputs='raw', target='drag'):
        self.inputs, self.target = inputs, target

    def x(self, X):
        return physics_features(X) if self.inputs == 'physics' else X

    def y(self, X, D):
        return np.log(D / m0_drag(X)) if self.target == 'correction' else np.log(D)

    def back(self, X, t):
        return np.exp(t) * m0_drag(X) if self.target == 'correction' else np.exp(t)


def fit_variant(variant, X_tr, D_tr, X_val, D_val, cfg, seed, penalty=None):
    """Train one ablation variant; returns a predict(X) function giving drag in newtons."""
    sx = Standardise().fit(variant.x(X_tr))
    t_tr = variant.y(X_tr, D_tr)
    sy = Standardise().fit(t_tr[:, None])
    pen_fn = None
    if penalty is not None:
        pen_fn = penalty.make(variant, sx, sy)
    model = train_mlp(sx(variant.x(X_tr)), (t_tr - sy.mu[0]) / sy.sd[0],
                      sx(variant.x(X_val)), (variant.y(X_val, D_val) - sy.mu[0]) / sy.sd[0],
                      seed=seed, penalty_fn=pen_fn, penalty_weight=penalty.weight if penalty else 0.0, **cfg)
    return lambda X: variant.back(X, mlp_predict(model, sx(variant.x(X))) * sy.sd[0] + sy.mu[0])


# ---------- physical consistency -----------------------------------------------------------------
def random_hulls(n, seed=0):
    """Random valid hulls inside the dataset's design space (no CFD needed) — 'collocation points'."""
    rng = np.random.default_rng(seed)
    out = []
    while len(out) < n:
        a, c = rng.uniform(50, 600, 2)
        L = rng.uniform(1000, 2000)
        b = L - a - c
        if b < 1:
            continue
        out.append([a, b, c, rng.uniform(50, 200), rng.uniform(1, 5), rng.uniform(1, 50)])
    return np.array(out)


def monotonicity_violations(predict, X, step=0.05):
    """Share (%) of hulls where the model breaks two physical rules:
    (1) a longer middle cylinder (b +5 %) must not reduce drag; (2) a larger diameter (d +5 %) must not reduce drag."""
    out = {}
    for col, name in [(1, 'longer_body'), (3, 'larger_diameter')]:
        X2 = X.copy()
        X2[:, col] *= 1 + step
        out[name] = 100 * np.mean(predict(X2) < predict(X) - 1e-9)
    return out


class MonotonicPenalty:
    """M4's physics penalty: on random unlabelled hulls, penalise any drop in predicted drag when the body gets
    longer or the diameter gets larger. Finite differences, so it works with any feature transform."""

    def __init__(self, n_points=256, weight=1.0, seed=0):
        self.X0 = random_hulls(n_points, seed)
        self.weight = weight

    def make(self, variant, sx, sy):
        pairs = []
        for col in (1, 3):
            X1 = self.X0.copy()
            X1[:, col] *= 1.05
            base0 = np.log(m0_drag(self.X0)) if variant.target == 'correction' else 0 * self.X0[:, 0]
            base1 = np.log(m0_drag(X1)) if variant.target == 'correction' else 0 * X1[:, 0]
            pairs.append((torch.tensor(sx(variant.x(self.X0)), dtype=torch.float32),
                          torch.tensor(sx(variant.x(X1)), dtype=torch.float32),
                          torch.tensor(base0, dtype=torch.float32), torch.tensor(base1, dtype=torch.float32)))
        s = float(sy.sd[0])

        def penalty(model):
            total = 0.0
            for x0, x1, b0, b1 in pairs:
                logD0 = model(x0).squeeze(1) * s + b0          # log drag (up to a constant)
                logD1 = model(x1).squeeze(1) * s + b1
                total = total + torch.relu(logD0 - logD1).mean()   # > 0 only when drag drops
            return total
        return penalty
