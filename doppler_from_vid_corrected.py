#!/usr/bin/env python3
"""
Korrigierte Hauptpipeline mit Range-Doppler-Features
Verwendet die korrigierte Visualisierung mit richtiger Achsen-Orientierung
"""

import argparse
import os
import numpy as np
import shutil
from config import get_paths

def main(args):
    # Video-Name extrahieren
    video_name = os.path.basename(args.input_video).replace('.mp4', '')
    
    # Output-Ordner festlegen
    output_folder = args.output_folder if hasattr(args, 'output_folder') and args.output_folder else "output"
    
    # Pipeline ausführen
    print(f"=== Starte korrigierte Pipeline für {video_name} ===")
    print(f"Input Video: {args.input_video}")
    print(f"Output Folder: {output_folder}")
    
    # 1. VIBE
    print("\n[1/5] VIBE-Verarbeitung...")
    os.system(f"python run_VIBE.py --input_video {args.input_video} --output_folder {output_folder}")
    
    # 2. Positionen berechnen
    print("\n[2/5] Positionen berechnen...")
    os.system(f"python compute_position.py --input_video {args.input_video} --output_folder {output_folder}")
    
    # 3. Frames interpolieren
    print("\n[3/5] Frames interpolieren...")
    os.system(f"python interpolate_frames.py --input_video {args.input_video} --output_folder {output_folder}")
    
    # 4. Geschwindigkeiten berechnen
    print("\n[4/5] Geschwindigkeiten berechnen...")
    os.system(f"python compute_velocity.py --input_video {args.input_video} --output_folder {output_folder}")
    
    # 5. Doppler-Daten generieren
    print("\n[5/7] Doppler-Daten generieren...")
    os.system(f"python compute_synth_doppler.py --input_video {args.input_video} --output_folder {output_folder}")
    
    # 6. Range-Doppler-Maps generieren
    print("\n[6/7] Range-Doppler-Maps generieren...")
    interpolate_flag = "--interpolate" if args.interpolate else ""
    os.system(f"python compute_range_doppler.py --input_video {args.input_video} --output_folder {output_folder} {interpolate_flag}")
    
    # 7. Korrigierte Range-Doppler-Visualisierung
    if args.visualize_rd:
        print("\n[7/7] Korrigierte Range-Doppler-Visualisierung...")
        save_frames_flag = "--save_frames" if args.save_frames else ""
        os.system(f"python visualize_range_doppler_corrected.py --input_video {args.input_video} --output_folder {output_folder} {save_frames_flag}")
    
    # Optional: Mesh-Visualisierung
    if args.visualize_mesh:
        print("\n[Optional] Mesh-Visualisierung...")
        os.system(f"python compute_visualization.py --input_video {args.input_video} --output_folder {output_folder} --wireframe")
    
    # Optional: Doppler-Plot
    if args.doppler_gt and args.model_path:
        print("\n[Optional] Doppler-Plot mit Ground Truth...")
        os.system(f"python plot_synth_dop.py --input_video {args.input_video} --model_path {args.model_path} --doppler_gt")
    elif args.model_path:
        print("\n[Optional] Doppler-Plot...")
        os.system(f"python plot_synth_dop.py --input_video {args.input_video} --model_path {args.model_path}")
    
    # Temporäre Dateien aufräumen
    try:
        paths = get_paths(video_name, output_folder)
        image_folder = str(np.load(paths['image_folder']))
        if os.path.exists(image_folder):
            shutil.rmtree(image_folder)
            print(f"\nTemporäre Bilddateien entfernt: {image_folder}")
    except Exception as e:
        print(f"\nWarnung: Konnte temporäre Dateien nicht entfernen: {e}")
    
    print(f"\n=== Korrigierte Pipeline abgeschlossen für {video_name} ===")
    print(f"Ergebnisse in: {paths['base']}")
    print("\nGenerierte Ordnerstruktur:")
    print(f" {paths['vibe']} - VIBE-Daten")
    print(f" {paths['positions']} - Positionen")
    print(f" {paths['velocities']} - Geschwindigkeiten")
    print(f" {paths['doppler']} - Doppler-Daten")
    print(f" {paths['videos']} - Videos")
    
    # Zeige Range-Doppler-Ergebnisse
    if os.path.exists(paths['range_doppler_maps']):
        rd_maps = np.load(paths['range_doppler_maps'])
        print(f"\nRange-Doppler-Maps erstellt:")
        print(f" Shape: {rd_maps.shape}")
        print(f" Orientierung: (frames, velocity_bins, range_bins)")
        print(f" Dauer: {rd_maps.shape[0] / 12.5:.2f} Sekunden")
        print(f" Datei: {paths['range_doppler_maps']}")
        print(f" Daten-Range: {rd_maps.min():.8f} bis {rd_maps.max():.8f}")
    
    if args.visualize_rd:
        corrected_path = os.path.join(paths['videos'], f"{video_name}_range_doppler_corrected.mp4")
        
        if os.path.exists(corrected_path):
            print(f"\nKorrigiertes Range-Doppler-Video erstellt:")
            print(f" Datei: {corrected_path}")
            print(f" Achsen-Orientierung: Range (Y) x Velocity (X)")
            print(f" Dimensionen: 168 Range-Bins x 125 Velocity-Bins")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Führt die korrigierte Vid2DopplerMulti Pipeline aus')
    
    parser.add_argument('--input_video', type=str, required=True, help='Input video file')
    parser.add_argument('--output_folder', type=str, default='output', help='Output folder (default: output)')
    parser.add_argument('--visualize_mesh', action='store_true', help='Render visibility mesh and velocity map')
    parser.add_argument('--visualize_rd', action='store_true', help='Create corrected Range-Doppler visualization video')
    parser.add_argument('--interpolate', action='store_true', help='Apply zero-interpolation to Range-Doppler maps')
    parser.add_argument('--save_frames', action='store_true', help='Save individual Range-Doppler frames as images')
    parser.add_argument('--model_path', type=str, help='Path to DL models')
    parser.add_argument('--doppler_gt', action='store_true', help='Doppler Ground Truth is available for reference')
    
    args = parser.parse_args()
    main(args)

