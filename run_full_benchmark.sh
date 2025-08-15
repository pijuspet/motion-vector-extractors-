#!/bin/bash
set -e

build() {
  echo "Building all extractors and tools..."
  make
  g++ -O2 -o benchmark_all_9 benchmarking.cpp \
    `pkg-config --cflags --libs libavformat libavcodec libavutil libswscale` -lm
  gcc -O2 -o combine_mv_csv combine_mv_csv.c
  gcc -O2 -o complete_video_generator_9 vidgenerator.c \
    `pkg-config --cflags --libs libavformat libavcodec libavutil libswscale` -lm
 
  echo "Build complete."
}

extract() {
  if [[ -z "$INPUT" ]]; then
    echo "Extraction step skipped: set INPUT environment variable to input file."
    return 1
  fi
  echo "Running 9-method benchmark suite..."
  ./benchmark_all_9 "$INPUT" "$INPUT1"
  echo "Benchmarks complete."
}

combine() {
  echo "Combining all CSV outputs..."
  ./combine_mv_csv
  echo "Combined motion vectors saved to all_motion_vectors.csv."
}

decode() {
  if [ ! -f decoded_output.mp4 ]; then
    echo "Creating decoded_output.mp4 reference video using ffmpeg..."
    ffmpeg -y -i "$INPUT" -c copy -an decoded_output.mp4
  else
    echo "decoded_output.mp4 already exists. Skipping decoding."
  fi
}

generate_videos() {
  for i in {0..8}; do
    ./complete_video_generator_9 decoded_output.mp4 all_motion_vectors.csv method${i}.mp4 $i
  done
  echo "Per-method motion vector videos generated."
}

plot() {
  if [[ -z "$INPUT" ]]; then
    echo "Plotting step skipped: set INPUT argument."
    return 1
  fi
  if [[ -z "$INPUT1" ]]; then
    echo "Streams count not specified; defaulting to 1."
    INPUT1=1
  fi
  echo "Running Python benchmark visualization and PPT generation..."
  python3 benchmark_python.py "$INPUT" "$INPUT1"
  echo "Plotting complete."
}

run_all() {
  build
  extract
  combine
  decode
  plot
}

usage() {
  echo
  echo "Usage: $0 <input_video_or_rtsp_url> [streams]"
  echo "  Set the input (video filename or RTSP URL) as the first argument."
  echo "  The number of 'streams' for benchmarking is optional (default = 1)."
  echo "  You will then be prompted to pick which step(s) to run."
  echo "    1 = Build"
  echo "    2 = Extract (run benchmark)"
  echo "    3 = Combine CSVs"
  echo "    4 = Decode Reference Video"
  echo "    5 = Generate Plots and PowerPoint"
  echo "    0 = Run ALL steps in sequence"
  echo
}

# --- Main ---

if [[ -z "$1" ]]; then
  usage
  exit 1
fi

INPUT="$1"
INPUT1="${2:-1}"    # Defaults to 1 if second argument missing

# Optional validation of streams argument:
if ! [[ "$INPUT1" =~ ^[0-9]+$ && "$INPUT1" -ge 1 ]]; then
  echo "Error: streams argument must be a positive integer"
  exit 1
fi

echo
echo "Select steps to run (enter one or more numbers separated by space):"
echo "  1: Build"
echo "  2: Extract (run benchmark)"
echo "  3: Combine CSVs"
echo "  4: Decode Reference Video"
echo "  5: Generate Plots and PowerPoint"
echo "  0: Run ALL steps"
echo
read -p "Choice(s): " CHOICES

for step in $CHOICES; do
  case "$step" in
    1) build ;;
    2) extract ;;
    3) combine ;;
    4) decode ;;
    5) plot ;;
    0) run_all; break ;;
    *) echo "Invalid step: $step" ;;
  esac
done

echo
echo "=== WORKFLOW COMPLETE ==="
echo "- Per-method CSVs:        method0_output.csv ... method8_output.csv"
echo "- Combined CSV:           all_motion_vectors.csv"
echo "- Reference video:        decoded_output.mp4"
echo "- Plots & PPTX in:        plots/"

