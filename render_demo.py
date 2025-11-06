from __future__ import annotations

import numpy as np
import numpy.typing as npt
import cv2

def show_falsecolor(
        data: npt.NDArray[np.float32],
        *,
        assume_demo: bool = True,
        writer: cv2.VideoWriter | None = None,
        show_window: bool = True,
        return_frame: bool = False,
):
    WIDTH = 1920
    HEIGHT = 1080

    if show_window:
        cv2.namedWindow("Radar", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("Radar", WIDTH, HEIGHT)

    FONT = cv2.FONT_HERSHEY_SIMPLEX
    FONT_SCALE = 1.0
    FONT_THICKNESS = 2

    if assume_demo:
        rd_map = data.copy()
        rd_map = np.clip(rd_map, 3.4, 3.9)
        rd_map = (255 * (rd_map - 3.4) / 0.5).astype(np.uint8)
    else:
        rd_map = np.flipud(data)
        rd_map = np.log10(np.maximum(0.001, rd_map))
        np.clip(rd_map, a_min=3.4, a_max=3.9, out=rd_map)
        rd_map = (255 * (rd_map - 3.4) / 0.5).astype(np.uint8)

    rd_map = cv2.applyColorMap(rd_map, cv2.COLORMAP_JET)

    # prepare canvas with axis (wie gehabt)
    text_size = cv2.getTextSize("range", FONT, FONT_SCALE, FONT_THICKNESS)
    text_x = HEIGHT // 2 - text_size[0][0] // 2
    text_y = text_size[0][1]
    y_axis = np.ones((text_size[0][1] + text_size[1], HEIGHT, 3), dtype=np.uint8) * 255
    cv2.putText(y_axis, "range", (text_x, text_y), FONT, FONT_SCALE, (0, 0, 0), FONT_THICKNESS,
                cv2.LINE_AA)
    y_axis = cv2.rotate(y_axis, cv2.ROTATE_90_COUNTERCLOCKWISE)

    text_size = cv2.getTextSize("velocity", FONT, FONT_SCALE, FONT_THICKNESS)
    text_x = WIDTH // 2 - text_size[0][0] // 2
    text_y = text_size[0][1]
    x_axis = np.ones((text_size[0][1] + text_size[1], WIDTH, 3), dtype=np.uint8) * 255
    cv2.putText(x_axis, "velocity", (text_x, text_y), FONT, FONT_SCALE, (0, 0, 0), FONT_THICKNESS,
                cv2.LINE_AA)

    background = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)
    background[0:y_axis.shape[0], 0:y_axis.shape[1]] = y_axis
    background[HEIGHT - x_axis.shape[0]:HEIGHT + x_axis.shape[0], y_axis.shape[1]:x_axis.shape[1]] = x_axis[
        :, :-y_axis.shape[1]]

    canvas_size = (HEIGHT - x_axis.shape[0], WIDTH - y_axis.shape[1])

    # resize
    rd_map = cv2.resize(rd_map, dsize=(canvas_size[1], canvas_size[0]), interpolation=cv2.INTER_NEAREST)

    background[0:canvas_size[0], y_axis.shape[1]:y_axis.shape[1] + canvas_size[1]] = rd_map

    # optional: schreiben/anzeigen
    if writer is not None:
        # Falls Writer-Auflösung ungerade ist, vorher passend skalieren:
        h, w = background.shape[:2]
        if (w % 2) or (h % 2):
            w2 = w + (w % 2)
            h2 = h + (h % 2)
            frame = cv2.resize(background, (w2, h2), interpolation=cv2.INTER_NEAREST)
            writer.write(frame)
        else:
            writer.write(background)

    if show_window:
        cv2.imshow("Radar", background)
        cv2.waitKey(1)

    if return_frame:
        return background
    return None


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--npy", required=True, help="Pfad zu range_doppler_maps_demo.npy (T,168,125), bereits log10+clipped [3.4..3.9]")
    ap.add_argument("--out", required=True, help="Ausgabe-MP4")
    ap.add_argument("--fps", type=float, default=12.5)
    ap.add_argument("--no-window", action="store_true", help="Nicht anzeigen, nur schreiben")
    args = ap.parse_args()

    demo = np.load(args.npy)  # (T,168,125)
    T, H, W = demo.shape

    # Einen Frame rendern um Größe zu bekommen:
    frame0 = show_falsecolor(demo[0], assume_demo=True, show_window=not args.no_window, return_frame=True)
    h, w = frame0.shape[:2]
    if (w % 2) or (h % 2):
        w += (w % 2); h += (h % 2)

    vw = cv2.VideoWriter(args.out, cv2.VideoWriter_fourcc(*"mp4v"), args.fps, (w, h))
    if not vw.isOpened():
        raise RuntimeError(f"Konnte Writer nicht öffnen: {args.out}")

    # Den ersten Frame (bereits erzeugt) reinschreiben:
    if frame0.shape[1] != w or frame0.shape[0] != h:
        frame0 = cv2.resize(frame0, (w, h), interpolation=cv2.INTER_NEAREST)
    vw.write(frame0)

    # Rest schreiben:
    for t in range(1, T):
        show_falsecolor(demo[t], assume_demo=True, writer=vw, show_window=not args.no_window)

    vw.release()
    cv2.destroyAllWindows()
    print(f"[OK] geschrieben: {args.out}  ({T} Frames, {w}x{h} @ {args.fps} fps)")
