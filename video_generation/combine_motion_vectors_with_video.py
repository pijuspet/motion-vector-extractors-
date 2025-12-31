import cv2
import numpy as np
import sys
from tqdm import tqdm
from typing import List, Optional

import motion_vector as mv


def create_combined_video(
    input_video_filename: str,
    motion_dataframes: List,
    output_path: str,
    video_segment_index: Optional[int] = None,
    max_frames: int = 660,
):
    video_capture = cv2.VideoCapture(input_video_filename)
    if not video_capture.isOpened():
        raise IOError(f"Cannot open video file {input_video_filename}")

    try:
        frame_width = int(video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(video_capture.get(cv2.CAP_PROP_FPS))

        # Calculate number of segments: one per motion dataframe + one for original video
        if len(motion_dataframes) > 0:
            num_segments = len(motion_dataframes) + 1
        else:
            num_segments = 1
        combined_width = frame_width * num_segments

        # Default video segment index: append the video after the motion segments
        if video_segment_index is None:
            video_segment_index = len(motion_dataframes)

        # Determine maximum frames across all data sources
        max_csv_frames = (
            max(
                (dataframe["frame"].max() if not dataframe.empty else 0)
                for dataframe in motion_dataframes
            )
            if motion_dataframes
            else 0
        )
        total_video_frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        num_frames = max(max_csv_frames, total_video_frames)

        # Initialize video writer for output
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        video_writer = cv2.VideoWriter(
            output_path, fourcc, fps, (combined_width, frame_height)
        )

        # Reset to first frame
        video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)

        for frame_number in tqdm(
            range(1, num_frames + 1), desc="Rendering video frames"
        ):
            if frame_number > max_frames:
                break

            # Initialize combined frame canvas
            combined_frame = np.zeros((frame_height, combined_width, 3), dtype=np.uint8)

            # Read current video frame
            if frame_number <= total_video_frames:
                frame_read_success, video_frame = video_capture.read()
                if not frame_read_success:
                    video_frame = np.zeros(
                        (frame_height, frame_width, 3), dtype=np.uint8
                    )
                else:
                    video_frame = cv2.resize(video_frame, (frame_width, frame_height))
            else:
                video_frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)

            for segment_index in range(num_segments):
                segment_x_offset = segment_index * frame_width

                if segment_index == video_segment_index:
                    # Place original video frame
                    combined_frame[
                        :, segment_x_offset : segment_x_offset + frame_width
                    ] = video_frame
                else:
                    # Draw motion vectors for corresponding method
                    motion_df_index = (
                        segment_index
                        if segment_index < video_segment_index
                        else segment_index - 1
                    )

                    # Handle out-of-range indices gracefully
                    if motion_df_index < 0 or motion_df_index >= len(motion_dataframes):
                        segment_image = np.zeros(
                            (frame_height, frame_width, 3), dtype=np.uint8
                        )
                    else:
                        current_dataframe = motion_dataframes[motion_df_index]
                        segment_image = np.zeros(
                            (frame_height, frame_width, 3), dtype=np.uint8
                        )
                        frame_motion_data = current_dataframe[
                            current_dataframe["frame"] == frame_number
                        ]

                        frame_motion_data = mv.reduce_motion_vectors(
                            frame_motion_data, max_vectors=15000
                        )
                        mv.draw_motion_vectors(segment_image, frame_motion_data)

                    combined_frame[
                        :, segment_x_offset : segment_x_offset + frame_width
                    ] = segment_image

                # Draw vertical dividing line between segments
                if segment_index > 0:
                    cv2.line(
                        combined_frame,
                        (segment_x_offset, 0),
                        (segment_x_offset, frame_height),
                        (128, 128, 128),
                        1,
                    )

            video_writer.write(combined_frame)

        video_writer.release()
        return output_path

    finally:
        video_capture.release()


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print(
            "Usage: python combine_motion_vectors_with_video.py "
            "[video_file] [csv_file] [results_path] [video_segment_index] [max_frames]"
        )
        sys.exit(1)

    input_video_filename = sys.argv[1]
    csv_file_path_orig = sys.argv[2]
    csv_file_path_cust = sys.argv[3]
    results_directory = sys.argv[4]

    original_motion_vectors = mv.load_motion_vectors(csv_file_path_orig)
    custom_motion_vectors = mv.load_motion_vectors(csv_file_path_cust)

    if len(sys.argv) > 5:
        video_position = int(sys.argv[5])
    else:
        video_position = None

    if len(sys.argv) > 6:
        max_frames_to_process = int(sys.argv[6])
    else:
        max_frames_to_process = 660

    output_path = f"{results_directory}/combined_motion_vectors_with_video.mp4"
    output_file_path = create_combined_video(
        input_video_filename,
        [original_motion_vectors, custom_motion_vectors],
        output_path,
        video_position,
        max_frames_to_process,
    )
    print(f"Combined video saved as {output_file_path}")
