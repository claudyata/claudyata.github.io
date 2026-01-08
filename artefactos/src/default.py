"""
Estilos CSS para Streamlit App
"""

def get_custom_css():
    """Retorna CSS personalizado para la app"""
    return """
    <style>
    /* Variables de color */
    :root {
        --primary-color: #2E86AB;
        --secondary-color: #A23B72;
        --success-color: #06A77D;
        --warning-color: #F77F00;
        --danger-color: #D62828;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: var(--primary-color);
    }
    
    /* Botones */
    .stButton>button {
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Métricas */
    div[data-testid="metric-container"] {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border-left: 4px solid var(--primary-color);
    }
    
    /* Code blocks */
    code {
        background-color: #1e1e1e;
        color: #d4d4d4;
        padding: 2px 6px;
        border-radius: 4px;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #f8f9fa;
    }
    </style>
    """