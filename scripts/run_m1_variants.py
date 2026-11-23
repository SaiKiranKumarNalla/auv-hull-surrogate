"""Train the two faithful versions of the paper's network (5 seeds each) and save them to results/benchmark.csv."""
import sys; sys.path.insert(0, '.')
from sklearn.preprocessing import MinMaxScaler
from models import harness, nets

VERSIONS = {  # name: (dropout, lr, select)
    'M1a paper code as run': (0.0, 1e-3, 'gap'),      # nn_train.py: lr 0.001, dropout never applied, gap checkpoint
    'M1b paper text as written': (0.2, 3e-4, 'val'),  # paper: dropout 0.2, lr 0.0003, validation early stopping
}
for name, (p, lr, sel) in VERSIONS.items():
    def fp(Xtr, ytr, Xv, yv, Xte, seed, p=p, lr=lr, sel=sel):
        sx, sy = MinMaxScaler().fit(Xtr), MinMaxScaler().fit(ytr[:, None])
        m = nets.train(nets.PaperSNet(dropout=p, xavier=True), sx.transform(Xtr), sy.transform(ytr[:, None]),
                       sx.transform(Xv), sy.transform(yv[:, None]), loss='l1', epochs=400, lr=lr, batch=32,
                       seed=seed, select=sel, adamw=False)
        return sy.inverse_transform(nets.predict(m, sx.transform(Xte))).ravel()
    harness.run(name, fp)
