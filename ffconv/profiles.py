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
    'name': 'Roku',
    'video': {
        'codecs': ['h264'],
        'container': 'mp4',
        'profile': 'high',
        'level': '4.1',
        'max_refs': 4,
        'quality': 21,
        'preset': 'slow'
    },
    'audio': {
        'codecs': ['mp3', 'aac', 'flac'],
        'container': 'mp3',
        'channels': 2,
        'quality': 2
    },
    'subtitle': {
        'codecs': ['srt'],
        'container': 'srt',
        'encodings': ['utf-8', 'iso-8859-1']
    }
}