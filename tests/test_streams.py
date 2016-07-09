__author__ = 'kako'

from unittest import TestCase
from unittest.mock import patch, MagicMock

from ffconv import profiles
from ffconv.stream_processors import VideoProcessor, AudioProcessor, SubtitleProcessor


class VideoProcessorTest(TestCase):

    def test_init(self):
        input, profile = 'some-film.mkv', profiles.ROKU
        stream = {'index': 7, 'codec_type': 'video', 'codec_name': 'h264',
                  'refs': 4, 'height': 720}

        # Init, make sure all attrs are set properly
        processor = VideoProcessor(input, stream, profile)
        self.assertEqual(processor.input, 'some-film.mkv')
        self.assertEqual(processor.index, 7)
        self.assertEqual(processor.codec, 'h264')
        self.assertEqual(processor.language, None)
        self.assertEqual(processor.target_codec, 'h264')
        self.assertEqual(processor.target_container, 'mp4')
        self.assertEqual(processor.output, 'video-7.mp4')

    @patch('ffconv.stream_processors.execute_cmd')
    def test_convert(self, ecmd):
        input, profile = 'some-film.mkv', profiles.ROKU

        # Convert h264 with 16 refs
        stream = {'index': 0, 'codec_type': 'video',
                  'codec_name': 'h264', 'refs': 16, 'level': 51, 'height': 720}
        processor = VideoProcessor(input, stream, profile)
        processor.convert()
        cmd = ['ffmpeg', '-i', 'some-film.mkv', '-map', '0:0', '-c:v', 'h264',
               '-preset', 'slow', '-crf', '22', '-profile:v', 'high',
               '-level', '4.1', 'video-0.mp4']
        self.assertTrue(ecmd.called)
        ecmd.assert_called_once_with(cmd)

    @patch('ffconv.stream_processors.VideoProcessor.convert', MagicMock())
    @patch('ffconv.stream_processors.VideoProcessor.clean_up', MagicMock())
    def test_process(self):
        input, profile = 'some-film.mkv', profiles.ROKU

        # Attempt process for 720:8 refs, nothing to do
        stream = {'index': 7, 'codec_type': 'video', 'codec_name': 'h264',
                  'refs': 8, 'height': 720}
        processor = VideoProcessor(input, stream, profile)
        res = processor.process()
        self.assertEqual(res, {'input': 'some-film.mkv', 'index': 7})
        self.assertFalse(processor.convert.called)
        self.assertFalse(processor.clean_up.called)

        # Attempt process for 1080:8 refs, needs to convert
        stream = {'index': 7, 'codec_type': 'video', 'codec_name': 'h264',
                  'refs': 8, 'height': 1080}
        processor = VideoProcessor(input, stream, profile)
        res = processor.process()
        self.assertEqual(res, {'input': 'video-7.mp4', 'index': 0})
        self.assertTrue(processor.convert.called)
        self.assertTrue(processor.clean_up.called)
        processor.convert.reset_mock()
        processor.clean_up.reset_mock()

        # Attempt to process 704:8, nothing to do
        stream = {'index': 7, 'codec_type': 'video', 'codec_name': 'h264',
                  'refs': 8, 'height': 704}
        processor = VideoProcessor(input, stream, profile)
        res = processor.process()
        self.assertEqual(res, {'input': 'some-film.mkv', 'index': 7})
        self.assertFalse(processor.convert.called)
        self.assertFalse(processor.clean_up.called)

        # Attempt process for 2160:8 refs, needs to convert (default ref is 4)
        stream = {'index': 7, 'codec_type': 'video', 'codec_name': 'h264',
                  'refs': 8, 'height': 2160}
        processor = VideoProcessor(input, stream, profile)
        res = processor.process()
        self.assertEqual(res, {'input': 'video-7.mp4', 'index': 0})
        self.assertTrue(processor.convert.called)
        self.assertTrue(processor.clean_up.called)
        processor.convert.reset_mock()
        processor.clean_up.reset_mock()

        # Attempt to process xvid, turn to h264
        stream = {'index': 7, 'codec_type': 'video', 'codec_name': 'xvid',
                  'refs': 1, 'height': 720}
        processor = VideoProcessor(input, stream, profile)
        res = processor.process()
        self.assertEqual(res, {'input': 'video-7.mp4', 'index': 0})
        self.assertTrue(processor.convert.called)
        self.assertTrue(processor.clean_up.called)


class AudioProcessorTest(TestCase):

    def test_init(self):
        input, profile = 'some-film.mkv', profiles.ROKU
        stream = {'index': 3, 'codec_type': 'audio', 'codec_name': 'ac3',
                  'channels': 2, 'tags': {'language': 'por'}}

        # Init, make sure all attrs are set properly
        processor = AudioProcessor(input, stream, profile)
        self.assertEqual(processor.input, 'some-film.mkv')
        self.assertEqual(processor.index, 3)
        self.assertEqual(processor.codec, 'ac3')
        self.assertEqual(processor.language, 'por')
        self.assertEqual(processor.target_codec, 'mp3')
        self.assertEqual(processor.output, 'audio-3.mp3')
        self.assertEqual(processor.channels, 2)
        self.assertEqual(processor.max_channels, 2)

    @patch('ffconv.stream_processors.execute_cmd')
    def test_convert(self, ecmd):
        input, profile = 'some-film.mkv', profiles.ROKU

        # Convert flac with 6 channels
        stream = {'index': 1, 'codec_type': 'audio', 'codec_name': 'flac',
                  'channels': 6, 'tags': {'language': 'por'}}
        processor = AudioProcessor(input, stream, profile)
        processor.convert()
        cmd = ['ffmpeg', '-i', 'some-film.mkv', '-map', '0:1', '-c:a', 'mp3',
               '-q:a', '2', '-ac:0', '2', 'audio-1.mp3']
        self.assertTrue(ecmd.called)
        ecmd.assert_called_once_with(cmd)

    @patch('ffconv.stream_processors.AudioProcessor.convert', MagicMock())
    @patch('ffconv.stream_processors.AudioProcessor.clean_up', MagicMock())
    def test_process(self):
        input, profile = 'some-film.mkv', profiles.ROKU

        # Attempt simple process, nothing to do
        stream = {'index': 1, 'codec_type': 'audio', 'codec_name': 'aac',
                  'channels': 2, 'tags': {'language': 'por'}}
        processor = AudioProcessor(input, stream, profile)
        res = processor.process()
        self.assertEqual(res, {'input': 'some-film.mkv', 'index': 1,
                               'language': 'por'})
        self.assertFalse(processor.convert.called)
        self.assertFalse(processor.clean_up.called)

        # Attempt process with less channels, should do nothing
        stream = {'index': 1, 'codec_type': 'audio', 'codec_name': 'aac',
                  'channels': 1, 'tags': {'language': 'por'}}

        processor = AudioProcessor(input, stream, profile)
        res = processor.process()
        self.assertEqual(res, {'input': 'some-film.mkv', 'index': 1,
                               'language': 'por'})
        self.assertFalse(processor.convert.called)
        self.assertFalse(processor.clean_up.called)

        # Attempt mp3 process, should convert
        stream = {'index': 1, 'codec_type': 'audio', 'codec_name': 'ac3',
                  'channels': 2, 'tags': {'language': 'por'}}
        processor = AudioProcessor(input, stream, profile)
        res = processor.process()
        self.assertEqual(res, {'input': 'audio-1.mp3', 'index': 0,
                               'language': 'por'})
        self.assertTrue(processor.convert.called)
        self.assertTrue(processor.clean_up.called)


class SubtitleProcessorTest(TestCase):

    def test_init(self):
        input, profile = 'some-film.mkv', profiles.ROKU
        stream = {'index': 2, 'codec_type': 'subtitle', 'codec_name': 'ass',
                  'tags': {'language': 'por'}}

        # Init, make sure all attrs are set properly
        processor = SubtitleProcessor(input, stream, profile)
        self.assertEqual(processor.input, 'some-film.mkv')
        self.assertEqual(processor.index, 2)
        self.assertEqual(processor.codec, 'ass')
        self.assertEqual(processor.language, 'por')
        self.assertEqual(processor.target_codec, 'srt')
        self.assertEqual(processor.output, 'subtitle-2.srt')

    @patch('ffconv.stream_processors.execute_cmd')
    def test_convert(self, ecmd):
        input, profile = 'some-film.mkv', profiles.ROKU

        # Convert flac with 6 channels
        stream = {'index': 5, 'codec_type': 'subtitle', 'codec_name': 'ass',
                  'tags': {'language': 'por'}}
        processor = SubtitleProcessor(input, stream, profile)
        processor.convert()
        cmd = ['ffmpeg', '-sub_charenc', 'utf-8', '-i', 'some-film.mkv',
               '-map', '0:5', 'subtitle-5.srt']
        self.assertTrue(ecmd.called)
        ecmd.assert_called_once_with(cmd)

    @patch('ffconv.stream_processors.execute_cmd')
    def test_clean_up(self, ecmd):
        input, profile = 'some-film.mkv', profiles.ROKU

        # Convert flac with 6 channels
        stream = {'index': 6, 'codec_type': 'subtitle', 'codec_name': 'ass',
                  'tags': {'language': 'por'}}
        processor = SubtitleProcessor(input, stream, profile)
        processor.clean_up()
        cmd = ['sed', '-i', '-e', r"s/<[^>]*>//ig", '-e', r"s/{[^}]*}//ig",
               'subtitle-6.srt']
        self.assertTrue(ecmd.called)
        ecmd.assert_called_once_with(cmd)

    @patch('ffconv.stream_processors.SubtitleProcessor.convert', MagicMock())
    @patch('ffconv.stream_processors.SubtitleProcessor.clean_up', MagicMock())
    def test_process(self):
        input, profile = 'some-film.mkv', profiles.ROKU

        # Attempt simple process, still converts
        stream = {'index': 4, 'codec_type': 'subtitle', 'codec_name': 'srt',
                  'tags': {'language': 'por'}}
        processor = SubtitleProcessor(input, stream, profile)
        res = processor.process()
        self.assertEqual(res, {'input': 'subtitle-4.srt', 'index': 0,
                               'language': 'por'})
        self.assertTrue(processor.convert.called)
        self.assertTrue(processor.clean_up.called)
