#!/usr/bin/env python3
"""
Erzeugt aus Vid2Doppler-Zwischendaten echte Range-Doppler-Maps,
in zwei Varianten:
  1) RAW  : (T, vel*, range)  = (T, 125, 168)
  2) DEMO : (T, range, vel*)  = (T, 168, 125), log10+Clipping auf [3.4, 3.9]

Damit ist DEMO sofort in show_falsecolor o.ä. nutzbar.
"""

import os
import argparse
import numpy as np
import cv2
from config import (
    get_paths, get_frame_path,
    RANGE_MIN, RANGE_MAX, RANGE_BINS,
    VELOCITY_MIN, VELOCITY_MAX, VELOCITY_BINS, VELOCITY_MASK_BINS,
    RADAR_FPS,
    LOG_EPS, LOG_CLIP_MIN, LOG_CLIP_MAX, LOG_SCALE_DEFAULT
)

def parse_camera_position(s: str) -> np.ndarray:
    s = s.strip().replace('[','').replace(']','')
    x, y, z = (float(t.strip()) for t in s.split(','))
    return np.array([x, y, z], dtype=np.float32)

def load_frame_position_csv(path):
    """
    CSV-Spalten: x, y, z, visibility
    Rückgabe: (N,3) Positions, (N,) Visibility
    """
    assert os.path.exists(path), f"Datei nicht gefunden: {path}"
    arr = np.genfromtxt(path, delimiter=',')
    assert arr.shape[1] == 4, f"Falsche Anzahl von Spalten in {path}"

    pos = arr[:, :3].astype(np.float32)
    vis = arr[:, 3].astype(np.float32)
    return pos, vis


def load_frame_velocity_csv(path):
    """
    CSV-Spalten: radial_velocity, visibility
    Rückgabe: (N,) vel, (N,) vis
    """
    assert os.path.exists(path), f"Datei nicht gefunden: {path}"

    arr = np.genfromtxt(path, delimiter=',')
    assert arr.shape[1] == 2, f"Falsche Anzahl von Spalten in {path}"

    vel = arr[:, 0].astype(np.float32)
    vis = arr[:, 1].astype(np.float32)
    return vel, vis

def compute_distance(pos: np.ndarray, sensor_position: np.ndarray) -> np.ndarray:
    """
    Computes the distance between the sensor and the points.
    pos: (N,3) array of points
    sensor_position: (3,) array of sensor position
    Returns: (N,) array of distances
    """
    return np.linalg.norm(pos - sensor_position[None, :], axis=1) 


def zero_interpolate(data: np.ndarray) -> np.ndarray:
    """
    Füllt 0-Werte durch Mittelung der Nachbarwerte.
    data: (H, W)
    """
    kernel = np.array([[0, 1, 0],
                       [1, 0, 1],
                       [0, 1, 0]])
    kernel = kernel / np.sum(kernel)

    from scipy.signal import convolve2d

    d_filled = data.copy()
    d_mean = convolve2d(d_filled, kernel, mode='same', boundary='symm')
    d_filled[d_filled == 0] = d_mean[d_filled == 0]
    return d_filled


def create_range_doppler_histogram(range: np.ndarray, velocity: np.ndarray, visibility: np.ndarray) -> np.ndarray:
    """
    2D-Histogramm über (Range, Velocity).
    Rückgabe: (velocity, range) = (VELOCITY_BINS, RANGE_BINS)
    """
    if visibility.sum() == 0:
        return np.zeros((VELOCITY_BINS, RANGE_BINS), dtype=np.float32)

    H, _, _ = np.histogram2d(
        range[visibility], velocity[visibility],
        bins=(RANGE_BINS, VELOCITY_BINS),
        range=((RANGE_MIN, RANGE_MAX), (VELOCITY_MIN, VELOCITY_MAX)),
    )
    H = H.astype(np.float32)
    # H /= max(1, vis.sum())               # optionale Normierung
    return H.T                          # (range, velocity)

def apply_velocity_mask(H_velocity_range: np.ndarray) -> np.ndarray:
    """
    Entfernt die mittleren Doppler-Bins (DC-Notch).
    Eingabe:  (vel=128, range=168)
    Ausgabe:  (vel*=125, range=168)   (bei 3 entfernten Spalten)
    """
    if not VELOCITY_MASK_BINS:
        return H_velocity_range
    keep_indices = [i for i in range(H_velocity_range.shape[0])
                    if i not in set(VELOCITY_MASK_BINS)]
    return H_velocity_range[keep_indices, :]

def enforce_strict_visibility_equality(visibility_from_positions: np.ndarray,
                                       visibility_from_velocity: np.ndarray,
                                       frame_index: int) -> np.ndarray:
    """
    Erzwingt identische Sichtbarkeit (0/1) zwischen beiden Quellen.
    Bricht mit klarer Fehlermeldung ab, falls irgendein Vertex abweicht.
    """
    assert visibility_from_positions.shape == visibility_from_velocity.shape, \
        f"[E] Frame {frame_index:06d}: Visibility length differs: pos={visibility_from_positions.shape}, vel={visibility_from_velocity.shape}"

    visibility_from_positions = np.nan_to_num(visibility_from_positions > 0.5, nan=False)
    visibility_from_velocity = np.nan_to_num(visibility_from_velocity > 0.5, nan=False)

    mismatch_indices = np.flatnonzero(visibility_from_positions ^ visibility_from_velocity)
    if mismatch_indices.size > 0:
        raise AssertionError(f"Sichtbarkeiten unterscheiden sich im Frame {frame_index:06d}!")
    return visibility_from_positions  

def to_demo_format(H_range_velocity_masked: np.ndarray, log_scale: float, do_log_clip: bool = True) -> np.ndarray:
    """
    (vel*, range) -> (range, vel*)
    + vertikal flip (Range-Ursprung oben)
    + optional: log10 + Clipping [3.4..3.9]
    """
    H_range_velocity = H_range_velocity_masked.T  # (range, vel*)
    H_range_velocity = np.flipud(H_range_velocity)  # Range nach oben

    if not do_log_clip:
        return H_range_velocity

    # log10 & Clipping
    H_log = np.log10(H_range_velocity * float(log_scale) + LOG_EPS)
    H_log = np.clip(H_log, LOG_CLIP_MIN, LOG_CLIP_MAX)
    return H_log


def temporal_resample_to_radar_fps(frames_arr: np.ndarray, input_fps: float) -> np.ndarray:
    """
    frames_arr: (T, H, W) → Mittelung von Video-FPS auf RADAR_FPS (12.5 Hz)
    """
    if input_fps <= 0:
        return frames_arr
    window = max(1, int(round(input_fps / RADAR_FPS)))
    out = []
    for i in range(0, frames_arr.shape[0], window):
        out.append(frames_arr[i:i + window].mean(axis=0))
    return np.asarray(out, dtype=np.float32)


def auto_calibrate_log_scale(frames_rv, percentile=95, target_db=3.7):
    """
    Wählt LOG-Skalierung so, dass der P95 der Nicht-Null-Werte ~ target_db wird.
    Idee:  log10(s * x) ≈ target_db  =>  s ≈ 10^target_db / median(P95)
    """
    vals = []
    for H in frames_rv[: min(10, len(frames_rv))]:  # nimm die ersten ~10 Frames
        nz = H[H > 0]
        if nz.size:
            vals.append(np.percentile(nz, percentile))
    if not vals:
        return LOG_SCALE_DEFAULT
    p95 = float(np.median(vals))
    s = (10.0 ** target_db) / max(p95, 1e-9)
    return s


def main(args):
    video_name = os.path.basename(args.input_video).rsplit('.', 1)[0]
    paths = get_paths(video_name, args.output_folder)

    sensor_position = parse_camera_position(args.sensor_position)

    # Video-FPS lesen (für Resampling)
    cap = cv2.VideoCapture(args.input_video)
    in_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    cap.release()
    print(f"[INFO] Video-FPS: {in_fps:.3f}, RADAR_FPS: {RADAR_FPS}")

    # Alle Frame-Indizes bestimmen (anhand Positions-Dateien)
    # frame_000000.csv, frame_000001.csv, ...
    pos_dir = paths['positions']
    frames = sorted([int(f.split('_')[-1].split('.')[0]) for f in os.listdir(pos_dir) if
                     f.startswith('frame_') and f.endswith('.csv')])

    raw_velocity_range = []  # (T, vel*, range) = (T, 125, 168)
    demo_range_velocity = []  # (T, range, vel*)  = (T, 168, 125) [log10+clip]

    # Erst: ohne log skalieren, um LOG_SCALE auto zu kalibrieren
    tmp_demo_range_velocity_no_log = []

    for idx in frames:
        pos_file = get_frame_path(paths, 'positions', idx)
        vel_file = get_frame_path(paths, 'velocities', idx)

        pos, vis_p = load_frame_position_csv(pos_file)
        velocity, vis_v = load_frame_velocity_csv(vel_file)

        assert pos is not None, f"Fehlende Positions-Datei: {pos_file}"
        assert velocity is not None, f"Fehlende Velocities-Datei: {vel_file}"

        range_values = compute_distance(pos, sensor_position)
        print(f"[DBG] rng {range_values.min():.2f}..{range_values.max():.2f}  vel {velocity.min():.2f}..{velocity.max():.2f}")

        visibility = enforce_strict_visibility_equality(vis_p, vis_v, idx)

        H_range_velocity = create_range_doppler_histogram(velocity=velocity, range=range_values, visibility=visibility)  # (range=168, velocity=128)
        H_range_velocity = apply_velocity_mask(H_range_velocity)  # (range=168, velocity*=125)

        raw_velocity_range.append(H_range_velocity)
        tmp_demo_range_velocity_no_log.append(zero_interpolate(np.flipud(H_range_velocity.T)))  # (range, vel*) ohne log

    raw_velocity_range = np.asarray(raw_velocity_range, dtype=np.float32)  # (T, 125, 168)
    tmp_demo_range_velocity_no_log = np.asarray(tmp_demo_range_velocity_no_log, np.float32)  # (T, 168, 125)

    raw_velocity_range = temporal_resample_to_radar_fps(raw_velocity_range, in_fps)
    tmp_demo_range_velocity_no_log = temporal_resample_to_radar_fps(tmp_demo_range_velocity_no_log, in_fps)

    if args.log_scale == 'auto':
        log_scale = auto_calibrate_log_scale(tmp_demo_range_velocity_no_log, percentile=95, target_db=3.7)
        print(f"[INFO] auto LOG_SCALE ≈ {log_scale:.3g}")
    else:
        log_scale = float(args.log_scale)

    demo_range_velocity = np.log10(tmp_demo_range_velocity_no_log * float(log_scale) + LOG_EPS)
    demo_range_velocity = np.clip(demo_range_velocity, LOG_CLIP_MIN, LOG_CLIP_MAX).astype(np.float32)  # (T, 168, 125)

    np.save(paths['range_doppler_maps'], raw_velocity_range )
    np.save(paths['range_doppler_maps_demo'], demo_range_velocity)

    print(
        f"[OK] RAW  saved: {paths['range_doppler_maps']}        shape={raw_velocity_range.shape}  (T, vel*, range) = (T,125,168)")
    print(
        f"[OK] DEMO saved: {paths['range_doppler_maps_demo']}   shape={demo_range_velocity.shape} (T, range, vel*) = (T,168,125)")
    print(
        f"[OK] DEMO value range (min..max): {float(demo_range_velocity.min()):.3f} .. {float(demo_range_velocity.max()):.3f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_video', required=True, help='Pfad zum Eingabe-Video')
    parser.add_argument('--output_folder', default='output', help='Ausgabe-Ordner')
    parser.add_argument('--sensor_position', default='[0,0,0]', help='Position des Sensors (x,y,z)')
    parser.add_argument('--log_scale', default='auto', help="Skalierungsfaktor vor log10 (Zahl oder 'auto')")
    args = parser.parse_args()
    main(args)
