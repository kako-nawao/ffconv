"""
This module contains the actual stream processors, which do the actual
media conversions.
"""

import logging

from .utils import execute_cmd, CalledProcessError


class StreamProcessor(object):
    """
    Base class for all stream processors, providing the basic interface and
    common functionality.
    """
    media_type = None

    def __init__(self, in_file, stream, profile):
        """
        Set generic input and target specs from input file, stream and profile.
        """
        # Set direct values from input and stream
        self.input = in_file
        self.index = stream['index']
        self.codec = stream['codec_name']
        self.language = stream.get('tags', {}).get('language')
        if self.language == 'und':
            self.language = None
        self.allowed_codecs = profile[self.media_type]['codecs']

        # Select target values from profile
        self.target_codec = self.allowed_codecs[0]
        self.target_container = profile[self.media_type]['container']
        self.output = '{}-{}.{}'.format(self.media_type, self.index,
                                        self.target_container)

        # Set logger
        self.logger = logging.getLogger()

        # Set stream-specific data
        self._init_stream(stream, profile)

    def __str__(self):
        return 'Stream <#{} {} {}>'.format(self.index, self.media_type, self.codec)

    def _init_stream(self, *args):
        """
        Set stream-specific input and target specs from input file, stream
        and profile.

        Must be overridden by subclasses.
        """
        return NotImplementedError('{} cannot set stream-specific data.'.format(self.__class__.__name__))

    @property
    def must_convert(self):
        """
        Default implementation for decision to convert the stream, based only
        on codec compatibility.

        Subclasses might modify or replace it completely.
        """
        return self.codec not in self.allowed_codecs

    def clean_up(self):
        """
        Post-conversion stream clean-up, must be defined by subclasses.
        """
        raise NotImplementedError('{} cannot clean up {} yet.'.format(self.__class__.__name__, self.media_type))

    def convert(self):
        """
        Conversion, must be defined by subclasses.
        """
        raise NotImplementedError('{} cannot convert {} yet.'.format(self.__class__.__name__, self.media_type))

    def process(self):
        """
        Process this stream, which might mean converting it or not.

        :return: processed stream data
        """
        if self.must_convert:
            # Must convert, run conversion and clean-up
            self.logger.debug('{}: converting to {}'.format(self, self.target_codec))
            self.convert()
            self.logger.debug('{}: cleaning up'.format(self))
            self.clean_up()
            self.input = self.output
            self.index = 0

        else:
            # Nothing to do
            self.logger.debug('{}: skipping, no conversion required'.format(self))

        # Build and return data: input file, index and language
        # (used by merger)
        res = {'input': self.input, 'index': self.index}
        if self.language:
            res['language'] = self.language
        return res


class VideoProcessor(StreamProcessor):
    """
    Video stream processor, provides specific video conversion functionality.
    """
    media_type = 'video'

    def _init_stream(self, stream, profile):
        """
        Set video-specific input and target specs,
        """
        # Set input reference frames value
        self.refs = int(stream['refs'])

        # Assert height is included in stream
        if 'height' not in stream:
            raise KeyError("Height not specified in video stream.")

        # Get height and set target for ref frames (default is 4)
        self.max_refs = 4
        height = int(stream['height'])
        for h, f in sorted(profile[self.media_type]['max_refs'].items()):
            if height <= h:
                self.max_refs = f
                break

        # Set target values for profile, level, preset and quality
        self.target_profile = profile[self.media_type]['profile']
        self.target_level = profile[self.media_type]['level']
        self.target_preset = profile[self.media_type]['preset']
        self.target_quality = profile[self.media_type]['quality']

    @property
    def must_convert(self):
        """
        Conversion check: besides base check (codec compatibility), check that
        reference frames are acceptable.
        """
        return any((super(VideoProcessor, self).must_convert,
                    self.refs > self.max_refs))

    def clean_up(self):
        """
        Cleanup is no-op for video, because the stream is not modified.
        """
        pass

    def convert(self):
        """
        Convert the video stream according to the selected target values,
        creating a temporary video file to use by merger.
        """
        cmd = ['ffmpeg', '-i', self.input, '-map', '0:{}'.format(self.index),
               '-c:v', self.target_codec, '-preset', str(self.target_preset),
               '-crf', str(self.target_quality), '-profile:v',
               self.target_profile, '-level', self.target_level, self.output]
        execute_cmd(cmd)


class AudioProcessor(StreamProcessor):
    """
    Audio stream processor, provides specific audio conversion functionality.
    """
    media_type = 'audio'

    def _init_stream(self, stream, profile):
        """
        Set audio-specific input and target specs,
        """
        # Set number of channels in input stream
        self.channels = int(stream['channels'])

        # Set target quality and channels
        self.max_channels = int(profile[self.media_type]['max_channels'])
        self.target_quality = profile[self.media_type]['quality']

    @property
    def must_convert(self):
        """
        Conversion check: besides base check (codec compatibility), check that
        number of channels is acceptable.
        """
        return any((super(AudioProcessor, self).must_convert,
                    self.channels > self.max_channels))

    def clean_up(self):
        """
        Cleanup is no-op for audio, because the stream is not modified.
        """
        pass

    def convert(self):
        """
        Convert the audio stream according to the selected target values,
        creating a temporary audio file to use by merger.
        """
        cmd = ['ffmpeg', '-i', self.input, '-map', '0:{}'.format(self.index),
               '-c:a', self.target_codec, '-q:a', str(self.target_quality),
               '-ac:0', str(self.max_channels), self.output]
        execute_cmd(cmd)


class SubtitleProcessor(StreamProcessor):
    """
    Subtitle stream processor, provides specific subtitle conversion
    functionality.
    """
    media_type = 'subtitle'

    # Override super property to always convert (we always want to clean-up)
    must_convert = True

    def _init_stream(self, stream, profile):
        """
        Set audio-specific input and target specs,
        """
        # Set target encodings
        self.target_encodings = profile[self.media_type]['encodings']

    def clean_up(self):
        """
        Cleanup for subtitles consists of removing "weird tags", such as fonts
        and comments (eg, <i></i>, {lala}).
        """
        cmd = ['sed', '-i', '-e', r"s/<[^>]*>//ig", '-e', r"s/{[^}]*}//ig",
               self.output]
        execute_cmd(cmd)

    def convert(self):
        """
        Convert the subtitle stream with the target encoding and extract it.

        Note: this will attempt to convert with all target encodings until one
        works or raise and exception if none did. Dumb? We've no way to detect
        the encoding, so it's our only choice.
        """
        index = '0:{}'.format(self.index)

        # Cycle through encodings
        for encoding in self.target_encodings:
            try:
                # Try to extract with current encoding
                cmd = ['ffmpeg', '-sub_charenc', encoding, '-i', self.input,
                       '-map', index, self.output]
                execute_cmd(cmd)

            except CalledProcessError:
                # Failed: erase output file
                cmd = ['rm', self.output]
                execute_cmd(cmd)

            else:
                # Worked
                return

        # If none worked, we raise an exception
        raise ValueError('Could not extract stream {}'.format(index))
