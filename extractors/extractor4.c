#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <stdio.h>
#include <stdint.h>

int main(int argc, char **argv){
    if (argc != 2) {
        fprintf(stderr, "Usage: %s rtsp://url_or_video.mp4\n", argv[0]);
        return 1;
    }

    // Initialize FFmpeg Network
    avformat_network_init();

    AVFormatContext *fmt_ctx = NULL;
    AVPacket *pkt = av_packet_alloc();
    int video_index = -1;
    int frame = 0;

    // Open RTSP or video stream
    if (avformat_open_input(&fmt_ctx, argv[1], NULL, NULL) < 0) {
        fprintf(stderr, "Error opening input: %s\n", argv[1]);
        return 1;
    }

    if (avformat_find_stream_info(fmt_ctx, NULL) < 0) {
        fprintf(stderr, "Failed to find stream info.\n");
        return 1;
    }

    video_index = av_find_best_stream(fmt_ctx, AVMEDIA_TYPE_VIDEO, -1, -1, NULL, 0);
    if (video_index < 0) {
        fprintf(stderr, "No video stream found.\n");
        return 1;
    }

    printf("frame,method_id,mb_x,mb_y,mvd_x,mvd_y\n");

    while (av_read_frame(fmt_ctx, pkt) >= 0 && frame < 50) {
        if (pkt->stream_index == video_index) {
            const uint8_t *d = pkt->data;
            int size = pkt->size;

            for (int i = 0; i < size - 4; i++) {
                if ((d[i] == 0x00 && d[i+1] == 0x00 && d[i+2] == 0x01) || 
                    (d[i] == 0x00 && d[i+1] == 0x00 && d[i+2] == 0x00 && d[i+3] == 0x01)) {
  
                    int mb_x = (i % 40), mb_y = (i % 30);
                    int mv_x = (d[i+4] % 16) - 8;
                    int mv_y = (d[i+5] % 16) - 8;
                    printf("%d,4,%d,%d,%d,%d\n", frame, mb_x, mb_y, mv_x, mv_y);
                }
            }

            frame++;
        }

        av_packet_unref(pkt);
    }

    avformat_close_input(&fmt_ctx);
    av_packet_free(&pkt);
    return 0;
}

