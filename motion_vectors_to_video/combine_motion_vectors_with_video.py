import cv2
import numpy as np
import pandas as pd
import sys
import math

# Usage: python combine_motion_vectors_with_video.py [video_file] [csv_file] [video_segment_index] [max_frames]
if len(sys.argv) < 3:
    print("Usage: python combine_motion_vectors_with_video.py [video_file] [csv_file] [video_segment_index] [max_frames]")
    sys.exit(1)

input_video_filename = sys.argv[1]
csv_file = sys.argv[2]

# Load CSV file into DataFrame
all_mvs = pd.read_csv(csv_file)

# Ensure numeric columns are integers
for col in ['src_x', 'src_y', 'motion_x', 'motion_y']:
    all_mvs[col] = pd.to_numeric(all_mvs[col], errors='coerce')

# Find unique method_ids in the CSV
method_ids = sorted(all_mvs['method_id'].unique())

# Open input video
cap = cv2.VideoCapture(input_video_filename)
if not cap.isOpened():
    raise IOError(f"Cannot open video file {input_video_filename}")

# Video parameters
frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = int(cap.get(cv2.CAP_PROP_FPS))

# Only keep method_ids for extractor0 and extractor7 that actually exist in the data
method_ids = [mid for mid in method_ids if mid in [0, 5, 7]]
motion_dfs = [all_mvs[all_mvs['method_id'] == mid] for mid in method_ids]

# Only add the video segment if there is at least one method segment
if len(motion_dfs) > 0:
    num_segments = len(motion_dfs) + 1
else:
    num_segments = 1

combined_width = frame_width * num_segments

# Get video segment index
if len(sys.argv) > 3:
    video_segment_index = int(sys.argv[3])
else:
    video_segment_index = len(motion_dfs)

# Get max_frames from command line if provided
if len(sys.argv) > 4:
    max_frames = int(sys.argv[4])
else:
    max_frames = 660

# Determine max number of frames
num_frames_csv = max((df['frame'].max() if not df.empty else 0) for df in motion_dfs)
num_frames_video = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
num_frames = max(num_frames_csv, num_frames_video)

# Create VideoWriter for combined output
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('combined_motion_vectors_with_video.mp4', fourcc, fps, (combined_width, frame_height))

def draw_motion_vector(img, start_x, start_y, motion_x, motion_y, scale=1):
    """
    Draw motion vector on image.
    NOTE: If vectors appear transposed, swap motion_x and motion_y in the call to this function.
    """
    start_point = (int(start_x), int(start_y))
    end_point = (int(start_x + motion_x * scale), int(start_y + motion_y * scale))
    color = (255, 255, 255)  # white arrow
    thickness = 1
    cv2.arrowedLine(img, start_point, end_point, color, thickness, tipLength=0.3)

for frame_num in range(1, num_frames + 1):
    if frame_num > max_frames:
        break
    
    # Create combined black frame
    combined_frame = np.zeros((frame_height, combined_width, 3), dtype=np.uint8)
    
    # Read frame from input video
    if frame_num <= num_frames_video:
        ret, video_frame = cap.read()
        if not ret:
            video_frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
        else:
            video_frame = cv2.resize(video_frame, (frame_width, frame_height))
    else:
        video_frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
    
    for i in range(num_segments):
        segment_x_offset = i * frame_width
        
        if i == video_segment_index:
            # Place the video frame
            combined_frame[:, segment_x_offset:segment_x_offset + frame_width] = video_frame
        else:
            # Draw motion vectors for the corresponding method_id
            method_idx = i if i < video_segment_index else i - 1
            df = motion_dfs[method_idx]
            segment_img = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)
            frame_vectors = df[df['frame'] == frame_num]
            
            for _, row in frame_vectors.iterrows():
                # The +8 offset centers the vector in a 16x16 macroblock
                start_x = row['src_x'] + 8
                start_y = row['src_y'] + 8
                motion_x = row['motion_x']
                motion_y = row['motion_y']
                
                if any(math.isnan(v) for v in [start_x, start_y, motion_x, motion_y]):
                    continue
                
                # FIX: If your motion vectors appear transposed (horizontal becomes vertical),
                # swap motion_x and motion_y here:
                # draw_motion_vector(segment_img, start_x, start_y, motion_y, motion_x)
                
                # Standard drawing (use this first, then swap if needed):
                draw_motion_vector(segment_img, start_x, start_y, motion_x, motion_y)
            
            combined_frame[:, segment_x_offset:segment_x_offset + frame_width] = segment_img
        
        # Draw vertical dividing line between segments
        if i > 0:
            cv2.line(combined_frame, (segment_x_offset, 0), (segment_x_offset, frame_height), (128, 128, 128), 1)
    
    out.write(combined_frame)
    
    if frame_num % 30 == 0:
        print(f"Processed frame {frame_num}/{min(max_frames, num_frames)}")

cap.release()
out.release()
print("Combined video saved as combined_motion_vectors_with_video.mp4")