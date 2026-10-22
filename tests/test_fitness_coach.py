import json
import unittest
from unittest.mock import patch
from io import BytesIO
import fitness_core as core


class CoachTests(unittest.TestCase):
    def test_stream_yields_before_response_completes(self):
        lines = [json.dumps(x).encode() + b'\n' for x in [
            {'message': {'content': 'Hallo'}},
            {'message': {'content': ' zusammen'}},
            {'done': True}]]
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def __iter__(self):
                for index, line in enumerate(lines):
                    self.read_count = index + 1
                    yield line
        response = Response()
        with patch.object(core.urllib.request, 'urlopen', return_value=response) as request:
            stream = core.stream_coach('model', None, [], 'Hallo')
            self.assertEqual(next(stream), 'Hallo')
            self.assertEqual(response.read_count, 1)
            self.assertEqual(''.join(stream), ' zusammen')
            payload = json.loads(request.call_args.args[0].data)
            self.assertTrue(payload['stream'])
            self.assertEqual(payload['keep_alive'], '30m')
            self.assertEqual(payload['options']['num_predict'], 512)

    def test_plan_mode_accepts_keyword_and_uses_larger_budget(self):
        response = BytesIO(b'{"message":{"content":"Plan"}}\n{"done":true}\n')
        with patch.object(core.urllib.request, 'urlopen', return_value=response) as request:
            self.assertEqual(''.join(core.stream_coach('model', None, [], 'Trainingsplan', plan=True)), 'Plan')
            payload = json.loads(request.call_args.args[0].data)
            self.assertEqual(payload['options']['num_predict'], 1800)
            self.assertIn('completeness', payload['messages'][0]['content'])

    def test_context_is_bounded_and_preserves_roles(self):
        history = [('user', 'Frage' * 400), ('assistant', 'Antwort' * 400)] * 8
        messages = core.coach_messages({'allergies': 'Nüsse'}, history, 'Was essen?')
        self.assertLessEqual(sum(len(x['content']) for x in messages), 10000)
        self.assertEqual(messages[0]['role'], 'system')
        self.assertIn('Nüsse', messages[0]['content'])
        self.assertEqual(messages[1]['role'], 'user')
        self.assertEqual(messages[-1]['content'], 'Was essen?')

    def test_incomplete_stream_is_not_saved_as_success(self):
        with patch.object(core.urllib.request, 'urlopen', return_value=BytesIO(b'{"message":{"content":"Teil"}}\n')):
            stream = core.stream_coach('model', None, [], 'Hallo')
            self.assertEqual(next(stream), 'Teil')
            with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                next(stream)

    def test_server_error_is_reported(self):
        with patch.object(core.urllib.request, 'urlopen', return_value=BytesIO(b'{"error":"model missing"}\n')):
            with self.assertRaisesRegex(RuntimeError, 'model missing'):
                list(core.stream_coach('model', None, [], 'Hallo'))

    def test_ui_saves_streamed_conversation(self):
        from streamlit.testing.v1 import AppTest
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as directory, \
             patch.object(core, 'DB', Path(directory) / 'test.sqlite3'), \
             patch.object(core, 'models', return_value=['test']), \
             patch.object(core, 'stream_coach', return_value=iter(['Hallo ', 'Sportler!'])):
            app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / 'fitness_app.py'), default_timeout=20).run()
            app.switch_page('fitness_pages/coach.py').run()
            app.chat_input[0].set_value('Wie starte ich?').run()
            self.assertFalse(app.exception)
            self.assertEqual(app.session_state['fitness_chat'], [('user', 'Wie starte ich?'), ('assistant', 'Hallo Sportler!')])

if __name__ == '__main__':
    unittest.main()
