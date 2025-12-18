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
    int video_idx, frame_num = 0;

    if (argc < 2) { printf("Usage: %s <input>\n", argv[0]); return 1; }

    avformat_network_init();
    avformat_open_input(&fmt_ctx, argv[1], NULL, NULL);
    avformat_find_stream_info(fmt_ctx, NULL);
    video_idx = av_find_best_stream(fmt_ctx, AVMEDIA_TYPE_VIDEO, -1, -1, NULL, 0);
    dec_ctx = avcodec_alloc_context3(NULL);
    // dec_ctx->thread_count = 1; extractor6.c
    avcodec_parameters_to_context(dec_ctx, fmt_ctx->streams[video_idx]->codecpar);
    avcodec_open2(dec_ctx, avcodec_find_decoder(dec_ctx->codec_id), NULL);
    pkt = av_packet_alloc();
    frame = av_frame_alloc();

    while (av_read_frame(fmt_ctx, pkt) >= 0) {
        if (pkt->stream_index == video_idx) {
            avcodec_send_packet(dec_ctx, pkt);
            while (avcodec_receive_frame(dec_ctx, frame) >= 0) {
                frame_num++;
                av_frame_unref(frame);
            }
        }
        av_packet_unref(pkt);
    }

    printf("Decoded %d frames\n", frame_num);

    avcodec_free_context(&dec_ctx); avformat_close_input(&fmt_ctx);
    av_frame_free(&frame); av_packet_free(&pkt);
    return 0;
}

