#include <stdio.h>

extern "C" {
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
}

int main(int argc, char** argv) {
    AVFormatContext* fmt_ctx = NULL;
    AVCodecContext* dec_ctx = NULL;
    AVPacket* pkt = NULL;
    AVFrame* frame = NULL;
    int video_stream_index = -1;
    int frame_num = 0;

    if (argc < 2) { printf("Usage: %s <input>\n", argv[0]); return 1; }

    avformat_network_init();

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

    dec_ctx = avcodec_alloc_context3(NULL);
    if (!dec_ctx) {
        fprintf(stderr, "Could not allocate codec context.\n");
        return -1;
    }

    // dec_ctx->thread_count = 1; extractor6.c
    if (avcodec_parameters_to_context(dec_ctx, fmt_ctx->streams[video_stream_index]->codecpar) < 0) {
        fprintf(stderr, "Failed to copy codec parameters to codec context.\n");
        return -1;
    }
    if (avcodec_open2(dec_ctx, avcodec_find_decoder(dec_ctx->codec_id), NULL) < 0) {
        fprintf(stderr, "Could not open codec.\n");
        return -1;
    }

    pkt = av_packet_alloc();
    frame = av_frame_alloc();

    if (!pkt || !frame) {
        fprintf(stderr, "Could not allocate packet or frame.\n");
        return -1;
    }

    while (av_read_frame(fmt_ctx, pkt) >= 0) {
        if (pkt->stream_index == video_stream_index) {
            avcodec_send_packet(dec_ctx, pkt);
            while (avcodec_receive_frame(dec_ctx, frame) >= 0) {
                frame_num++;
                av_frame_unref(frame);
            }
        }
        av_packet_unref(pkt);
    }

    printf("Decoded %d frames\n", frame_num);

    avcodec_free_context(&dec_ctx);
    avformat_close_input(&fmt_ctx);
    av_frame_free(&frame);
    av_packet_free(&pkt);
    return 0;
}

