#!/bin/bash

set -e

# Load GitHub token from environment variable
GITHUB_TOKEN=${GITHUB_TOKEN}
if [ -z "$GITHUB_TOKEN" ]; then
  echo -e "\033[31mGITHUB_TOKEN environment variable is not set.\033[0m"  # Red color for errors
  exit 1
fi

# Define color codess
GREEN='\033[32m'
YELLOW='\033[0;33m'
RED='\033[31m'
NC='\033[0m'  # No Color

# Function to check if a tag exists in the repository
tag_exists() {
  local repo=$1
  local tag=$2
  if git ls-remote --tags "https://$GITHUB_TOKEN:x-oauth-basic@github.com/$repo.git" | grep -q "refs/tags/$tag"; then
    return 0
  else
    return 1
  fi
}

# Function to update the image tag in the deployment.yaml file
update_deployment_image() {
  local deployment_path=$1
  local tag=$2
  if [ -f "$deployment_path" ]; then
    sed -i "s|\(image: .*:\).*|\1$tag|g" "$deployment_path"
    return 0
  else
    echo -e "${RED}Error: The deployment.yaml structure is not as expected or file not found: $deployment_path${NC}"
    return 1
  fi
}

# Read YAML file
if [ ! -f repos.yaml ]; then
  echo -e "${RED}repos.yaml file not found.${NC}"
  exit 1
fi

repositories=$(yq e '.repositories' repos.yaml)

# Get the length of the repositories array
repo_length=$(echo "$repositories" | yq e 'length' -)

# Iterate over repositories
for index in $(seq 0 $(($repo_length - 1))); do
  enabled=$(echo "$repositories" | yq e ".[$index].enabled" -)
  
  if [ "$enabled" == "true" ]; then
    repo=$(echo "$repositories" | yq e ".[$index].name" -)
    release_notes=$(echo "$repositories" | yq e -o=json ".[$index].release_notes" - | jq -r '.[]' | sed 's/^/- /')
    tag=$(echo "$repositories" | yq e ".[$index].tag" -)
    deployment_path=$(echo "$repositories" | yq e ".[$index].deployment_path" -)

    echo -e "${YELLOW}=================================================================================${NC}"
    echo -e "${YELLOW}Processing repository: $repo${NC}"

    if tag_exists "$repo" "$tag"; then
      echo -e "Tag $tag already exists in $repo. Skipping..."
      continue
    fi

    # Clone the repository and checkout the xyz branch
    git clone "https://$GITHUB_TOKEN:x-oauth-basic@github.com/$repo.git" "${repo##*/}"
    cd "${repo##*/}"
    echo "Cloned repository $repo and switched to directory ${repo##*/}"
    git fetch origin xyz:xyz
    git checkout xyz
    echo "checked out xyz branch"

    # Create or update release_notes.txt with the release notes
    echo -e "$release_notes" > release_notes.txt
    echo -e "${GREEN}release_notes.txt file generated successfully${NC}"
    echo "release_notes.txt content:"
    cat release_notes.txt

    # Update the deployment.yaml file with the new tag if deployment_path is specified
    if [ -n "$deployment_path" ] && [ "$deployment_path" != "null" ]; then
      # Update the deployment.yaml file with the new tag
      if update_deployment_image "$deployment_path" "$tag"; then
        echo -e "${GREEN}$deployment_path file updated successfully${NC}"
      else
        cd ..
        rm -rf "${repo##*/}"
        continue
      fi
    else
      echo "${repo} does not have deployment file to update or deployment_path is null, skipping deployment update."
    fi

    # Commit and push the changes if there are any
    if [ -n "$(git status --porcelain)" ]; then
      git config --global user.name "github-actions"
      git config --global user.email "github-actions@github.com"
      git add .
      commit_message="Add release notes and update deployment.yaml with tag $tag"
      if [ -z "$deployment_path" ] || [ "$deployment_path" == "null" ]; then
        commit_message="Add release notes with tag $tag"
      fi
      git commit -m "$commit_message"
      echo "Committed changes to git"
      git push origin xyz
      echo "Pushed changes to xyz branch"
    else
      echo "No changes to commit"
    fi

    if [ -n "$deployment_path" ] && [ "$deployment_path" != "null" ]; then
      echo "updated $repo to prep xyz branch for gh release."
    fi
    echo -e "${GREEN}release_notes.txt file uploaded successfully${NC}"

    # Go back to the root directory
    cd ..
    rm -rf "${repo##*/}"
    echo "Cleaned up local repository ${repo}"
  fi
done