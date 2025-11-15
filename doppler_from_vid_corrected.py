import argparse
import os
import numpy as np
import shutil
from config import get_paths
import sys
import subprocess

def main(args):
    # Video-Name extrahieren
    video_name = os.path.basename(args.input_video).replace('.mp4', '')
    
    # Output-Ordner festlegen
    output_folder = args.output_folder if hasattr(args, 'output_folder') and args.output_folder else "output"
    
    # Pipeline ausführen
    print(f"=== Starte korrigierte Pipeline für {video_name} ===")
    print(f"Input Video: {args.input_video}")
    print(f"Output Folder: {output_folder}")

    try:
        # 1. VIBE
        print("\n[1/7] VIBE-Verarbeitung...")
        cmd_vibe = [
            sys.executable, "run_VIBE.py",
            "--input_video", args.input_video,
            "--output_folder", output_folder,
        ]
        subprocess.run(cmd_vibe, check=True)

        # 2. Positionen berechnen
        print("\n[2/7] Positionen berechnen...")
        cmd_pos = [
            sys.executable, "compute_position.py",
            "--input_video", args.input_video,
            "--output_folder", output_folder,
        ]
        subprocess.run(cmd_pos, check=True)

        # 3. Frames interpolieren
        print("\n[3/7] Frames interpolieren...")
        cmd_interp = [
            sys.executable, "interpolate_frames.py",
            "--input_video", args.input_video,
            "--output_folder", output_folder,
        ]
        subprocess.run(cmd_interp, check=True)

        # 4. Geschwindigkeiten berechnen
        print("\n[4/7] Geschwindigkeiten berechnen...")
        cmd_vel = [
            sys.executable, "compute_velocity.py",
            "--input_video", args.input_video,
            "--output_folder", output_folder,
        ]
        subprocess.run(cmd_vel, check=True)

        # 5. Doppler-Daten generieren
        print("\n[5/7] Doppler-Daten generieren...")
        cmd_doppler = [
            sys.executable, "compute_synth_doppler.py",
            "--input_video", args.input_video,
            "--output_folder", output_folder,
        ]
        subprocess.run(cmd_doppler, check=True)

        # 6. Range-Doppler-Maps generieren
        print("\n[6/7] Range-Doppler-Maps generieren...")
        cmd_rd = [
            sys.executable, "compute_range_doppler.py",
            "--input_video", args.input_video,
            "--output_folder", output_folder,
        ]
        if args.interpolate:
            cmd_rd.append("--interpolate")
        subprocess.run(cmd_rd, check=True)

        # 7. Korrigierte Range-Doppler-Visualisierung
        if args.visualize_rd:
            print("\n[7/7] Korrigierte Range-Doppler-Visualisierung...")
            cmd_vis = [
                sys.executable, "visualize_range_doppler_corrected.py",
                "--input_video", args.input_video,
                "--output_folder", output_folder,
            ]
            if args.save_frames:
                cmd_vis.append("--save_frames")
            subprocess.run(cmd_vis, check=True)

        # Optional: Mesh-Visualisierung
        if args.visualize_mesh:
            print("\n[Optional] Mesh-Visualisierung...")
            cmd_mesh = [
                sys.executable, "compute_visualization.py",
                "--input_video", args.input_video,
                "--output_folder", output_folder,
                "--wireframe",
            ]
            subprocess.run(cmd_mesh, check=True)

        # Optional: Doppler-Plot
        if args.doppler_gt and args.model_path:
            print("\n[Optional] Doppler-Plot mit Ground Truth...")
            cmd_plot_gt = [
                sys.executable, "plot_synth_dop.py",
                "--input_video", args.input_video,
                "--model_path", args.model_path,
                "--doppler_gt",
            ]
            subprocess.run(cmd_plot_gt, check=True)
        elif args.model_path:
            print("\n[Optional] Doppler-Plot...")
            cmd_plot = [
                sys.executable, "plot_synth_dop.py",
                "--input_video", args.input_video,
                "--model_path", args.model_path,
            ]
            subprocess.run(cmd_plot, check=True)

    except subprocess.CalledProcessError as e:
        print("\n\n!!! FEHLER: Ein Sub-Skript ist fehlgeschlagen !!!")
        try:
            print(f"Befehl: {' '.join(e.cmd)}")
        except Exception:
            pass
        print(f"Exit-Code: {e.returncode}")
        print("Das Skript wird abgebrochen. Bitte behebe den Fehler im obigen Skript.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n!!! Ein unerwarteter Fehler ist aufgetreten: {e} !!!")
        sys.exit(1)
    
    # Temporäre Dateien aufräumen
    try:
        paths = get_paths(video_name, output_folder)
        image_folder_path = paths['image_folder']
        # Lade den Pfad aus der .npy-Datei
        if os.path.exists(image_folder_path):
            image_folder = str(np.load(image_folder_path))
            if os.path.exists(image_folder):
                shutil.rmtree(image_folder)
                print(f"\nTemporäre Bilddateien entfernt: {image_folder}")
        else:
             print(f"\nWarnung: 'image_folder.npy' nicht gefunden unter {image_folder_path}, konnte temporäre Dateien nicht löschen.")
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

