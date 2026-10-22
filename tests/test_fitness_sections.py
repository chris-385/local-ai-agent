"""End-to-end UI behavior with an isolated database and deterministic AI."""
from datetime import date
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
import fitness_core as core

APP=str(Path(__file__).resolve().parents[1]/'fitness_app.py')

class SectionTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        for mock in [patch.object(core,'DB',Path(self.directory.name)/'data.sqlite3'),patch.object(core,'models',return_value=['test'])]:
            mock.start()
            self.addCleanup(mock.stop)
        self.app=AppTest.from_file(APP,default_timeout=20).run()
        self.assertFalse(self.app.exception)

    def page(self,path):
        self.app.switch_page('fitness_pages/'+path+'.py').run()
        self.assertFalse(self.app.exception)

    def button(self,label):
        return next(b for b in self.app.button if b.label==label)

    def save_profile(self):
        self.button('Save profile').click().run()
        self.assertFalse(self.app.exception)

    def test_profile_weight_and_four_pages(self):
        self.save_profile()
        self.assertEqual(core.records('profile')[0]['goal'],'Improve fitness')
        self.button('Save weight').click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(core.records('weight')[0]['kg'],75)
        for page in ['training','nutrition','coach','overview']:
            self.page(page)

    def test_training_session_and_exercise_progress(self):
        self.page('training')
        self.app.segmented_control(key='training_view').set_value('Sessions').run()
        next(x for x in self.app.text_input if x.label=='Session name').set_value('Full body A')
        self.button('Save session').click().run()
        self.assertFalse(self.app.exception)
        workout=core.records('workout')[0]
        self.app.segmented_control(key='training_view').set_value('Exercises & progress').run()
        next(x for x in self.app.text_input if x.label=='Exercise').set_value('Squat')
        next(x for x in self.app.selectbox if x.label=='Add to a session').set_value(workout)
        self.button('Save exercise').click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(core.records('exercise')[0]['workout_id'],workout['id'])
        self.assertTrue(self.app.dataframe)

    def test_meal_and_daily_totals(self):
        self.page('nutrition')
        self.app.segmented_control(key='nutrition_view').set_value('Log a meal').run()
        next(x for x in self.app.text_input if x.label=='Meal').set_value('Lunch')
        next(x for x in self.app.number_input if x.label=='Calories (kcal)').set_value(650.)
        self.button('Save meal').click().run()
        self.assertFalse(self.app.exception)
        self.app.segmented_control(key='nutrition_view').set_value('Daily overview').run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.metric[0].value,'650 kcal')
        self.button('Save daily targets').click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(core.records('nutrition_targets')),1)

    def test_coach_plan_adoption_and_persistence(self):
        self.save_profile()
        self.page('coach')
        with patch.object(core,'stream_coach',return_value=iter(['# My training plan\n','Squat 3 × 10'])):
            self.app.chat_input[0].set_value('Create a training plan').run()
        self.assertFalse(self.app.exception)
        self.button('Use as training plan').click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(core.records('training_plan')),1)
        self.assertEqual(core.records('training_plan')[0]['source'],'coach')
        self.assertTrue(any(b.label=='Already added' and b.disabled for b in self.app.button))
        self.assertFalse(any(b.label=='Use as meal plan' for b in self.app.button))
        self.page('training')
        self.assertTrue(any('Squat 3 × 10' in m.value for m in self.app.markdown))
        self.page('coach')
        with patch.object(core,'stream_coach',return_value=iter(['# Your meal plan\nBreakfast: oats 100 g, 400 kcal'])):
            self.app.chat_input[0].set_value('Create a meal plan').run()
        self.button('Use as meal plan').click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(len(core.records('nutrition_plan')),1)
        app2=AppTest.from_file(APP,default_timeout=20).run()
        self.assertFalse(app2.exception)
        self.assertTrue(any('Active since' in c.value for c in app2.caption))

    def test_normal_chat_has_no_adoption_actions(self):
        self.page('coach')
        with patch.object(core,'stream_coach',return_value=iter(['Hello! How can I help?'])):
            self.app.chat_input[0].set_value('Hey').run()
        self.assertFalse(self.app.exception)
        self.assertFalse(any('Use as' in b.label for b in self.app.button))

    def test_stale_saved_action_cannot_force_adoption_buttons(self):
        self.app.session_state['fitness_chat']=[('user','Hey'),('assistant','Hallo! Wie geht es dir?')]
        self.app.session_state['coach_actions']={1:'training_plan'}
        self.page('coach')
        self.assertFalse(any('Use as' in b.label for b in self.app.button))
        self.assertFalse(any('Add plan' in x.label for x in self.app.expander))

    def test_exercise_can_be_added_and_replaced(self):
        self.save_profile()
        core.save('training_plan',date.today(),{'content':'# Training plan\n## Monday\nSquat 3 × 10','profile':{},'source':'generator'})
        self.page('coach')
        with patch.object(core,'stream_coach',return_value=iter(['- Bench press 3 × 8'])):
            self.app.chat_input[0].set_value('Which exercise should I use for my chest?').run()
        self.assertFalse(self.app.exception)
        self.assertFalse(any(b.label=='Use as training plan' for b in self.app.button))
        next(x for x in self.app.text_input if x.label=='Training day / session').set_value('Monday')
        self.button('Add exercise').click().run()
        self.assertFalse(self.app.exception)
        self.assertIn('Bench press',core.records('training_plan')[-1]['content'])
        self.assertIn('Squat',core.records('training_plan')[-1]['content'])
        self.app.radio[0].set_value('Replace').run()
        next(x for x in self.app.text_input if x.label=='Training day / session').set_value('Monday')
        self.button('Replace exercise').click().run()
        self.assertFalse(self.app.exception)
        self.assertNotIn('Squat',core.records('training_plan')[-1]['content'])
        self.assertEqual(len(core.records('training_plan')),3)

    def test_existing_records_are_available(self):
        core.save('workout',date.today(),{'name':'Alte Einheit','minutes':30,'notes':'Bestehend'})
        core.save('meal',date.today(),{'name':'Alte Mahlzeit','kcal':500,'protein':30,'carbs':50,'fat':20})
        self.page('training')
        self.app.segmented_control(key='training_view').set_value('Sessions').run()
        self.assertEqual(self.app.metric[0].value,'1')
        self.page('nutrition')
        self.assertEqual(self.app.metric[0].value,'500 kcal')

if __name__=='__main__': unittest.main()
