import requests
from bs4 import BeautifulSoup
import os
from typing import Optional

def fetch_url_content(url: str) -> str:
    """Fetch and extract text content from a URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for element in soup(["script", "style"]):
            element.decompose()
            
        # Get text
        text = soup.get_text()
        
        # Break into lines and remove leading and trailing whitespace
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text[:10000] # Cap at 10k chars for LLM context
    except Exception as e:
        return f"Error fetching URL: {str(e)}"

def download_skill(url: str, skill_name: str) -> str:
    """Download a skill (.md file) and save it locally."""
    skills_dir = os.path.abspath("skills")
    if not os.path.exists(skills_dir):
        os.makedirs(skills_dir)
        
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        file_path = os.path.join(skills_dir, f"{skill_name}.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(response.text)
            
        return f"Skill '{skill_name}' downloaded and saved to skills/{skill_name}.md"
    except Exception as e:
        return f"Error downloading skill: {str(e)}"

def get_skill_content(skill_name: str) -> str:
    """Read a saved skill's content."""
    skills_dir = os.path.abspath("skills")
    file_path = os.path.join(skills_dir, f"{skill_name}.md")
    
    if not os.path.exists(file_path):
        return f"Skill '{skill_name}' not found."
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading skill: {str(e)}"

def list_skills() -> list:
    """List all downloaded skills."""
    skills_dir = os.path.abspath("skills")
    if not os.path.exists(skills_dir):
        return []
        
    return [f.replace(".md", "") for f in os.listdir(skills_dir) if f.endswith(".md")]
