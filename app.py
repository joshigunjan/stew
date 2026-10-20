import os
os.environ["GRADIO_SSR_MODE"] = "False"

import uvicorn
import gradio as gr
from clara.api.server import app as fastapi_app

# Gradio definition for Hugging Face Spaces compatibility
with gr.Blocks(title="Stew: The Helmholtz AI Data Steward") as demo:
    gr.HTML("""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; text-align: center; padding: 2rem;">
        <h2 style="color: #26211e; font-size: 1.8rem; margin-bottom: 0.5rem;">🍲 Stew: The Helmholtz AI Data Steward</h2>
        <p style="color: #635b54; font-size: 1rem; margin-bottom: 1.5rem;">
            Sovereign FAIR² & MLCommons Croissant Research Data Management
        </p>
        <p>
            <a href="/" target="_self" style="display: inline-block; background: #c2593f; color: white; padding: 0.75rem 1.5rem; border-radius: 8px; text-decoration: none; font-weight: 600;">
                Open Full Interactive Web Cockpit &rarr;
            </a>
        </p>
    </div>
    """)

# Mount Gradio onto the existing FastAPI application
# Root / serves our complete Stew web portal; /gradio serves the Gradio interface
app = gr.mount_gradio_app(fastapi_app, demo, path="/gradio")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
