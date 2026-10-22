import unittest
from fitness_actions import detect_action, change_exercise

class ActionTests(unittest.TestCase):
    def test_plain_chat_and_mentions_are_not_plans(self):
        self.assertIsNone(detect_action('Hallo','Hallo!'))
        self.assertIsNone(detect_action('Erstelle einen Trainingsplan','Welche Ausstattung hast du?'))
        self.assertIsNone(detect_action('Was ist ein Ernährungsplan?','Ein Ernährungsplan hilft beim Strukturieren deiner Mahlzeiten.'))
    def test_only_matching_plan_type(self):
        self.assertEqual(detect_action('Trainingsplan bitte','# Dein Trainingsplan\nKniebeuge 3 × 10'),'training_plan')
        self.assertEqual(detect_action('Ernährungsplan bitte','Frühstück: Haferflocken 100 g, 400 kcal'),'nutrition_plan')
        self.assertEqual(detect_action('Welche Übungen für die Brust?','Bankdrücken 3 × 8'),'exercise')
        self.assertIsNone(detect_action('Trainingsplan bitte','Kniebeuge 3 × 10\nAntwortlimit erreicht.'))
    def test_exercise_request_mentioning_plan_is_not_full_plan(self):
        self.assertEqual(detect_action('Welche Übung kann ich in meinem Plan für die Brust austauschen?', '- Bankdrücken 3 × 8'), 'exercise')

    def test_edit_preserves_other_days(self):
        plan='## Montag\nKniebeuge 3 × 10\n## Dienstag\nRudern 3 × 8'
        result=change_exercise(plan,'Bankdrücken 3 × 8','Montag')
        self.assertLess(result.index('Bankdrücken'),result.index('## Dienstag'))
        self.assertIn('Rudern 3 × 8',result)
        result=change_exercise(plan,'Ausfallschritte 3 × 10','Montag',replace='Kniebeuge 3 × 10')
        self.assertNotIn('Kniebeuge',result)
        self.assertIn('Rudern',result)
