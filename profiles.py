"""
Streams information

input:
    codec_type: [video, audio, subtitle]
    codec_name: [h264, aac, ass, srt]
    channels: [2, 6]
    channel_layout: [stereo, 5.1]
    tags:
        LANGUAGE: [eng, spa, fre]

output:
    filename: name of file that will be input for merged file
    index: index of the stream in the input file
    language (optional): metadata for the stream

"""

ROKU = {
    'video': {
        'codec': 'h264'
    },
    'audio': {
        'codec': 'aac',
        'channels': 2
    },
    'subtitle': {
        'codec': 'srt'
    }
}