
import json
import subprocess

from profiles import ROKU


def execute_cmd(cmd, split=True):
    """
    Wrapper around subprocess' Popen/communicate usage pattern, capturing
    output and errors (which are raised).

    :param cmd: shell command as string
    :return: output of command
    """
    if split:
        cmd = cmd.split()
    output = subprocess.check_output(cmd)
    return output.decode('utf-8')


class FileProcessor(object):
    tmp_file = 'tmp.mkv'

    def __init__(self, input, output, profile):
        self.input = input
        self.output = output
        self.profile = globals().get(profile.upper())
        if not self.profile:
            raise ValueError('Profile {} could not be found'.format(profile))

    def process(self):
        """
        Main method, used to process a file completely.

        :return: processing stats
        """
        original_streams = self.probe()
        processed_streams = self.process_streams(original_streams)
        inputs = self.merge(processed_streams)

        # Note: at this point, input can be empty if no streams were converted,
        # in which case the original file is our output
        if inputs:
            if not self.output:
                self.replace_original()
            self.clean_up(inputs)

        # Return stats
        return {'streams': len(processed_streams), 'output': self.output}

    def probe(self):
        """
        Probe the input file to get the streams data.

        :return: list of streams data (dicts)
        """
        cmd = 'ffprobe -v quiet -of json -show_streams {}'.format(self.input)
        output = execute_cmd(cmd)
        return json.loads(output)['streams']

    def process_streams(self, original_streams):
        """
        Process each of the streams in the input file.
        The processing is delegated to StreamProcessor subclasses.

        :param original_streams: list of streams data as probed
        :return: list of processed streams data
        """
        processed_streams = []
        for stream in original_streams:
            processor_cls = list(filter(lambda x: x.media_type == stream['codec_type'],
                                        [VideoProcessor, AudioProcessor, SubtitleProcessor]))[0]
            processor = processor_cls(self.input, stream, self.profile)
            result = processor.process()
            processed_streams.append(result)
        return processed_streams

    def merge(self, streams):
        """
        Merge all processed streams into output file.

        :param streams: processed streams data
        :return: list of input files
        """
        inputs = []
        maps = []
        meta = []

        # Construct lists with parameters
        for stream in streams:
            # First, add stream filename to inputs if not there yet
            if not stream['filename'] in inputs:
                inputs.append(stream['filename'])

            # Then add mapping (input index must come from filename)
            maps.append('-map {}:{}'.format(inputs.index(stream['filename']), stream['index']))

            # Finally, add language if available (map index is always last one)
            if stream.get('language'):
                meta.append('-metadata:s:{} language={}'.format(len(maps) - 1, stream['language']))

        # Merge inputs if we have more than one (1 means no streams were converted, nothing to do)
        if len(inputs) > 1:
            # Build merge command and execute it
            cmd = 'ffmpeg -i {} {} -c copy {} {}'.format(
                ' -i '.join(inputs), ' '.join(maps), ' '.join(meta), self.output or self.tmp_file
            )
            execute_cmd(cmd)

        # Remove input main input from list of inputs, because we either keep it
        # or we replace it, in which case we'll "mv <tmp> <input>" anyway
        inputs.remove(self.input)

        # Finally, return all inputs used in merge (empty if there was no merge)
        return inputs

    def replace_original(self):
        """
        Replace the original input with the temporary file.

        :return:
        """
        cmd = 'mv {} {}'.format(self.tmp_file, self.input)
        execute_cmd(cmd)
        self.output = self.input

    def clean_up(self, files):
        """
        Remove the given files.

        :param files: files used as input in the final merge
        :return:
        """
        cmd = 'rm {}'.format(' '.join(files))
        execute_cmd(cmd)


class StreamProcessor(object):
    media_type = None

    def __init__(self, input, stream, profile):
        self.input = input
        self.index = stream['index']
        self.codec = stream['codec_name']
        self.language = stream.get('tags', {}).get('LANGUAGE')
        self.target_codec = profile[self.media_type]['codec']
        self.output = '{}-{}.{}'.format(self.media_type, self.index, self.target_codec)

    @property
    def must_convert(self):
        """
        Do we need to convert this stream?

        :return:
        """
        return self.codec != self.target_codec

    def clean_up(self):
        raise NotImplementedError()

    def convert(self):
        raise NotImplementedError()

    def process(self):
        """
        Process this stream, which might mean converting it or not.

        :return: processed stream data
        """
        if self.must_convert:
            self.convert()
            self.clean_up()
            self.input = self.output
            self.index = 0

        res = {'input': self.input, 'index': self.index}
        if self.language:
            res['language'] = self.language

        return res


class VideoProcessor(StreamProcessor):
    media_type = 'video'


class AudioProcessor(StreamProcessor):
    media_type = 'audio'

    def __init__(self, input, stream, profile):
        super(AudioProcessor, self).__init__(input, stream, profile)
        self.channels = str(stream['channels'])
        self.target_channels = profile[self.media_type]['channels']

    @property
    def must_convert(self):
        return any((super(AudioProcessor, self).must_convert,
                    self.channels != self.target_channels))

    def clean_up(self):
        pass

    def convert(self):
        cmd = 'ffmpeg -i {} -map 0:{} -strict experimental -c:a {} -ac:0:{} {} {}'.format(
            self.input, self.index, self.target_codec, self.index,
            self.target_channels, self.output
        )
        execute_cmd(cmd)


class SubtitleProcessor(StreamProcessor):
    media_type = 'subtitle'

    def clean_up(self):
        cmd = ['sed', '-i', '-e', r"s/<font[^>]*>//g", '-e', r"s/<\/font>//g",
               '-e', r"s/<I>/<i>/g", '-e', r"s/<\/I>/<\/i>/g", self.output]
        execute_cmd(cmd, split=False)

    def convert(self):
        cmd = 'ffmpeg -i {} -map 0:{} {}'.format(self.input, self.index, self.output)
        execute_cmd(cmd)

