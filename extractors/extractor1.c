#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>
#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/motion_vector.h>
#include <libavutil/opt.h>

void print_mv(const AVMotionVector* mv, int frame_idx, FILE* out) {
    fprintf(out, "%d,2,%d,%d,%d,%d,%d,%d,%d,0x%" PRIx64 ",%d,%d,%d\n",
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

    if (avformat_find_stream_info(fmt_ctx, NULL) < 0) {
        fprintf(stderr, "Could not find stream info.\n");
        return -1;
    }

    int video_stream_index = -1;
    for (unsigned i = 0; i < fmt_ctx->nb_streams; i++) {
        if (fmt_ctx->streams[i]->codecpar->codec_type == AVMEDIA_TYPE_VIDEO) {
            video_stream_index = i;
            break;
        }
    }
    if(video_stream_index < 0) {
        fprintf(stderr, "No video stream found.\n");
        return -1;
    }

    AVCodec* codec = avcodec_find_decoder(fmt_ctx->streams[video_stream_index]->codecpar->codec_id);
    if(!codec){
        fprintf(stderr, "Codec not found.\n");
        return -1;
    }

    AVCodecContext* codec_ctx = avcodec_alloc_context3(codec);
    if(!codec_ctx){
        fprintf(stderr, "Could not allocate codec context.\n");
        return -1;
    }
    if (avcodec_parameters_to_context(codec_ctx, fmt_ctx->streams[video_stream_index]->codecpar) < 0) {
        fprintf(stderr, "Failed to copy codec parameters to codec context.\n");
        return -1;
    }

    // Enable multi-threaded decoding
    codec_ctx->thread_count = 1; // 0 lets ffmpeg decide based on CPU cores
    codec_ctx->export_side_data |= AV_CODEC_EXPORT_DATA_MVS;

    if (avcodec_open2(codec_ctx, codec, NULL) < 0) {
        fprintf(stderr, "Could not open codec.\n");
        return -1;
    }

    AVPacket* pkt = av_packet_alloc();
    AVFrame* frame = av_frame_alloc();
    if(!pkt || !frame) {
        fprintf(stderr, "Could not allocate packet or frame.\n");
        return -1;
    }

    int frame_idx = 0;
    // Buffer output to a file (stdout could be slow)
    FILE* out = stdout;

    fprintf(out, "frame,method_id,source,w,h,src_x,src_y,dst_x,dst_y,flags,motion_x,motion_y,motion_scale\n");

    while (av_read_frame(fmt_ctx, pkt) >= 0) {
        if (pkt->stream_index == video_stream_index) {
            int ret = avcodec_send_packet(codec_ctx, pkt);
            if (ret < 0) {
                fprintf(stderr, "Error sending packet for decoding: %d\n", ret);
                break;
            }

            // Receive all available frames
            while (ret >= 0) {
                ret = avcodec_receive_frame(codec_ctx, frame);
                if (ret == AVERROR(EAGAIN) || ret == AVERROR_EOF)
                    break;
                else if (ret < 0) {
                    fprintf(stderr, "Error during decoding.\n");
                    break;
                }

                AVFrameSideData* sd = av_frame_get_side_data(frame, AV_FRAME_DATA_MOTION_VECTORS);
                if (sd) {
                    const AVMotionVector* mvs = (const AVMotionVector*)sd->data;
                    int nb_mvs = sd->size / sizeof(AVMotionVector);
                    for (int i = 0; i < nb_mvs; ++i) {
                        i=i;
                        print_mv(&mvs[i], frame_idx, out);
                    }
                }

                av_frame_unref(frame);
                frame_idx++;
            }
        }
        av_packet_unref(pkt);
    }

    // Flush decoder
    avcodec_send_packet(codec_ctx, NULL);
    while (avcodec_receive_frame(codec_ctx, frame) == 0) {
        AVFrameSideData* sd = av_frame_get_side_data(frame, AV_FRAME_DATA_MOTION_VECTORS);
        if (sd) {
            const AVMotionVector* mvs = (const AVMotionVector*)sd->data;
            int nb_mvs = sd->size / sizeof(AVMotionVector);
            for (int i = 0; i < nb_mvs; ++i) {
                i=i;
                print_mv(&mvs[i], frame_idx, out);
            }
        }
        av_frame_unref(frame);
        frame_idx++;
    }

    av_frame_free(&frame);
    av_packet_free(&pkt);
    avcodec_free_context(&codec_ctx);
    avformat_close_input(&fmt_ctx);

    return 0;
}

