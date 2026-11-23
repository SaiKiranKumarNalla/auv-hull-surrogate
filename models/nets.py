"""Neural-network architectures and one shared training loop (PyTorch, CPU is enough)."""
import numpy as np
import torch
import torch.nn as nn


class PaperSNet(nn.Module):
    """Vardhan et al.'s network (student_model.py), written cleanly.
    9 linear layers 6→128→64→64→32→32→64→64→8→1, ReLU, one skip connection after layer 3.
    Their two dropout layers were created but never applied, so there is no dropout here either."""
    WIDTHS = [6, 128, 64, 64, 32, 32, 64, 64, 8, 1]

    def __init__(self, dropout=0.0, xavier=False):
        """dropout=0.2 gives the paper-as-written version (their code never applied it).
        xavier=True uses their init: Xavier-normal weights, zero biases (utils.initialize_weights)."""
        super().__init__()
        w = self.WIDTHS
        self.fc = nn.ModuleList(nn.Linear(w[i], w[i + 1]) for i in range(len(w) - 1))
        self.drop = nn.Dropout(dropout)
        if xavier:
            for layer in self.fc:
                nn.init.xavier_normal_(layer.weight, gain=1.0)
                nn.init.zeros_(layer.bias)

    def forward(self, x):
        x = torch.relu(self.fc[0](x))
        x = torch.relu(self.fc[1](x))
        h = self.fc[2](x)
        x = self.drop(h + torch.relu(h))           # their skip connection, then dropout 1
        for i, layer in enumerate(self.fc[3:-1]):
            x = torch.relu(layer(x))
            if i == 2:                             # after layer 6, where their code put dropout 2
                x = self.drop(x)
        return self.fc[-1](x)


class SimpleMLP(nn.Module):
    """A small modern MLP: `depth` hidden layers of `width` units with SiLU (smooth) activations."""

    def __init__(self, n_in=6, width=64, depth=3):
        super().__init__()
        layers, d = [], n_in
        for _ in range(depth):
            layers += [nn.Linear(d, width), nn.SiLU()]
            d = width
        layers.append(nn.Linear(d, 1))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x)


def n_params(model):
    return sum(p.numel() for p in model.parameters())


def train(model, x_tr, y_tr, x_val, y_val, loss='l1', epochs=400, lr=1e-3, batch=32, weight_decay=0.0,
          patience=None, seed=0, select='val', at_least=25, adamw=True):
    """Mini-batch training with Adam(W); keeps the weights with the lowest validation loss.
    Inputs are numpy arrays already scaled; y has shape (n, 1). Returns the trained model.
    select='val': keep the epoch with the lowest validation loss (standard).
    select='gap': their nn_train.py rule: save every epoch up to `at_least`, then keep the epoch where
                  |train loss - validation loss| is smallest.
    adamw=False: plain Adam (their optimiser)."""
    torch.manual_seed(seed)
    T = lambda a: torch.tensor(a, dtype=torch.float32)
    xt, yt, xv, yv = T(x_tr), T(y_tr), T(x_val), T(y_val)
    loss_fn = nn.functional.l1_loss if loss == 'l1' else nn.functional.mse_loss
    opt = (torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay) if adamw
           else torch.optim.Adam(model.parameters(), lr=lr))
    best, best_state, since = float('inf'), None, 0
    for ep in range(epochs):
        model.train()
        for i in torch.randperm(len(xt)).split(batch):
            opt.zero_grad()
            loss_fn(model(xt[i]), yt[i]).backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            v = loss_fn(model(xv), yv).item()
            if select == 'gap':
                v = abs(loss_fn(model(xt), yt).item() - v)
                if ep <= at_least:                 # their warm-up: always save, then start comparing
                    best = float('inf')
        if v < best:
            best, best_state, since = v, {k: t.clone() for k, t in model.state_dict().items()}, 0
        else:
            since += 1
            if patience and since >= patience:
                break
    model.load_state_dict(best_state)
    return model


def predict(model, x):
    with torch.no_grad():
        return model(torch.tensor(x, dtype=torch.float32)).numpy()
