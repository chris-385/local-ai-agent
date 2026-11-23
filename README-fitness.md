# FitCoach AI — local fitness assistant

Start the app in the existing project:

```sh
.venv/bin/python -m pip install -r requirements-fitness.txt
ollama serve
ollama pull llama3.2:3b
ollama pull llama3.2-vision:11b
.venv/bin/streamlit run fitness_app.py
```

Start Ollama in a separate terminal if it is not already running as a service. Vision models require sufficient memory. You can change model names in the sidebar. Model errors are shown to the user; the app never fabricates analysis values.

The app has four sections:

- **Home:** Today at a glance (weight, distance to target, calories, workouts this week), quick actions, weight progress, and the status of your plans.
- **Training:** Log a workout with its exercises in one form, see weekly training time and exercise progress, and view or create your training plan.
- **Nutrition:** Today's calories and macros against optional targets, logging meals manually or from a photo (with editable AI estimates), and your meal plan.
- **AI Coach:** A streaming chat with one-click suggestions. Concrete plan or exercise suggestions can be added to your active plans; previous versions remain available.

**Profiles:** Use the profile selector in the sidebar to switch between people, **New** to create a profile, and **Edit** to change or delete the active one. Every profile has its own weight history, workouts, meals, targets, plans, and chats. Data from before profiles existed belongs to the first profile.

Saved plans appear in their respective sections and as links on the Dashboard. Adding an AI Coach suggestion does not automatically change profile values or nutrition targets. The latest logged weight is included in AI requests.

Profiles, meals, weight entries, and training data from the original German version remain compatible. New entries use English labels and values. Entries can be exported or deleted in their respective sections.

Run tests without real AI calls:

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_fitness*.py' -v
```

Data is stored in `data/fitness.sqlite3`; images are not stored permanently. Ollama receives the profile or image through localhost, so no cloud API is required. All app sessions share the same local database. Profiles separate data for convenience, but there is no authentication: anyone with access to the app can open every profile. Set `FITNESS_DB` to use a different database path in tests.

The existing `app.py` remains the original document assistant. The fitness app does not provide medically validated plans or guaranteed photo accuracy. Review generated plans before use, and correct photo-based portions and ingredients before saving.
