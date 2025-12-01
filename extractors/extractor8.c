#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/motion_vector.h>
#include <libavutil/opt.h>

void print_mv(const AVMotionVector* mv, int frame_idx) {
    printf("%d,2,%d,%d,%d,%d,%d,%d,%d,0x%" PRIx64 ",%d,%d,%d\n",
           frame_idx,
           mv->source,
           mv->w, mv->h,
           mv->src_x, mv->src_y,
           mv->dst_x, mv->dst_y,
           (uint64_t)mv->flags,
           mv->motion_x, mv->motion_y, mv->motion_scale);
}

int main(int argc, char** argv) {
    if (argc < 2) {
        fprintf(stderr, "Usage: %s <input>\n", argv[0]);
        return -1;
    }

    avformat_network_init();

    AVFormatContext* fmt_ctx = NULL;
    if (avformat_open_input(&fmt_ctx, argv[1], NULL, NULL) < 0) {
        fprintf(stderr, "Could not open input file.\n");
        return -1;
    }

    avformat_find_stream_info(fmt_ctx, NULL);

    int video_stream_index = -1;
    for (unsigned i = 0; i < fmt_ctx->nb_streams; i++) {
        if (fmt_ctx->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_VIDEO) {
            video_stream_index = i;
            break;
        }
    }

    AVCodec* codec = avcodec_find_decoder(fmt_ctx->streams[video_stream_index]->codecpar->codec_id);
    AVCodecContext* codec_ctx = avcodec_alloc_context3(codec);
    avcodec_parameters_to_context(codec_ctx, fmt_ctx->streams[video_stream_index]->codecpar);

    codec_ctx->export_side_data = AV_CODEC_EXPORT_DATA_MVS;
    av_opt_set_int(codec_ctx, "motion_vectors_only", 1, 0);  // CUSTOM PATCHED FLAG

    avcodec_open2(codec_ctx, codec, NULL);

    AVPacket* pkt = av_packet_alloc();
    AVFrame* frame = av_frame_alloc();

    int frame_idx = 0;

    printf("frame,method_id,source,w,h,src_x,src_y,dst_x,dst_y,flags,motion_x,motion_y,motion_scale\n");

    while (av_read_frame(fmt_ctx, pkt) >= 0) {
        if (pkt->stream_index == video_stream_index) {
            avcodec_send_packet(codec_ctx, pkt);
            while (avcodec_receive_frame(codec_ctx, frame) == 0) {
                AVFrameSideData* sd = av_frame_get_side_data(frame, AV_FRAME_DATA_MOTION_VECTORS);
                if (sd) {
                    const AVMotionVector* mvs = (const AVMotionVector*)sd->data;
                    int nb_mvs = sd->size / sizeof(AVMotionVector);
                    for (int i = 0; i < nb_mvs; ++i) {
                        print_mv(&mvs[i], frame_idx);
                    }
                }
                av_frame_unref(frame);
                frame_idx++;
            }
        }
        av_packet_unref(pkt);
    }

    av_frame_free(&frame);
    av_packet_free(&pkt);
    avcodec_free_context(&codec_ctx);
    avformat_close_input(&fmt_ctx);
    return 0;
}

