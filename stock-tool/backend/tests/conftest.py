import os
import tempfile

# Use a temp file so each new aiosqlite connection sees the same DB.
# (`:memory:` would not persist across separate connections.)
TEST_DB = tempfile.NamedTemporaryFile(delete=False, suffix=".db").name

os.environ["APP_PASSWORD"] = "test"
os.environ["SECRET_KEY"] = "test-secret-64-chars-padding-padding-padding-padding-pad"
os.environ["DATABASE_URL"] = TEST_DB
