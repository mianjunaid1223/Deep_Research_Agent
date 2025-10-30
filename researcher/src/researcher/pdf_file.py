import pdfkit
from litellm import completion
import os
from dotenv import load_dotenv
import tempfile
from datetime import datetime, timedelta
import threading
import platform


load_dotenv()

os.environ["GEMINI_API_KEY"] = os.getenv("API_KEY")

# Research paper standards and their guidelines
PAPER_STANDARDS = {
    "ITTT": {
        "name": "International Technology, Education, and Training Standard",
        "sections": [
            "Title Page",
            "Abstract",
            "Keywords",
            "Introduction",
            "Literature Review",
            "Methodology",
            "Results and Analysis",
            "Discussion",
            "Conclusion and Recommendations",
            "References"
        ],
        "formatting": {
            "font": "Times New Roman",
            "size": "12pt",
            "spacing": "1.5",
            "margins": "1 inch (2.54 cm)",
            "alignment": "Justified",
            "citations": "APA 7th Edition"
        }
    },
    "IEEE": {
        "name": "Institute of Electrical and Electronics Engineers",
        "sections": [
            "Title Page",
            "Abstract",
            "Index Terms",
            "Introduction",
            "Background",
            "Methodology",
            "Results",
            "Discussion",
            "Conclusion",
            "References"
        ],
        "formatting": {
            "font": "Times New Roman",
            "size": "10pt",
            "spacing": "1.0",
            "margins": "0.75 inch",
            "alignment": "Justified",
            "citations": "IEEE Citation Style"
        }
    },
    "APA": {
        "name": "American Psychological Association",
        "sections": [
            "Title Page",
            "Abstract",
            "Introduction",
            "Method",
            "Results",
            "Discussion",
            "References",
            "Tables and Figures"
        ],
        "formatting": {
            "font": "Times New Roman",
            "size": "12pt",
            "spacing": "2.0",
            "margins": "1 inch",
            "alignment": "Left-aligned",
            "citations": "APA 7th Edition"
        }
    }
}

# Store PDF file cleanup information
pdf_cleanup_tasks = {}

def get_wkhtmltopdf_path():
    """Get the appropriate wkhtmltopdf path based on the operating system."""
    system = platform.system().lower()
    
    if system == 'windows':
        # Common Windows installation paths
        possible_paths = [
            r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe',
            r'C:\Program Files (x86)\wkhtmltopdf\bin\wkhtmltopdf.exe',
            # Add the path from environment variable if it exists
            os.environ.get('WKHTMLTOPDF_PATH', '')
        ]
        
        # Return the first valid path
        for path in possible_paths:
            if path and os.path.exists(path):
                return path
                
        raise Exception("wkhtmltopdf not found. Please install it from https://wkhtmltopdf.org/downloads.html")
        
    elif system == 'darwin':  # macOS
        return '/usr/local/bin/wkhtmltopdf'
    else:  # Linux
        return '/usr/bin/wkhtmltopdf'

def cleanup_pdf(filepath, delay_hours=1):
    """Delete the PDF file after specified delay."""
    def delete_file():
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"Cleaned up file: {filepath}")
        except Exception as e:
            print(f"Error cleaning up file {filepath}: {e}")
    
    # Schedule deletion
    timer = threading.Timer(delay_hours * 3600, delete_file)
    timer.start()
    pdf_cleanup_tasks[filepath] = timer

def extract_research_content(chat_history):
    """Extract research content from chat history."""
    content = {
        'topic': '',
        'main_points': [],
        'sources': []
    }
    
    # Extract topic and content from chat history
    for msg in chat_history:
        if msg.get("role") == "user" and msg.get("content"):
            # Use the user's query as the topic
            content['topic'] = msg["content"]
            break
    
    for msg in chat_history:
        if msg.get("role") == "assistant":
            if msg.get("content"):
                content['main_points'].append(msg["content"])
            if msg.get("sources"):
                content['sources'].extend(msg["sources"])
    
    return content

def generate_section_content(section_name, chat_history, standard, context=""):
    """Generate content for a specific section using a dedicated LLM call."""
    
    research = extract_research_content(chat_history)
    
    # Use actual topic from chat history
    topic = research['topic']
    content = "\n".join(research['main_points'])
    
    prompt = f"""Write a {section_name} section for a research paper about {topic}.
    Use this content as reference:
    {content}
    
    Format Requirements:
    - Follow {standard['name']} format
    - Use plain text only
    - No HTML or LaTeX tags
    - Be specific and detailed
    - Use academic language
    - Include proper citations if needed
    
    Additional Context: {context}
    """

    response = completion(
        model=os.getenv("MODEL"),
        messages=[{"content": prompt, "role": "user"}]
    )
    
    return format_section_content(section_name, response['choices'][0]['message']['content'].strip())

def format_section_content(section_name, content):
    """Format section content into proper HTML."""
    if section_name == "Title Page":
        lines = content.split('\n')
        return f"""
            <div class="title-page">
                <h1>{lines[0] if lines else ''}</h1>
                <div class="author">{lines[1] if len(lines) > 1 else ''}</div>
                <div class="institution">{lines[2] if len(lines) > 2 else ''}</div>
                <div class="date">{lines[3] if len(lines) > 3 else ''}</div>
            </div>
        """
    elif section_name == "Keywords":
        keywords = content.split('\n')
        formatted_keywords = ', '.join(k.strip() for k in keywords if k.strip())
        return f"""
            <div class="keywords">
                <h2>Keywords</h2>
                <p>{formatted_keywords}</p>
            </div>
        """
    elif section_name == "Abstract":
        return f"""
            <div class="abstract">
                <h2>Abstract</h2>
                <p>{content}</p>
            </div>
        """
    else:
        # Handle regular sections
        paragraphs = content.split('\n\n')
        formatted_content = []
        for p in paragraphs:
            if p.strip().startswith('#'):  # Handle headers
                level = p.count('#')
                text = p.strip('#').strip()
                formatted_content.append(f"<h{level}>{text}</h{level}>")
            else:
                formatted_content.append(f"<p>{p}</p>")
        
        return f"""
            <div class="section">
                <h2>{section_name}</h2>
                {''.join(formatted_content)}
            </div>
        """

def generate_research_paper(chat_history, paper_standard="ITTT", formatting_options=None, instructions="", output_path=None):
    """Generate a research paper PDF from chat history and instructions."""
    
    if output_path is None:
        # Create temporary directory if it doesn't exist
        temp_dir = os.path.join(os.getcwd(), 'temp_pdfs')
        os.makedirs(temp_dir, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = os.path.join(temp_dir, f'research_paper_{timestamp}.pdf')
    
    # Get standard guidelines
    standard = PAPER_STANDARDS.get(paper_standard, PAPER_STANDARDS["ITTT"])
    
    # Generate content for each section
    sections_content = []
    
    for section in standard['sections']:
        print(f"Generating {section}...")
        section_html = generate_section_content(
            section,
            chat_history,
            standard,
            context=instructions
        )
        sections_content.append(section_html)
    
    # Combine all sections
    html_text = "\n".join(sections_content)
    
    # Update CSS for better page layout
    html_with_css = f"""
    <html>
    <head>
        <style>
            @page {{
                size: A4;
                margin: {standard['formatting']['margins']};
            }}
            body {{ 
                font-family: "{standard['formatting']['font']}", serif;
                font-size: {standard['formatting']['size']};
                line-height: {standard['formatting']['spacing']};
                margin: 0;
                padding: 2.54cm;  /* 1 inch margin */
                color: #000;
            }}
            
            .title-page {{
                height: 100vh;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                text-align: center;
                page-break-after: always;
            }}
            
            .title-page h1 {{
                font-size: 24pt;
                font-weight: bold;
                margin-bottom: 4cm;
                text-align: center;
                max-width: 80%;
            }}
            
            .title-page .author {{
                font-size: 14pt;
                margin-bottom: 1cm;
            }}
            
            .title-page .institution {{
                font-size: 12pt;
                margin-bottom: 1cm;
            }}
            
            .title-page .date {{
                font-size: 12pt;
            }}
            
            .section {{
                margin-top: 1cm;
                page-break-before: always;
            }}
            
            h2 {{
                font-size: 14pt;
                margin-top: 1cm;
                margin-bottom: 0.5cm;
            }}
            
            p {{
                text-align: justify;
                margin: 0.5cm 0;
                line-height: 1.5;
            }}
            
            .abstract {{
                margin: 1cm 0;
            }}
            
            .keywords {{
                margin: 1cm 0;
            }}
        </style>
    </head>
    <body>
        {html_text}
    </body>
    </html>
    """

    # Configure PDF options for better layout
    options = {
        'page-size': 'A4',
        'margin-top': '25mm',
        'margin-right': '25mm',
        'margin-bottom': '25mm',
        'margin-left': '25mm',
        'encoding': 'UTF-8',
        'no-outline': None,
        'enable-local-file-access': None,
        'print-media-type': None,
        'quiet': '',
        'footer-right': '[page]',
        'footer-font-size': '10',
        'footer-line': True,
        'enable-smart-shrinking': True,
        'dpi': 300
    }

    try:
        wkhtmltopdf_path = get_wkhtmltopdf_path()
        config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
        
        pdfkit.from_string(html_with_css, output_path, options=options, configuration=config)
        
        cleanup_pdf(output_path)
        return output_path
        
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        return None

