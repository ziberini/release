import os
import yaml
import subprocess
from github import Github

# Load the YAML configuration file
def load_config(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

# Function to run a shell command
def run_command(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error running command: {command}\n{result.stderr}")
        raise Exception(f"Command failed: {command}")
    return result.stdout

# Main function
def main():
    config = load_config('repos.yaml')

    # Authenticate with GitHub using a personal access token
    token = os.getenv('PERSONAL_ACCESS_TOKEN')
    if not token:
        raise ValueError("PERSONAL_ACCESS_TOKEN environment variable is not set")

    # Using an access token
    g = Github(token)

    for repo_info in config['repositories']:
        if repo_info['enabled']:
            repo_name = repo_info['name']
            tag = repo_info['tag']
            deployment_path = repo_info['deployment_path']
            release_notes = repo_info['release_notes']
            release_notes_str = "\n".join(release_notes)  # Join release notes with new line character

            try:
                print(f"Processing repository: {repo_name}")

                # Clone the repository and checkout the xyz branch
                repo_dir = repo_name.split('/')[-1]
                run_command(f'git clone https://{token}:x-oauth-basic@github.com/{repo_name}.git')
                os.chdir(repo_dir)
                print(f"Cloned repository {repo_name} and switched to directory {repo_dir}")
                run_command('git checkout xyz')
                print(f"Checked out 'xyz' branch in {repo_name}")

                # Create or update release_notes.txt with the release notes
                with open('release_notes.txt', 'w') as file:
                    file.write(release_notes_str)
                print("release_notes.txt file generated successfully")

                # Verify the release_notes.txt file content
                with open('release_notes.txt', 'r') as file:
                    content = file.read()
                    print(f"release_notes.txt content:\n{content}")

                # Update the deployment.yaml file with the new tag
                with open(deployment_path, 'r') as file:
                    deployment_data = yaml.safe_load(file)

                # Find and update the image tag in the containers section
                for container in deployment_data['spec']['template']['spec']['containers']:
                    if 'image' in container:
                        container['image'] = f"{container['image'].split(':')[0]}:{tag}"

                with open(deployment_path, 'w') as file:
                    yaml.safe_dump(deployment_data, file)
                print(f"deployment.yaml file updated successfully in {repo_name} repo")

                # Commit and push the changes
                run_command('git config --global user.name "github-actions"')
                run_command('git config --global user.email "github-actions@github.com"')
                run_command('git add .')
                run_command(f'git commit -m "Update deployment.yaml with tag {tag} and add release_notes.txt"')
                print("Committed changes to git")
                run_command('git push origin xyz')
                print(f"Pushed changes to 'xyz' branch - {repo_name} repo")

                # Go back to the root directory
                os.chdir('..')
                run_command(f'rm -rf {repo_dir}')
                print(f"Cleaned up local repository {repo_dir}")

                print(f"Updated {repo_name} with tag {tag} in deployment.yaml and pushed to 'xyz' branch with release notes.")
                print(f"release_notes.txt file uploaded successfully in {repo_name} repo")

            except Exception as e:
                print(f"Error accessing repository {repo_name}: {e}")

if __name__ == "__main__":
    main()