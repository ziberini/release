import os
import yaml
import json
import subprocess
from github import Github
import base64

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
            release_notes_b64 = base64.b64encode(release_notes_str.encode()).decode()  # Base64 encode the release notes
            try:
                repo = g.get_repo(repo_name)
                if not tag_exists(repo, tag):
                    print(f"Tag {tag} not found in {repo_name}, creating tag and dispatching event.")
                    
                    # Set up git with the PAT
                    subprocess.run(['git', 'config', '--global', 'user.name', 'github-actions'], check=True)
                    subprocess.run(['git', 'config', '--global', 'user.email', 'github-actions@github.com'], check=True)
                    subprocess.run(['git', 'config', '--global', 'credential.helper', 'store'], check=True)
                    with open(os.path.expanduser("~/.git-credentials"), 'w') as creds:
                        creds.write(f'https://{token}:x-oauth-basic@github.com\n')
                    
                    # Clone the repository
                    subprocess.run(['git', 'clone', f'https://{token}:x-oauth-basic@github.com/{repo_name}.git'], check=True)
                    os.chdir(repo_name.split('/')[-1])
                    
                    # Create and push the tag
                    subprocess.run(['git', 'tag', tag], check=True)
                    subprocess.run(['git', 'push', 'origin', tag], check=True)
                    
                    # Trigger the deployment workflow in the respective repository
                    dispatch_payload = {
                        "event_type": "trigger-deploy",
                        "client_payload": {
                            "tag": tag,
                            "release_notes": release_notes_b64
                        }
                    }
                    subprocess.run([
                        'curl', '-X', 'POST', '-H', f"Authorization: token {token}", 
                        '-H', 'Accept: application/vnd.github.v3+json', 
                        f'https://api.github.com/repos/{repo_name}/dispatches', 
                        '-d', json.dumps(dispatch_payload)
                    ], check=True)
                else:
                    print(f"Tag {tag} already exists in {repo_name}, skipping update.")
            except Exception as e:
                print(f"Error accessing repository {repo_name}: {e}")

if __name__ == "__main__":
    main()