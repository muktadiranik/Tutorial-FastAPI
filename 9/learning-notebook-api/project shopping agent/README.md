# Shopping assistant

Streamlit chat interface for the shopping agent, with product search, customer
ratings, photo matching, conversation history, and order confirmation.

From `9/learning-notebook-api`, run:

```powershell
uv sync
uv run streamlit run "project shopping agent/app.py"
```

Set `GROQ_API_KEY` in your environment, this folder's `.env`, or the parent
project's `.env`. Existing environment variables take precedence. There is no
API-key input in the app. The app uses the models configured in `agent.py`.

If the store database has not been initialized, run:

```powershell
uv run python "project shopping agent/database.py"
```

Ask for products by keyword, price, organic status, or minimum rating. Attach a
JPEG, PNG, or WebP photo using the chat input's paperclip to search by image.
Photos are sent to Groq for analysis and retained in a temporary directory for
the conversation. **New conversation** clears the history and those files.

When ordering, review the products and total, then select **Confirm order** or
**Cancel order**. Ratings never create orders. Confirmed orders are stored in
the local `store.db`; this demo does not submit purchases to an external store.
Orders are also shown in the conversation, including when the model fails after
checkout. A failed conversation requires starting a new one to avoid replaying
an interrupted turn automatically.

Run the tests without calling Groq or changing the store database:

```powershell
uv run python -m unittest discover -s "project shopping agent" -p "test_*.py" -v
```
