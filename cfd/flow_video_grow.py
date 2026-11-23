"""CFD-style flow video: streamlines grow from an upstream rake and wrap around the body, coloured by velocity
(rainbow), on a light background, with a slow camera sweep. Steady RANS solution, so the growth is the fluid's
travel time along each streamline (U_inf = 1), not unsteady flow.

    python cfd/flow_video_grow.py runs/pilot_full/front_Re3e6 results/pilot/video_front_Re3e6.mp4
"""
import json, os, sys
import numpy as np
import pyvista as pv
import imageio.v2 as imageio

pv.OFF_SCREEN = True
FRAMES, FPS, HOLD = 180, 30, 45


def main(case, out):
    m = json.load(open(os.path.join(case, 'case.json')))
    open(os.path.join(case, 'case.foam'), 'w').close()
    r = pv.OpenFOAMReader(os.path.join(case, 'case.foam')); r.set_active_time_value(r.time_values[-1]); r.enable_all_patch_arrays()
    data = r.read()
    vol = data['internalMesh'].cell_data_to_point_data()
    body = data['boundary']['body'].extract_surface().cell_data_to_point_data()
    lo, hi = np.array(m['bbox_lo']), np.array(m['bbox_hi'])
    hy, hz = hi[1] - lo[1], hi[2] - lo[2]
    # two crossed rakes (horizontal and vertical) just upstream of the nose, denser close to the body axis
    rakes = []
    for size, res, axis in ((max(hy, hz) * 2.2, 70, 'y'), (max(hy, hz) * 2.2, 70, 'z')):
        s = np.sign(np.linspace(-1, 1, res)) * np.linspace(-1, 1, res) ** 2 * size / 2
        for off in (-0.012, 0.012):
            p = np.zeros((res, 3)); p[:, 0] = lo[0] - 0.12
            p[:, 1 if axis == 'y' else 2] = s; p[:, 2 if axis == 'y' else 1] = off
            rakes.append(p)
    seeds = pv.PolyData(np.vstack(rakes))
    sl = vol.streamlines_from_source(seeds, vectors='U', max_length=4.5, integration_direction='forward', max_step_length=0.01, max_steps=40000)
    tracks = []
    for i in range(sl.n_cells):
        ids = sl.get_cell(i).point_ids
        if len(ids) > 10:
            tracks.append((sl.points[ids], sl['IntegrationTime'][ids], np.linalg.norm(sl['U'][ids], axis=1)))
    tmax = max(t[1][-1] for t in tracks)

    pl = pv.Plotter(off_screen=True, window_size=(1280, 720))
    pl.set_background('#eef3f8', top='#b9cde3')
    pl.add_mesh(body, color='#9aa3ab', smooth_shading=True, specular=0.4)
    pl.add_text(f"Flow around an AUV hull (REMUS-like, v{m['variant']:02d}) · Re = {m['Re']:.0e} · steady RANS k-ω SST",
                font_size=11, color='#22303a')
    focus = np.array([(lo[0] + hi[0]) / 2 + 0.2, 0, 0])
    actor = None
    w = imageio.get_writer(out, fps=FPS, quality=8, macro_block_size=8)
    for f in range(FRAMES + HOLD):
        tau = min(f, FRAMES) / FRAMES * tmax
        pts, sc, lines, n = [], [], [], 0
        for P, T, U in tracks:
            k = np.searchsorted(T, tau)
            if k < 2:
                continue
            pts.append(P[:k]); sc.append(U[:k]); lines.append(np.r_[k, np.arange(n, n + k)]); n += k
        if pts:
            poly = pv.PolyData(np.vstack(pts), lines=np.concatenate(lines)); poly['|U| / U∞'] = np.concatenate(sc)
            if actor is not None:
                pl.remove_actor(actor)
            actor = pl.add_mesh(poly, scalars='|U| / U∞', cmap='turbo', clim=(0.55, 1.15), line_width=2.5,
                                render_lines_as_tubes=True,
                                scalar_bar_args=dict(title='|U| / U∞', color='#22303a', position_x=0.7, position_y=0.05,
                                                     width=0.25, height=0.05))
        ang = np.radians(-125 + 55 * f / (FRAMES + HOLD))
        pl.camera_position = [tuple(focus + np.array([1.25 * np.cos(ang), 1.25 * np.sin(ang), 0.45])), tuple(focus), (0, 0, 1)]
        w.append_data(pl.screenshot(return_img=True))
    w.close(); pl.close()
    print('saved', out, 'streamlines', len(tracks), 'travel time', round(float(tmax), 2))


if __name__ == '__main__':
    os.makedirs(os.path.dirname(sys.argv[2]), exist_ok=True)
    main(sys.argv[1], sys.argv[2])
