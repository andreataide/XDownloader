import unittest
from unittest.mock import patch
from batch import parse_links
from app import Worker

class BatchTests(unittest.TestCase):
    def test_deduplicates_normalized_links(self):
        self.assertEqual(parse_links('\nhttps://x.com/a/status/123?s=20\nhttps://twitter.com/b/status/123\n'), ['https://x.com/i/status/123'])
    def test_invalid_lines_identified(self):
        with self.assertRaisesRegex(ValueError, 'Linha 2'):
            parse_links('https://x.com/a/status/123\nhttps://example.org')
        with self.assertRaises(ValueError):
            parse_links(' \n')
    def test_continues_after_failure_and_reuses_session(self):
        session = object()
        worker = Worker(['first', 'bad', 'last'], '/tmp', session)
        results = []
        progress = []
        worker.result.connect(lambda ok, message: results.append((ok, message)))
        worker.queue_progress.connect(lambda done, total: progress.append((done, total)))
        def fake(url, *args, **kwargs):
            self.assertIs(kwargs['session'], session)
            if url == 'bad':
                raise RuntimeError('Indisponível')
        with patch('app.download', side_effect=fake) as fetch:
            worker.run()
            self.assertEqual(fetch.call_count, 3)
        self.assertEqual(progress[-1], (3, 3))
        self.assertFalse(results[0][0])
        self.assertIn('2 publicações baixadas, 1 falhas', results[0][1])
    def test_cancel_stops_queue(self):
        worker = Worker(['first', 'second'], '/tmp')
        results = []
        worker.result.connect(lambda ok, message: results.append(message))
        def cancel(*args, **kwargs):
            worker.stop.set()
            raise RuntimeError('Cancelado')
        with patch('app.download', side_effect=cancel) as fetch:
            worker.run()
            self.assertEqual(fetch.call_count, 1)
        self.assertIn('Lote cancelado', results[0])
        self.assertIn('2 não processadas', results[0])

if __name__ == '__main__':
    unittest.main()
