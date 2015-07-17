__author__ = 'kako'

from unittest import TestCase, main
from unittest.mock import patch, MagicMock

from ffconv import profiles, process


class VideoProcessorTest(TestCase):

    def test_init(self):
        input, profile = 'some-film.mkv', profiles.ROKU
        stream = {'index': 7, 'codec_type': 'video', 'codec_name': 'h264'}

        # Init, make sure all attrs are set properly
        processor = process.VideoProcessor(input, stream, profile)
        self.assertEqual(processor.input, 'some-film.mkv')
        self.assertEqual(processor.index, 7)
        self.assertEqual(processor.codec, 'h264')
        self.assertEqual(processor.language, None)
        self.assertEqual(processor.target_codec, 'h264')
        self.assertEqual(processor.output, 'video-7.h264')

    def test_process(self):
        input, profile = 'some-film.mkv', profiles.ROKU

        # Attempt simple process, nothing to do
        stream = {'index': 7, 'codec_type': 'video', 'codec_name': 'h264'}
        processor = process.VideoProcessor(input, stream, profile)
        res = processor.process()
        self.assertEqual(res, {'input' : 'some-film.mkv', 'index': 7})

        # Attempt to process xvid, not implemented error
        stream = {'index': 7, 'codec_type': 'video', 'codec_name': 'xvid'}
        processor = process.VideoProcessor(input, stream, profile)
        self.assertRaises(NotImplementedError, processor.process)


class AudioProcessorTest(TestCase):

    def test_init(self):
        input, profile = 'some-film.mkv', profiles.ROKU
        stream = {'index': 3, 'codec_type': 'audio', 'codec_name': 'mp3', 'channels': 2, 'tags': {'LANGUAGE': 'por'}}

        # Init, make sure all attrs are set properly
        processor = process.AudioProcessor(input, stream, profile)
        self.assertEqual(processor.input, 'some-film.mkv')
        self.assertEqual(processor.index, 3)
        self.assertEqual(processor.codec, 'mp3')
        self.assertEqual(processor.language, 'por')
        self.assertEqual(processor.target_codec, 'aac')
        self.assertEqual(processor.output, 'audio-3.aac')
        self.assertEqual(processor.channels, 2)
        self.assertEqual(processor.target_channels, 2)

    @patch('process.execute_cmd', MagicMock())
    def test_convert(self):
        input, profile = 'some-film.mkv', profiles.ROKU

        # Convert flac with 6 channels
        stream = {'index': 1, 'codec_type': 'audio', 'codec_name': 'flac', 'channels': 6, 'tags': {'LANGUAGE': 'por'}}
        processor = process.AudioProcessor(input, stream, profile)
        processor.convert()
        cmd = 'ffmpeg -i some-film.mkv -map 0:1 -strict experimental -c:a aac -ac:0 2 audio-1.aac'
        process.execute_cmd.assert_called_once_with(cmd)

    @patch('process.AudioProcessor.convert', MagicMock())
    @patch('process.AudioProcessor.clean_up', MagicMock())
    def test_process(self):
        input, profile = 'some-film.mkv', profiles.ROKU

        # Attempt simple process, nothing to do
        stream = {'index': 1, 'codec_type': 'audio', 'codec_name': 'aac', 'channels': 2, 'tags': {'LANGUAGE': 'por'}}
        processor = process.AudioProcessor(input, stream, profile)
        res = processor.process()
        self.assertEqual(res, {'input': 'some-film.mkv', 'index': 1, 'language': 'por'})
        self.assertFalse(processor.convert.called)
        self.assertFalse(processor.clean_up.called)

        # Attempt mp3 process, should convert
        stream = {'index': 1, 'codec_type': 'audio', 'codec_name': 'mp3', 'channels': 2, 'tags': {'LANGUAGE': 'por'}}
        processor = process.AudioProcessor(input, stream, profile)
        res = processor.process()
        self.assertEqual(res, {'input': 'audio-1.aac', 'index': 0, 'language': 'por'})
        self.assertTrue(processor.convert.called)
        self.assertTrue(processor.clean_up.called)


class SubtitleProcessorTest(TestCase):

    def test_init(self):
        input, profile = 'some-film.mkv', profiles.ROKU
        stream = {'index': 2, 'codec_type': 'subtitle', 'codec_name': 'ass', 'tags': {'LANGUAGE': 'por'}}

        # Init, make sure all attrs are set properly
        processor = process.SubtitleProcessor(input, stream, profile)
        self.assertEqual(processor.input, 'some-film.mkv')
        self.assertEqual(processor.index, 2)
        self.assertEqual(processor.codec, 'ass')
        self.assertEqual(processor.language, 'por')
        self.assertEqual(processor.target_codec, 'srt')
        self.assertEqual(processor.output, 'subtitle-2.srt')

    @patch('process.execute_cmd', MagicMock())
    def test_convert(self):
        input, profile = 'some-film.mkv', profiles.ROKU

        # Convert flac with 6 channels
        stream = {'index': 5, 'codec_type': 'subtitle', 'codec_name': 'ass', 'tags': {'LANGUAGE': 'por'}}
        processor = process.SubtitleProcessor(input, stream, profile)
        processor.convert()
        cmd = 'ffmpeg -i some-film.mkv -map 0:5 subtitle-5.srt'
        process.execute_cmd.assert_called_once_with(cmd)

    @patch('process.execute_cmd', MagicMock())
    def test_clean_up(self):
        input, profile = 'some-film.mkv', profiles.ROKU

        # Convert flac with 6 channels
        stream = {'index': 6, 'codec_type': 'subtitle', 'codec_name': 'ass', 'tags': {'LANGUAGE': 'por'}}
        processor = process.SubtitleProcessor(input, stream, profile)
        processor.clean_up()
        cmd = ['sed', '-i', '-e', r"s/<font[^>]*>//g", '-e', r"s/<\/font>//g",
               '-e', r"s/<I>/<i>/g", '-e', r"s/<\/I>/<\/i>/g", 'subtitle-6.srt']
        process.execute_cmd.assert_called_once_with(cmd, split=False)

    @patch('process.SubtitleProcessor.convert', MagicMock())
    @patch('process.SubtitleProcessor.clean_up', MagicMock())
    def test_process(self):
        input, profile = 'some-film.mkv', profiles.ROKU

        # Attempt simple process, nothing to do
        stream = {'index': 4, 'codec_type': 'subtitle', 'codec_name': 'srt', 'tags': {'LANGUAGE': 'por'}}
        processor = process.SubtitleProcessor(input, stream, profile)
        res = processor.process()
        self.assertEqual(res, {'input': 'some-film.mkv', 'index': 4, 'language': 'por'})
        self.assertFalse(processor.convert.called)
        self.assertFalse(processor.clean_up.called)

        # Attempt ass process, should convert
        stream = {'index': 4, 'codec_type': 'subtitle', 'codec_name': 'ass', 'tags': {'LANGUAGE': 'por'}}
        processor = process.SubtitleProcessor(input, stream, profile)
        res = processor.process()
        self.assertEqual(res, {'input': 'subtitle-4.srt', 'index': 0, 'language': 'por'})
        self.assertTrue(processor.convert.called)
        self.assertTrue(processor.clean_up.called)
