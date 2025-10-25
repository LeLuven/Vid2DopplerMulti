import os

def get_paths(video_name, output_folder):
    """Gibt alle relevanten Pfade für ein Video zurück"""
    base_path = os.path.join(output_folder, video_name)
    
    paths = {
        'base': base_path,
        'vibe': os.path.join(base_path, 'vibe'),
        'positions': os.path.join(base_path, 'positions'),
        'velocities': os.path.join(base_path, 'velocities'),
        'doppler': os.path.join(base_path, 'doppler'),
        'videos': os.path.join(base_path, 'videos'),
        
        # VIBE-Dateien
        'frames': os.path.join(base_path, 'vibe', 'frames.npy'),
        'frames_new': os.path.join(base_path, 'vibe', 'frames_new.npy'),
        'orig_cam': os.path.join(base_path, 'vibe', 'orig_cam.csv'),
        'orig_cam_new': os.path.join(base_path, 'vibe', 'orig_cam_new.csv'),
        'frame_results': os.path.join(base_path, 'vibe', 'frame_results.npy'),
        'image_folder': os.path.join(base_path, 'vibe', 'image_folder.npy'),
        'orig_width': os.path.join(base_path, 'vibe', 'orig_width.npy'),
        'orig_height': os.path.join(base_path, 'vibe', 'orig_height.npy'),
        
        # Ausgabe-Dateien
        'synth_doppler': os.path.join(base_path, 'doppler', 'synth_doppler.npy')
    }
    
    for key in ['vibe', 'positions', 'velocities', 'doppler', 'videos']:
        os.makedirs(paths[key], exist_ok=True)
    
    return paths

def get_frame_path(paths, folder_key, frame_idx):
    """Hilfsfunktion für Frame-Dateipfade"""
    return os.path.join(paths[folder_key], f'frame_{frame_idx:06d}.csv')
