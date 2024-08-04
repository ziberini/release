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
YELLOW='\033[1;33'
RED='\033[31m'
NC='\033[0m'  # No Color

# Function to check if a tag exists in the repository
tag_exists() {
  local repo=$1
  local tag=$2
  echo -e "${YELLOW}Checking if tag $tag exists in repository $repo...${NC}"
  local tags=$(curl -s -H "Authorization: token $GITHUB_TOKEN" "https://api.github.com/repos/$repo/git/refs/tags")
  if echo "$tags" | grep -q "refs/tags/$tag"; then
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
      echo -e "${GREEN}Tag $tag already exists in $repo. Skipping...${NC}"
      continue
    fi

    # Clone the repository and checkout the xyz branch
    git clone "https://$GITHUB_TOKEN:x-oauth-basic@github.com/$repo.git" "${repo##*/}"
    cd "${repo##*/}"
    echo "Cloned repository $repo and switched to directory ${repo##*/}"
    git fetch origin xyz:xyz
    git checkout xyz
    echo "Checked out xyz branch"

    # Create or update release_info.txt with the tag and release notes
    echo -e "TAG: $tag\n\nRELEASE NOTES:\n$release_notes" > release_info.txt
    echo -e "${GREEN}release_info.txt file generated successfully${NC}"
    echo "release_info.txt content:"
    cat release_info.txt

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
      echo -e "${YELLOW}${repo} does not have a deployment file to update or deployment_path is null.${NC}"
    fi

    # Commit and push the changes if there are any
    if [ -n "$(git status --porcelain)" ]; then
      git config --global user.name "github-actions"
      git config --global user.email "github-actions@github.com"
      git add .
      commit_message="Add release notes and update deployment.yaml with tag $tag"
      if [ -z "$deployment_path" ] || [ "$deployment_path" == "null" ]; then
        commit_message="Add release_info.txt with tag $tag and release notes"
      fi
      git commit -m "$commit_message"
      echo "Committed changes to git"
      git push origin xyz
      echo "Pushed changes to xyz branch"
    else
      echo "No changes to commit"
    fi

    if [ -n "$deployment_path" ] && [ "$deployment_path" != "null" ]; then
      echo "Updated $repo with new image tag and release notes"
    else
      echo -e "${GREEN}release_info.txt file created for $repo with tag $tag and release notes.${NC}"
    fi

    # Go back to the root directory
    cd ..
    rm -rf "${repo##*/}"
    echo -e "Cleaned up local repository ${repo}"
  fi
done