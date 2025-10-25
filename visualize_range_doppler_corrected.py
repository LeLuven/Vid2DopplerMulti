#!/usr/bin/env python3
"""
Korrigierte Visualisierung der Range-Doppler-Maps
Behebt das Achsen-Orientierungsproblem
"""

import os
import argparse
import numpy as np
import cv2
from config import get_paths, RANGE_MIN, RANGE_MAX, VELOCITY_MIN, VELOCITY_MAX, EFFECTIVE_VELOCITY_BINS, RADAR_FPS

def create_false_color_frame_corrected(rd_map, frame_idx, total_frames):
    """
    Erstellt ein korrigiertes False-Color-Frame für eine Range-Doppler-Map
    Korrigiert die Achsen-Orientierung: Range (Y) x Velocity (X)
    """
    # Display-Konfiguration
    WIDTH = 1920
    HEIGHT = 1080
    
    # Korrigiere Achsen-Orientierung
    # rd_map ist (velocity_bins, range_bins) -> transponieren zu (range_bins, velocity_bins)
    rd_map_corrected = rd_map.T  # Jetzt: (range_bins, velocity_bins)
    
    # Flip 'distance origin' (analog zu demo.py)
    rd_map_corrected = np.flipud(rd_map_corrected)
    
    # Direkte Skalierung ohne Log (da Werte sehr niedrig sind)
    data_max = np.max(rd_map_corrected)
    if data_max > 0:
        # Normalisiere auf [0, 255]
        scaled = (rd_map_corrected / data_max) * 255
    else:
        scaled = np.zeros_like(rd_map_corrected)
    
    # Konvertiere zu uint8
    rd_map_uint8 = np.clip(scaled, 0, 255).astype(np.uint8)
    
    # False-Color-Mapping
    rd_map_color = cv2.applyColorMap(rd_map_uint8, cv2.COLORMAP_JET)
    
    # Canvas mit Achsen vorbereiten
    FONT = cv2.FONT_HERSHEY_SIMPLEX
    FONT_SCALE = 1.0
    FONT_THICKNESS = 2
    
    # Y-Achse (Range) - jetzt korrekt
    text_size = cv2.getTextSize("range", FONT, FONT_SCALE, FONT_THICKNESS)
    text_x = HEIGHT//2 - text_size[0][0]//2
    text_y = text_size[0][1]
    y_axis = np.ones((text_size[0][1] + text_size[1], HEIGHT, 3), dtype=np.uint8) * 255
    cv2.putText(y_axis, "range", (text_x, text_y), FONT, FONT_SCALE, (0, 0, 0), FONT_THICKNESS, cv2.LINE_AA)
    y_axis = cv2.rotate(y_axis, cv2.ROTATE_90_COUNTERCLOCKWISE)
    
    # X-Achse (Velocity) - jetzt korrekt
    text_size = cv2.getTextSize("velocity", FONT, FONT_SCALE, FONT_THICKNESS)
    text_x = WIDTH//2 - text_size[0][0]//2
    text_y = text_size[0][1]
    x_axis = np.ones((text_size[0][1] + text_size[1], WIDTH, 3), dtype=np.uint8) * 255
    cv2.putText(x_axis, "velocity", (text_x, text_y), FONT, FONT_SCALE, (0, 0, 0), FONT_THICKNESS, cv2.LINE_AA)
    
    # Hintergrund erstellen
    background = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    background[0:y_axis.shape[0], 0:y_axis.shape[1]] = y_axis
    background[HEIGHT-x_axis.shape[0]:HEIGHT+x_axis.shape[0], y_axis.shape[1]:x_axis.shape[1]] = x_axis[:,:-y_axis.shape[1]]
    
    # Verfügbare Größe für Range-Doppler-Map
    canvas_size = (HEIGHT-x_axis.shape[0], WIDTH-y_axis.shape[1])
    
    # Range-Doppler-Map skalieren
    rd_map_color = cv2.resize(rd_map_color, dsize=(canvas_size[1], canvas_size[0]), interpolation=cv2.INTER_NEAREST)
    
    # Map in Hintergrund einfügen
    background[0:canvas_size[0], y_axis.shape[1]:y_axis.shape[1] + canvas_size[1]] = rd_map_color
    
    # Frame-Info hinzufügen
    frame_text = f"Frame {frame_idx+1}/{total_frames}"
    cv2.putText(background, frame_text, (10, 30), FONT, 0.7, (255, 255, 255), 2)
    
    # Zeit-Info hinzufügen
    time_sec = frame_idx / RADAR_FPS
    time_text = f"Time: {time_sec:.2f}s"
    cv2.putText(background, time_text, (10, 60), FONT, 0.7, (255, 255, 255), 2)
    
    # Range-Info hinzufügen (Y-Achse)
    range_text = f"Range: {RANGE_MIN}-{RANGE_MAX}m (Y-Achse)"
    cv2.putText(background, range_text, (10, 90), FONT, 0.7, (255, 255, 255), 2)
    
    # Velocity-Info hinzufügen (X-Achse)
    vel_text = f"Velocity: {VELOCITY_MIN}-{VELOCITY_MAX}m/s (X-Achse)"
    cv2.putText(background, vel_text, (10, 120), FONT, 0.7, (255, 255, 255), 2)
    
    # Daten-Range-Info hinzufügen
    data_text = f"Data: {data_max:.6f} (max)"
    cv2.putText(background, data_text, (10, 150), FONT, 0.7, (255, 255, 255), 2)
    
    # Achsen-Info hinzufügen
    axes_text = f"Axes: Range={rd_map_corrected.shape[0]}x{rd_map_corrected.shape[1]}=Velocity"
    cv2.putText(background, axes_text, (10, 180), FONT, 0.7, (255, 255, 255), 2)
    
    return background

def main(args):
    print(f"Korrigierte Visualisierung der Range-Doppler-Maps für Video: {args.input_video}")
    
    # Pfade initialisieren
    video_file = args.input_video
    video_name = os.path.basename(video_file).replace('.mp4', '')
    paths = get_paths(video_name, args.output_folder)
    
    # Lade Range-Doppler-Maps
    range_doppler_path = paths['range_doppler_maps']
    if not os.path.exists(range_doppler_path):
        print(f"Fehler: Range-Doppler-Maps nicht gefunden: {range_doppler_path}")
        print("Führe zuerst compute_range_doppler.py aus!")
        return
    
    range_doppler_maps = np.load(range_doppler_path)
    print(f"Geladen: {range_doppler_maps.shape}")
    print(f"Original: (frames, velocity_bins, range_bins)")
    print(f"Nach Korrektur: (frames, range_bins, velocity_bins)")
    
    # Video-Writer initialisieren
    output_path = os.path.join(paths['videos'], f"{video_name}_range_doppler_corrected.mp4")
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    fps = RADAR_FPS
    
    # Video-Dimensionen
    WIDTH = 1920
    HEIGHT = 1080
    
    out = cv2.VideoWriter(output_path, fourcc, fps, (WIDTH, HEIGHT))
    
    print(f"Erstelle korrigiertes Video: {output_path}")
    print(f"FPS: {fps}, Auflösung: {WIDTH}x{HEIGHT}")
    
    # Verarbeite jedes Frame
    for i, rd_map in enumerate(range_doppler_maps):
        if i % 10 == 0:
            print(f"Verarbeitung Frame {i+1}/{len(range_doppler_maps)}")
        
        # Erstelle korrigiertes False-Color-Frame
        frame = create_false_color_frame_corrected(rd_map, i, len(range_doppler_maps))
        
        # Schreibe Frame
        out.write(frame)
    
    # Video schließen
    out.release()
    
    print(f"Korrigiertes Range-Doppler-Video erstellt: {output_path}")
    print(f"Gesamt-Frames: {len(range_doppler_maps)}")
    print(f"Video-Dauer: {len(range_doppler_maps) / RADAR_FPS:.2f} Sekunden")
    
    # Optional: Einzelne Frames als Bilder speichern
    if args.save_frames:
        frames_dir = os.path.join(paths['videos'], f"{video_name}_range_doppler_frames_corrected")
        os.makedirs(frames_dir, exist_ok=True)
        
        print(f"Speichere korrigierte Einzel-Frames in: {frames_dir}")
        for i, rd_map in enumerate(range_doppler_maps):
            frame = create_false_color_frame_corrected(rd_map, i, len(range_doppler_maps))
            frame_path = os.path.join(frames_dir, f"frame_{i:06d}.png")
            cv2.imwrite(frame_path, frame)
        
        print(f"Korrigierte Einzel-Frames gespeichert: {len(range_doppler_maps)} Bilder")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Korrigierte Visualisierung der Range-Doppler-Maps')
    parser.add_argument('--input_video', required=True, help='Pfad zum Eingabe-Video')
    parser.add_argument('--output_folder', default='output', help='Ausgabe-Ordner')
    parser.add_argument('--save_frames', action='store_true', help='Einzel-Frames als Bilder speichern')
    
    args = parser.parse_args()
    main(args)

