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

# Function to check if there are any changes to commit
def has_changes():
    result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    return bool(result.stdout.strip())

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

    # Using an access token
    g = Github(token)

    for repo_info in config['repositories']:
        if repo_info['enabled']:
            repo_name = repo_info['name']
            tag = repo_info['tag']
            deployment_path = repo_info.get('deployment_path', '')
            release_notes = repo_info['release_notes']
            release_notes_str = "\n".join(release_notes)  # Join release notes with new line character

            try:
                print("=============================================================================")
                print(f"Processing repository: {repo_name}")

                repo = g.get_repo(repo_name)
                if tag_exists(repo, tag):
                    print(f"Tag {tag} already exists in {repo_name}. Skipping processing.")
                    continue

                # Clone the repository and checkout the xyz branch
                repo_dir = repo_name.split('/')[-1]
                run_command(f'git clone https://{token}:x-oauth-basic@github.com/{repo_name}.git')
                os.chdir(repo_dir)
                print(f"Cloned repository {repo_name} and switched to directory {repo_dir}")
                run_command('git fetch origin xyz:xyz')
                run_command('git checkout xyz')
                print("Checked out xyz branch")

                # Create or update release_notes.txt with the release notes
                with open('release_notes.txt', 'w') as file:
                    file.write(release_notes_str)
                print("release_notes.txt file generated successfully")

                # Verify the release_notes.txt file content
                with open('release_notes.txt', 'r') as file:
                    content = file.read()
                    print(f"release_notes.txt content:\n{content}")

                if deployment_path:
                    # Update the deployment.yaml file with the new tag
                    with open(deployment_path, 'r') as file:
                        deployment_data = yaml.safe_load(file)

                    # Find and update the image tag in the containers section
                    for container in deployment_data['spec']['template']['spec']['containers']:
                        if 'image' in container:
                            container['image'] = f"{container['image'].split(':')[0]}:{tag}"

                    with open(deployment_path, 'w') as file:
                        yaml.safe_dump(deployment_data, file)
                    print(f"{deployment_path} file updated successfully")

                # Commit and push the changes if there are any
                if has_changes():
                    run_command('git config --global user.name "github-actions"')
                    run_command('git config --global user.email "github-actions@github.com"')
                    run_command('git add .')
                    commit_message = f"Add release notes and update deployment.yaml with tag {tag}"
                    if not deployment_path:
                        commit_message = f"Add release notes with tag {tag}"
                    run_command(f'git commit -m "{commit_message}"')
                    print("Committed changes to git")
                    run_command('git push origin xyz')
                    print("Pushed changes to xyz branch")
                else:
                    print("No changes to commit")

                # Go back to the root directory
                os.chdir('..')
                run_command(f'rm -rf {repo_dir}')
                print(f"Cleaned up local repository {repo_dir}")

                if deployment_path:
                    print(f"Updated {repo_name} with tag {tag} in deployment.yaml and pushed to xyz branch with release notes.")
                print("release_notes.txt file uploaded successfully")

            except Exception as e:
                print(f"Error accessing repository {repo_name}: {e}")

if __name__ == "__main__":
    main()