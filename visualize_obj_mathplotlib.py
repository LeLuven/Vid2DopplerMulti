import os
import numpy as np
import matplotlib.pyplot as plt
import argparse
import sys

# Die Anzahl der Vertices pro Person (Standard für SMPL-Modelle)
VERTICES_PER_PERSON = 6890

def load_all_vertices(obj_path):
    """Liest ALLE 'v'-Zeilen aus einer .obj-Datei."""
    vertices = []
    try:
        with open(obj_path, 'r') as f:
            for line in f:
                if line.startswith('v '):
                    parts = line.split()
                    vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
    except IOError as e:
        print(f"Fehler beim Lesen der Datei: {e}")
        return None
    
    return np.array(vertices)

def main():
    parser = argparse.ArgumentParser(description="Visualisiert Personen-Punktwolken aus einer .obj-Datei mit Matplotlib.")
    parser.add_argument('obj_file', type=str, help='Pfad zur .obj-Datei, die visualisiert werden soll.')
    args = parser.parse_args()

    print(f"Lade Vertices aus: {args.obj_file}")
    all_vertices = load_all_vertices(args.obj_file)
    
    if all_vertices is None or all_vertices.shape[0] == 0:
        print("Keine Vertices gefunden. Beende.")
        sys.exit(1)
        
    total_verts = all_vertices.shape[0]
    print(f"Insgesamt {total_verts} Vertices gefunden.")

    # --- Trenne die Personen ---
    end_p1 = min(VERTICES_PER_PERSON, total_verts)
    person1_verts = all_vertices[0:end_p1]
    
    person2_verts = None
    if total_verts > VERTICES_PER_PERSON:
        person2_verts = all_vertices[VERTICES_PER_PERSON:]
        print(f"Person 1 (Rot): {person1_verts.shape[0]} Vertices")
        print(f"Person 2 (Blau): {person2_verts.shape[0]} Vertices")
    else:
        print(f"Person 1 (Rot): {person1_verts.shape[0]} Vertices")

    # --- Matplotlib 3D-Plot ---
    print("\nStarte Visualisierung. (Fenster schließen, um fortzufahren)...")
    
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')
    
    # Plotte Person 1 in Rot
    # s=1 setzt die Punktgröße auf sehr klein
    ax.scatter(person1_verts[:, 0], person1_verts[:, 1], person1_verts[:, 2], 
               c='r', s=1, label='Person 1 (Erste 6890 Vertices)')
    
    # Plotte Person 2 in Blau, falls vorhanden
    if person2_verts is not None and person2_verts.shape[0] > 0:
        ax.scatter(person2_verts[:, 0], person2_verts[:, 1], person2_verts[:, 2], 
                   c='b', s=1, label='Person 2 (Restliche Vertices)')

    ax.set_xlabel('X-Achse')
    ax.set_ylabel('Y-Achse')
    ax.set_zlabel('Z-Achse')
    ax.legend()
    
    # Setze gleiche Skalierung für alle Achsen, um Verzerrungen zu vermeiden
    max_range = np.array([person1_verts.max(axis=0) - person1_verts.min(axis=0)]).max() / 2.0
    mid = person1_verts.mean(axis=0)
    ax.set_xlim(mid[0] - max_range, mid[0] + max_range)
    ax.set_ylim(mid[1] - max_range, mid[1] + max_range)
    ax.set_zlim(mid[2] - max_range, mid[2] + max_range)
    
    plt.title(f"{os.path.basename(args.obj_file)} ({total_verts} Vertices)")
    plt.show()

if __name__ == "__main__":
    main()