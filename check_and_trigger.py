import os
import yaml
import json
import subprocess
from github import Github

# Load the YAML configuration file
def load_config(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

# Function to check if a tag exists in the repository
def tag_exists(repo, tag):
    try:
        tags = repo.get_tags()
        for t in tags:
            if t.name == tag:
                return True
        return False
    except Exception as e:
        print(f"Error checking tags for {repo.name}: {e}")
        return False

# Main function
def main():
    config = load_config('repos.yaml')

    # Authenticate with GitHub using a personal access token
    token = os.getenv('PERSONAL_ACCESS_TOKEN')
    if not token:
        raise ValueError("PERSONAL_ACCESS_TOKEN environment variable is not set")

    # using an access token
    g = Github(token)

    for repo_info in config['repositories']:
        if repo_info['enabled']:
            repo_name = repo_info['name']
            tag = repo_info['tag']
            release_notes = repo_info['release_notes']
            release_notes_str = "\n".join(release_notes)  # Join release notes with new line character
            owner, repo = repo_name.split('/')
            deployment_repo = f"{owner}/{repo}-deploy"
            try:
                repo = g.get_repo(repo_name)
                if not tag_exists(repo, tag):
                    print(f"Tag {tag} not found in {repo_name}, creating tag and dispatching event.")
                    
                    # Create and push the tag
                    subprocess.run(['git', 'tag', tag], check=True)
                    subprocess.run(['git', 'push', 'origin', tag], check=True)
                    
                    # Trigger the deployment workflow in the deployment repository
                    dispatch_payload = {
                        "event_type": "trigger-deploy",
                        "client_payload": {
                            "tag": tag,
                            "release_notes": release_notes_str
                        }
                    }
                    subprocess.run([
                        'curl', '-X', 'POST', '-H', f"Authorization: token {token}", 
                        '-H', 'Accept: application/vnd.github.v3+json', 
                        f'https://api.github.com/repos/{deployment_repo}/dispatches', 
                        '-d', json.dumps(dispatch_payload)
                    ], check=True)
                else:
                    print(f"Tag {tag} already exists in {repo_name}, skipping update.")
            except Exception as e:
                print(f"Error accessing repository {repo_name}: {e}")

if __name__ == "__main__":
    main()