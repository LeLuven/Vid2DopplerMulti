from dataclasses import dataclass
from typing import Generator
from typing import List
from typing import Tuple

import numpy as np
import numpy.typing as npt
from radar.RadarSettingsReader import RadarSettings

dt_header = np.dtype(
    [
        ("sync_word", np.uint32),
        ("idx", np.uint32),
        ("timestamp", np.uint64),
        ("state", np.uint16),
        ("stream_data_mask", np.uint16),
        ("data_bytes", np.uint32),
    ]
)
dt_header = dt_header.newbyteorder(">")

dt_rd_map = np.dtype(np.uint16)
dt_rd_map = dt_rd_map.newbyteorder(">")

dt_num_detections = np.dtype(np.uint16)
dt_num_detections = dt_num_detections.newbyteorder(">")

dt_detections = np.dtype(
    [
        ("r_bin", np.uint16),
        ("d_bin", np.int16),
        ("magnitude", np.uint16),
        ("azimuth", np.int16),
        ("elevation", np.int16),
    ]
)
dt_detections = dt_detections.newbyteorder(">")

dt_num_trackings = np.dtype(np.uint16)
dt_num_trackings = dt_num_trackings.newbyteorder(">")

dt_tracking = np.dtype(
    [
        ("id", np.uint16),
        ("distance", np.float32),
        ("speed", np.float32),
        ("magnitude", np.uint16),
        ("azimuth", np.float32),
        ("elevation", np.float32),
        ("life_time", np.uint32),
    ]
)
dt_tracking = dt_tracking.newbyteorder(">")

dt_arrival_time = np.dtype(np.int64)
dt_arrival_time = dt_arrival_time.newbyteorder(">")


@dataclass
class RadarDetection:
    r_bin: np.uint16
    d_bin: np.int16
    magnitude: np.uint16
    azimuth: np.int16
    elevation: np.int16


@dataclass
class RadarTracking:
    id: np.uint16
    distance: np.float32
    speed: np.float32
    magnitude: np.uint16
    azimuth: np.float32
    elevation: np.float32
    life_time: np.uint32


@dataclass
class RadarRecord:
    idx: np.uint32
    state: np.uint16
    stream_data_mask: np.uint16
    data_bytes: np.uint32
    radar_time: np.uint64
    """Time of measurement in ms since epoch. DEBUG: processing time in us"""
    arrival_time: np.uint64
    """Arrival time of package in ns"""
    offset: np.uint32
    length: np.uint32

    def save_time_us(self) -> np.uint64:
        if self.radar_time > 500000:
            # Normal time
            return self.radar_time * np.uint64(1000)
        else:
            # Use arrival time if radar_time is very small -> is time from debug version
            return self.arrival_time / np.uint64(1000)


class RadarRecordReader:
    @staticmethod
    def read_records(
        path: str, stop_at_error: bool = False
    ) -> Generator[RadarRecord, None, None]:
        with open(path, "rb") as file:
            buffer = file.read()
            offset: int = 0

            while offset < len(buffer):
                offset, record = RadarRecordReader.__read_record(
                    buffer, offset, stop_at_error
                )
                if stop_at_error and offset < 0:
                    print("Stopping after error")
                    break
                yield record

    @staticmethod
    def read_rd_maps(file_path: str, settings: RadarSettings, frame_offsets: List[int],
                     db_conversion: bool = True) -> npt.NDArray[np.float32]:
        frame_count = len(frame_offsets)

        a_rbs, a_dbs = settings.active_bins()
        active_bins = a_rbs * a_dbs

        rd_maps = np.zeros(shape=(frame_count, active_bins), dtype=np.float32)

        with open(file_path, "rb") as file:
            buffer = file.read()

            for frame_number, offset in enumerate(frame_offsets):
                _, record = RadarRecordReader.__read_record(buffer, offset)

                # Magnitudes
                _, rd_map = RadarRecordReader.__read_rd_map(
                    True,
                    record.stream_data_mask,
                    buffer,
                    offset + dt_header.itemsize,
                    active_bins,
                )

                rd_maps[frame_number] = rd_map

            del buffer

            if db_conversion:
                # Convert to db
                rd_maps = (rd_maps - 3584.0) / 85.0

                # TODO
                # Clip below zero, should not occur if above formula is corrected
                rd_maps = np.clip(rd_maps, a_min=0, a_max=None)

            # Split last part to bin dimensions
            rd_maps = np.reshape(rd_maps, newshape=(frame_count, a_dbs, a_rbs))

            # (Time, DBin, RBin) -> (Time, RBin, DBin)
            rd_maps = np.transpose(rd_maps, (0, 2, 1))

            return rd_maps

    @staticmethod
    def read_rd_maps_seeked(file_path: str, settings: RadarSettings,
                            start_offset: int, frame_count: int) -> npt.NDArray[np.float32]:

        a_rbs, a_dbs = settings.active_bins()
        active_bins = a_rbs * a_dbs
        radar_record_measurement_size = a_rbs * a_dbs * dt_rd_map.itemsize + dt_header.itemsize + dt_arrival_time.itemsize

        rd_maps = np.zeros(shape=(frame_count, active_bins), dtype=np.float32)

        with open(file_path, "rb") as file:
            file.seek(start_offset)

            buffer = file.read(frame_count * radar_record_measurement_size)
            frame_offsets = [i*radar_record_measurement_size for i in range(frame_count)]

            for frame_number, offset in enumerate(frame_offsets):
                _, record = RadarRecordReader.__read_record(buffer, offset)

                # Magnitudes
                _, rd_map = RadarRecordReader.__read_rd_map(
                    True,
                    record.stream_data_mask,
                    buffer,
                    offset + dt_header.itemsize,
                    active_bins,
                )

                rd_maps[frame_number] = rd_map

            del buffer

            # Split last part to bin dimensions
            rd_maps = np.reshape(rd_maps, newshape=(frame_count, a_dbs, a_rbs))

            # (Time, DBin, RBin) -> (Time, RBin, DBin)
            rd_maps = np.transpose(rd_maps, (0, 2, 1))

            return rd_maps

    @staticmethod
    def __read_record(
        buffer: bytes, offset_extern: int, stop_at_error: bool = True
    ) -> Tuple[int, RadarRecord | None]:
        offset = offset_extern

        if offset + dt_header.itemsize > len(buffer):
            print(f"Data was smaller than header at offset {offset} / {len(buffer)}")
            if stop_at_error:
                return -1, None
            exit(1)

        # Read header
        header = np.frombuffer(buffer, dtype=dt_header, count=1, offset=offset)
        offset += dt_header.itemsize

        sword = header["sync_word"][0]
        idx = header["idx"][0]
        radar_time = header["timestamp"][0]
        state = header["state"][0]
        stream_data_mask = header["stream_data_mask"][0]
        data_bytes = header["data_bytes"][0]

        # Skip content of recording
        offset += data_bytes

        # Read arrival time
        arrival_time = np.frombuffer(
            buffer, dtype=dt_arrival_time, count=1, offset=offset
        )
        offset += dt_arrival_time.itemsize

        arrival_time = arrival_time[0].item()

        length = offset - offset_extern

        # Check sync word
        if sword != 0xAA55CC33:
            print(f"Sync word was wrong: {sword:#0{10}x}")
            if stop_at_error:
                return -1, None
            exit(1)

        record = RadarRecord(
            idx,
            state,
            stream_data_mask,
            data_bytes,
            radar_time,
            arrival_time,
            offset_extern,
            length,
        )

        return offset, record

    @staticmethod
    def __read_rd_map(
        include: bool,
        mask: np.uint16,
        buffer: bytes,
        offset_extern: int,
        active_bins: int,
    ) -> Tuple[int, npt.NDArray[np.uint16] | None]:
        offset = offset_extern

        if not ((mask & 0x0004) == 0x0004):
            if include:
                return offset, np.zeros(active_bins, dtype=np.uint16)
            else:
                return offset, None

        if not include:
            offset += active_bins * dt_rd_map.itemsize
            return offset, None

        rd_map = np.frombuffer(
            buffer, dtype=dt_rd_map, count=active_bins, offset=offset
        )
        offset += active_bins * dt_rd_map.itemsize

        return offset, rd_map

    @staticmethod
    def __read_detections(
        include: bool, mask: np.uint16, buffer: bytes, offset_extern: int
    ) -> Tuple[int, List[RadarDetection] | None]:
        offset = offset_extern

        if not ((mask & 0x0020) == 0x0020):
            return offset, []

        # Read number of detections
        num_detections = np.frombuffer(
            buffer, dtype=dt_num_detections, count=1, offset=offset
        )
        num_detections = num_detections[0]

        offset += dt_num_detections.itemsize

        if not include or num_detections <= 0:
            offset += num_detections * dt_detections.itemsize
            return offset, []

        dat_detections = np.frombuffer(
            buffer, dtype=dt_detections, count=num_detections, offset=offset
        )
        offset += num_detections * dt_detections.itemsize

        detections: List[RadarDetection] = []
        for dat_detection in dat_detections:
            r_bin = dat_detection["r_bin"]
            d_bin = dat_detection["d_bin"]
            magnitude = dat_detection["magnitude"]
            azimuth = dat_detection["azimuth"]
            if azimuth < -90 or azimuth > 90:
                print(f"\tAzimuth {azimuth} out or range (det)")

            elevation = dat_detection["elevation"]

            detection = RadarDetection(r_bin, d_bin, magnitude, azimuth, elevation)
            detections.append(detection)

        return offset, detections

    @staticmethod
    def __read_trackings(
        include: bool, mask: np.uint16, buffer: bytes, offset_extern: int
    ) -> Tuple[int, List[RadarTracking] | None]:
        offset = offset_extern

        if not ((mask & 0x0040) == 0x0040):
            return offset, []

        # Read number of trackings
        num_trackings = np.frombuffer(
            buffer, dtype=dt_num_trackings, count=1, offset=offset
        )
        num_trackings = num_trackings[0]

        offset += dt_num_trackings.itemsize

        if not include or num_trackings <= 0:
            offset += num_trackings * dt_tracking.itemsize
            return offset, []

        dat_trackings = np.frombuffer(
            buffer, dtype=dt_tracking, count=num_trackings, offset=offset
        )
        offset += num_trackings * dt_tracking.itemsize

        trackings: List[RadarTracking] = []
        for dat_tracking in dat_trackings:
            t_id = dat_tracking["id"]
            distance = dat_tracking["distance"]
            speed = dat_tracking["speed"]
            magnitude = dat_tracking["magnitude"]
            azimuth = dat_tracking["azimuth"]
            if azimuth < -90 or azimuth > 90:
                print(f"\tAzimuth {azimuth} out or range (tra)")

            elevation = dat_tracking["elevation"]
            life_time = dat_tracking["life_time"]

            tracking = RadarTracking(
                t_id, distance, speed, magnitude, azimuth, elevation, life_time
            )
            trackings.append(tracking)

        return offset, trackings
