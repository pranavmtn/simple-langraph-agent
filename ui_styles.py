import streamlit as st

LAYOUT_CSS = """
section.main > div.block-container {
    max-width: 680px;
    margin-left: auto;
    margin-right: auto;
    padding-left: 1.25rem;
    padding-right: 1.25rem;
}
.page-header {
    text-align: center;
    margin-bottom: 1.25rem;
}
.page-header h1 {
    font-size: 2.1rem;
    font-weight: 700;
    margin: 0 0 0.35rem 0;
    line-height: 1.2;
}
.page-header p {
    color: #64748b;
    font-size: 1rem;
    max-width: 34rem;
    margin: 0 auto;
    line-height: 1.5;
}
.story-page {
    max-width: 640px;
    margin: 0 auto;
}
.story-page .story-header {
    text-align: center;
    margin-bottom: 1.5rem;
}
.story-page .story-header h1 {
    font-size: 2rem;
    font-weight: 700;
    margin: 0 0 0.35rem 0;
}
.story-page .story-header p {
    color: #64748b;
    margin: 0;
}
.under-hood-divider {
    border: none;
    border-top: 1px solid #e2e8f0;
    margin: 0 0 0.85rem 0;
}
div[data-testid="column"]:has(.under-hood-complete-marker) {
    background-color: #f0fdf4;
    border: 1px solid #dcfce7;
    border-radius: 12px;
    padding: 0.5rem 0.75rem 0.75rem;
    transition: background-color 0.45s ease, border-color 0.45s ease;
}
.node-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 999px;
    background: transparent;
    border: 1.5px solid;
    font-weight: 600;
    font-size: 0.82rem;
    margin-right: 6px;
    white-space: nowrap;
    transition: color 0.3s ease, border-color 0.3s ease;
}
.trace-step-header {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    margin-bottom: 0.35rem;
    padding: 0.1rem 0;
}
.trace-step-num {
    color: #c5d0dc;
    font-size: 0.68rem;
    font-weight: 400;
    margin-left: 0.65rem;
    letter-spacing: 0.03em;
    text-transform: lowercase;
}
.ai-flow-line {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.35rem;
    margin: 0.2rem 0 0.45rem 0;
    font-size: 0.86rem;
    color: #b8c5d6;
    font-weight: 500;
}
.ai-flow-arrow {
    color: #d4dde8;
    font-weight: 400;
}
.visit-flow-wrap {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.35rem;
    margin: 0.25rem 0 0.75rem 0;
}
.visit-arrow {
    color: #64748b;
    font-weight: 700;
    padding: 0 0.15rem;
}
.live-pulse {
    animation: pulse 1.2s ease-in-out infinite;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.45; }
}
.sidebar-erase-wrap {
    margin-top: 1.5rem;
    padding-top: 1rem;
    border-top: 1px solid #e2e8f0;
}
.sidebar-token-line {
    font-size: 0.78rem;
    color: #64748b;
    line-height: 1.4;
    margin: 0;
}
.graph-running-banner {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    padding: 0.55rem 0.75rem;
    margin-bottom: 0.75rem;
    background: linear-gradient(90deg, #fffbeb 0%, #fef9c3 50%, #fffbeb 100%);
    background-size: 200% 100%;
    border: 1px solid #fde68a;
    border-radius: 8px;
    font-size: 0.88rem;
    font-weight: 600;
    color: #854d0e;
    animation: trace-shimmer 2.2s ease-in-out infinite, fade-in 0.35s ease;
}
.graph-running-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #facc15;
    animation: pulse 1s ease-in-out infinite;
}
.trace-step-marker {
    height: 0;
    margin: 0;
    padding: 0;
    border: none;
    overflow: hidden;
}
.trace-step-marker.trace-step-running + div[data-testid="stExpander"] {
    border: 1px solid #fde68a;
    border-radius: 10px;
    background: linear-gradient(90deg, #fffbeb 0%, #fef9c3 45%, #fffbeb 90%);
    background-size: 220% 100%;
    animation: trace-shimmer 1.8s ease-in-out infinite;
    transition: border-color 0.35s ease, background 0.35s ease, box-shadow 0.35s ease;
    box-shadow: 0 0 0 1px rgba(250, 204, 21, 0.15);
}
.trace-step-marker.trace-step-running + div[data-testid="stExpander"] summary {
    font-weight: 600;
    color: #854d0e;
}
.trace-step-marker.trace-step-done + div[data-testid="stExpander"] {
    border: 1px solid #d9f99d;
    border-radius: 10px;
    background-color: #fefce8;
    transition: border-color 0.35s ease, background-color 0.35s ease;
}
.trace-step-marker.trace-step-done + div[data-testid="stExpander"] summary {
    color: #4d7c0f;
}
.state-snapshot-complete-marker + div[data-testid="stExpander"] {
    border: 1px solid #bbf7d0;
    border-radius: 10px;
    background-color: #f0fdf4;
    transition: background-color 0.45s ease, border-color 0.45s ease;
}
.state-snapshot-complete-marker + div[data-testid="stExpander"] summary {
    color: #166534;
    font-weight: 600;
}
div[data-testid="stExpander"] details {
    transition: all 0.35s ease;
}
div[data-testid="stExpander"] summary {
    transition: color 0.3s ease;
}
.step-running-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    color: #a16207;
    font-size: 0.9rem;
    font-weight: 500;
    padding: 0.15rem 0;
    animation: fade-in 0.3s ease;
}
.step-running-bar {
    height: 3px;
    border-radius: 999px;
    background: #fef3c7;
    overflow: hidden;
    margin: 0.35rem 0 0.5rem 0;
}
.step-running-bar-fill {
    height: 100%;
    width: 40%;
    border-radius: 999px;
    background: linear-gradient(90deg, #fde68a, #facc15, #fde68a);
    animation: bar-slide 1.4s ease-in-out infinite;
}
.assistant-thinking {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    color: #64748b;
    font-size: 0.92rem;
}
.thinking-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #94a3b8;
    animation: thinking-bounce 1.2s ease-in-out infinite;
}
.thinking-dot:nth-child(2) { animation-delay: 0.15s; }
.thinking-dot:nth-child(3) { animation-delay: 0.3s; }
.thinking-label {
    margin-left: 0.35rem;
    color: #854d0e;
    font-weight: 500;
}
@keyframes trace-shimmer {
    0% { background-position: 100% 0; }
    100% { background-position: -100% 0; }
}
@keyframes fade-in {
    from { opacity: 0; transform: translateY(4px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes bar-slide {
    0% { transform: translateX(-120%); }
    100% { transform: translateX(320%); }
}
@keyframes thinking-bounce {
    0%, 80%, 100% { transform: translateY(0); opacity: 0.45; }
    40% { transform: translateY(-5px); opacity: 1; }
}
"""


def inject_layout_css():
    st.markdown(f"<style>{LAYOUT_CSS}</style>", unsafe_allow_html=True)
