from pathlib import Path
from typing import List
import sys

import pandas as pd

def compare_frames(
    method0_df: pd.DataFrame,
    method7_df: pd.DataFrame,
    start_frame: int,
    end_frame: int
) -> List[str]:
    """Compare two DataFrames frame by frame within a specified range.
    
    Args:
        method0_df: First DataFrame (method 0), indexed by frame
        method7_df: Second DataFrame (method 7), indexed by frame
        start_frame: Starting frame number (inclusive)
        end_frame: Ending frame number (inclusive)
        
    Returns:
        List of difference descriptions, empty if no differences found
    """
    differences = []
    excluded_columns = {'frame', 'method_id'}
    
    # Pre-compute comparison columns once
    comparison_columns = [col for col in method0_df.columns if col not in excluded_columns]
    
    # Set frame as index for O(1) lookups
    method0_indexed = method0_df.set_index('frame')
    method7_indexed = method7_df.set_index('frame')
    
    for frame_number in range(start_frame, end_frame + 1):
        # Use .loc for faster indexed access
        try:
            method0_data = method0_indexed.loc[frame_number]
            method7_data = method7_indexed.loc[frame_number]
            
            # Handle duplicate frames - take first row if Series returned
            if isinstance(method0_data, pd.DataFrame):
                method0_row = method0_data.iloc[0]
            else:
                method0_row = method0_data
                
            if isinstance(method7_data, pd.DataFrame):
                method7_row = method7_data.iloc[0]
            else:
                method7_row = method7_data
                
        except KeyError:
            differences.append(f"Frame {frame_number}: missing in one of the files")
            continue
        
        # Compare all columns
        for column in comparison_columns:
            method0_value = method0_row[column]
            method7_value = method7_row[column]
            
            # Skip if both values are null
            if pd.isnull(method0_value) and pd.isnull(method7_value):
                continue
            
            # Record difference if values don't match
            if method0_value != method7_value:
                differences.append(
                    f"Frame {frame_number}: '{column}' differs "
                    f"(method0={method0_value}, method7={method7_value})"
                )
    
    return differences


def write_results(
    differences: List[str],
    output_path: Path,
    start_frame: int,
    end_frame: int
) -> None:
    """Write comparison results to a file.
    
    Args:
        differences: List of difference descriptions
        output_path: Path to the output file
        start_frame: Starting frame number used in comparison
        end_frame: Ending frame number used in comparison
    """
    with open(output_path, 'w') as output_file:
        if differences:
            output_file.write('\n'.join(differences) + '\n')
        else:
            output_file.write(
                f'No differences found in frames {start_frame} to {end_frame}.\n'
            )


def main() -> None:
    """Main entry point for the motion vector comparison tool."""
    if len(sys.argv) != 6:
        print("Usage: python3 mv_compare.py <method0.csv> <method7.csv> "
              "<start_frame> <end_frame> <output.txt>")
        sys.exit(1)
    
    method0_path = Path(sys.argv[1])
    method7_path = Path(sys.argv[2])
    start_frame = int(sys.argv[3])
    end_frame = int(sys.argv[4])
    output_path = Path(sys.argv[5])
    
    # Validate frame range
    if start_frame > end_frame:
        print(f"Error: start_frame ({start_frame}) must be <= end_frame ({end_frame})")
        sys.exit(1)
    
    try:
        method0_df =  pd.read_csv(method0_path)
        method7_df =  pd.read_csv(method7_path)
        
        differences = compare_frames(method0_df, method7_df, start_frame, end_frame)
        write_results(differences, output_path, start_frame, end_frame)
        print(f"Comparison complete. Results written to {output_path}")
        
    except FileNotFoundError as error:
        print(f"Error: Could not find file - {error}")
        sys.exit(1)
    except pd.errors.ParserError as error:
        print(f"Error: Could not parse CSV file - {error}")
        sys.exit(1)
    except KeyError as error:
        print(f"Error: Required column not found in CSV - {error}")
        sys.exit(1)
    except Exception as error:
        print(f"Unexpected error: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()