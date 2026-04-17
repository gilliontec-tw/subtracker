import os
from dotenv import load_dotenv
import uvicorn

load_dotenv()

if __name__ == "__main__":
    host = os.getenv("APP_HOST", "0.0.0.0")
    port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run("src.interfaces.web.app:app", host=host, port=port, reload=False)
