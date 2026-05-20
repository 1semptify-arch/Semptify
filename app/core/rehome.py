"""
Rehome file generation utility.

Generates the Rehome.html file used for device reconnection.
This is a standalone utility that can be used by both the old vault_manager
and the new Vault SDK + Installer architecture.
"""

from app.core.user_id import parse_user_id


def generate_rehome_html(user_id: str, provider: str, base_url: str) -> str:
    """
    Generate Rehome.html - the reconnection script users click to sync new devices.
    This file is stored in user's cloud storage root Semptify5.0 folder.
    
    Args:
        user_id: User ID (GU2L3wyfBy format)
        provider: Storage provider (google_drive, dropbox, onedrive)
        base_url: Semptify base URL for redirect
    
    Returns:
        HTML content for Rehome.html
    """
    _, role, _ = parse_user_id(user_id)
    
    provider_names = {
        "google_drive": "Google Drive",
        "dropbox": "Dropbox",
        "onedrive": "OneDrive"
    }
    provider_display = provider_names.get(provider, provider)
    
    provider_icons = {
        "google_drive": "🔷",
        "dropbox": "📦",
        "onedrive": "☁️"
    }
    provider_icon = provider_icons.get(provider, "📁")
    
    return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Semptify - Reconnect Device</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .container {{
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            max-width: 500px;
            width: 100%;
            padding: 40px;
            text-align: center;
        }}
        .icon {{
            font-size: 64px;
            margin-bottom: 20px;
        }}
        h1 {{
            color: #333;
            font-size: 28px;
            margin-bottom: 15px;
        }}
        p {{
            color: #666;
            font-size: 16px;
            line-height: 1.6;
            margin-bottom: 25px;
        }}
        .provider {{
            background: #f5f5f5;
            padding: 15px;
            border-radius: 10px;
            margin-bottom: 25px;
            font-weight: 600;
            color: #333;
        }}
        .btn {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            font-size: 18px;
            border-radius: 50px;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
            text-decoration: none;
            display: inline-block;
        }}
        .btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
        }}
        .spinner {{
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            width: 20px;
            height: 20px;
            animation: spin 1s linear infinite;
            display: none;
            margin: 0 auto;
        }}
        @keyframes spin {{
            0% {{ transform: rotate(0deg); }}
            100% {{ transform: rotate(360deg); }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="icon">{provider_icon}</div>
        <h1>Reconnect Your Device</h1>
        <p>Click below to reconnect this device to your Semptify vault on {provider_display}.</p>
        <div class="provider">{provider_display}</div>
        <button class="btn" onclick="reconnect()">Reconnect Now</button>
        <div class="spinner" id="spinner"></div>
    </div>
    <script>
        async function reconnect() {{
            const btn = document.querySelector('.btn');
            const spinner = document.getElementById('spinner');
            
            btn.style.display = 'none';
            spinner.style.display = 'block';
            
            try {{
                const response = await fetch('{base_url}/storage/rehome', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json',
                    }},
                    body: JSON.stringify({{ user_id: '{user_id}', provider: '{provider}' }}),
                }});
                
                if (response.ok) {{
                    window.location.href = '{base_url}/tenant/home';
                }} else {{
                    throw new Error('Reconnection failed');
                }}
            }} catch (error) {{
                spinner.style.display = 'none';
                btn.style.display = 'inline-block';
                btn.textContent = 'Try Again';
                alert('Reconnection failed. Please try again.');
            }}
        }}
    </script>
</body>
</html>'''
