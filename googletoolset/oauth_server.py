import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "OAuth Callback Server is running. Awaiting redirect from Google."}

@app.get("/callback")
async def handle_google_callback(request: Request, code: str):
    """
    This is the REDIRECT_URI.
    It receives the code from Google and displays it to the user.
    """
    print(f"[OAuth Server] Received authorization code from Google.")
    
    # Simple HTML page to display the code and instructions
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Authentication Successful</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background-color: #f4f7f6; color: #333; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }}
            .container {{ background-color: white; padding: 40px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); text-align: center; max-width: 600px; }}
            h1 {{ color: #28a745; }}
            p {{ font-size: 1.1em; }}
            code {{ background-color: #e9ecef; padding: 10px; border-radius: 4px; font-size: 1em; display: block; margin: 20px 0; word-break: break-all; }}
            button {{ background-color: #007bff; color: white; border: none; padding: 10px 20px; border-radius: 4px; font-size: 1em; cursor: pointer; }}
            #copy-status {{ color: green; font-weight: bold; margin-top: 10px; visibility: hidden; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Authentication Successful</h1>
            <p><strong>Step 1:</strong> Copy the authorization code below.</p>
            <code id="auth-code">{code}</code>
            <button onclick="copyCode()">Copy Code</button>
            <p id="copy-status">Copied to clipboard!</p>
            <p><strong>Step 2:</strong> Paste this code into the 'authorization_code' field in the ADK Web UI and submit.</p>
        </div>
        <script>
            function copyCode() {{
                const codeElement = document.getElementById('auth-code');
                navigator.clipboard.writeText(codeElement.innerText).then(() => {{
                    document.getElementById('copy-status').style.visibility = 'visible';
                }}, (err) => {{
                    alert('Failed to copy code: ', err);
                }});
            }}
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

if __name__ == "__main__":
    print("--- Starting FastAPI OAuth Callback Server on http://localhost:8000 ---")
    uvicorn.run(app, host="0.0.0.0", port=9000)