"""
This module contains the actual file processor, which is the main object
that carries out the conversion.
"""
import json

from . import profiles
from .utils import execute_cmd, log
from .stream_processors import StreamProcessor


class FileProcessor(object):
    """
    Process for multimedia file, which delegates processing of streams to
    StreamProcessor subclasses.
    """
    tmp_file = 'tmp.mkv'

    @staticmethod
    def _build_merge_params(streams, inputs, maps, meta):
        """
        Build lists of inputs, maps and meta from processed streams.
        """
        for stream in streams:
            # First, add stream filename to inputs if not there yet
            if not stream['input'] in inputs:
                inputs.append(stream['input'])

            # Then add mapping (input index must come from filename)
            maps.append('{}:{}'.format(inputs.index(stream['input']),
                                       stream['index']))

            # Finally, add language if available (map index is always last one)
            if stream.get('language'):
                meta.extend(['-metadata:s:{}'.format(len(maps) - 1),
                             'language={}'.format(stream['language'])])

    @staticmethod
    def _build_merge_command(inputs, maps, meta, output):
        """
        Build merge command (if we need to make a conversion) as a list of
        strings.
        """
        cmd = []
        if len(inputs) > 1:
            # Build merge command and execute it
            cmd.append('ffmpeg')

            # Add each of the resulting inputs
            for in_file in inputs:
                cmd.extend(['-i', in_file])

            # Add each of the maps
            for map in maps:
                cmd.extend(['-map', map])

            # Extend with metadata
            cmd.extend(meta)

            # Copy all streams (they are already converted)
            cmd.extend(['-c', 'copy'])
            cmd.append(output)

        # Return command as list
        return cmd

    @staticmethod
    def clean_up(files):
        """
        Remove the given files.
        """
        cmd = ['rm']
        cmd.extend(files)
        execute_cmd(cmd)

    def __init__(self, in_file, output, profile):
        """
        Set input, output, profile and error placeholder.
        """
        # Set files and error placeholder
        self.input = in_file
        self.output = output
        self.error = None

        # Set profile if found (or raise an error)
        try:
            self.profile = getattr(profiles, profile.upper())
        except AttributeError:
            raise ValueError('Profile {} could not be found'.format(profile))

    def process(self):
        """
        Main process method, which probes the input file to get the input
        streams information, then delegates the stream processing to stream
        processor objects and then merges all resulting stream files into
        a single output file.
        """
        log('Processing file <input:{} profile:{} output:{}>'\
            .format(self.input, self.profile['name'], self.output))

        # First step, probe for file streams
        log('Probing...', 1)
        original_streams = self.probe()

        # Process streams
        log('Processing streams...', 1)
        processed_streams = self.process_streams(original_streams)

        # By now we could have an error
        if self.error:
            # We've an error, clean up all files
            inputs = {s['input'] for s in processed_streams}\
                .difference([self.input])
        else:
            # No errors, merge the files
            log('Merging streams into output...', 1)
            inputs = self.merge(processed_streams)

        # Clean up if we have inputs
        # Note: input can be empty if no streams were converted, in which case
        # the original file is our output, so we do nothing
        if inputs:
            log('Cleaning temporary files...', 1)
            if not (self.output or self.error):
                self.replace_original()
            self.clean_up(inputs)

        # If we had an error, raise it
        if isinstance(self.error, Exception):
            raise self.error

        # No errors, log that we're done and return result
        log('Done')
        return {'streams': len(processed_streams), 'output': self.output}

    def probe(self):
        """
        Probe the input file to get the streams data.

        :return: list of streams data (dicts)
        """
        cmd = ['ffprobe', '-v', 'quiet', '-show_streams',
               '-of', 'json', self.input]
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
        try:
            for stream in original_streams:
                # Find all processors that match media type
                proc_types = [pt for pt in StreamProcessor.__subclasses__()
                              if pt.media_type == stream['codec_type']]

                if proc_types:
                    # For now just select the first one that matched media type
                    processor_cls = proc_types[0]
                    processor = processor_cls(self.input, stream, self.profile)
                    result = processor.process()
                    processed_streams.append(result)
                else:
                    log('Skipping stream {}, media type {} not recognized'\
                        .format(stream['index'], stream['codec_type']), 2)

        except Exception as e:
            # This means some stream could not be processed, clean up and stop
            log('Error: {}'.format(e), 2)
            self.error = e

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

        # Construct lists with parameters and build command
        self._build_merge_params(streams, inputs, maps, meta)
        cmd = self._build_merge_command(inputs, maps, meta,
                                        self.output or self.tmp_file)
        if cmd:
            # We have a command -> we have something to merge
            try:
                execute_cmd(cmd)

            except Exception as e:
                # Oops, merge failed, log an set error
                log('Error: {}'.format(e), 2)
                self.error = e
                inputs.append(cmd[-1])

        # Remove main input from list of inputs, because we either keep it
        # or we replace it, in which case we'll "mv <tmp> <input>" anyway
        # Note: if we transcode it might not be in inputs list
        if self.input in inputs:
            inputs.remove(self.input)

        # Finally, return all inputs used in merge
        # (empty if there was no merge)
        return inputs

    def replace_original(self):
        """
        Replace the original input with the temporary file.

        :return:
        """
        cmd = ['mv', self.tmp_file, self.input]
        execute_cmd(cmd)
        self.output = self.input
