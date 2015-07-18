__author__ = 'kako'

import subprocess

from unittest import TestCase
from unittest.mock import patch, MagicMock

from ffconv import profiles
from ffconv.process import FileProcessor, VideoProcessor, AudioProcessor, SubtitleProcessor, execute_cmd


class ExecuteCommandTest(TestCase):

    @patch('subprocess.Popen.__enter__')
    def test_errors(self, ctx_mgr):
        ctx_mgr.return_value = MagicMock(stdout=MagicMock(readline=MagicMock(side_effect=[b''])),
                                         poll=MagicMock(return_value=0))

        # Return value 0, no error, read output
        ctx_mgr.return_value = MagicMock(stdout=MagicMock(readline=MagicMock(side_effect=[b'lala', b''])),
                                         poll=MagicMock(return_value=0))
        output = execute_cmd(['ls', '-al'])
        self.assertEqual(output, 'lala')

        # Return value 1, raise CalledProcessError
        ctx_mgr.return_value = MagicMock(stdout=MagicMock(readline=MagicMock(side_effect=[b'lala', b''])),
                                         poll=MagicMock(return_value=1))
        self.assertRaises(subprocess.CalledProcessError, execute_cmd, ['ls', '-al'])

        # Return value 0 with errors, raise ValueError
        ctx_mgr.return_value = MagicMock(stdout=MagicMock(readline=MagicMock(side_effect=[b'lala', b'Error', b''])),
                                         poll=MagicMock(return_value=1))
        self.assertRaises(ValueError, execute_cmd, ['ls', '-al'])


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
        self.assertEqual(processor.profile, profiles.ROKU)
        self.assertEqual(processor.input, 'lalala.csv')
        self.assertEqual(processor.output, 'lololo.csv')

        # Roku with weird case and without output, still good
        processor = FileProcessor('lalala.csv', None, 'ROKU')
        self.assertEqual(processor.profile, profiles.ROKU)
        processor = FileProcessor('lalala.csv', None, 'RoKu')
        self.assertEqual(processor.profile, profiles.ROKU)

    def test_probe(self):
        processor = FileProcessor('input.mkv', 'output.mkv', 'roku')

        # Check correct command construction
        with patch('ffconv.process.execute_cmd') as execute_cmd:
            execute_cmd.return_value = '{"streams": []}'

            self.assertFalse(execute_cmd.called)
            processor.probe()
            cmd = ['ffprobe', '-v', 'quiet', '-show_streams', '-of', 'json', 'input.mkv']
            execute_cmd.assert_called_once_with(cmd)

        # Check correct result parsing
        with patch('subprocess.Popen.__enter__') as ctx_mgr:
            # Mock the process's stdout.readline and poll methods
            res = [b'{"streams": [{"codec_type": "video", "codec_name": "h264", "index": 0}]}', b'']
            ctx_mgr.return_value = MagicMock(stdout=MagicMock(readline=MagicMock(side_effect=res)),
                                             poll=MagicMock(return_value=0))

            # Run probe, make sure it returns the correct result
            res = processor.probe()
            self.assertEqual(res, [{"codec_type": "video", "codec_name": "h264", "index": 0}])

    @patch('ffconv.process.VideoProcessor.process',
           MagicMock(return_value={'input': 'input.mkv', 'index': 0}))
    @patch('ffconv.process.AudioProcessor.process',
           MagicMock(side_effect=[{'input': 'input.mkv', 'index': 1, 'language': 'jap'},
                                  {'input': 'input.mkv', 'index': 2, 'language': 'eng'}]))
    @patch('ffconv.process.SubtitleProcessor.process',
           MagicMock(side_effect=[{'input': 'input.mkv', 'index': 3, 'language': 'spa'},
                                  {'input': 'input.mkv', 'index': 4, 'language': 'por'}]))
    def test_process_streams(self):
        processor = FileProcessor('input.mkv', 'output.mkv', 'roku')

        # Process empty streams list
        res = processor.process_streams([])
        self.assertEqual(res, [])

        # Process weird streams, ignore
        streams = [{'codec_type': 'pr0n', 'codec_name': 'h264', 'index': 0}]
        res = processor.process_streams(streams)
        self.assertEqual(res, [])

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

    @patch('ffconv.process.execute_cmd')
    def test_merge(self, execute_cmd):
        processor = FileProcessor('input.mkv', 'output.mkv', 'roku')

        # Merge streams without conversion, should return empty list
        streams = [{'input': 'input.mkv', 'index': 0},
                   {'input': 'input.mkv', 'index': 1},
                   {'input': 'input.mkv', 'index': 2},
                   {'input': 'input.mkv', 'index': 3},
                   {'input': 'input.mkv', 'index': 4}]
        inputs = processor.merge(streams)
        self.assertEqual(inputs, [])
        self.assertFalse(execute_cmd.called)

        # Merge streams with 3 conversions, should return those three
        streams = [{'input': 'input.mkv', 'index': 0},
                   {'input': 'audio-1.aac', 'index': 0, 'language': 'jap'},
                   {'input': 'input.mkv', 'index': 2, 'language': 'eng'},
                   {'input': 'subtitle-3.srt', 'index': 0, 'language': 'eng'},
                   {'input': 'subtitle-4.srt', 'index': 0, 'language': 'spa'}]
        res = processor.merge(streams)
        self.assertEqual(res, ['audio-1.aac', 'subtitle-3.srt', 'subtitle-4.srt'])
        cmd = ['ffmpeg', '-i', 'input.mkv', '-i', 'audio-1.aac', '-i', 'subtitle-3.srt',
               '-i', 'subtitle-4.srt', '-map', '0:0', '-map', '1:0', '-map', '0:2',
               '-map', '2:0', '-map', '3:0', '-metadata:s:1', 'language=jap',
               '-metadata:s:2', 'language=eng', '-metadata:s:3', 'language=eng',
               '-metadata:s:4', 'language=spa', '-c', 'copy', 'output.mkv']
        execute_cmd.assert_called_once_with(cmd)
        execute_cmd.reset_mock()

        # Do the same without output, should do the same but use tmp.mkv as output
        processor.output = None
        cmd[-1] = 'tmp.mkv'
        res = processor.merge(streams)
        self.assertEqual(res, ['audio-1.aac', 'subtitle-3.srt', 'subtitle-4.srt'])
        self.assertEqual(processor.error, None)
        execute_cmd.assert_called_once_with(cmd)
        execute_cmd.reset_mock()

        # Simulate failure, should add output to cleanup and update error
        execute_cmd.side_effect = ValueError('Something failed')
        res = processor.merge(streams)
        self.assertEqual(res, ['audio-1.aac', 'subtitle-3.srt', 'subtitle-4.srt', 'tmp.mkv'])
        self.assertEqual(type(processor.error), ValueError)

    @patch('ffconv.process.execute_cmd')
    def test_replace_original(self, execute_cmd):
        processor = FileProcessor('another-input.mkv', None, 'roku')

        # Replace original, make sure output is updated
        processor.replace_original()
        cmd = ['mv', 'tmp.mkv', 'another-input.mkv']
        execute_cmd.assert_called_once_with(cmd)
        self.assertEqual(processor.output, 'another-input.mkv')

    @patch('ffconv.process.execute_cmd')
    def test_clean_up(self, execute_cmd):
        processor = FileProcessor('another-input.mkv', 'output.mkv', 'roku')

        # Clean up, make sure all files are removed
        inputs = ['audio-2.aac', 'audio-4.aac', 'subtitle-5.srt']
        processor.clean_up(inputs)
        cmd = ['rm', 'audio-2.aac', 'audio-4.aac', 'subtitle-5.srt']
        execute_cmd.assert_called_once_with(cmd)

    @patch('ffconv.process.execute_cmd')
    @patch('ffconv.process.FileProcessor.probe', MagicMock(return_value=[
        {'index': 0, 'codec_type': 'video', 'codec_name': 'h264'},
        {'index': 1, 'codec_type': 'audio', 'codec_name': 'aac', 'channels': 6, 'tags': {'LANGUAGE': 'eng'}},
        {'index': 2, 'codec_type': 'subtitle', 'codec_name': 'ass', 'tags': {'LANGUAGE': 'spa'}},
        {'index': 3, 'codec_type': 'subtitle', 'codec_name': 'srt', 'tags': {'LANGUAGE': 'por'}},
    ]))
    def test_process(self, execute_cmd):
        # Run example process with output
        processor = FileProcessor('Se7en.mkv', 'seven.mkv', 'roku')
        res = processor.process()
        self.assertEqual(res, {'streams': 4, 'output': 'seven.mkv'})

        # Run example process without output, output should be same as input
        processor.output = None
        res = processor.process()
        self.assertEqual(res, {'streams': 4, 'output': 'Se7en.mkv'})
