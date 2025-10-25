#!/usr/bin/env python3
"""
Konvertierung der synthetischen Doppler-Daten in Radar-Format (168 x 125 Range-Doppler Maps)
"""

import os
import argparse
import numpy as np
import pandas as pd
from config import get_paths, get_frame_path, RANGE_MIN, RANGE_MAX, RANGE_BINS, VELOCITY_MIN, VELOCITY_MAX, VELOCITY_BINS, VELOCITY_MASK_BINS, RADAR_FPS, EFFECTIVE_VELOCITY_BINS

def calculate_range_from_positions(positions_df):
    """
    Berechnet Range aus 3D-Vertex-Positionen
    Fallback: Wenn keine Kamera-Info, nimm z-Koordinate als Tiefe
    """
    # Da CSV ohne Header geladen wird, verwende Spalten-Indizes
    # Spalten: x, y, z, visibility
    if positions_df.shape[1] >= 3:
        # Euklidische Distanz vom Kamera-Ursprung
        ranges = np.sqrt(positions_df.iloc[:, 0]**2 + positions_df.iloc[:, 1]**2 + positions_df.iloc[:, 2]**2)
    else:
        # Fallback: z-Koordinate als Tiefe
        ranges = positions_df.iloc[:, 2]  # Annahme: z ist in Spalte 2
    
    return ranges

def create_range_doppler_histogram(velocities, ranges, visibility):
    """
    Erstellt 2D-Histogramm (Range x Velocity) für ein Frame
    """
    # Filtere nur sichtbare Vertices
    visible_mask = visibility > 0.5
    visible_velocities = velocities[visible_mask]
    visible_ranges = ranges[visible_mask]
    
    if len(visible_velocities) == 0:
        # Leeres Histogramm wenn keine sichtbaren Vertices
        return np.zeros((RANGE_BINS, VELOCITY_BINS), dtype=np.float32)
    
    # Erstelle 2D-Histogramm
    histogram, _, _ = np.histogram2d(
        visible_ranges, 
        visible_velocities,
        bins=[RANGE_BINS, VELOCITY_BINS],
        range=[[RANGE_MIN, RANGE_MAX], [VELOCITY_MIN, VELOCITY_MAX]]
    )
    
    # Normalisiere durch Anzahl sichtbarer Vertices
    histogram = histogram.astype(np.float32)
    if len(visible_velocities) > 0:
        histogram /= len(visible_velocities)
    
    return histogram.T  # Transponieren für korrekte Orientierung (velocity x range)

def apply_velocity_masking(histogram):
    """
    Entfernt mittlere 3 Doppler-Bins (analog zu demo.py)
    """
    # Entferne Bins bei ~0 m/s
    masked_histogram = np.delete(histogram, VELOCITY_MASK_BINS, axis=0)
    return masked_histogram

def zero_interpolation(data):
    """
    Implementiert Convolution-basierte Interpolation für Null-Werte
    """
    kernel = np.array([[0, 1, 0],
                       [1, 0, 1],
                       [0, 1, 0]])
    kernel = kernel / np.sum(kernel)
    
    for t in range(data.shape[0]):
        d = data[t].copy()
        d_mean = np.zeros_like(d)
        
        # Convolution für jeden Channel separat
        for i in range(d.shape[1]):
            d_mean[:, i] = np.convolve(d[:, i], kernel[1, :], mode='same')
        
        # Fülle nur Null-Werte
        d[d == 0] = d_mean[d == 0]
        data[t] = d
    
    return data

def temporal_resampling(range_doppler_maps, video_fps):
    """
    Downsampling von Video-FPS auf Radar-FPS durch Frame-Mittelung
    """
    window_size = int(video_fps / RADAR_FPS)
    num_frames = len(range_doppler_maps)
    num_radar_frames = int(num_frames / window_size)
    
    resampled_maps = []
    
    for i in range(num_radar_frames):
        start_idx = i * window_size
        end_idx = min(start_idx + window_size, num_frames)
        
        # Mittelwert über Zeitfenster
        window_maps = range_doppler_maps[start_idx:end_idx]
        averaged_map = np.mean(window_maps, axis=0)
        resampled_maps.append(averaged_map)
    
    return np.array(resampled_maps, dtype=np.float32)

def main(args):
    print(f"Konvertierung zu Range-Doppler-Maps für Video: {args.input_video}")
    
    # Pfade initialisieren
    video_file = args.input_video
    video_name = os.path.basename(video_file).replace('.mp4', '')
    paths = get_paths(video_name, args.output_folder)
    
    # Lade Frame-Informationen
    frames = np.load(paths['frames'], allow_pickle=True)
    print(f"Verarbeitung von {len(frames)} Frames")
    
    # Bestimme Video-FPS aus Frame-Anzahl und geschätzter Dauer
    # Annahme: ~24s Video basierend auf vorherigen Tests
    estimated_duration = 24.0  # Sekunden
    video_fps = len(frames) / estimated_duration
    print(f"Geschätzte Video-FPS: {video_fps:.1f}")
    
    range_doppler_maps = []
    
    # Verarbeite jedes Frame
    for i, frame_idx in enumerate(frames):
        if i % 100 == 0:
            print(f"Verarbeitung Frame {i+1}/{len(frames)} (Frame {frame_idx})")
        
        try:
            # Lade Positionen und Geschwindigkeiten
            positions_path = get_frame_path(paths, 'positions', frame_idx)
            velocities_path = get_frame_path(paths, 'velocities', frame_idx)
            
            if not os.path.exists(positions_path) or not os.path.exists(velocities_path):
                print(f"Warnung: Frame {frame_idx} nicht gefunden, überspringe...")
                continue
            
            # Lade Daten (ohne Header, da erste Zeile Daten enthält)
            positions_df = pd.read_csv(positions_path, header=None)
            velocities_df = pd.read_csv(velocities_path, header=None)
            
            # Berechne Range aus Positionen
            ranges = calculate_range_from_positions(positions_df)
            
            # Extrahiere Geschwindigkeiten und Visibility
            velocities = velocities_df.iloc[:, 0].values  # Spalte 0: radiale Geschwindigkeit
            visibility = velocities_df.iloc[:, 1].values  # Spalte 1: visibility
            
            # Erstelle Range-Doppler-Histogramm
            histogram = create_range_doppler_histogram(velocities, ranges, visibility)
            
            # Wende Velocity-Maskierung an
            masked_histogram = apply_velocity_masking(histogram)
            
            range_doppler_maps.append(masked_histogram)
            
        except Exception as e:
            print(f"Fehler bei Frame {frame_idx}: {e}")
            continue
    
    if len(range_doppler_maps) == 0:
        print("Fehler: Keine Range-Doppler-Maps erstellt!")
        return
    
    range_doppler_maps = np.array(range_doppler_maps, dtype=np.float32)
    print(f"Erstellt {len(range_doppler_maps)} Range-Doppler-Maps mit Shape: {range_doppler_maps.shape}")
    
    # Optional: Zero-Interpolation
    if args.interpolate:
        print("Wende Zero-Interpolation an...")
        range_doppler_maps = zero_interpolation(range_doppler_maps)
    
    # Temporal Resampling
    print(f"Temporal Resampling von {video_fps:.1f} Hz auf {RADAR_FPS} Hz...")
    resampled_maps = temporal_resampling(range_doppler_maps, video_fps)
    print(f"Resampled zu {len(resampled_maps)} Radar-Frames")
    
    # Speichere Ergebnis
    output_path = paths['range_doppler_maps']
    np.save(output_path, resampled_maps)
    print(f"Range-Doppler-Maps gespeichert: {output_path}")
    print(f"Finale Shape: {resampled_maps.shape}")
    print(f"Daten-Range: {resampled_maps.min():.6f} bis {resampled_maps.max():.6f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Konvertierung zu Range-Doppler-Maps')
    parser.add_argument('--input_video', required=True, help='Pfad zum Eingabe-Video')
    parser.add_argument('--output_folder', default='output', help='Ausgabe-Ordner')
    parser.add_argument('--interpolate', action='store_true', help='Zero-Interpolation aktivieren')
    
    args = parser.parse_args()
    main(args)
