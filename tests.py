__author__ = 'kako'

from unittest import TestCase, main
from unittest.mock import patch, MagicMock

import process
import profiles


class FileProcessorTest(TestCase):

    def test_init(self):
        # Try to init with missing params, error
        self.assertRaises(TypeError, process.FileProcessor)
        self.assertRaises(TypeError, process.FileProcessor, 'lalala.csv')
        self.assertRaises(TypeError, process.FileProcessor, 'lalala.csv', 'lololo.mkv')

        # Use a weird profile, error
        self.assertRaises(ValueError, process.FileProcessor, 'lalala.csv', 'lololo.mkv', 'ipod')

        # Use roku in different forms, all good
        processor = process.FileProcessor('lalala.csv', 'lololo.csv', 'roku')
        self.assertEqual(processor.profile, profiles.ROKU)
        self.assertEqual(processor.input, 'lalala.csv')
        self.assertEqual(processor.output, 'lololo.csv')

        # Roku with weird case and without output, still good
        processor = process.FileProcessor('lalala.csv', None, 'ROKU')
        self.assertEqual(processor.profile, profiles.ROKU)
        processor = process.FileProcessor('lalala.csv', None, 'RoKu')
        self.assertEqual(processor.profile, profiles.ROKU)

    def test_probe(self):
        processor = process.FileProcessor('input.mkv', 'output.mkv', 'roku')

        # Check correct command construction
        with patch('process.execute_cmd', MagicMock(return_value='{"streams": []}')) as execute_cmd:
            self.assertFalse(execute_cmd.called)
            processor.probe()
            execute_cmd.assert_called_once_with('ffprobe -v quiet -of json -show_streams input.mkv')

        # Check correct result parsing
        cmd_res = b'{"streams": [{"codec_type": "video", "codec_name": "h264", "index": 0}]}'
        with patch('subprocess.check_output', MagicMock(return_value=cmd_res)):
            res = processor.probe()
            self.assertEqual(res, [{"codec_type": "video", "codec_name": "h264", "index": 0}])

    @patch('process.VideoProcessor.process',
           MagicMock(return_value={'input': 'input.mkv', 'index': 0}))
    @patch('process.AudioProcessor.process',
           MagicMock(side_effect=[{'input': 'input.mkv', 'index': 1, 'language': 'jap'},
                                  {'input': 'input.mkv', 'index': 2, 'language': 'eng'}]))
    @patch('process.SubtitleProcessor.process',
           MagicMock(side_effect=[{'input': 'input.mkv', 'index': 3, 'language': 'spa'},
                                  {'input': 'input.mkv', 'index': 4, 'language': 'por'}]))
    def test_process_streams(self):
        processor = process.FileProcessor('input.mkv', 'output.mkv', 'roku')

        # Process empty streams list
        res = processor.process_streams([])
        self.assertEqual(res, [])

        # Process weird streams, explode
        streams = [{'codec_type': 'pr0n', 'codec_name': 'h264', 'index': 0}]
        self.assertRaises(IndexError, processor.process_streams, streams)

        # Process 1 video only
        streams = [{'codec_type': 'video', 'codec_name': 'h264', 'index': 0}]
        res = processor.process_streams(streams)
        self.assertEqual(len(res), 1)
        self.assertEqual(process.VideoProcessor.process.call_count, 1)
        self.assertEqual(process.AudioProcessor.process.call_count, 0)
        self.assertEqual(process.SubtitleProcessor.process.call_count, 0)
        process.VideoProcessor.process.reset_mock()

        # Process 1 video, 2 audio, 2 subs
        streams = [{'codec_type': 'video', 'codec_name': 'h264', 'index': 0},
                   {'codec_type': 'audio', 'codec_name': 'aac', 'index': 0, 'channels': 2},
                   {'codec_type': 'audio', 'codec_name': 'aac', 'index': 0, 'channels': 6},
                   {'codec_type': 'subtitle', 'codec_name': 'srt', 'index': 0},
                   {'codec_type': 'subtitle', 'codec_name': 'srt', 'index': 0}]
        res = processor.process_streams(streams)
        self.assertEqual(len(res), 5)
        self.assertEqual(process.VideoProcessor.process.call_count, 1)
        self.assertEqual(process.AudioProcessor.process.call_count, 2)
        self.assertEqual(process.SubtitleProcessor.process.call_count, 2)

    @patch('process.execute_cmd', MagicMock())
    def test_merge(self):
        processor = process.FileProcessor('input.mkv', 'output.mkv', 'roku')

        # Merge streams without conversion, should return empty list
        streams = [{'input': 'input.mkv', 'index': 0},
                   {'input': 'input.mkv', 'index': 1},
                   {'input': 'input.mkv', 'index': 2},
                   {'input': 'input.mkv', 'index': 3},
                   {'input': 'input.mkv', 'index': 4}]
        inputs = processor.merge(streams)
        self.assertEqual(inputs, [])
        self.assertFalse(process.execute_cmd.called)

        # Merge streams with 3 conversions, should return those three
        streams = [{'input': 'input.mkv', 'index': 0},
                   {'input': 'audio-1.aac', 'index': 0, 'language': 'jap'},
                   {'input': 'input.mkv', 'index': 2, 'language': 'eng'},
                   {'input': 'subtitle-3.srt', 'index': 0, 'language': 'eng'},
                   {'input': 'subtitle-4.srt', 'index': 0, 'language': 'spa'}]
        res = processor.merge(streams)
        self.assertEqual(res, ['audio-1.aac', 'subtitle-3.srt', 'subtitle-4.srt'])
        cmd = ' '.join([
            'ffmpeg -i input.mkv -i audio-1.aac -i subtitle-3.srt -i subtitle-4.srt -map 0:0 -map 1:0',
            '-map 0:2 -map 2:0 -map 3:0 -c copy -metadata:s:1 language=jap -metadata:s:2 language=eng',
            '-metadata:s:3 language=eng -metadata:s:4 language=spa output.mkv'
        ])
        process.execute_cmd.assert_called_once_with(cmd)
        process.execute_cmd.reset_mock()

        # Do the same without output, should do the same but use tmp.mkv as output
        processor.output = None
        cmd = cmd.replace('output.mkv', 'tmp.mkv')
        res = processor.merge(streams)
        self.assertEqual(res, ['audio-1.aac', 'subtitle-3.srt', 'subtitle-4.srt'])
        process.execute_cmd.assert_called_once_with(cmd)

    @patch('process.execute_cmd', MagicMock())
    def test_replace_original(self):
        processor = process.FileProcessor('another-input.mkv', None, 'roku')

        # Replace original, make sure output is updated
        processor.replace_original()
        process.execute_cmd.assert_called_once_with('mv tmp.mkv another-input.mkv')
        self.assertEqual(processor.output, 'another-input.mkv')

    @patch('process.execute_cmd', MagicMock())
    def test_clean_up(self):
        processor = process.FileProcessor('another-input.mkv', 'output.mkv', 'roku')

        # Clean up, make sure all files are removed
        inputs = ['audio-2.aac', 'audio-4.aac', 'subtitle-5.srt']
        processor.clean_up(inputs)
        process.execute_cmd.assert_called_once_with('rm audio-2.aac audio-4.aac subtitle-5.srt')

    @patch('process.execute_cmd', MagicMock())
    @patch('process.FileProcessor.probe', MagicMock(return_value=[
        {'index': 0, 'codec_type': 'video', 'codec_name': 'h264'},
        {'index': 1, 'codec_type': 'audio', 'codec_name': 'aac', 'channels': 6, 'tags': {'LANGUAGE': 'eng'}},
        {'index': 2, 'codec_type': 'subtitle', 'codec_name': 'ass', 'tags': {'LANGUAGE': 'spa'}},
        {'index': 3, 'codec_type': 'subtitle', 'codec_name': 'srt', 'tags': {'LANGUAGE': 'por'}},
    ]))
    def test_process(self):
        # Run example process with output
        processor = process.FileProcessor('Se7en.mkv', 'seven.mkv', 'roku')
        res = processor.process()
        self.assertEqual(res, {'streams': 4, 'output': 'seven.mkv'})

        # Run example process without output, output should be same as input
        processor.output = None
        res = processor.process()
        self.assertEqual(res, {'streams': 4, 'output': 'Se7en.mkv'})


class StreamProcessorTest(TestCase):
    pass


class VideoProcessorTest(TestCase):
    pass


class AudioProcessorTest(TestCase):
    pass


class SubtitleProcessorTest(TestCase):
    pass


if __name__ == '__main__':
    main()

