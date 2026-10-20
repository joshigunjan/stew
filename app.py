import os
import gradio as gr
from clara.api.server import app as fastapi_app

# Gradio app wrapper for Hugging Face Spaces (ZeroGPU & Free CPU Compatible)
with gr.Blocks(
    title="Stew: The Helmholtz AI Data Steward",
    theme=gr.themes.Base(),
    css="footer {visibility: hidden} .gradio-container {max-width: 100% !important; padding: 0 !important;}"
) as demo:
    gr.HTML("""
    <div style="width: 100%; height: 96vh; margin: 0; padding: 0;">
        <iframe 
            src="/app" 
            style="width: 100%; height: 100%; border: none; display: block;"
            title="Stew: The Helmholtz Data Steward">
        </iframe>
    </div>
    """)

# Mount FastAPI app onto Gradio
app = gr.mount_gradio_app(fastapi_app, demo, path="/")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    demo.launch(server_name="0.0.0.0", server_port=port, share=False)
