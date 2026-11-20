# Punchcard
A daily game where given a year, you must guess whether the item in front of you costs more or less than one hour, day, week, month, and year's labor. Point multipliers if you have high conviction!

## Run with Streamlit

Run `streamlit run streamlit_app.py` to serve the generated game in Streamlit.
The app loads the checked-in `index.html` directly, so it avoids running the
build-time Wikimedia image lookup on every app start. After changing the game
data or HTML template, run `python3 build_punchcard.py` and include the updated
`index.html` in the deployment.
