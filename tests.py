__author__ = 'kako'

from unittest import TestCase, main
from unittest.mock import patch, MagicMock

from process import FileProcessor, StreamProcessor, VideoProcessor, \
    AudioProcessor, SubtitleProcessor, execute_cmd
from profiles import ROKU


class FileProcessorTest(TestCase):

    def test_init(self):
        # Try to init with missing params, error
        self.assertRaises(TypeError, FileProcessor)
        self.assertRaises(TypeError, FileProcessor, 'lalala.csv')
        self.assertRaises(TypeError, FileProcessor, 'lalala.csv', 'lololo.mkv')

        # Use a weird profile, error
        self.assertRaises(ValueError, FileProcessor, 'lalala.csv', 'lololo.mkv', 'ipod')

        # Use roku in different forms, all good
        processor = FileProcessor('lalala.csv', 'lololo.csv', 'roku')
        self.assertEqual(processor.profile, ROKU)
        self.assertEqual(processor.input, 'lalala.csv')
        self.assertEqual(processor.output, 'lololo.csv')

        # Roku with weird case and without output, still good
        processor = FileProcessor('lalala.csv', None, 'ROKU')
        self.assertEqual(processor.profile, ROKU)
        processor = FileProcessor('lalala.csv', None, 'RoKu')
        self.assertEqual(processor.profile, ROKU)

    def test_probe(self):
        processor = FileProcessor('input.mkv', 'output.mkv', 'roku')

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
        processor = FileProcessor('input.mkv', 'output.mkv', 'roku')

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
        self.assertEqual(VideoProcessor.process.call_count, 1)
        self.assertEqual(AudioProcessor.process.call_count, 0)
        self.assertEqual(SubtitleProcessor.process.call_count, 0)
        VideoProcessor.process.reset_mock()

        # Process 1 video, 2 audio, 2 subs
        streams = [{'codec_type': 'video', 'codec_name': 'h264', 'index': 0},
                   {'codec_type': 'audio', 'codec_name': 'aac', 'index': 0, 'channels': 2},
                   {'codec_type': 'audio', 'codec_name': 'aac', 'index': 0, 'channels': 6},
                   {'codec_type': 'subtitle', 'codec_name': 'srt', 'index': 0},
                   {'codec_type': 'subtitle', 'codec_name': 'srt', 'index': 0}]
        res = processor.process_streams(streams)
        self.assertEqual(len(res), 5)
        self.assertEqual(VideoProcessor.process.call_count, 1)
        self.assertEqual(AudioProcessor.process.call_count, 2)
        self.assertEqual(SubtitleProcessor.process.call_count, 2)

    def test_merge(self):
        processor = FileProcessor('input.mkv', 'output.mkv', 'roku')
        pass

    def test_replace_output(self):
        pass

    def test_clean_up(self):
        pass

    def test_process(self):
        pass


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

