#!/usr/bin/env python3
"""
Beautiful Streamlit web interface for the Multi-Service Customer Service System.
Alternative to Gradio with a different design aesthetic.
"""

import os
import sys
from datetime import datetime
from typing import Dict, Any
try:
    from dotenv import load_dotenv
except:
    def load_dotenv(): pass

try:
    import streamlit as st
except ImportError:
    print("ERROR: Streamlit not installed. Install it with:")
    print("  pip install streamlit")
    sys.exit(1)

from mvp_pipeline import SimpleCustomerServicePipeline


# Page configuration
st.set_page_config(
    page_title="AI Customer Service",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
    }
    .response-box {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-top: 1rem;
    }
    .classification-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-weight: 600;
        padding: 0.75rem;
        border: none;
    }
    .example-button {
        background: #f3f4f6;
        padding: 0.75rem;
        border-radius: 8px;
        margin: 0.25rem 0;
        cursor: pointer;
        border: 2px solid #e5e7eb;
        transition: all 0.2s;
    }
    .example-button:hover {
        border-color: #667eea;
        background: #e5e7eb;
    }
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def initialize_pipeline():
    """Initialize and cache the AI pipeline."""
    load_dotenv()
    return SimpleCustomerServicePipeline()


def display_classification(classification: Dict[str, Any]):
    """Display classification results beautifully."""
    domain_colors = {
        "AIRTIME": "#10b981",
        "POWER": "#f59e0b",
        "DATA": "#3b82f6",
        "MULTI": "#8b5cf6"
    }

    priority_colors = {
        "LOW": "#10b981",
        "MEDIUM": "#f59e0b",
        "HIGH": "#ef4444",
        "CRITICAL": "#dc2626"
    }

    domain = classification.get('service_domain', 'UNKNOWN')
    domain_color = domain_colors.get(domain, "#6b7280")

    st.markdown("""
    <div class="classification-box">
        <h3 style="margin-top: 0;">🔍 Request Analysis</h3>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div style="text-align: center;">
            <div style="font-size: 12px; opacity: 0.8;">Service Domain</div>
            <div style="font-size: 20px; font-weight: bold; background: {domain_color}; padding: 8px; border-radius: 5px; margin-top: 5px;">
                {domain}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="text-align: center;">
            <div style="font-size: 12px; opacity: 0.8;">Intent</div>
            <div style="font-size: 16px; font-weight: 600; margin-top: 10px;">
                {classification.get('intent', 'unknown')}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        priority = classification.get('priority', 'MEDIUM')
        priority_color = priority_colors.get(priority, "#6b7280")
        st.markdown(f"""
        <div style="text-align: center;">
            <div style="font-size: 12px; opacity: 0.8;">Priority</div>
            <div style="font-size: 20px; font-weight: bold; background: {priority_color}; padding: 8px; border-radius: 5px; margin-top: 5px;">
                {priority}
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        sentiment = classification.get('sentiment', 'NEUTRAL')
        sentiment_emoji = {
            "VERY_NEGATIVE": "😡",
            "NEGATIVE": "😟",
            "NEUTRAL": "😐",
            "POSITIVE": "😊"
        }
        st.markdown(f"""
        <div style="text-align: center;">
            <div style="font-size: 12px; opacity: 0.8;">Sentiment</div>
            <div style="font-size: 24px; margin-top: 5px;">
                {sentiment_emoji.get(sentiment, "😐")}
            </div>
            <div style="font-size: 12px; margin-top: 2px;">{sentiment}</div>
        </div>
        """, unsafe_allow_html=True)

    # Confidence bar
    confidence = classification.get('confidence', 0.0)
    confidence_percent = int(confidence * 100)
    st.markdown(f"""
    <div style="margin-top: 15px;">
        <div style="font-size: 12px; opacity: 0.8; margin-bottom: 5px;">AI Confidence: {confidence_percent}%</div>
        <div style="background: rgba(0,0,0,0.2); height: 25px; border-radius: 12px; overflow: hidden;">
            <div style="background: #10b981; height: 100%; width: {confidence_percent}%; transition: width 0.5s;"></div>
        </div>
    </div>
    </div>
    """, unsafe_allow_html=True)

    # Entities
    entities = classification.get('entities', {})
    if any(entities.values()):
        st.markdown("### 📋 Extracted Information")
        entity_cols = st.columns(3)

        idx = 0
        if entities.get('phone_numbers'):
            with entity_cols[idx % 3]:
                st.info(f"📱 **Phone:** {', '.join(entities['phone_numbers'])}")
                idx += 1

        if entities.get('amounts'):
            amounts = [f"₦{float(a):,.0f}" for a in entities['amounts']]
            with entity_cols[idx % 3]:
                st.success(f"💰 **Amount:** {', '.join(amounts)}")
                idx += 1

        if entities.get('networks'):
            with entity_cols[idx % 3]:
                st.info(f"📡 **Network:** {', '.join(entities['networks'])}")
                idx += 1

        if entities.get('meter_numbers'):
            with entity_cols[idx % 3]:
                st.warning(f"🔌 **Meter:** {', '.join(entities['meter_numbers'])}")
                idx += 1

        if entities.get('discos'):
            with entity_cols[idx % 3]:
                st.warning(f"⚡ **DISCO:** {', '.join(entities['discos'])}")


def display_response(response: str, metadata: Dict[str, Any]):
    """Display assistant response beautifully."""
    status = metadata.get('status', 'unknown')
    proc_time = metadata.get('processing_time_ms', 0)

    # Status indicator
    if status == 'completed':
        st.success(f"✅ Response ready in {proc_time}ms")
    else:
        st.error(f"❌ Processing failed ({proc_time}ms)")

    # Response content
    st.markdown("""
    <div class="response-box">
        <h3>🤖 Assistant Response</h3>
    """, unsafe_allow_html=True)

    # Format response
    st.markdown(response)

    st.markdown("</div>", unsafe_allow_html=True)

    # Agents involved
    agents = metadata.get('agents_involved', [])
    if agents:
        st.markdown("**🤖 AI Agents:** " + " → ".join(agents))

    # Escalation notice
    if 'escalation_summary' in metadata:
        st.warning("⚠️ This enquiry has been flagged for human review")


def main():
    """Main Streamlit app."""

    # Header
    st.markdown("""
    <div class="main-header">
        <h1 style="margin: 0; font-size: 36px;">🤖 AI Customer Service Assistant</h1>
        <p style="margin: 10px 0 0 0; font-size: 18px; opacity: 0.9;">
            Airtime • Power/Electricity • Data Bundles
        </p>
        <p style="margin: 5px 0 0 0; font-size: 14px; opacity: 0.8;">
            Get instant guidance and navigation for Nigerian mobile and utility services
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.markdown("### 👤 Customer Information")
        customer_name = st.text_input("Name (Optional)", value="Customer", key="name")
        customer_phone = st.text_input("Phone (Optional)", value="+2348000000000", key="phone")
        tenant_id = st.text_input("Tenant ID", value="legacy-ng-telecom", key="tenant_id")

        st.markdown("---")
        st.markdown("### 📊 Session Info")

        # Initialize session state
        if 'query_count' not in st.session_state:
            st.session_state.query_count = 0
            st.session_state.start_time = datetime.now()

        duration = (datetime.now() - st.session_state.start_time).total_seconds()
        st.metric("Queries Processed", st.session_state.query_count)
        st.metric("Session Duration", f"{int(duration//60)}m {int(duration%60)}s")

        st.markdown("---")
        st.markdown("### 💡 Quick Help")
        st.markdown("""
        **Airtime:**
        - "1000 naira MTN airtime for 08012345678"

        **Power:**
        - "5000 naira EKEDC token for meter 12345678901"

        **Data:**
        - "10GB MTN data bundle"
        """)

        if st.button("Clear History"):
            st.session_state.query_count = 0
            st.session_state.start_time = datetime.now()
            if 'messages' in st.session_state:
                st.session_state.messages = []
            st.rerun()

    # Main content
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 💬 Your Request")

        # Message input
        user_message = st.text_area(
            "Type your message here:",
            placeholder="Example: I need 1000 naira MTN airtime for 08012345678",
            height=100,
            key="message_input"
        )

        submit_col1, submit_col2 = st.columns([3, 1])
        with submit_col1:
            submit = st.button("🚀 Send Request", type="primary", use_container_width=True)
        with submit_col2:
            clear = st.button("🗑️ Clear", use_container_width=True)

        if clear:
            st.session_state.message_input = ""
            st.rerun()

    with col2:
        st.markdown("### 📝 Example Queries")

        examples = [
            "I need 1000 naira MTN airtime for 08012345678",
            "Buy me 5000 naira EKEDC token for meter 12345678901",
            "How much is 10GB data on Airtel?",
            "Send me 2000 naira Glo airtime",
            "Recommend a data plan for heavy usage",
        ]

        for example in examples:
            if st.button(f"💡 {example[:40]}...", key=example, use_container_width=True):
                st.session_state.message_input = example
                st.rerun()

    # Process query
    if submit and user_message.strip():
        try:
            with st.spinner("🤖 AI is processing your request..."):
                # Initialize pipeline
                pipeline = initialize_pipeline()

                # Process query
                result = pipeline.process(
                    customer_message=user_message,
                    customer_phone=customer_phone,
                    customer_name=customer_name,
                    tenant_id=tenant_id or "legacy-ng-telecom",
                )

                # Increment counter
                st.session_state.query_count += 1

            # Display results
            st.markdown("---")

            # Classification
            display_classification(result['classification'])

            # Response
            st.markdown("---")
            display_response(
                result.get('final_response', 'No response generated'),
                result
            )

        except Exception as e:
            st.error(f"❌ Error: {str(e)}")
            import traceback
            with st.expander("Show technical details"):
                st.code(traceback.format_exc())

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 20px; background: #f9fafb; border-radius: 8px;">
        <p style="margin: 0; color: #6b7280; font-size: 14px;">
            🔒 Your information is secure • 🚀 Powered by AI • 🇳🇬 Supporting Nigerian Services
        </p>
        <p style="margin: 5px 0 0 0; color: #9ca3af; font-size: 12px;">
            This system provides guidance and navigation to self-service portals
        </p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
