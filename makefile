CC = gcc

# System FFmpeg flags (default pkg-config)
SYS_PKG = pkg-config
SYS_FF = $(shell $(SYS_PKG) --cflags --libs libavformat libavcodec libavutil)

# Custom FFmpeg install path
CUSTOM_PREFIX = /home/loab/Documents/MotionVectors/ffmpeg-mvonly
CUSTOM_PKG_CONFIG = PKG_CONFIG_PATH=$(CUSTOM_PREFIX)/lib/pkgconfig
CUST_FF_CFLAGS = $(shell $(CUSTOM_PKG_CONFIG) pkg-config --cflags libavformat libavcodec libavutil)
CUST_FF_LIBS   = $(shell $(CUSTOM_PKG_CONFIG) pkg-config --libs libavformat libavcodec libavutil)
CUST_RPATH = -Wl,-rpath,$(CUSTOM_PREFIX)/lib
CUST_FF = $(CUST_FF_CFLAGS) $(CUST_FF_LIBS) $(CUST_RPATH)

all:
	$(CC) -O2 -o extractor0 extractors/extractor0.c $(SYS_FF)
	$(CC) -O2 -o extractor1 extractors/extractor1.c $(SYS_FF)
	$(CC) -O2 -o extractor2 extractors/extractor2.c $(CUST_FF)
	$(CC) -O2 -o extractor3 extractors/extractor3.c $(SYS_FF)
	$(CC) -O2 -o extractor4 extractors/extractor4.c $(SYS_FF)
	$(CC) -O2 -o extractor5 extractors/extractor5.c $(SYS_FF)
	$(CC) -O2 -o extractor6 extractors/extractor6.c $(SYS_FF)
	$(CC) -O2 -o extractor7 extractors/extractor7.c $(CUST_FF)
	$(CC) -O2 -o extractor8 extractors/extractor8.c $(CUST_FF)
	echo $(CUSTOM_PREFIX) > custom
	
clean:
	rm -f extractor*

