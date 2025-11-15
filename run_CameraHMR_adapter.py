# DATEI: ~/git/Vid2DopplerMulti/run_CameraHMR_adapter_v2.py

import argparse
import os
import shutil
import numpy as np
import cv2
import subprocess
import glob 
from tqdm import tqdm
from config import get_paths

# ... (Funktionen video_to_frames, get_video_metadata, load_vertices_from_obj, get_mesh_center bleiben 1:1 gleich) ...
def video_to_frames(video_path, frames_dir):
    os.makedirs(frames_dir, exist_ok=True)
    cmd = [
        "ffmpeg", "-i", video_path,
        "-f", "image2",
        "-v", "error",
        f"{frames_dir}/frame_%06d.png"
    ]
    print(f"Extrahiere Frames nach: {frames_dir}")
    subprocess.run(cmd)
    return len(os.listdir(frames_dir))

def get_video_metadata(video_path):
    video = cv2.VideoCapture(video_path)
    if not video.isOpened():
        raise IOError(f"Konnte Video nicht öffnen: {video_path}")
    orig_width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
    video.release()
    return orig_width, orig_height, total_frames

def load_vertices_from_obj(obj_path, expected_vertices=6890):
    vertices = []
    try:
        with open(obj_path, 'r') as f:
            for line in f:
                if line.startswith('v '): 
                    parts = line.split()
                    vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
    except IOError as e:
        print(f"[WARNUNG] Konnte {obj_path} nicht lesen: {e}")
        return None
    
    verts_array = np.array(vertices)
    
    if verts_array.shape[0] != expected_vertices:
         print(f"[WARNUNG] {obj_path}: Falsche Vertex-Anzahl! "
               f"Erwartet={expected_vertices}, Gefunden={verts_array.shape[0]}. Überspringe Mesh.")
         return None
    return verts_array

def get_mesh_center(vertices):
    return np.mean(vertices, axis=0)

def main(args):
    video_name = os.path.basename(args.input_video).replace('.mp4', '')
    paths = get_paths(video_name, args.output_folder)

    # --- SCHRITT 1 & 2: Pfade vorbereiten und Frames extrahieren ---
    print(f"[INFO] Verarbeite Video: {video_name}")
    os.makedirs(paths['vibe'], exist_ok=True)
    orig_width, orig_height, total_frames = get_video_metadata(args.input_video)
    
    # Hole die ABSOLUTEN Pfade
    temp_frames_dir = os.path.abspath(os.path.join(paths['base'], "temp_hmr_frames"))
    hmr_output_dir = os.path.abspath(os.path.join(paths['base'], "hmr_raw_output"))
    
    num_extracted_frames = video_to_frames(args.input_video, temp_frames_dir)
    print(f"[INFO] {num_extracted_frames} Frames extrahiert.")
    total_frames = num_extracted_frames 

    # --- SCHRITT 3: HMR-Demo (NEUES SKRIPT) ausführen ---
    print(f"[INFO] Führe HMR-Export-Skript in 'camerahmr'-Umgebung aus...")
    hmr_repo_dir = os.path.expanduser("~/git/CameraHMR") 
    hmr_export_script_path = os.path.join(hmr_repo_dir, "export_all_meshes.py") 
    hmr_env_lib_path = os.path.expanduser("~/anaconda3/envs/camerahmr/lib") 

    # --- KORREKTUR: KEINE relativen Pfade mehr. ---
    # Wir übergeben die absoluten Pfade temp_frames_dir und hmr_output_dir direkt.

    cmd = [
        "conda", "run", "-n", "camerahmr",
        "env", f"LD_LIBRARY_PATH={hmr_env_lib_path}:$LD_LIBRARY_PATH",
        "python", hmr_export_script_path, 
        "--image_folder", temp_frames_dir,     # <-- ABSOLUTER PFAD
        "--output_folder", hmr_output_dir    # <-- ABSOLUTER PFAD
    ]
    subprocess.run(cmd, cwd=hmr_repo_dir) # cwd ist immer noch HMR, für die Imports
    print(f"[INFO] HMR-Export abgeschlossen. Ergebnisse in: {hmr_output_dir}")

    # --- SCHRITT 4: HMR-Daten konvertieren (MIT TRACKING) ---
    print(f"[INFO] Konvertiere HMR-Daten mit Tracking in VIBE-Format...")
    
    all_frame_results = []
    dummy_cam_data = []
    frames_list = []

    last_known_position = None

    for i in tqdm(range(total_frames), desc="Tracking Person"):
        frame_index_1_based = i + 1
        frame_index_0_based = i
        
        frame_basename = f"frame_{frame_index_1_based:06d}"
        
        search_pattern = os.path.join(hmr_output_dir, f"{frame_basename}_*.obj")
        found_files = sorted(glob.glob(search_pattern))
        
        if not found_files:
            print(f"[WARNUNG] Frame {i}: Keine Person gefunden. Verwende leere Daten.")
            verts = np.zeros((6890, 3))
            last_known_position = None 
        else:
            candidates = []
            for f_path in found_files:
                v = load_vertices_from_obj(f_path)
                if v is not None:
                    candidates.append({
                        'vertices': v,
                        'center': get_mesh_center(v),
                        'path': f_path
                    })
            
            if not candidates:
                 print(f"[WARNUNG] Frame {i}: Personen-Dateien gefunden, aber keine gültigen Meshes. Verwende leere Daten.")
                 verts = np.zeros((6890, 3))
                 last_known_position = None
                 continue

            if last_known_position is None:
                best_match = candidates[0]
                print(f"[INFO] Frame {i}: Tracker initialisiert. Folge {os.path.basename(best_match['path'])}.")
            else:
                distances = [np.linalg.norm(c['center'] - last_known_position) for c in candidates]
                best_match_index = np.argmin(distances)
                best_match = candidates[best_match_index]
                
                if np.min(distances) > 1.0:
                     print(f"[INFO] Frame {i}: Tracking verloren (Distanz {np.min(distances):.2f}m). Wähle nächste Person.")
                
            verts = best_match['vertices']
            last_known_position = best_match['center']

        # 4.1. frame_results.npy
        frame_dict = {
            0: { 'verts': verts, 'pose': [], 'pred_cam': [], 'bboxes': [], 'frame_ids': frame_index_0_based }
        }
        all_frame_results.append(frame_dict)
        
        # 4.2. frames.npy
        frames_list.append(frame_index_0_based) 
        
        # 4.3. orig_cam.csv (Dummy-Daten)
        dummy_cam_data.append([1.0, 0.0, 0.0]) 

    np.save(paths['frame_results'], np.array(all_frame_results))
    np.save(paths['frames'], np.array(frames_list))
    np.savetxt(paths['orig_cam'], np.array(dummy_cam_data), delimiter=",")

    np.save(paths['orig_width'], orig_width)
    np.save(paths['orig_height'], orig_height)
    np.save(paths['image_folder'], temp_frames_dir) 

    print(f"[INFO] VIBE-kompatible Dateien in {paths['vibe']} gespeichert.")

    # --- SCHRITT 5 (Aufräumen) ---
    if not args.keep_temp_files:
        print(f"[INFO] Lösche temporären Frame-Ordner: {temp_frames_dir}")
        shutil.rmtree(temp_frames_dir)
        print(f"[INFO] Lösche HMR-Rohdaten-Ordner: {hmr_output_dir}")
        shutil.rmtree(hmr_output_dir)
    
    print(f"\n=== CameraHMR-Adapter v2.1 (Absolute Paths) erfolgreich abgeschlossen für {video_name} ===")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Adapter v2.1 für CameraHMR (mit Tracking, absoluten Pfaden) für die Vid2Doppler-Pipeline")
    parser.add_argument('--input_video', type=str, required=True, help='Input-Videodatei')
    parser.add_argument('--output_folder', type=str, default='output', help='Basis-Output-Ordner')
    parser.add_argument('--keep_temp_files', action='store_true', help='Temporäre Frame- und HMR-Ordner nicht löschen')
    
    args = parser.parse_args()
    main(args)