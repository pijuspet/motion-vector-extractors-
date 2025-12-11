import pandas as pd 
import numpy as np 
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch 
import cv2 
import os
from tqdm import tqdm
from multiprocessing import Pool
import functools

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

def optimized_visualize_motion_vectors_png(df, frame_num, output_path,
                                         frame_width=1920, frame_height=1080,
                                         max_vectors=15000):
    """Optimized motion vector visualization using vectorized operations."""
    
    frame_data = df[df['frame'] == frame_num]
    if frame_data.empty:
        print(f"No motion vectors for frame {frame_num}")
        return False
    
    # Reduce data size for performance
    frame_data = reduce_motion_vectors(frame_data, max_vectors)
    print(f"Visualizing {len(frame_data)} motion vectors for frame {frame_num}")
    
    # Vectorized computation - much faster than iterrows()
    src_x = frame_data['src_x'].to_numpy()
    src_y = frame_data['src_y'].to_numpy()
    dst_x = frame_data['dst_x'].to_numpy()
    dst_y = frame_data['dst_y'].to_numpy()
    motion_x = frame_data['motion_x'].to_numpy()
    motion_y = frame_data['motion_y'].to_numpy()
    
    # Calculate magnitudes vectorized
    mag = np.hypot(motion_x, motion_y)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(19.2, 10.8), dpi=100)
    ax.set_xlim(0, frame_width)
    ax.set_ylim(0, frame_height)
    ax.set_aspect('equal')
    ax.invert_yaxis()
    ax.set_facecolor('black')
    fig.patch.set_facecolor('black')
    
    # Vectorized color assignment
    colors = np.where(mag > 20, 'red', 
                     np.where(mag > 10, 'yellow', 'white'))
    alphas = np.where(mag > 20, 1.0,
                     np.where(mag > 10, 0.8, 0.6))
    
    # Batch processing for better performance
    batch_size = 1000
    for i in tqdm(range(0, len(src_x), batch_size), desc="Drawing arrows"):
        end_idx = min(i + batch_size, len(src_x))
        batch_src_x = src_x[i:end_idx]
        batch_src_y = src_y[i:end_idx]
        batch_dst_x = dst_x[i:end_idx]
        batch_dst_y = dst_y[i:end_idx]
        batch_colors = colors[i:end_idx]
        batch_alphas = alphas[i:end_idx]
        
        for j in range(len(batch_src_x)):
            arrow = FancyArrowPatch((batch_src_x[j], batch_src_y[j]), 
                                  (batch_dst_x[j], batch_dst_y[j]),
                                  arrowstyle='->', color=batch_colors[j],
                                  linewidth=1.5, alpha=batch_alphas[j], 
                                  mutation_scale=15)
            ax.add_patch(arrow)
            
            # Add source point
            circle = plt.Circle((batch_src_x[j], batch_src_y[j]), 2, 
                              color='cyan', alpha=0.7)
            ax.add_patch(circle)
    
    ax.set_title(f'Motion Vectors - Frame {frame_num}', color='white', fontsize=18)
    ax.set_xlabel('X Position (pixels)', color='white', fontsize=14)
    ax.set_ylabel('Y Position (pixels)', color='white', fontsize=14)
    ax.tick_params(colors='white')
    
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='black')
    plt.close()
    print(f"Saved motion vector PNG: {output_path}")
    return True

def opencv_visualize_motion_vectors(df, frame_num, output_path, 
                                  frame_width=1920, frame_height=1080,
                                  max_vectors=20000):
    """Ultra-fast OpenCV-based visualization."""
    
    frame_data = df[df['frame'] == frame_num]
    if frame_data.empty:
        print(f"No motion vectors for frame {frame_num}")
        return False
    
    # Reduce data size
    frame_data = reduce_motion_vectors(frame_data, max_vectors)
    print(f"OpenCV rendering {len(frame_data)} motion vectors for frame {frame_num}")
    
    # Create image
    img = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
    
    # Vectorized operations
    src_x = frame_data['src_x'].values.astype(int)
    src_y = frame_data['src_y'].values.astype(int)
    dst_x = frame_data['dst_x'].values.astype(int)
    dst_y = frame_data['dst_y'].values.astype(int)
    motion_x = frame_data['motion_x'].values
    motion_y = frame_data['motion_y'].values
    
    # Calculate magnitudes
    mag = np.hypot(motion_x, motion_y)
    
    # Batch drawing for performance
    for sx, sy, dx, dy, m in tqdm(zip(src_x, src_y, dst_x, dst_y, mag), 
                                  total=len(src_x), desc="Drawing vectors"):
        # Skip very small motions
        if m < 2:
            continue
            
        # Color based on magnitude
        if m > 20:
            color = (0, 0, 255)  # Red
            thickness = 3
        elif m > 10:
            color = (0, 255, 255)  # Yellow
            thickness = 2
        else:
            color = (255, 255, 255)  # White
            thickness = 1
        
        # Draw arrow
        cv2.arrowedLine(img, (sx, sy), (dx, dy), color, thickness, tipLength=0.3)
        # Draw source point
        cv2.circle(img, (sx, sy), 3, (255, 255, 0), -1)
    
    # Add frame number
    cv2.putText(img, f'Frame: {frame_num}', (50, 50), 
                cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 3)
    
    cv2.imwrite(output_path, img)
    print(f"Saved OpenCV motion vector image: {output_path}")
    return True

def motion_heatmap_visualization(df, frame_num, output_path,
                               frame_width=1920, frame_height=1080):
    """Create a motion magnitude heatmap - very fast for large datasets."""
    
    frame_data = df[df['frame'] == frame_num]
    if frame_data.empty:
        print(f"No motion vectors for frame {frame_num}")
        return False
    
    # Calculate motion magnitude
    mag = np.hypot(frame_data['motion_x'], frame_data['motion_y'])
    
    # Create heatmap
    plt.figure(figsize=(19.2, 10.8))
    plt.hexbin(frame_data['src_x'], frame_data['src_y'], C=mag, 
               gridsize=100, cmap='hot', mincnt=1, extent=[0, frame_width, 0, frame_height])
    plt.colorbar(label='Motion Magnitude (pixels)')
    plt.title(f'Motion Density Heatmap - Frame {frame_num}', fontsize=18)
    plt.xlabel('X Position (pixels)', fontsize=14)
    plt.ylabel('Y Position (pixels)', fontsize=14)
    plt.gca().invert_yaxis()
    
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Saved motion heatmap: {output_path}")
    return True

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
    # csv_file = './results/20251211_120301/method0_output_0.csv'
    csv_file = 'out.csv'
    
    if not os.path.isfile(csv_file):
        print(f"Error: File '{csv_file}' not found.")
        exit(1)
    
    print("Loading motion vector data...")
    df = load_motion_vectors(csv_file)
    
    print(f"Loaded {len(df):,} motion vectors.")
    print(f"Frames in data: {sorted(df['frame'].unique())[:10]}{'...' if len(df['frame'].unique())>10 else ''}")
    
    # Get first frame for visualization
    frame_to_visualize = df['frame'].min()
    
    print("\nChoose visualization method:")
    print("1. Matplotlib (high quality, slower)")
    print("2. OpenCV (fast, good quality)")
    print("3. Heatmap (fastest, shows density)")
    print("4. Create video (OpenCV-based)")
    print("5. All visualizations")
    
    choice = input("Enter choice (1-5): ").strip()
    
    if choice == "1" or choice == "5":
        print("Creating matplotlib visualization...")
        optimized_visualize_motion_vectors_png(df, frame_to_visualize, 
                                             f'motion_vectors_matplotlib_frame_{frame_to_visualize}.png')
    
    if choice == "2" or choice == "5":
        print("Creating OpenCV visualization...")
        opencv_visualize_motion_vectors(df, frame_to_visualize, 
                                      f'motion_vectors_opencv_frame_{frame_to_visualize}.png')
    
    if choice == "3" or choice == "5":
        print("Creating heatmap visualization...")
        motion_heatmap_visualization(df, frame_to_visualize, 
                                   f'motion_vectors_heatmap_frame_{frame_to_visualize}.png')
    
    if choice == "4" or choice == "5":
        print("Creating motion vector video...")
        create_optimized_motion_vector_video(df, 'motion_vectors_video_optimized.mp4')
    
    print("Visualization complete!")

