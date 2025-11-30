import streamlit as st
import streamlit.components.v1 as components


def scroll_to_top(anchor_id: str):
    """
    Forza lo scroll della pagina in alto usando JavaScript.
    Inserisce un'ancora HTML invisibile e uno script che tenta di raggiungerla.
    
    Args:
        anchor_id (str): ID univoco per l'ancora (es. "top-marker-eval")
    """
    # 1. Piazza l'ancora invisibile
    st.markdown(f'<div id="{anchor_id}" style="position: absolute; top: -150px; left: 0;"></div>', unsafe_allow_html=True)
    
    # 2. Script JS universale (scrollIntoView + scrollTop reset)
    js = f"""
    <script>
        function forceScroll() {{
            try {{
                // Metodo 1: Cerca l'ancora specifica
                var marker = window.parent.document.getElementById("{anchor_id}");
                if (marker) {{
                    marker.scrollIntoView({{behavior: "auto", block: "start"}});
                }}
                
                // Metodo 2: Reset forzato del contenitore principale (backup)
                var mainView = window.parent.document.querySelector('[data-testid="stAppViewContainer"]');
                if (mainView) {{ mainView.scrollTop = 0; }}
                
            }} catch(e) {{}}
        }}
        
        // Tentativi multipli per vincere la race condition di Streamlit
        forceScroll();
        setTimeout(forceScroll, 50);
        setTimeout(forceScroll, 150);
        setTimeout(forceScroll, 300);
    </script>
    """
    components.html(js, height=0)