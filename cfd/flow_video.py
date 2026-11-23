"""Flow video of a steady case: tracer particles released upstream travel along the computed streamlines at their
true local speed, past the hull coloured by Cp, while the camera turns slowly. The flow itself is steady (RANS);
the motion shows how fluid moves through it, not unsteady shedding.

    python cfd/flow_video.py runs/pilot_full/side_Re3e6 results/pilot/video_side_Re3e6.mp4
"""
import json, os, sys
import numpy as np
import pyvista as pv
import imageio.v2 as imageio

pv.OFF_SCREEN = True
FRAMES, FPS = 150, 30


def main(case, out):
    m = json.load(open(os.path.join(case, 'case.json')))
    open(os.path.join(case, 'case.foam'), 'w').close()
    r = pv.OpenFOAMReader(os.path.join(case, 'case.foam')); r.set_active_time_value(r.time_values[-1]); r.enable_all_patch_arrays()
    data = r.read()
    vol = data['internalMesh'].cell_data_to_point_data()
    body = data['boundary']['body'].extract_surface().cell_data_to_point_data(); body['Cp'] = 2 * body['p']
    lo, hi = np.array(m['bbox_lo']), np.array(m['bbox_hi'])
    seeds = pv.Plane(center=(lo[0] - 0.3, 0, 0), direction=(1, 0, 0), i_size=(hi[1] - lo[1]) + 0.12,
                     j_size=(hi[2] - lo[2]) + 0.12, i_resolution=int(10 + 30 * (hi[1] - lo[1])),
                     j_resolution=int(10 + 30 * (hi[2] - lo[2])))
    sl = vol.streamlines_from_source(seeds, vectors='U', max_length=5.0, integration_direction='forward',
                                     max_step_length=0.01)
    # each streamline: points ordered by integration time, which is real travel time (U_inf = 1)
    tracks = []
    for i in range(sl.n_cells):
        ids = sl.get_cell(i).point_ids
        if len(ids) > 10:
            P, T = sl.points[ids], sl['IntegrationTime'][ids]
            U = np.linalg.norm(sl['U'][ids], axis=1)
            tracks.append((P, T, U))
    tmax = max(t[1][-1] for t in tracks)
    period = 2.6                                          # time between particle releases along each line
    phase = np.random.default_rng(1).random(len(tracks)) * period

    pl = pv.Plotter(off_screen=True, window_size=(1280, 720))
    pl.set_background('#0d151b')
    pl.add_mesh(body, scalars='Cp', cmap='RdBu_r', clim=(-0.8, 1.0), smooth_shading=True,
                scalar_bar_args=dict(title='Cp', color='white', position_x=0.05, width=0.25, height=0.05))
    pl.add_mesh(sl, color='#3a4d5c', opacity=0.18, line_width=1)
    vol['|U|'] = np.linalg.norm(vol['U'], axis=1)
    wake = vol.contour([0.5], scalars='|U|').clip_box([lo[0] + 0.02, hi[0] + 3.0, -1.5, 1.5, -1.5, 1.5], invert=False)
    if wake.n_points:
        pl.add_mesh(wake, color='#5DCAA5', opacity=0.22)              # slow wake region (|U| < 0.5 U_inf)
    pl.add_text(f"{m['design']} v{m['variant']:02d} · {m['orientation']} · Re = {m['Re']:.0e}", font_size=11, color='white')
    pts_actor = None
    focus = np.array([(lo[0] + hi[0]) / 2 + 0.3, 0, 0])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    w = imageio.get_writer(out, fps=FPS, quality=8, macro_block_size=8)
    for f in range(FRAMES):
        t = f / FRAMES * 2 * period
        P, C = [], []
        for (Pk, Tk, Uk), ph in zip(tracks, phase):
            for k in range(3):                             # a few particles per line, spaced by the period
                tau = (t + ph + k * period) % (3 * period)
                if tau <= Tk[-1]:
                    j = np.searchsorted(Tk, tau)
                    j = min(max(j, 1), len(Tk) - 1)
                    a = (tau - Tk[j - 1]) / max(Tk[j] - Tk[j - 1], 1e-9)
                    P.append(Pk[j - 1] + a * (Pk[j] - Pk[j - 1])); C.append(Uk[j - 1] + a * (Uk[j] - Uk[j - 1]))
        cloud = pv.PolyData(np.array(P)); cloud['|U|'] = np.array(C)
        if pts_actor is not None:
            pl.remove_actor(pts_actor)
        pts_actor = pl.add_mesh(cloud, scalars='|U|', cmap='plasma', clim=(0.6, 1.3), point_size=7,
                                render_points_as_spheres=True,
                                scalar_bar_args=dict(title='|U| / U∞', color='white', position_x=0.7, width=0.25, height=0.05))
        ang = np.radians(-140 + 50 * f / FRAMES)                 # from upstream-left, sweeping toward the side
        pl.camera_position = [tuple(focus + np.array([2.0 * np.cos(ang), 2.0 * np.sin(ang), 0.9])), tuple(focus), (0, 0, 1)]
        w.append_data(pl.screenshot(return_img=True))
    w.close(); pl.close()
    print('saved', out, 'tracks', len(tracks), 'max travel time', round(float(tmax), 2))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
