import sys
import pandas as pd

def load_csv(path):
    df = pd.read_csv(path)
    return df

def compare_frames(df0, df7, start, end):
    # Assumes both have a 'frame' column and are sorted by frame
    diffs = []
    for frame in range(start, end+1):
        row0 = df0[df0['frame'] == frame]
        row7 = df7[df7['frame'] == frame]
        if row0.empty or row7.empty:
            diffs.append(f"Frame {frame}: missing in one of the files.")
            continue
        # Compare all columns except frame and method
        for col in df0.columns:
            if col in ('frame', 'method_id'):
                continue
            v0 = row0.iloc[0][col]
            v7 = row7.iloc[0][col]
            if pd.isnull(v0) and pd.isnull(v7):
                continue
            if v0 != v7:
                diffs.append(f"Frame {frame}: {col} differs (method0={v0}, method7={v7})")
    return diffs

def main():
    if len(sys.argv) != 6:
        print("Usage: python3 mv_compare.py <method0.csv> <method7.csv> <start_frame> <end_frame> <output.txt>")
        sys.exit(1)
    path0, path7, start, end, outpath = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
    df0 = load_csv(path0)
    df7 = load_csv(path7)
    diffs = compare_frames(df0, df7, start, end)
    with open(outpath, 'w') as f:
        if diffs:
            f.write('\n'.join(diffs))
        else:
            f.write('No differences found in frames {} to {}.\n'.format(start, end))
    print(f"Comparison complete. Results written to {outpath}")

if __name__ == "__main__":
    main()
