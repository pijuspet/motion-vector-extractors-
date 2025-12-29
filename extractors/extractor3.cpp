#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "writer.h"

extern  "C" {
#include <libavformat/avformat.h>
}

typedef struct {
    const uint8_t* buf;
    size_t size;
    size_t bitpos;
} BitReader;

static void br_init(BitReader* br, const uint8_t* buf, size_t size) {
    br->buf = buf;
    br->size = size;
    br->bitpos = 0;
}

static int br_read_bit(BitReader* br) {
    if (br->bitpos >= br->size * 8)
        return -1;
    size_t b = br->bitpos >> 3;
    int bit = (br->buf[b] >> (7 - (br->bitpos & 7))) & 1;
    br->bitpos++; return bit;
}

static uint32_t br_read_ue(BitReader* br) {
    int zeros = 0;
    while (br_read_bit(br) == 0)
        if (++zeros > 31)
            break;
    uint32_t val = 1;
    for (int i = 0;i < zeros;i++)
        val = (val << 1) | br_read_bit(br);
    return val - 1;
}

static int32_t br_read_se(BitReader* br) {
    uint32_t v = br_read_ue(br);
    return (v & 1) ? (int32_t)((v + 1) / 2) : -(int32_t)(v / 2);
}

const uint8_t* find_start_code(const uint8_t* p, const uint8_t* e) {
    for (; p + 3 < e; p++) {
        if (p[0] == 0 && p[1] == 0 && p[2] == 1)
            return p + 3; if (p + 4 < e && p[0] == 0 && p[1] == 0 && p[2] == 0 && p[3] == 1)
            return p + 4;
    }
    return NULL;
}

int main(int argc, char** argv) {
    AVFormatContext* fmt_ctx = NULL;
    AVPacket* pkt = NULL;
    int video_stream_index = -1;
    int frame_num = 0;
    int do_print = 1;
    std::string file_name = "";

    if (argc <= 2) {
        fprintf(stderr, "Usage: %s file_or_rtsp_url\n", argv[0]);
        return 1;
    }
    if (argc >= 3)
        do_print = atoi(argv[2]);
    if (argc >= 4)
        file_name = argv[3];


    if (avformat_open_input(&fmt_ctx, argv[1], NULL, NULL) < 0) {
        fprintf(stderr, "Could not open input file.\n");
        return -1;
    }
    
    if (avformat_find_stream_info(fmt_ctx, NULL) < 0) {
        fprintf(stderr, "Could not find stream info.\n");
        return -1;
    }

    video_stream_index = av_find_best_stream(fmt_ctx, AVMEDIA_TYPE_VIDEO, -1, -1, NULL, 0);
    if (video_stream_index < 0) {
        fprintf(stderr, "Could not find video stream\n");
        return 1;
    }

    pkt = av_packet_alloc();

    if (!pkt) {
        fprintf(stderr, "Could not allocate packet.\n");
        return -1;
    }

    MotionVectorWriter writer;
    if (do_print) {
        if (!writer.Open(file_name)) {
            fprintf(stderr, "Failed to open output file\n");
            return 1;
        }
    }

    while (av_read_frame(fmt_ctx, pkt) >= 0) {
        if (pkt->stream_index == video_stream_index) {
            const uint8_t* start = pkt->data, * end = pkt->data + pkt->size, * nal;
            while ((nal = find_start_code(start, end))) {
                int nal_type = nal[0] & 0x1F;
                const uint8_t* next = find_start_code(nal, end);
                int nalsz = (next ? next : end) - nal;
                if (nal_type == 1 || nal_type == 5) {
                    BitReader br;
                    br_init(&br, nal + 1, nalsz - 1);
                    br_read_ue(&br);
                    br_read_ue(&br);
                    br_read_ue(&br);
                    int mb_x = 0, mb_y = 0;
                    for (int i = 0;i < 100 && br.bitpos < br.size * 8;i++) {
                        int32_t mvd_x = br_read_se(&br), mvd_y = br_read_se(&br);
                        //printf("%d,3,%d,%d,%d,%d\n",frame_num,mb_x,mb_y,mvd_x,mvd_y);
                        mb_x++;
                        if (mb_x >= 120) {
                            mb_x = 0;
                            mb_y++;
                        }
                    }
                }
                start = next ? next : end;
            }
            frame_num++;
        }
        av_packet_unref(pkt);
    }

    avformat_close_input(&fmt_ctx);
    av_packet_free(&pkt);
    return 0;
}
