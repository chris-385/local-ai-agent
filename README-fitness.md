# Form — local AI fitness assistant

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

- **Overview:** Current profile, personal goal, optional target weight, weight history, and links to active plans.
- **Training:** Active and previous training plans, individual sessions, and exercises with sets, reps, and additional weight. Charts show weight and volume per exercise as well as weekly training time.
- **Nutrition:** Daily calories and macros, optional self-defined targets, a meal log, camera and image upload with editable AI estimates, and an active meal plan.
- **Coach:** A personal streaming chat. Adoption actions appear only for concrete plan suggestions and only for the matching plan type. Regular chat responses do not show actions. After review, concrete exercise suggestions can be added to the active plan or replace a selected exercise. Previous plan versions remain available, duplicate adoptions are prevented, and truncated responses are not treated as complete plans.

Saved plans appear in their respective sections and as links on Overview. Adding a coach suggestion does not automatically change profile values or nutrition targets. The latest logged weight is included in AI requests.

Profiles, meals, weight entries, and training data from the original German version remain compatible. New entries use English labels and values. Entries can be exported or deleted in their respective sections.

Run tests without real AI calls:

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_fitness*.py' -v
```

Data is stored in `data/fitness.sqlite3`; images are not stored permanently. Ollama receives the profile or image through localhost, so no cloud API is required. All app sessions share the same local database. The app is intended for personal use on one computer and has no user separation or authentication. Set `FITNESS_DB` to use a different database path in tests.

The existing `app.py` remains the original document assistant. The fitness app does not provide medically validated plans or guaranteed photo accuracy. Review generated plans before use, and correct photo-based portions and ingredients before saving.
