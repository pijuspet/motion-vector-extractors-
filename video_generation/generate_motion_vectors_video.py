import pandas as pd 
import sys
import numpy as np 
import cv2 
import os
from tqdm import tqdm

def load_motion_vectors(csv_file):
    """Load motion vector data with optimized processing."""
    df = pd.read_csv(csv_file)
    
    # Verify and convert columns to numeric types
    expected_cols = ['frame', 'method_id', 'source', 'w', 'h', 'src_x', 'src_y', 'dst_x', 'dst_y', 'flags', 'motion_x', 'motion_y', 'motion_scale']
    present_cols = [c for c in expected_cols if c in df.columns]
    
    for col in present_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Drop rows with missing src or dst coordinates
    df = df.dropna(subset=['frame','src_x','src_y','dst_x','dst_y'])
    
    # Add computed motion columns if not present
    if 'motion_x' not in df.columns:
        df['motion_x'] = df['dst_x'] - df['src_x']
    if 'motion_y' not in df.columns:
        df['motion_y'] = df['dst_y'] - df['src_y']
    
    return df.reset_index(drop=True)

def reduce_motion_vectors(frame_data, max_vectors=10000):
    """Intelligently reduce motion vector count for visualization."""
    
    # Calculate motion magnitude
    mag = np.hypot(frame_data['motion_x'], frame_data['motion_y'])
    frame_data = frame_data.copy()
    frame_data['magnitude'] = mag
    
    # Strategy 1: Keep only significant motion (magnitude > 2 pixels)
    significant = frame_data[mag > 2]
    
    # Strategy 2: If still too many, sample by magnitude
    if len(significant) > max_vectors:
        # Sort by magnitude and keep the largest motions
        significant = significant.nlargest(max_vectors, 'magnitude')
    
    return significant

def create_optimized_motion_vector_video(df, output_path,
                                       frame_width=1920, frame_height=1080, 
                                       fps=24, max_vectors_per_frame=15000):
    """Optimized video creation with progress tracking."""
    
    frames = sorted(df['frame'].unique())
    print(f"Creating video with {len(frames)} frames...")
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))
    
    for i, frame_num in enumerate(tqdm(frames, desc="Rendering video frames")):
        frame_data = df[df['frame'] == frame_num]
        
        # Reduce vectors per frame for performance
        frame_data = reduce_motion_vectors(frame_data, max_vectors_per_frame)
        
        # Create frame image
        img = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
        
        # Vectorized processing
        src_x = frame_data['src_x'].values.astype(int)
        src_y = frame_data['src_y'].values.astype(int)
        dst_x = frame_data['dst_x'].values.astype(int)
        dst_y = frame_data['dst_y'].values.astype(int)
        motion_x = frame_data['motion_x'].values
        motion_y = frame_data['motion_y'].values
        
        mag = np.hypot(motion_x, motion_y)
        
        # Fast batch drawing
        for sx, sy, dx, dy, m in zip(src_x, src_y, dst_x, dst_y, mag):
            if m < 2:
                continue
            
            if m > 20:
                color = (0, 0, 255)
                thickness = 3
            elif m > 10:
                color = (0, 255, 255)
                thickness = 2
            else:
                color = (255, 255, 255)
                thickness = 1
            
            cv2.arrowedLine(img, (sx, sy), (dx, dy), color, thickness, tipLength=0.3)
            cv2.circle(img, (sx, sy), 3, (255, 255, 0), -1)
        
        # Add frame info
        cv2.putText(img, f'Frame: {frame_num}', (50, 50), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
        cv2.putText(img, f'Vectors: {len(frame_data)}', (50, 100), 
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
        
        out.write(img)
    
    out.release()
    print(f"Saved optimized motion vector video: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python generate_motion_vectors_video.py [csv_file] [results_path]")
        sys.exit(1)

    csv_file = sys.argv[1]
    results_path = sys.argv[2]
    
    if not os.path.isfile(csv_file):
        print(f"Error: File '{csv_file}' not found.")
        exit(1)
    
    print("Loading motion vector data...")
    df = load_motion_vectors(csv_file)
    
    print(f"Loaded {len(df):,} motion vectors.")
    print(f"Frames in data: {sorted(df['frame'].unique())[:10]}{'...' if len(df['frame'].unique())>10 else ''}")
    
    # Get first frame for visualization
    frame_to_visualize = df['frame'].min()
    
    print("Creating motion vector video...")
    create_optimized_motion_vector_video(df, results_path + '/motion_vectors_video_optimized.mp4')
    
    print("Visualization complete!")