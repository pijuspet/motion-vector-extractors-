#include <libavutil/motion_vector.h>
#include <libavformat/avformat.h>
#include <libavcodec/avcodec.h>
#include <stdio.h>

int main(int argc, char **argv) {
    AVFormatContext *fmt_ctx = NULL;
    AVCodecContext *dec_ctx = NULL;
    AVPacket *pkt = NULL;
    AVFrame *frame = NULL;
    int video_idx, frame_num = 0;

    int do_print = 1;
    if (argc < 2) { printf("Usage: %s <input> [print]\n", argv[0]); return 1; }
    if (argc >= 3) do_print = atoi(argv[2]);

    avformat_network_init();
    avformat_open_input(&fmt_ctx, argv[1], NULL, NULL);
    avformat_find_stream_info(fmt_ctx, NULL);
    video_idx = av_find_best_stream(fmt_ctx, AVMEDIA_TYPE_VIDEO, -1, -1, NULL, 0);
    dec_ctx = avcodec_alloc_context3(NULL);
    dec_ctx->thread_count = 1;
    avcodec_parameters_to_context(dec_ctx, fmt_ctx->streams[video_idx]->codecpar);
    AVDictionary *opts = NULL; av_dict_set(&opts, "flags2", "+export_mvs", 0);
    avcodec_open2(dec_ctx, avcodec_find_decoder(dec_ctx->codec_id), &opts);
    pkt = av_packet_alloc();
    frame = av_frame_alloc();

    if (do_print)
        printf("frame,method_id,source,w,h,src_x,src_y,dst_x,dst_y,flags,motion_x,motion_y,motion_scale\n");

    while (av_read_frame(fmt_ctx, pkt) >= 0) {
        if (pkt->stream_index == video_idx) {
            avcodec_send_packet(dec_ctx, pkt);
            while (avcodec_receive_frame(dec_ctx, frame) >= 0) {
                AVFrameSideData *sd = av_frame_get_side_data(frame, AV_FRAME_DATA_MOTION_VECTORS);
                if (sd && do_print) {
                    const AVMotionVector *mvs = (const AVMotionVector *)sd->data;
                    for (int i = 0; i < sd->size / sizeof(*mvs); i++) {
                        const AVMotionVector *mv = &mvs[i];
                        printf("%d,0,%d,%d,%d,%d,%d,%d,%d,0x%llx,%d,%d,%d\n",
                            frame_num, mv->source, mv->w, mv->h, mv->src_x, mv->src_y,
                            mv->dst_x, mv->dst_y, mv->flags, mv->motion_x, mv->motion_y, mv->motion_scale);
                    }
                }
                frame_num++;
                av_frame_unref(frame);
            }
        }
        av_packet_unref(pkt);
    }

    avcodec_free_context(&dec_ctx); avformat_close_input(&fmt_ctx);
    av_frame_free(&frame); av_packet_free(&pkt);
    return 0;
}
