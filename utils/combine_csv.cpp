#include <stdio.h>
#include <string>

int main(int argc, char* argv[]) {
    std::string absolute_path = argv[1];
    std::string fullpath = absolute_path + "/all_motion_vectors.csv";

    FILE* out = fopen(fullpath.c_str(), "w");
    if (!out) {
        fprintf(stderr, "Failed to open all_motion_vectors.csv for writing.\n");
        return 1;
    }

    // Write CSV header
    fprintf(out, "frame,method_id,source,w,h,src_x,src_y,dst_x,dst_y,flags,motion_x,motion_y,motion_scale\n");

    // Loop over method0_output.csv to method8_output.csv
    for (int i = 0; i < 9; i++) {
        char fname[256];
        snprintf(fname, sizeof(fname), "%s/method%d_output_0.csv", absolute_path.c_str(), i);


        FILE* in = fopen(fname, "r");
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
    printf("Combined CSV: all_motion_vectors.csv created.\n");
    return 0;
}

