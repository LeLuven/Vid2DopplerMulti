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
    print(f"=== Starte Pipeline für {video_name} ===")
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
    print("\n[5/5] Doppler-Daten generieren...")
    os.system(f"python compute_synth_doppler.py --input_video {args.input_video} --output_folder {output_folder}")
    
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
    
    print(f"\n=== Pipeline abgeschlossen für {video_name} ===")
    print(f"Ergebnisse in: {paths['base']}")
    print("\nGenerierte Ordnerstruktur:")
    print(f" {paths['vibe']} - VIBE-Daten")
    print(f" {paths['positions']} - Positionen")
    print(f" {paths['velocities']} - Geschwindigkeiten")
    print(f" {paths['doppler']} - Doppler-Daten")
    print(f" {paths['videos']} - Videos")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Führt die komplette Vid2DopplerMulti Pipeline aus')
    
    parser.add_argument('--input_video', type=str, required=True, help='Input video file')
    parser.add_argument('--output_folder', type=str, default='output', help='Output folder (default: output)')
    parser.add_argument('--visualize_mesh', action='store_true', help='Render visibility mesh and velocity map')
    parser.add_argument('--model_path', type=str, help='Path to DL models')
    parser.add_argument('--doppler_gt', action='store_true', help='Doppler Ground Truth is available for reference')
    
    args = parser.parse_args()
    main(args)
