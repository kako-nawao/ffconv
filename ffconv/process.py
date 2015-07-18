import json
import subprocess

from ffconv import profiles


def execute_cmd(cmd):
    """
    Wrapper around subprocess' Popen/communicate usage pattern, capturing
    output and errors (which are raised).

    :param cmd: shell command as string
    :return: output of command
    """
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as process:
        try:
            output = b''
            for line in iter(process.stdout.readline, b''):
                if b'Error' in line:
                    raise ValueError(line.decode('utf-8'))
                else:
                    output += line

        except:
            process.kill()
            process.wait()
            raise

        else:
            retcode = process.poll()
            if retcode:
                raise subprocess.CalledProcessError(retcode, process.args, output=output)

    # All good, decode output and return it
    return output.decode('utf-8')


class FileProcessor(object):
    tmp_file = 'tmp.mkv'

    def __init__(self, input, output, profile):
        self.input = input
        self.output = output
        try:
            self.profile = getattr(profiles, profile.upper())
        except AttributeError:
            raise ValueError('Profile {} could not be found'.format(profile))

    def process(self):
        """
        Main method, used to process a file completely.

        :return: processing stats
        """
        print('Processing file <input:{} profile:{} output:{}>'.format(self.input, self.profile['name'], self.output))
        print(' - Probing...')
        original_streams = self.probe()
        print(' - Processing streams...')
        processed_streams = self.process_streams(original_streams)
        print(' - Merging streams into output...')
        inputs = self.merge(processed_streams)

        # Note: at this point, input can be empty if no streams were converted,
        # in which case the original file is our output
        res = {}
        if inputs:
            print(' - Cleaning temporary files...')
            if not self.output:
                self.replace_original()
            self.clean_up(inputs)
            res.update({'streams': len(processed_streams), 'output': self.output})

        # Return stats
        print('Done')
        return res

    def probe(self):
        """
        Probe the input file to get the streams data.

        :return: list of streams data (dicts)
        """
        cmd = ['ffprobe', '-v', 'quiet', '-show_streams', '-of', 'json', self.input]
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
            # Find all processors that match media type
            processor_types = list(filter(lambda x: x.media_type == stream['codec_type'],
                                          [VideoProcessor, AudioProcessor, SubtitleProcessor]))

            if processor_types:
                # For now just select the first one that matched media type
                processor_cls = processor_types[0]
                processor = processor_cls(self.input, stream, self.profile)
                result = processor.process()
                processed_streams.append(result)
            else:
                print('   - Skipping stream {}, media type {} not recognized'.format(stream['index'], stream['codec_type']))

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
            if not stream['input'] in inputs:
                inputs.append(stream['input'])

            # Then add mapping (input index must come from filename)
            maps.append('{}:{}'.format(inputs.index(stream['input']), stream['index']))

            # Finally, add language if available (map index is always last one)
            if stream.get('language'):
                meta.extend(['-metadata:s:{}'.format(len(maps) - 1),
                             'language={}'.format(stream['language'])])

        # Merge inputs if we have more than one (1 means no streams were converted, nothing to do)
        if len(inputs) > 1:
            # Build merge command and execute it
            cmd = ['ffmpeg']
            for input in inputs:
                cmd.extend(['-i', input])
            for map in maps:
                cmd.extend(['-map', map])
            cmd.extend(meta)
            cmd.extend(['-c', 'copy'])
            cmd.append(self.output or self.tmp_file)
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
        cmd = ['mv', self.tmp_file, self.input]
        execute_cmd(cmd)
        self.output = self.input

    def clean_up(self, files):
        """
        Remove the given files.

        :param files: files used as input in the final merge
        :return:
        """
        cmd = ['rm']
        cmd.extend(files)
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
        raise NotImplementedError('{} cannot clean up {} yet.'.format(self.__class__.__name__, self.media_type))

    def convert(self):
        raise NotImplementedError('{} cannot convert {} yet.'.format(self.__class__.__name__, self.media_type))

    def process(self):
        """
        Process this stream, which might mean converting it or not.

        :return: processed stream data
        """
        print('   - Processing stream <index:{} type:{} codec:{}>...'.format(self.index, self.media_type, self.codec))
        if self.must_convert:
            print('     - Converting...')
            self.convert()
            print('     - Cleaning up file...')
            self.clean_up()
            self.input = self.output
            self.index = 0
            print('   - Done')
        else:
            print('     - Skipping, no conversion required')

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
        self.channels = int(stream['channels'])
        self.target_channels = int(profile[self.media_type]['channels'])

    @property
    def must_convert(self):
        return any((super(AudioProcessor, self).must_convert,
                    self.channels != self.target_channels))

    def clean_up(self):
        pass

    def convert(self):
        cmd = ['ffmpeg', '-i', self.input, '-map', '0:{}'.format(self.index),
               '-strict', '-2', '-c:a', self.target_codec, '-ac:0',
               str(self.target_channels), self.output]
        execute_cmd(cmd)


class SubtitleProcessor(StreamProcessor):
    media_type = 'subtitle'
    encodings = ('utf-8', 'iso-8859-1')

    def clean_up(self):
        cmd = ['sed', '-i', '-e', r"s/<font[^>]*>//g", '-e', r"s/<\/font>//g",
               '-e', r"s/<I>/<i>/g", '-e', r"s/<\/I>/<\/i>/g", self.output]
        execute_cmd(cmd)

    def convert(self):
        index = '0:{}'.format(self.index)
        for encoding in self.encodings:
            try:
                cmd = ['ffmpeg', '-sub_charenc', encoding, '-i', self.input, '-map', index, self.output]
                execute_cmd(cmd)
                return

            except Exception as e:
                cmd = ['rm', self.output]
                execute_cmd(cmd)

        raise ValueError('Could not extract stream {}'.format(index))

