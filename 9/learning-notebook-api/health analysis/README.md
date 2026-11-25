# Blood Work & Diet

Streamlit version of `1.ipynb`. It uses the same Groq model (`openai/gpt-oss-20b`)
to extract blood-test values, compare them with the report's reference ranges,
and generate a brief health summary and Indian diet plan.

From the `9/learning-notebook-api` directory, run:

```powershell
uv run --no-project --with-requirements "health analysis/requirements.txt" streamlit run "health analysis/app.py"
```

This installs the app's dependencies in an isolated uv environment without
requiring the other tutorial projects.

Set the `GROQ_API_KEY` environment variable before launching the app, or define it
in `health analysis/.env`. An existing environment variable takes precedence
over `.env`. The app has no API-key input field. A Google API key is not required.

Paste a report or upload a UTF-8 `.txt` file. If you have a local `blood_work.txt`
beside the app, select **Use notebook report** to read it. Notebook files and
patient reports are not included with the app. Select **Analyze report** to run both steps.
Results remain available during Streamlit reruns and can be downloaded as
Markdown. **Clear results** removes the generated results from the session.

Reports are sent to Groq when analysis is requested. The app does not write
reports or results to disk or cache them across sessions. Its output is
AI-generated educational information and should be reviewed with a clinician.

Run the mocked tests from the same directory:

```powershell
uv run --no-project --with-requirements "health analysis/requirements.txt" python -m unittest discover -s "health analysis" -p test_app.py -v
```
