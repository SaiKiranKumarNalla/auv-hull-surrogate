"""3D picture of a full OpenFOAM case: hull coloured by Cp, streamlines coloured by |U|, translucent wake surface.

    python cfd/render3d.py runs/pilot_full/front_Re3e6 results/pilot/3d_front_Re3e6.png
Needs pyvista. U_inf = rho = 1, so Cp = 2 p.
"""
import json, os, sys
import numpy as np
import pyvista as pv

pv.OFF_SCREEN = True


def render(case, out):
    m = json.load(open(os.path.join(case, 'case.json')))
    open(os.path.join(case, 'case.foam'), 'w').close()
    r = pv.OpenFOAMReader(os.path.join(case, 'case.foam'))
    r.set_active_time_value(r.time_values[-1])
    r.enable_all_patch_arrays()
    data = r.read()
    vol = data['internalMesh']
    body = data['boundary']['body'].extract_surface()
    body = body.cell_data_to_point_data()
    body['Cp'] = 2 * body['p']
    vol = vol.cell_data_to_point_data()
    vol['|U|'] = np.linalg.norm(vol['U'], axis=1)
    lo, hi = np.array(m['bbox_lo']), np.array(m['bbox_hi'])
    span = max(hi[1] - lo[1], hi[2] - lo[2])
    seeds = pv.Plane(center=(lo[0] - 0.1, 0, 0), direction=(1, 0, 0), i_size=0.9 * (hi[1] - lo[1]) + 0.04,
                     j_size=0.9 * (hi[2] - lo[2]) + 0.04, i_resolution=9, j_resolution=9)
    lines = vol.streamlines_from_source(seeds, vectors='U', max_length=4.0, integration_direction='forward')
    wake = vol.contour([0.6], scalars='|U|')
    wake = wake.clip_box([hi[0] - 0.05, hi[0] + 3.5, -1.5, 1.5, -1.5, 1.5], invert=False) if wake.n_points else wake

    pl = pv.Plotter(off_screen=True, window_size=(1600, 900))
    pl.set_background('white')
    pl.add_mesh(body, scalars='Cp', cmap='RdBu_r', clim=(-0.8, 1.0), smooth_shading=True,
                scalar_bar_args=dict(title='Cp on hull', color='black', position_x=0.05, width=0.3))
    if lines.n_points:
        pl.add_mesh(lines.tube(radius=0.0015), scalars='|U|', cmap='viridis', clim=(0.3, 1.2),
                    scalar_bar_args=dict(title='|U| / U∞ (streamlines)', color='black', position_x=0.6, width=0.3))
    if wake.n_points:
        pl.add_mesh(wake, color='#5DCAA5', opacity=0.25, show_scalar_bar=False)
    pl.add_text(f"{m['design']} v{m['variant']:02d} · {m['orientation']} · Re = {m['Re']:.0e} · flow +x",
                font_size=12, color='black')
    focus = np.array([(lo[0] + hi[0]) / 2 + 0.25, 0, 0])
    pl.camera_position = [tuple(focus + np.array([-1.7, -2.2, 1.0])), tuple(focus), (0, 0, 1)]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    pl.screenshot(out); pl.close()
    print('saved', out, 'cells', vol.n_cells, 'streamline points', lines.n_points, 'wake points', wake.n_points)


if __name__ == '__main__':
    render(sys.argv[1], sys.argv[2])
