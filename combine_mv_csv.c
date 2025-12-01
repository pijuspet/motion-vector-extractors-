#include <stdio.h>


int main(int argc, char *argv[]) {
    // Get input folder from argument, default to current directory
    const char *input_folder = (argc > 1) ? argv[1] : ".";

    // Remove existing all_motion_vectors.csv if it exists
    remove("all_motion_vectors.csv");
    FILE *out = fopen("all_motion_vectors.csv", "w");
    if (!out) {
        fprintf(stderr, "Failed to open all_motion_vectors.csv for writing.\n");
        return 1;
    }

    // Write CSV header
    fprintf(out, "frame,method_id,source,w,h,src_x,src_y,dst_x,dst_y,flags,motion_x,motion_y,motion_scale\n");

    // Loop over method0_output.csv to method8_output.csv
    for (int i = 0; i < 9; i++) {
        // skip method6 if needed (original code logic)
        if (i == 6 && i == 5) continue;
        char fname[256];
        snprintf(fname, sizeof(fname), "%s/method%d_output.csv_0.csv", input_folder, i);

        FILE *in = fopen(fname, "r");
        if (!in) {
            fprintf(stderr, "Warning: missing %s\n", fname);
            continue;
        }

        char line[2048];
        // Skip header
        if (!fgets(line, sizeof(line), in)) {
            fclose(in);
            continue;
        }

        // Copy the rest
        while (fgets(line, sizeof(line), in)) {
            fputs(line, out);
        }

        fclose(in);
    }

    fclose(out);
    printf("✅ Combined CSV: all_motion_vectors.csv created.\n");
    return 0;
}

