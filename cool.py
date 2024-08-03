import os
import yaml
import json
import subprocess
from github import Github

# Load the YAML configuration file
def load_config(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

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
            deployment_path = repo_info['deployment_path']
            release_notes = repo_info['release_notes']
            release_notes_str = "\n".join(release_notes)  # Join release notes with new line character

            try:
                # Clone the repository and checkout the xyz branch
                subprocess.run(['git', 'clone', f'https://{token}:x-oauth-basic@github.com/{repo_name}.git'], check=True)
                os.chdir(repo_name.split('/')[-1])
                subprocess.run(['git', 'checkout', 'xyz'], check=True)

                # Update the deployment.yaml file with the new tag
                with open(deployment_path, 'r') as file:
                    deployment_data = yaml.safe_load(file)

                # Find and update the image tag in the containers section
                for container in deployment_data['spec']['template']['spec']['containers']:
                    if 'image' in container:
                        container['image'] = f"{container['image'].split(':')[0]}:{tag}"

                with open(deployment_path, 'w') as file:
                    yaml.safe_dump(deployment_data, file)

                # Commit and push the changes
                subprocess.run(['git', 'config', '--global', 'user.name', 'github-actions'], check=True)
                subprocess.run(['git', 'config', '--global', 'user.email', 'github-actions@github.com'], check=True)
                subprocess.run(['git', 'add', deployment_path], check=True)
                subprocess.run(['git', 'commit', '-m', f'Update deployment.yaml with tag {tag}'], check=True)
                subprocess.run(['git', 'push', 'origin', 'xyz'], check=True)

                # Go back to the root directory
                os.chdir('..')
                subprocess.run(['rm', '-rf', repo_name.split('/')[-1]], check=True)

                # Trigger the deployment workflow in the respective repository
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
                    f'https://api.github.com/repos/{repo_name}/dispatches', 
                    '-d', json.dumps(dispatch_payload)
                ], check=True)

                print(f"Updated {repo_name} with tag {tag} in deployment.yaml and pushed to xyz branch.")

            except Exception as e:
                print(f"Error accessing repository {repo_name}: {e}")

if __name__ == "__main__":
    main()