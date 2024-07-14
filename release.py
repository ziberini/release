import yaml
from github import Github
import os
import warnings

# Suppress specific warnings globally
from urllib3.exceptions import NotOpenSSLWarning
warnings.filterwarnings('ignore', category=NotOpenSSLWarning)

# Load the YAML configuration file
def load_config(file_path):
    with open(file_path, 'r') as file:
        return yaml.safe_load(file)

# Create a git tag on GitHub
def create_git_tag(repo, tag):
    try:
        # Get the latest commit SHA
        commits = repo.get_commits()
        latest_commit_sha = commits[0].sha

        # Create the tag object
        tag_object = repo.create_git_tag(
            tag=tag,
            message=f"Tag {tag}",
            object=latest_commit_sha,
            type="commit"
        )

        # Create the reference for the tag
        ref = repo.create_git_ref(
            ref=f"refs/tags/{tag}",
            sha=tag_object.sha
        )

        print(f"Tag {tag} created for {repo.name}")
    except Exception as e:
        print(f"Failed to create tag for {repo.name}: {e}")

# Create a release on GitHub
def create_release(repo, tag, release_name, release_notes):
    try:
        release_message = "\n".join(f"- {note}" for note in release_notes)
        release = repo.create_git_release(
            tag=tag,
            name=release_name,
            message=release_message,
            draft=False,
            prerelease=False
        )
        print(f"Release {release_name} created for {repo.name} with tag {tag}")
    except Exception as e:
        print(f"Failed to create release for {repo.name}: {e}")

# Main function
def main():
    config = load_config('repos.yaml')

    # Authenticate with GitHub using a personal access token
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        raise ValueError("GITHUB_TOKEN environment variable is not set")
    
    g = Github(token)

    for repo_info in config['repositories']:
        if repo_info['enabled']:
            repo_name = repo_info['name']
            release_notes = repo_info['release_notes']
            tag = repo_info['tag']
            try:
                repo = g.get_repo(repo_name)
                # Check if release with the specified tag already exists
                releases = repo.get_releases()
                if any(release.tag_name == tag for release in releases):
                    print(f"Release with tag {tag} already exists for {repo_name}. Skipping...")
                    continue

                # Create the git tag
                create_git_tag(repo, tag)
                
                # Create the release with the specified tag
                create_release(repo, tag, tag, release_notes)
            except Exception as e:
                if "404" in str(e):
                    print(f"Repository {repo_name} not found. Please check the repository name and your permissions.")
                else:
                    print(f"Error accessing repository {repo_name}: {e}")

if __name__ == "__main__":
    main()