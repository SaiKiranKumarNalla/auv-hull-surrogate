"""Sample parametric designs with fins, flaps and fish-like fins -> design/specs/*.json, design/samples_full/*.stl, figure."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import appendages as ap

HERE = os.path.dirname(__file__)
D = 0.191
REMUS = {'family': 'myring', 'params': dict(a=0.19, b=0.85, c=0.29, d=D, n=2.0, theta_deg=20)}


def fin(name, rolls, x_le, cr, ct, span, sweep=15, t=0.12, defl=0, flap_f=0.0, flap=0):
    return dict(name=name, rolls_deg=rolls, x_le=x_le, root_chord=cr, tip_chord=ct, span=span, sweep_deg=sweep,
                thickness=t, deflection_deg=defl, flap_fraction=flap_f, flap_deg=flap)


DESIGNS = {
    'myring_cruciform': {'hull': REMUS, 'fins': [fin('tail', [0, 90, 180, 270], 1.12, 0.10, 0.07, 0.09)]},
    'myring_x_tail_flaps': {'hull': REMUS, 'fins': [
        fin('x_tail', [45, 135, 225, 315], 1.12, 0.11, 0.07, 0.10, sweep=25, flap_f=0.35, flap=20)]},
    'myring_tall_rudder': {'hull': REMUS, 'fins': [
        fin('rudder', [90, 270], 1.08, 0.14, 0.10, 0.22, sweep=10, flap_f=0.4, flap=15),
        fin('elevators', [0, 180], 1.14, 0.09, 0.06, 0.08, defl=-5)]},
    'haack_bow_and_stern_planes': {'hull': {'family': 'haack', 'params': dict(a=0.30, b=0.65, c=0.38, d=D, C=1 / 3)},
                                   'fins': [fin('bow_planes', [0, 180], 0.32, 0.07, 0.05, 0.07, sweep=5, defl=10),
                                            fin('stern', [0, 90, 180, 270], 1.10, 0.10, 0.06, 0.09, sweep=30)]},
    'flat_stern_finned': {'hull': {'family': 'flat_stern', 'params': dict(a=0.15, b=0.80, c=0.38, d=D, n=2.0,
                                                                          theta_deg=25, stern_ratio=0.45)},
                          'fins': [fin('tail', [0, 90, 180, 270], 1.02, 0.12, 0.08, 0.08, sweep=20)]},
    'fish_like': {'hull': {'family': 'fish_like', 'params': dict(L=1.33, t=D / 1.33, x_max=0.35, tail=0.012),
                           'width': 0.65, 'height': 1.0},
                  'fins': [fin('dorsal', [90], 0.40, 0.30, 0.05, 0.10, sweep=50, t=0.08),
                           fin('pectoral', [-25, 205], 0.30, 0.12, 0.05, 0.12, sweep=35, t=0.08),
                           fin('anal', [270], 0.85, 0.12, 0.04, 0.05, sweep=45, t=0.08),
                           fin('caudal', [90, 270], 1.20, 0.13, 0.035, 0.20, sweep=55, t=0.08)]},
}

os.makedirs(os.path.join(HERE, 'specs'), exist_ok=True)
os.makedirs(os.path.join(HERE, 'samples_full'), exist_ok=True)
fig = plt.figure(figsize=(16, 9))
for i, (name, d) in enumerate(DESIGNS.items()):
    json.dump(d, open(os.path.join(HERE, 'specs', f'{name}.json'), 'w'), indent=1)
    man = ap.build(d)
    n = ap.save_stl(man, os.path.join(HERE, 'samples_full', f'{name}.stl'), name)
    print(f'{name:28s} {n:7d} triangles  genus {man.genus()}  volume {man.volume() * 1e3:6.2f} L  '
          f'surface {man.surface_area():.3f} m^2')
    mesh = man.to_mesh()
    V = np.asarray(mesh.vert_properties)[:, :3]; T = V[np.asarray(mesh.tri_verts)]
    nrm = np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]); nrm /= np.linalg.norm(nrm, axis=1, keepdims=True).clip(1e-30)
    shade = 0.35 + 0.65 * np.clip(nrm @ np.array([0.3, -0.5, 0.8]), 0, 1)
    ax = fig.add_subplot(2, 3, i + 1, projection='3d')
    ax.add_collection3d(Poly3DCollection(T, facecolors=plt.cm.Blues(0.3 + 0.6 * shade), linewidths=0))
    ax.set_xlim(0, 1.35); ax.set_ylim(-0.3, 0.3); ax.set_zlim(-0.3, 0.3); ax.set_box_aspect((1.35, 0.6, 0.6))
    ax.view_init(22, -55); ax.set_axis_off(); ax.set_title(name.replace('_', ' '), fontsize=10)
plt.tight_layout(); plt.savefig(os.path.join(HERE, 'appendage_samples.png'), dpi=120)
