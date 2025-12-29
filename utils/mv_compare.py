from pathlib import Path
from typing import List, Set
import pandas as pd
import sys


def compare_frames(
    first_method_df: pd.DataFrame,
    second_method_df: pd.DataFrame,
    start_frame: int,
    end_frame: int,
) -> List[str]:
    differences: List[str] = []
    excluded_columns: Set[str] = {"frame", "method_id"}

    # Pre-compute comparison columns once
    columns_to_compare: List[str] = [
        column_name
        for column_name in first_method_df.columns
        if column_name not in excluded_columns
    ]

    # Set frame as index for O(1) lookups
    first_method_indexed = first_method_df.set_index("frame")
    second_method_indexed = second_method_df.set_index("frame")

    for frame_number in range(start_frame, end_frame + 1):
        # Use .loc for faster indexed access
        try:
            first_method_data = first_method_indexed.loc[frame_number]
            second_method_data = second_method_indexed.loc[frame_number]

            # Handle duplicate frames - take first row if DataFrame returned
            if isinstance(first_method_data, pd.DataFrame):
                first_method_row = first_method_data.iloc[0]
            else:
                first_method_row = first_method_data

            if isinstance(second_method_data, pd.DataFrame):
                second_method_row = second_method_data.iloc[0]
            else:
                second_method_row = second_method_data

        except KeyError:
            differences.append(f"Frame {frame_number}: missing in one of the files")
            continue

        # Compare all columns
        for column_name in columns_to_compare:
            first_value = first_method_row[column_name]
            second_value = second_method_row[column_name]

            # Skip if both values are null
            if pd.isnull(first_value) and pd.isnull(second_value):
                continue

            # Record difference if values don't match
            if first_value != second_value:
                differences.append(
                    f"Frame {frame_number}: '{column_name}' differs "
                    f"(method0={first_value}, method7={second_value})"
                )

    return differences


def write_results(
    differences: List[str], output_path: Path, start_frame: int, end_frame: int
) -> None:
    with open(output_path, "w") as output_file:
        if differences:
            output_file.write("\n".join(differences) + "\n")
        else:
            output_file.write(
                f"No differences found in frames {start_frame} to {end_frame}.\n"
            )


def main() -> None:
    """Main entry point for the motion vector comparison tool."""
    if len(sys.argv) != 6:
        print(
            "Usage: python3 mv_compare.py <method0.csv> <method7.csv> "
            "<start_frame> <end_frame> <output.txt>"
        )
        sys.exit(1)

    method0_file_path = Path(sys.argv[1])
    method7_file_path = Path(sys.argv[2])
    start_frame = int(sys.argv[3])
    end_frame = int(sys.argv[4])
    output_file_path = Path(sys.argv[5])

    # Validate frame range
    if start_frame > end_frame:
        print(f"Error: start_frame ({start_frame}) must be <= end_frame ({end_frame})")
        sys.exit(1)

    try:
        method0_dataframe = pd.read_csv(method0_file_path)
        method7_dataframe = pd.read_csv(method7_file_path)

        frame_differences: List[str] = compare_frames(
            method0_dataframe, method7_dataframe, start_frame, end_frame
        )
        write_results(frame_differences, output_file_path, start_frame, end_frame)
        print(f"Comparison complete. Results written to {output_file_path}")

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
