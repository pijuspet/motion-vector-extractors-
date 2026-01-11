import sys
import numpy as np
import cv2
import pandas as pd
import os
from tqdm import tqdm

import video_generation.motion_vector as mv


def create_motion_vector_video(
    df: pd.DataFrame,
    output_path: str,
    width: int = 1920,
    height: int = 1080,
    fps: int = 24,
    max_vectors: int = 15000,
):
    """Create motion vector visualization video."""

    frames = sorted(df["frame"].unique())
    print(f"Creating video with {len(frames)} frames...")

    writer = cv2.VideoWriter(
        output_path, cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height)
    )

    for frame_num in tqdm(frames, desc="Rendering"):
        frame_data = df[df["frame"] == frame_num]

        if len(frame_data) > max_vectors:
            frame_data = mv.reduce_motion_vectors(frame_data, max_vectors)

        img = np.zeros((height, width, 3), dtype=np.uint8)
        mv.draw_motion_vectors(img, frame_data)

        cv2.putText(
            img,
            f"Frame: {frame_num}",
            (50, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.5,
            (255, 255, 255),
            3,
        )
        cv2.putText(
            img,
            f"Vectors: {len(frame_data)}",
            (50, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            (255, 255, 255),
            2,
        )

        writer.write(img)

    writer.release()
    print(f"Saved optimized motion vector video: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_motion_vectors_video.py [csv_file] [output_dir]")
        sys.exit(1)

    csv_file = sys.argv[1]
    output_dir = sys.argv[2]

    if not os.path.isfile(csv_file):
        print(f"Error: File '{csv_file}' not found.")
        sys.exit(1)

    print("Loading motion vector data...")
    df = mv.load_motion_vectors(csv_file)

    output_path = os.path.join(output_dir, "motion_vectors_video.mp4")

    print(f"Loaded {len(df):,} motion vectors.")
    print(
        f"Frames in data: {sorted(df['frame'].unique())[:10]}{'...' if len(df['frame'].unique())>10 else ''}"
    )

    print("Creating motion vector video...")
    create_motion_vector_video(df, output_path)
    print("Visualization complete!")
