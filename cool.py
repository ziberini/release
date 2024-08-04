import os
import yaml
import subprocess
import sys
from github import Github

# Load the YAML configuration file
def load_config(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

# Function to run a shell command
def run_command(command):
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"\033[31mError running command: {command}\n{result.stderr}\033[0m")
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

# Function to update the image tag in the deployment.yaml file
def update_deployment_image(deployment_path, tag):
    try:
        with open(deployment_path, 'r') as file:
            deployment_data = yaml.safe_load(file)
        
        updated = False
        if 'spec' in deployment_data and 'template' in deployment_data['spec'] and 'spec' in deployment_data['spec']['template'] and 'containers' in deployment_data['spec']['template']['spec']:
            for container in deployment_data['spec']['template']['spec']['containers']:
                if 'image' in container:
                    container['image'] = f"{container['image'].split(':')[0]}:{tag}"
                    updated = True
        
        if updated:
            with open(deployment_path, 'w') as file:
                yaml.safe_dump(deployment_data, file)
            return True
        else:
            print(f"\033[31mError: The deployment.yaml structure is not as expected or file not found: {deployment_path}\033[0m")
            return False
    except Exception as e:
        print(f"\033[31mError updating deployment image: {e}\033[0m")
        return False

# Main function
def main():
    try:
        config = load_config('repos.yaml')

        # Authenticate with GitHub using a personal access token
        token = os.getenv('GITHUB_TOKEN')
        if not token:
            print("\033[31mGITHUB_TOKEN environment variable is not set.\033[0m")
            sys.exit(1)

        # Using an access token
        g = Github(token)

        for repo_info in config['repositories']:
            if repo_info['enabled']:
                repo_name = repo_info['name']
                tag = repo_info['tag']
                deployment_path = repo_info.get('deployment_path', '')
                release_notes = repo_info['release_notes']
                release_notes_str = "\n".join([f"- {note}" for note in release_notes])  # Join release notes with new line character

                try:
                    print("\033[38;5;226m=================================================================================\033[0m")
                    print(f"\033[38;5;226mProcessing repository: {repo_name}\033[0m")

                    repo = g.get_repo(repo_name)
                    if tag_exists(repo, tag):
                        print(f"\033[32mTag {tag} already exists in {repo_name}. Skipping...\033[0m")
                        continue

                    # Clone the repository and checkout the xyz branch
                    repo_dir = repo_name.split('/')[-1]
                    run_command(f'echo "Tag 1.0.20-cool does not exist in ${repo_name} repo. Proceeding..."')
                    run_command(f'git clone https://{token}:x-oauth-basic@github.com/{repo_name}.git')
                    os.chdir(repo_dir)
                    print(f"Cloned repository {repo_name} and switched to directory {repo_dir}")
                    run_command('git fetch origin xyz:xyz')
                    run_command('git checkout xyz')
                    print("Checked out xyz branch")

                    # Create or update release_info.txt with the tag and release notes
                    with open('release_info.txt', 'w') as file:
                        file.write(f"TAG: {tag}\n\nRELEASE NOTES:\n{release_notes_str}")
                    print("release_info.txt file generated successfully")

                    # Verify the release_info.txt file content
                    with open('release_info.txt', 'r') as file:
                        content = file.read()
                        print(f"release_info.txt content:\n{content}")

                    if deployment_path:
                        # Update the deployment.yaml file with the new tag
                        if not update_deployment_image(deployment_path, tag):
                            os.chdir('..')
                            run_command(f'rm -rf {repo_dir}')
                            continue
                        print(f"\033[32m{deployment_path} file updated successfully\033[0m")

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
                        print("\033[32mPushed release changes to xyz branch.\033[0m")
                        print(f"\033[38;5;226mTo TAG and RELEASE '{repo_dir}' repository, merge 'xyz' into 'main' branch which will kick off its build and release pipeline.\033[0m")
                    else:
                        print(f"No changes to commit. Intended Changes are already in {repo_name} - xyz' branch.")

                    # Go back to the root directory
                    os.chdir('..')
                    run_command(f'rm -rf {repo_dir}')
                    print(f"Cleaned up local repository {repo_dir}")

                    if deployment_path:
                        print(f"Updated {repo_name} with new image tag for prod env and release notes")

                except Exception as e:
                    print(f"Error processing repository {repo_name}: {e}")
                    os.chdir('..')
                    run_command(f'rm -rf {repo_dir}')
                    raise

    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()