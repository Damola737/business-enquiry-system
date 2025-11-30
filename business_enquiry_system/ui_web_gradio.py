#!/usr/bin/env python3
"""
Beautiful web-based UI using Gradio for the Multi-Service Customer Service System.
Modern, responsive, and easy to use.
"""

import os
import sys
from datetime import datetime
from typing import List, Tuple, Dict, Any
try:
    from dotenv import load_dotenv
except:
    def load_dotenv(): pass

try:
    import gradio as gr
except ImportError:
    print("ERROR: Gradio not installed. Install it with:")
    print("  pip install gradio")
    sys.exit(1)

from mvp_pipeline import SimpleCustomerServicePipeline


# Global pipeline instance
pipeline = None


def initialize_pipeline():
    """Initialize the AI pipeline."""
    global pipeline
    if pipeline is None:
        load_dotenv()
        pipeline = SimpleCustomerServicePipeline()
    return pipeline


def format_classification_html(classification: Dict[str, Any]) -> str:
    """Format classification results as beautiful HTML."""
    domain_colors = {
        "AIRTIME": "#10b981",  # Green
        "POWER": "#f59e0b",    # Yellow/Orange
        "DATA": "#3b82f6",     # Blue
        "MULTI": "#8b5cf6"     # Purple
    }

    priority_colors = {
        "LOW": "#10b981",
        "MEDIUM": "#f59e0b",
        "HIGH": "#ef4444",
        "CRITICAL": "#dc2626"
    }

    domain = classification.get('service_domain', 'UNKNOWN')
    domain_color = domain_colors.get(domain, "#6b7280")
    priority = classification.get('priority', 'MEDIUM')
    priority_color = priority_colors.get(priority, "#6b7280")
    confidence = classification.get('confidence', 0.0)

    # Progress bar for confidence
    confidence_percent = int(confidence * 100)
    confidence_color = "#10b981" if confidence >= 0.8 else "#f59e0b" if confidence >= 0.5 else "#ef4444"

    html = f"""
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px;">
    <h3 style="margin: 0 0 15px 0; font-size: 18px;">🔍 Request Analysis</h3>

    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px;">
        <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px;">
            <div style="font-size: 12px; opacity: 0.8; margin-bottom: 5px;">Service Domain</div>
            <div style="font-size: 18px; font-weight: bold;">
                <span style="background: {domain_color}; padding: 4px 12px; border-radius: 5px;">{domain}</span>
            </div>
        </div>

        <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px;">
            <div style="font-size: 12px; opacity: 0.8; margin-bottom: 5px;">Intent</div>
            <div style="font-size: 16px; font-weight: 600;">{classification.get('intent', 'unknown')}</div>
        </div>

        <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px;">
            <div style="font-size: 12px; opacity: 0.8; margin-bottom: 5px;">Priority</div>
            <div style="font-size: 18px; font-weight: bold;">
                <span style="background: {priority_color}; padding: 4px 12px; border-radius: 5px;">{priority}</span>
            </div>
        </div>

        <div style="background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px;">
            <div style="font-size: 12px; opacity: 0.8; margin-bottom: 5px;">Sentiment</div>
            <div style="font-size: 16px; font-weight: 600;">{classification.get('sentiment', 'NEUTRAL')}</div>
        </div>
    </div>

    <div style="margin-top: 15px; background: rgba(255,255,255,0.1); padding: 12px; border-radius: 8px;">
        <div style="font-size: 12px; opacity: 0.8; margin-bottom: 8px;">AI Confidence</div>
        <div style="background: rgba(0,0,0,0.2); height: 25px; border-radius: 12px; overflow: hidden;">
            <div style="background: {confidence_color}; height: 100%; width: {confidence_percent}%; display: flex; align-items: center; justify-content: center; color: white; font-weight: bold; font-size: 12px; transition: width 0.5s;">
                {confidence_percent}%
            </div>
        </div>
    </div>
</div>
"""

    # Add entities if present
    entities = classification.get('entities', {})
    if any(entities.values()):
        html += """
<div style="background: #f3f4f6; padding: 15px; border-radius: 8px; border-left: 4px solid #3b82f6; margin-bottom: 15px;">
    <h4 style="margin: 0 0 10px 0; color: #1f2937;">📋 Extracted Information</h4>
    <div style="color: #4b5563; line-height: 1.8;">
"""
        if entities.get('phone_numbers'):
            html += f"        <div>📱 <strong>Phone:</strong> {', '.join(entities['phone_numbers'])}</div>\n"
        if entities.get('amounts'):
            amounts = [f"₦{float(a):,.0f}" for a in entities['amounts']]
            html += f"        <div>💰 <strong>Amount:</strong> {', '.join(amounts)}</div>\n"
        if entities.get('networks'):
            html += f"        <div>📡 <strong>Network:</strong> {', '.join(entities['networks'])}</div>\n"
        if entities.get('meter_numbers'):
            html += f"        <div>🔌 <strong>Meter:</strong> {', '.join(entities['meter_numbers'])}</div>\n"
        if entities.get('discos'):
            html += f"        <div>⚡ <strong>DISCO:</strong> {', '.join(entities['discos'])}</div>\n"

        html += "    </div>\n</div>"

    return html


def format_response_html(response: str, proc_time: int, status: str) -> str:
    """Format the assistant response as beautiful HTML."""
    status_color = "#10b981" if status == "completed" else "#ef4444"
    status_icon = "✅" if status == "completed" else "❌"

    # Convert line breaks to HTML
    response_html = response.replace('\n', '<br>')

    # Highlight URLs
    import re
    response_html = re.sub(
        r'(https?://[^\s<]+)',
        r'<a href="\1" target="_blank" style="color: #3b82f6; text-decoration: underline;">\1</a>',
        response_html
    )

    # Highlight amounts
    response_html = re.sub(
        r'(₦[\d,]+(?:\.\d{2})?)',
        r'<strong style="color: #10b981;">\1</strong>',
        response_html
    )

    html = f"""
<div style="background: white; border-radius: 10px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
    <div style="display: flex; align-items: center; margin-bottom: 15px; padding-bottom: 15px; border-bottom: 2px solid #e5e7eb;">
        <div style="font-size: 24px; margin-right: 10px;">🤖</div>
        <div>
            <div style="font-size: 18px; font-weight: bold; color: #1f2937;">Assistant Response</div>
            <div style="font-size: 12px; color: #6b7280;">
                <span style="background: {status_color}; color: white; padding: 2px 8px; border-radius: 4px; margin-right: 10px;">{status_icon} {status.upper()}</span>
                <span>⏱️ {proc_time}ms</span>
            </div>
        </div>
    </div>

    <div style="color: #374151; line-height: 1.8; font-size: 15px;">
        {response_html}
    </div>
</div>
"""
    return html


def process_query(message: str, name: str, phone: str, tenant_id: str, history: List[Tuple[str, str]]) -> Tuple[List[Tuple[str, str]], str, str]:
    """
    Process a customer query and return chat history, classification HTML, and response HTML.
    """
    if not message.strip():
        return history, "", ""

    try:
        # Initialize pipeline if needed
        initialize_pipeline()

        # Add user message to history
        history = history + [(message, None)]

        # Process the query
        result = pipeline.process(
            customer_message=message,
            customer_phone=phone or "+2348000000000",
            customer_name=name or "Customer",
            tenant_id=tenant_id or "legacy-ng-telecom",
        )

        # Format classification
        classification_html = format_classification_html(result['classification'])

        # Format response
        response_text = result.get('final_response', 'No response generated')
        proc_time = result.get('processing_time_ms', 0)
        status = result.get('status', 'unknown')

        response_html = format_response_html(response_text, proc_time, status)

        # Update history with assistant response
        history[-1] = (message, response_text)

        return history, classification_html, response_html

    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        history[-1] = (message, error_msg)
        return history, "", f'<div style="color: red; padding: 20px;">{error_msg}</div>'


def create_interface():
    """Create the Gradio interface."""

    # Custom CSS for beautiful styling
    custom_css = """
    .gradio-container {
        max-width: 1200px !important;
    }
    .header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 30px;
        border-radius: 10px;
        text-align: center;
        margin-bottom: 20px;
    }
    .example-btn {
        background: #f3f4f6 !important;
        border: 2px solid #e5e7eb !important;
        border-radius: 8px !important;
    }
    .example-btn:hover {
        background: #e5e7eb !important;
        border-color: #667eea !important;
    }
    """

    with gr.Blocks(css=custom_css, title="AI Customer Service") as demo:
        # Header
        gr.HTML("""
        <div class="header">
            <h1 style="margin: 0; font-size: 32px;">🤖 AI Customer Service Assistant</h1>
            <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">
                Airtime • Power/Electricity • Data Bundles
            </p>
            <p style="margin: 5px 0 0 0; font-size: 14px; opacity: 0.7;">
                Get instant guidance and navigation for Nigerian mobile and utility services
            </p>
        </div>
        """)

        with gr.Row():
            with gr.Column(scale=2):
                # Chat interface
                chatbot = gr.Chatbot(
                    label="💬 Conversation",
                    height=400,
                    show_label=True,
                    avatar_images=("👤", "🤖")
                )

                with gr.Row():
                    message_input = gr.Textbox(
                        placeholder="Type your request here... (e.g., 'I need 1000 naira MTN airtime')",
                        label="Your Message",
                        lines=2,
                        scale=4
                    )
                    send_btn = gr.Button("Send 📤", variant="primary", scale=1)

                with gr.Row():
                    clear_btn = gr.Button("Clear Chat 🗑️")

            with gr.Column(scale=1):
                # Customer info
                gr.Markdown("### 👤 Customer Information")
                name_input = gr.Textbox(
                    label="Name (Optional)",
                    placeholder="John Doe",
                    value="Customer"
                )
                phone_input = gr.Textbox(
                    label="Phone (Optional)",
                    placeholder="+2348012345678",
                    value="+2348000000000"
                )
                tenant_input = gr.Textbox(
                    label="Tenant ID",
                    placeholder="legacy-ng-telecom",
                    value="legacy-ng-telecom"
                )

        # Analysis and Response sections
        with gr.Row():
            with gr.Column():
                classification_output = gr.HTML(label="Analysis")

        with gr.Row():
            with gr.Column():
                response_output = gr.HTML(label="Assistant Response")

        # Example queries
        gr.Markdown("### 💡 Example Queries")
        gr.Examples(
            examples=[
                ["I need 1000 naira MTN airtime for 08012345678"],
                ["Buy me 5000 naira EKEDC token for meter 12345678901"],
                ["How much is 10GB data on Airtel?"],
                ["Send me 2000 naira Glo airtime"],
                ["I want to purchase 15000 naira prepaid electricity"],
                ["Recommend a data plan for heavy usage"],
            ],
            inputs=message_input,
            label="Click to try:",
        )

        # Footer
        gr.HTML("""
        <div style="text-align: center; margin-top: 30px; padding: 20px; background: #f9fafb; border-radius: 8px;">
            <p style="margin: 0; color: #6b7280; font-size: 14px;">
                🔒 Your information is secure • 🚀 Powered by AI • 🇳🇬 Supporting Nigerian Services
            </p>
            <p style="margin: 5px 0 0 0; color: #9ca3af; font-size: 12px;">
                This system provides guidance and navigation to self-service portals
            </p>
        </div>
        """)

        # Event handlers
        def submit_message(message, name, phone, tenant_id, history):
            return process_query(message, name, phone, tenant_id, history)

        send_btn.click(
            fn=submit_message,
            inputs=[message_input, name_input, phone_input, tenant_input, chatbot],
            outputs=[chatbot, classification_output, response_output]
        ).then(
            lambda: "",  # Clear message input after sending
            inputs=None,
            outputs=message_input
        )

        message_input.submit(
            fn=submit_message,
            inputs=[message_input, name_input, phone_input, tenant_input, chatbot],
            outputs=[chatbot, classification_output, response_output]
        ).then(
            lambda: "",
            inputs=None,
            outputs=message_input
        )

        clear_btn.click(
            lambda: ([], "", ""),
            inputs=None,
            outputs=[chatbot, classification_output, response_output]
        )

    return demo


def main():
    """Launch the web interface."""
    print("🚀 Initializing AI Customer Service Web Interface...")
    print("⏳ Loading AI models...")

    # Pre-initialize pipeline
    try:
        initialize_pipeline()
        print("✅ AI agents ready!")
    except Exception as e:
        print(f"⚠️  Warning: Could not pre-initialize pipeline: {e}")
        print("   Pipeline will initialize on first query.")

    print("\n" + "=" * 60)
    print("🌐 Starting web server...")
    print("=" * 60 + "\n")

    # Create and launch interface
    demo = create_interface()
    demo.launch(
        server_name="0.0.0.0",  # Allow external connections
        server_port=7860,
        share=False,  # Set to True to create a public link
        show_error=True,
        quiet=False
    )


if __name__ == "__main__":
    main()
