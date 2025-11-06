import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import threading

import cv2
import pandas as pd
import scipy.signal
import numpy as np
import numpy.typing as npt

from radar.RadarSettingsReader import RadarSettingsReader
from radar.RadarRecordReader import RadarRecordReader, dt_header, dt_arrival_time, dt_rd_map

# =============================================================================

def preprocess_data(data: npt.NDArray[np.float32]) -> npt.NDArray[np.float32]:
    """Bereitet die Rohdaten für die Visualisierung vor."""
    # Entferne mittlere Bins --> numMeasures x 168 x 125
    data = np.delete(data, 63, 2)
    data = np.delete(data, 63, 2)
    data = np.delete(data, 63, 2)

    # Zero-Interpolation
    kernel = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]])
    kernel = kernel / np.sum(kernel)
    for t in range(data.shape[0]):
        d = data[t]
        d_mean = scipy.signal.convolve2d(d, kernel, mode='same', boundary='symm')
        d[d == 0] = d_mean[d == 0]  # Fülle nur Nullen auf
        data[t] = d
    return data


def create_frame_image(data: npt.NDArray[np.float32]) -> npt.NDArray[np.uint8]:
    """Erstellt ein einzelnes farbiges Bild (Frame) aus den Radardaten,
       passend zur Originalauflösung der Daten."""
    rd_map = np.flipud(data)

    rd_map = np.log10(np.maximum(0.001, rd_map))
    np.clip(rd_map, a_min=3.4, a_max=3.9, out=rd_map)

    rd_map = (255 * (rd_map - 3.4) / 0.5).astype(np.uint8)
    
    rd_map_colored = cv2.applyColorMap(rd_map, cv2.COLORMAP_JET)
    
    return rd_map_colored


class RadarGuiApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Radar Video Generator")
        self.root.geometry("800x350")

        self.radar_file_path = tk.StringVar()
        self.index_file_path = tk.StringVar()
        self.output_path = tk.StringVar()

        frame = tk.Frame(root, padx=10, pady=10)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Radar-Datei (.bin):").grid(row=0, column=0, sticky="w", pady=2)
        tk.Entry(frame, textvariable=self.radar_file_path, width=70).grid(row=0, column=1, sticky="ew")
        tk.Button(frame, text="...", command=self.select_radar_file).grid(row=0, column=2, padx=5)

        tk.Label(frame, text="Index-Datei (.csv):").grid(row=1, column=0, sticky="w", pady=2)
        tk.Entry(frame, textvariable=self.index_file_path, width=70).grid(row=1, column=1, sticky="ew")
        tk.Button(frame, text="...", command=self.select_index_file).grid(row=1, column=2, padx=5)

        tk.Label(frame, text="Output-Verzeichnis:").grid(row=2, column=0, sticky="w", pady=2)
        tk.Entry(frame, textvariable=self.output_path, width=70).grid(row=2, column=1, sticky="ew")
        tk.Button(frame, text="...", command=self.select_output_path).grid(row=2, column=2, padx=5)

        self.start_button = tk.Button(frame, text="Video generieren", command=self.start_processing_thread, height=2, bg="#4CAF50", fg="white")
        self.start_button.grid(row=3, column=0, columnspan=3, pady=20, sticky="ew")

        self.status_label = tk.Label(frame, text="Bitte Dateien auswählen und starten.", wraplength=580)
        self.status_label.grid(row=4, column=0, columnspan=3, pady=5)

        frame.grid_columnconfigure(1, weight=1)

    def select_radar_file(self):
        path = filedialog.askopenfilename(filetypes=[("Binary files", "*.bin"), ("All files", "*.*")])
        if path:
            self.radar_file_path.set(path)
            p = Path(path)
            self.output_path.set(str(p.parent))
            
            index_guess = p.parent / f"{p.stem}_index.csv"
            if index_guess.exists():
                self.index_file_path.set(str(index_guess))
            else:
                 self.index_file_path.set("")

    def select_index_file(self):
        path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if path:
            self.index_file_path.set(path)

    def select_output_path(self):
        path = filedialog.askdirectory()
        if path:
            self.output_path.set(path)

    def start_processing_thread(self):
        """Startet die Videoverarbeitung in einem separaten Thread, um die GUI nicht zu blockieren."""
        self.start_button.config(state=tk.DISABLED, text="Verarbeite...")
        self.status_label.config(text="Starte Verarbeitung...")
        
        thread = threading.Thread(target=self.process_video)
        thread.daemon = True
        thread.start()
        
    def process_video(self):
        """Hauptlogik zur Videoverarbeitung."""
        try:
            radar_bin_path = Path(self.radar_file_path.get())
            radar_index_path = Path(self.index_file_path.get())
            output_dir = Path(self.output_path.get())
            
            if not radar_bin_path.exists() or not radar_index_path.exists():
                raise FileNotFoundError("Radar- oder Index-Datei nicht gefunden.")
            if not output_dir.is_dir():
                raise NotADirectoryError("Output-Pfad ist kein gültiges Verzeichnis.")

            output_video_path = output_dir / "output.mp4"
            self.status_label.config(text=f"Video wird erstellt: {output_video_path}")

            radar_settings_path = radar_bin_path.parent / "radar_configuration.json"
            if not radar_settings_path.exists():
                 raise FileNotFoundError(f"Konfigurationsdatei nicht gefunden: {radar_settings_path}")

            radar_settings_reader = RadarSettingsReader()
            radar_settings = radar_settings_reader.read(radar_settings_path)

            num_range_bins, num_doppler_bins = radar_settings.active_bins()
            MEAS_SIZE = num_range_bins * num_doppler_bins * dt_rd_map.itemsize + dt_header.itemsize + dt_arrival_time.itemsize
            assert num_range_bins == 168 and num_doppler_bins == 128
            assert MEAS_SIZE == 43040

            radar_index = pd.read_csv(radar_index_path, sep=';', names=["radar_idx", "radar_time", "arrival_time", "offset"], skiprows=0)

            frame_height = 168 
            frame_width = 125 
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            fps = 12.5 
            video_writer = cv2.VideoWriter(str(output_video_path), fourcc, fps, (frame_width, frame_height))

            if not video_writer.isOpened():
                raise IOError("VideoWriter konnte nicht geöffnet werden.")

            start_index = 0
            chunk_size = 50
            end_index = chunk_size
            total_frames = len(radar_index)
            
            while start_index < total_frames:
                current_chunk_size = min(chunk_size, total_frames - start_index)
                if current_chunk_size <= 0:
                    break
                
                self.status_label.config(text=f"Verarbeite Frames {start_index} bis {start_index + current_chunk_size} von {total_frames}")
                
                data = RadarRecordReader.read_rd_maps_seeked(
                    radar_bin_path,
                    settings=radar_settings,
                    start_offset=radar_index.iloc[start_index]['offset'],
                    frame_count=current_chunk_size
                )

                data = preprocess_data(data)
                for t in range(data.shape[0]):
                    frame_image = create_frame_image(data[t])
                    video_writer.write(frame_image)

                start_index += current_chunk_size
                end_index += current_chunk_size

            video_writer.release()
            self.status_label.config(text=f"Erfolgreich! Video gespeichert unter:\n{output_video_path}")

        except Exception as e:
            # Fehler im GUI anzeigen
            self.status_label.config(text=f"Fehler: {e}")
            messagebox.showerror("Fehler", f"Ein Fehler ist aufgetreten:\n{e}")
        finally:
            # Button wieder aktivieren
            self.start_button.config(state=tk.NORMAL, text="Video generieren")

# =============================================================================
# Hauptprogramm
# =============================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = RadarGuiApp(root)
    root.mainloop()

